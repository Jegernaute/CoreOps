from rest_framework import viewsets, permissions
from .models import Sprint
from .serializers import SprintSerializer


class SprintViewSet(viewsets.ModelViewSet):
    """
    CRUD для спринтів.
    GET /planning/ -> Список спринтів (моїх проєктів).
    POST /planning/ -> Створити спринт.
    """
    serializer_class = SprintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Показуємо тільки спринти з проєктів, де користувач є учасником.
        Також додаємо можливість фільтрації по ID проєкту.
        Приклад: /api/v1/planning/?project=1
        """
        user = self.request.user

        # 1. Базова фільтрація: тільки мої проєкти
        queryset = Sprint.objects.filter(project__members__user=user).distinct()

        # 2. Додаткова фільтрація: якщо в URL передали ?project=5
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        return queryset