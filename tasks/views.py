from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Task, TaskComment, TaskResource
from .serializers import TaskSerializer, TaskCommentSerializer, TaskResourceSerializer
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .permissions import IsAuthorOrProjectOwnerOrAdmin
from Core.pagination import StandardResultsSetPagination

class TaskViewSet(viewsets.ModelViewSet):
    """
    CRUD для задач.
    GET /tasks/ -> Всі задачі (з моїх проєктів).
    POST /tasks/ -> Створити.
    """

    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    # --- ПІДКЛЮЧАЄМО ФІЛЬТРИ ---
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
    filterset_fields = ['project', 'status', 'priority', 'assignee', 'reporter', 'task_type']

    def get_queryset(self):
        # Показуємо тільки задачі з проєктів, де користувач є учасником.
        # Адмін бачить все.
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return Task.objects.all()

        return Task.objects.filter(project__members__user=user).select_related(
            'project', 'assignee', 'reporter'
        ).distinct()

    def perform_create(self, serializer):
        # Автоматично ставимо поточного юзера як Автора (Reporter)
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

        # Визначаємо ролі
        is_reporter = instance.reporter == user
        is_owner = user == project_owner
        is_admin = user.is_staff or user.is_superuser

        # --- 1. ПЕРЕВІРКА ЦІЛІСНОСТІ (History Protection) ---
        # Якщо статус 'done', видаляти не можна нікому.
        if instance.status == Task.STATUS_DONE:
            raise ValidationError(
                {"error": "Неможливо видалити завершену задачу. Це порушить історію проєкту."}
            )

        # --- 2. ЛОГІКА ВЛАСНИКА (Super Access) ---
        # Власник проєкту може видалити задачу в будь-якому статусі (крім Done)
        if is_owner or is_admin:
            instance.delete()
            return  # Успіх

        # --- 3. ЛОГІКА АВТОРА (Mistake Correction) ---
        # Автор може виправити помилку, тільки поки задача не пішла в роботу
        if is_reporter:
            if instance.status == Task.STATUS_TODO:
                instance.delete()
                return  # Успіх
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
    # Підключаємо базову перевірку токена + нашу кастомну логіку (Автор/Власник/Адмін)
    permission_classes = [permissions.IsAuthenticated, IsAuthorOrProjectOwnerOrAdmin]
    pagination_class = StandardResultsSetPagination

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

        # Зберігаємо коментар, примусово встановлюючи автора (захист від підробки)
        serializer.save(author=user)


class TaskResourceViewSet(viewsets.ModelViewSet):
    """
    CRUD для файлів/ресурсів задачі.
    GET /resources/?task=5 -> Отримати файли конкретної задачі.
    POST /resources/ -> Завантажити файл.
    """
    serializer_class = TaskResourceSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthorOrProjectOwnerOrAdmin]

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

        # Зберігаємо файл, примусово встановлюючи того, хто завантажив
        serializer.save(uploaded_by=user)