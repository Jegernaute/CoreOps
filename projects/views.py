import csv
from django.db.models import Q, Count
from rest_framework import viewsets, permissions, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from .models import Project, ProjectMember
from .serializers import ProjectSerializer, ProjectCreateSerializer, AddProjectMemberSerializer
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from .permissions import IsProjectOwnerOrAdmin
from Core.pagination import CoreCursorPagination

User = get_user_model()

class ProjectViewSet(viewsets.ModelViewSet):
    """
    Повний CRUD для проєктів.
    GET /projects/ -> Список проєктів, де я учасник.
    POST /projects/ -> Створити новий.
    GET, PATCH, PUT /projects/{id}/ -> Деталі.
    """
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrAdmin]
    pagination_class = CoreCursorPagination

    # 1. Підключає "двигуни" фільтрації
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

        # Існуючі оптимізації (Big O(1) SQL агрегація)
        queryset = Project.objects.select_related('owner').prefetch_related('members').annotate(
            total_tasks=Count('tasks', distinct=True),
            active_tasks=Count('tasks', filter=~Q(tasks__status='done'), distinct=True),
            completed_tasks=Count('tasks', filter=Q(tasks__status='done'), distinct=True)
        )

        # 1. Логіка "Хто бачить?"
        if user.is_staff or user.is_superuser:
            # Адмін бачить ВСІ проєкти в системі
            pass
        else:
            # Використовує Q, щоб гарантувати доступ власнику,
            # навіть якщо він випадково зник з списку members.
            queryset = queryset.filter(
                Q(owner=user) | Q(members__user=user)
            ).distinct()

        # 2. Логіка фільтрації списк
        # ВАЖЛИВА ЗМІНА: Ховає архів ТІЛЬКИ якщо це список (action == 'list').
        # Якщо запитує конкретний ID (retrieve/update) - показує завжди,
        # щоб можна було відновити проєкт.

        if self.action == 'list':
            show_archived = self.request.query_params.get('show_archived')
            if not show_archived:
                queryset = queryset.exclude(status=Project.STATUS_ARCHIVED)


            # Фільтр статусів (підтримка через кому: ?status=in_progress,backlog)
            statuses = self.request.query_params.get('status')
            if statuses:
                status_list = statuses.split(',')
                queryset = queryset.filter(status__in=status_list)

            # Фільтр активних задач (?has_active_tasks=true)
            has_active = self.request.query_params.get('has_active_tasks')
            if has_active:
                if has_active.lower() == 'true':
                    queryset = queryset.filter(active_tasks__gt=0)
                elif has_active.lower() == 'false':
                    queryset = queryset.filter(active_tasks=0)

            # Фільтр завершеності (?is_completed=true)
            is_completed = self.request.query_params.get('is_completed')
            if is_completed:
                from django.db.models import F
                completed_condition = Q(status=Project.STATUS_COMPLETED) | Q(total_tasks__gt=0,
                                                                             total_tasks=F('completed_tasks'))

                if is_completed.lower() == 'true':
                    queryset = queryset.filter(completed_condition)
                elif is_completed.lower() == 'false':
                    queryset = queryset.exclude(completed_condition)

        return queryset

    def get_serializer_class(self):
        # Для створення використовується спрощений серіалізатор
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
            # 1. Створює проєкт
            project = serializer.save(owner=self.request.user)

            # 2. Додає запис у ProjectMember
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

        # 2. Передає проєкт у контекст серіалізатора!
        serializer = AddProjectMemberSerializer(data=request.data, context={'project': project})

        # 3. Валідація (чи існує пошта? чи вже в команді?)
        if serializer.is_valid():
            # Якщо перевірка пройшла тут — значить все ідеально.
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

        # Якщо помилка (нема пошти або дублікат) — повертає помилки серіалізатора
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

        # 2. Шукає і видаляє запис у ProjectMember
        member_record = get_object_or_404(ProjectMember, project=project, user_id=user_id)

        # Очищення задач (Unassign tasks) ---
        from tasks.models import Task  # Імпорт всередині, щоб уникнути циркулярних помилок

        # Знаходить всі задачі цього юзера В ЦЬОМУ проєкті, які ще не зроблені
        user_tasks = Task.objects.filter(
            project=project,
            assignee_id=user_id
        ).exclude(status=Task.STATUS_DONE)

        # Очищає поле assignee
        updated_count = user_tasks.update(assignee=None)
        # ----------------------------------------------------

        # 3. Видаляє учасника
        member_record.delete()

        return Response(
            {"message": f"Користувача видалено. {updated_count} задач тепер без виконавця."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def export_tasks(self, request, pk=None):
        """
        Експорт задач проєкту у форматі CSV.
        Ендпоінт: GET /api/v1/projects/{id}/export_tasks/
        """
        project = self.get_object()  # Отримує поточний проєкт
        tasks = project.tasks.all()  # Дістає всі задачі

        # Створює HTTP-відповідь спеціально для файлу
        response = HttpResponse(content_type='text/csv')
        # Вказує браузеру/Postman, що це файл для завантаження, і задає ім'я
        response['Content-Disposition'] = f'attachment; filename="tasks_project_{project.id}.csv"'

        # Ініціалізує CSV-writer
        writer = csv.writer(response)

        # 1. Записує заголовки колонок (перший рядок)
        writer.writerow(['ID', 'Назва', 'Статус', 'Пріоритет', 'Виконавець', 'Створено'])

        # 2. Проходиться циклом по задачах і записує дані
        for task in tasks:
            writer.writerow([
                task.id,
                task.title,
                task.status,
                task.priority,
                task.assignee.email if task.assignee else 'Не призначено',
                task.created_at.strftime('%Y-%m-%d %H:%M')  # Форматує дату
            ])

        return response
