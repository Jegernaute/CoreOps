from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db import transaction
from .models import Project, ProjectMember
from .serializers import ProjectSerializer, ProjectCreateSerializer
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

User = get_user_model()

class ProjectViewSet(viewsets.ModelViewSet):
    """
    Повний CRUD для проєктів.
    GET /projects/ -> Список проєктів, де я учасник.
    POST /projects/ -> Створити новий.
    GET, PATCH, PUT /projects/{id}/ -> Деталі.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Повертаємо тільки ті проєкти, де користувач є учасником
        user = self.request.user
        queryset = Project.objects.filter(members__user=user).distinct()
        # Фільтрація: Якщо фронтенд не просить конкретно archived, показуємо тільки активні
        # Приклад запиту: /projects/?show_archived=true
        show_archived = self.request.query_params.get('show_archived')

        if not show_archived:
            # Виключаємо архівовані (показуємо Active, On Hold, Completed)
            queryset = queryset.exclude(status=Project.STATUS_ARCHIVED)

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
        # Перевірка: тільки власник може архівувати
        if instance.owner != self.request.user:
            raise PermissionDenied("Тільки власник може архівувати проєкт.")

        instance.status = instance.STATUS_ARCHIVED
        instance.save()

    @action(detail=True, methods=['delete'], url_path='remove_member/(?P<user_id>\d+)')
    def remove_member(self, request, pk=None, user_id=None):
        """
        Видалення учасника з проєкту.
        URL: DELETE /api/v1/projects/{id}/remove_member/{user_id}/
        """
        project = self.get_object()

        # 1. Перевірка прав: тільки Owner може видаляти людей
        if project.owner != request.user:
            return Response({"error": "Тільки власник може керувати командою."}, status=status.HTTP_403_FORBIDDEN)

        # 2. Не можна видалити самого себе (власника)
        if int(user_id) == project.owner.id:
            return Response({"error": "Власник не може видалити себе з проєкту."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Шукаємо і видаляємо запис у ProjectMember
        member_record = get_object_or_404(ProjectMember, project=project, user_id=user_id)

        # Очищення задач (Unassign tasks) ---
        from tasks.models import Task  # Імпорт всередині, щоб уникнути циркулярних помилок

        # Знаходимо всі задачі цього юзера В ЦЬОМУ проєкті, які ще не зроблені
        user_tasks = Task.objects.filter(
            project=project,
            assignee_id=user_id
        ).exclude(status='done')  # (Опціонально: закриті задачі можна залишити "для історії", або теж очистити)

        # Очищаємо поле assignee
        updated_count = user_tasks.update(assignee=None)
        # ----------------------------------------------------

        # 3. Видаляємо учасника
        member_record.delete()

        return Response(
            {"message": f"Користувача видалено. {updated_count} задач тепер без виконавця."},
            status=status.HTTP_200_OK
        )