from django.db.models import Q
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from django.db import transaction
from .models import Project, ProjectMember
from .serializers import ProjectSerializer, ProjectCreateSerializer, AddProjectMemberSerializer
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .permissions import IsProjectOwnerOrAdmin

User = get_user_model()

class ProjectViewSet(viewsets.ModelViewSet):
    """
    Повний CRUD для проєктів.
    GET /projects/ -> Список проєктів, де я учасник.
    POST /projects/ -> Створити новий.
    GET, PATCH, PUT /projects/{id}/ -> Деталі.
    """
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrAdmin]

    # 1. Підключаємо "двигуни" фільтрації
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # 2. По яких полях шукати (Search)
    # ?search=Super -> знайде в назві, ключі або описі
    search_fields = ['name', 'key', 'description']

    # 3. По яких полях можна сортувати (Ordering)
    # ?ordering=priority (від низького до високого)
    # ?ordering=-due_date (спочатку термінові)
    ordering_fields = ['name', 'priority', 'start_date', 'due_date']

    def get_queryset(self):
        """
        Логіка видимості проєктів.
        """
        user = self.request.user
        queryset = Project.objects.select_related('owner').prefetch_related('members')

        # 1. Логіка "Хто бачить?"
        if user.is_staff or user.is_superuser:
            # Адмін бачить ВСІ проєкти в системі
            pass
        else:
            # Використовуємо Q, щоб гарантувати доступ власнику,
            # навіть якщо він випадково зник з списку members.
            queryset = queryset.filter(
                Q(owner=user) | Q(members__user=user)
            ).distinct()

        # 2. Логіка "Архівовані" (фільтрація)
        # ВАЖЛИВА ЗМІНА: Ховаємо архів ТІЛЬКИ якщо це список (action == 'list').
        # Якщо ми запитуємо конкретний ID (retrieve/update) - показуємо завжди,
        # щоб можна було відновити проєкт.

        if self.action == 'list':  # <--- Додали цю перевірку
            show_archived = self.request.query_params.get('show_archived')
            if not show_archived:
                queryset = queryset.exclude(status='archived')

        return queryset

    def get_serializer_class(self):
        # Для створення використовуємо спрощений серіалізатор
        if self.action == 'create':
            return ProjectCreateSerializer
        return ProjectSerializer

    def perform_create(self, serializer):
        """
        Логіка створення проєкту:
        1. Зберегти проєкт.
        2. Автоматично додати автора як Project Owner у таблицю ProjectMember.
        """
        with transaction.atomic():  # Гарантує, що виконається або все, або нічого
            # 1. Створюємо проєкт
            project = serializer.save(owner=self.request.user)

            # 2. Додаємо запис у ProjectMember
            ProjectMember.objects.create(
                project=project,
                user=self.request.user,
                role=ProjectMember.ROLE_OWNER
            )

    def perform_destroy(self, instance):
        """
        Реалізація Soft Delete (М'яке видалення).
        Замість фізичного видалення з БД, ми змінюємо статус на ARCHIVED.
        """

        instance.status = instance.STATUS_ARCHIVED
        instance.save()

    @action(detail=True, methods=['post'], url_path='add_member')
    def add_member(self, request, pk=None):
        """
        Додавання учасника до проєкту за EMAIL.
        URL: POST /api/v1/projects/{id}/add_member/
        Body: { "email": "developer@example.com", "role": "member" }
        """
        project = self.get_object()  # 1. Перевірка прав (Permissions) спрацює тут

        # 2. Передаємо проєкт у контекст серіалізатора!
        serializer = AddProjectMemberSerializer(data=request.data, context={'project': project})

        # 3. Валідація (чи існує пошта? чи вже в команді?)
        if serializer.is_valid():
            # Якщо ми тут — значить все ідеально.
            # user вже знайдений всередині validate() і покладений в validated_data
            user = serializer.validated_data['user']
            role = serializer.validated_data['role']

            # 4. Створення запису
            ProjectMember.objects.create(
                project=project,
                user=user,
                role=role
            )

            return Response(
                {"message": f"Користувача {user.get_full_name()} додано."},
                status=status.HTTP_201_CREATED
            )

        # Якщо помилка (нема пошти або дублікат) — повертаємо помилки серіалізатора
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='remove_member/(?P<user_id>\d+)')
    def remove_member(self, request, pk=None, user_id=None):
        """
        Видалення учасника з проєкту.
        URL: DELETE /api/v1/projects/{id}/remove_member/{user_id}/
        """
        project = self.get_object()

        # 1. Не можна видалити самого себе (власника)
        if int(user_id) == project.owner.id:
            return Response({"error": "Власник не може видалити себе з проєкту."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Шукаємо і видаляємо запис у ProjectMember
        member_record = get_object_or_404(ProjectMember, project=project, user_id=user_id)

        # Очищення задач (Unassign tasks) ---
        from tasks.models import Task  # Імпорт всередині, щоб уникнути циркулярних помилок

        # Знаходимо всі задачі цього юзера В ЦЬОМУ проєкті, які ще не зроблені
        user_tasks = Task.objects.filter(
            project=project,
            assignee_id=user_id
        ).exclude(status=Task.STATUS_DONE)

        # Очищаємо поле assignee
        updated_count = user_tasks.update(assignee=None)
        # ----------------------------------------------------

        # 3. Видаляємо учасника
        member_record.delete()

        return Response(
            {"message": f"Користувача видалено. {updated_count} задач тепер без виконавця."},
            status=status.HTTP_200_OK
        )

