from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db import transaction
from .models import Project, ProjectMember
from .serializers import ProjectSerializer, ProjectCreateSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    """
    Повний CRUD для проєктів.
    GET /projects/ -> Список проєктів, де я учасник.
    POST /projects/ -> Створити новий.
    GET /projects/{id}/ -> Деталі.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Повертаємо тільки ті проєкти, де користувач є учасником
        user = self.request.user
        return Project.objects.filter(members__user=user).distinct()

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