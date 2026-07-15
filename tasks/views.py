import django_filters
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Task, TaskComment, TaskResource
from .serializers import TaskListSerializer, TaskDetailSerializer, TaskCommentSerializer, TaskResourceSerializer
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from .permissions import IsAuthorOrProjectOwnerOrAdmin
from Core.pagination import CoreCursorPagination

# --- ДОДАНО КЛАС ФІЛЬТРАЦІЇ ---
class TaskFilter(django_filters.FilterSet):
    """
    Кастомний фільтр для підтримки діапазонів дат.
    """
    due_date_after = django_filters.DateTimeFilter(field_name='due_date', lookup_expr='gte')
    due_date_before = django_filters.DateTimeFilter(field_name='due_date', lookup_expr='lte')
    # Додано фільтрацію за конкретною датою без урахування часу
    due_date = django_filters.DateFilter(field_name='due_date', lookup_expr='date')

    class Meta:
        model = Task
        fields = ['project', 'status', 'priority', 'assignee', 'reporter', 'task_type']


class TaskViewSet(viewsets.ModelViewSet):
    """
    CRUD для задач.
    GET /tasks/ -> Всі задачі (з моїх проєктів).
    POST /tasks/ -> Створити.
    """

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CoreCursorPagination

    # --- ПІДКЛЮЧАЄ ФІЛЬТРИ ---
    filter_backends = [
        DjangoFilterBackend,  # <--- Дозволяє фільтрувати по полях (?status=done)
        filters.SearchFilter,  # <--- Дозволяє шукати текстом (?search=bug)
        filters.OrderingFilter  # <--- Дозволяє сортувати (?ordering=-created_at)
    ]

    # 1. Пошук (Search)
    search_fields = ['title', 'description']

    # 2. Сортування (Ordering)
    ordering_fields = ['priority', 'due_date', 'created_at']

    # 3. Фільтрація по полях (Filtering)
    # Це додасть можливість писати: ?project=1&status=to_do&priority=high
    #  Підключено кастомний клас фільтрів замість filterset_fields
    filterset_class = TaskFilter

    def get_serializer_class(self):
        """
        Динамічний вибір серіалізатора для оптимізації Payload.
        """
        if self.action == 'list':
            return TaskListSerializer

        # Для action = 'retrieve' (GET /tasks/{id}/), 'create', 'update', 'partial_update'
        return TaskDetailSerializer

    def get_queryset(self):
        # Показує тільки задачі з проєктів де користувач є учасником.
        # Адмін бачить все.
        user = self.request.user
        qs = Task.objects.select_related('project', 'assignee', 'reporter')

        if not (user.is_staff or user.is_superuser):
            qs = qs.filter(project__members__user=user).distinct()

        # Анотує кількість коментарів та вкладень на рівні БД (1 SQL запит)
        qs = qs.annotate(
            comments_count=Count('comments', distinct=True),
            resources_count=Count('resources', distinct=True)
        )
        return qs

    def perform_create(self, serializer):
        # Автоматично ставить  поточного юзера як Автора (Reporter)
        serializer.save(reporter=self.request.user)

    def perform_destroy(self, instance):
        """
        Розумне видалення (Smart Delete):
        1. Ніхто не видаляє 'Done' (Історія).
        2. Project Owner може видаляти будь-які активні задачі.
        3. Reporter (Автор) може видалити задачу, ТІЛЬКИ якщо вона ще в 'to_do'.
        """
        user = self.request.user
        project_owner = instance.project.owner

        # Визначає ролі
        is_reporter = instance.reporter == user
        is_owner = user == project_owner
        is_admin = user.is_staff or user.is_superuser

        # --- 1. ПЕРЕВІРКА ЦІЛІСНОСТІ (History Protection) ---
        # Якщо статус 'done' видаляти не можна нікому.
        if instance.status == Task.STATUS_DONE:
            raise PermissionDenied(
                "Заборонено видаляти завершену задачу. Це порушує цілісність історії."
            )

        # --- 2. ЛОГІКА ВЛАСНИКА (Super Access) ---
        # Власник проєкту може видалити задачу в будь-якому статусі (крім Done)
        if is_owner or is_admin:
            instance.delete()
            return

        # --- 3. ЛОГІКА АВТОРА (Mistake Correction) ---
        # Автор може виправити помилку тільки поки задача не пішла в роботу
        if is_reporter:
            if instance.status == Task.STATUS_TODO:
                instance.delete()
                return
            else:
                raise PermissionDenied(
                    "Ви не можете видалити цю задачу, бо робота над нею вже почалася (статус не 'To Do'). Зверніться до менеджера."
                )

        # --- 4. ВСІ ІНШІ ---
        raise PermissionDenied("У вас недостатньо прав для видалення цієї задачі.")


class TaskCommentViewSet(viewsets.ModelViewSet):
    """
    CRUD для коментарів задачі.
    GET /comments/?task=5 -> Отримати коментарі конкретної задачі.
    POST /comments/ -> Створити коментар.
    """
    serializer_class = TaskCommentSerializer
    # Підключає базову перевірку токена + кастомну логіку (Автор/Власник/Адмін)
    permission_classes = [permissions.IsAuthenticated, IsAuthorOrProjectOwnerOrAdmin]
    pagination_class = CoreCursorPagination

    # Підключення фільтрів
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task']  # Дозволяє фільтрувати по ID задачі
    ordering_fields = ['created_at']

    # Налаштування get_queryset (Безпека)
    def get_queryset(self):
        user = self.request.user

        # Адмін бачить всі коментарі
        if user.is_staff or user.is_superuser:
            return TaskComment.objects.all()

        # Звичайний юзер бачить тільки ті, де він учасник проєкту АБО власник проєкту
        return TaskComment.objects.filter(
            Q(task__project__members__user=user) | Q(task__project__owner=user)
        ).distinct()

    # Налаштування perform_create
    def perform_create(self, serializer):
        user = self.request.user
        task = serializer.validated_data['task']

        # Перевірка: чи має цей юзер доступ до цієї задачі?
        if not (user.is_staff or user.is_superuser):
            is_member = task.project.members.filter(user=user).exists()
            is_owner = task.project.owner == user
            if not (is_member or is_owner):
                raise PermissionDenied("Ви не можете коментувати задачу з проєкту, до якого не маєте доступу.")

        # Зберігає коментар, примусово встановлюючи автора (захист від підробки)
        serializer.save(author=user)


class TaskResourceViewSet(viewsets.ModelViewSet):
    """
    CRUD для файлів/ресурсів задачі.
    GET /resources/?task=5 -> Отримати файли конкретної задачі.
    POST /resources/ -> Завантажити файл.
    """
    serializer_class = TaskResourceSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthorOrProjectOwnerOrAdmin]
    pagination_class = CoreCursorPagination

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task']
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return TaskResource.objects.all()

        return TaskResource.objects.filter(
            Q(task__project__members__user=user) | Q(task__project__owner=user)
        ).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        task = serializer.validated_data['task']

        # Перевірка доступу до задачі
        if not (user.is_staff or user.is_superuser):
            is_member = task.project.members.filter(user=user).exists()
            is_owner = task.project.owner == user
            if not (is_member or is_owner):
                raise PermissionDenied("Ви не можете завантажувати файли до задачі з чужого проєкту.")

        # Зберігає файл примусово встановлюючи того хто завантажив
        serializer.save(uploaded_by=user)