from rest_framework import viewsets, permissions
from .models import Sprint
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from tasks.models import Task
from .serializers import SprintSerializer, SprintCompleteSerializer
from rest_framework.exceptions import PermissionDenied
from projects.permissions import IsProjectOwnerOrAdmin
from Core.pagination import StandardResultsSetPagination
class SprintViewSet(viewsets.ModelViewSet):
    """
    CRUD для спринтів.
    GET /planning/ -> Список спринтів (моїх проєктів).
    POST /planning/ -> Створити спринт.
    """
    queryset = Sprint.objects.all()
    serializer_class = SprintSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrAdmin]
    pagination_class = StandardResultsSetPagination

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

    # Захист створення: Тільки власник проєкту може планувати нові спринти
    def perform_create(self, serializer):
        user = self.request.user
        project = serializer.validated_data['project']

        # Перевіряємо, чи юзер є адміном або власником цього конкретного проєкту
        if not (user.is_staff or user.is_superuser or project.owner == user):
            raise PermissionDenied("Тільки Власник проєкту може планувати нові спринти.")

        serializer.save()

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Екшен для старту спринту.
        POST /api/v1/planning/{id}/start/
        """
        sprint = self.get_object()

        # 1. Базова перевірка статусу
        if sprint.status != 'planned':
            return Response(
                {"detail": "Можна розпочати лише запланований спринт."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Перевірка бізнес-правила Scrum (один активний спринт на проєкт)
        has_active_sprint = Sprint.objects.filter(project=sprint.project, status='active').exists()
        if has_active_sprint:
            return Response(
                {"detail": "У цьому проєкті вже є активний спринт. Завершіть його перед початком нового."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Успішний старт
        sprint.status = 'active'
        sprint.save()
        return Response({"detail": "Спринт успішно розпочато."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Екшен для завершення спринту.
        POST /api/v1/planning/{id}/complete/
        """
        sprint = self.get_object()

        if sprint.status != 'active':
            return Response(
                {"detail": "Завершити можна лише активний спринт."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Валідуємо вхідні дані (чи передали move_to_sprint_id)
        serializer = SprintCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        move_to_sprint_id = serializer.validated_data.get('move_to_sprint_id')

        # Перевірка безпеки: чи належить новий спринт (якщо він є) до ТОГО Ж проєкту?
        next_sprint = None
        if move_to_sprint_id:
            try:
                next_sprint = Sprint.objects.get(id=move_to_sprint_id, project=sprint.project)
            except Sprint.DoesNotExist:
                return Response(
                    {"detail": "Спринт для перенесення не знайдено або він належить іншому проєкту."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Транзакція гарантує, що задачі та статус спринту оновляться СИНХРОННО
        with transaction.atomic():
            # 1. Завершуємо поточний спринт і ставимо реальну дату
            sprint.status = 'completed'
            sprint.actual_end_date = timezone.now().date()
            sprint.save()

            # 2. Знаходимо всі НЕвиконані задачі (статус НЕ 'done')
            unfinished_tasks = Task.objects.filter(sprint=sprint).exclude(status='done')

            # 3. Переносимо задачі масовим оновленням (bulk update - працює дуже швидко)
            if next_sprint:
                unfinished_tasks.update(sprint=next_sprint)
            else:
                unfinished_tasks.update(sprint=None)  # Відправляємо в Backlog

        action_msg = "задачі перенесено у новий спринт." if next_sprint else "задачі повернуто у Backlog."
        return Response({"detail": f"Спринт успішно завершено, {action_msg}"}, status=status.HTTP_200_OK)