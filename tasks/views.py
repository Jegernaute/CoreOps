from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Task, TaskComment, TaskResource
from .serializers import TaskSerializer, TaskCommentSerializer, TaskResourceSerializer
from rest_framework.exceptions import PermissionDenied, ValidationError

class TaskViewSet(viewsets.ModelViewSet):
    """
    CRUD для задач.
    GET /tasks/ -> Всі задачі (з моїх проєктів).
    POST /tasks/ -> Створити.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Показуємо тільки задачі з проєктів, де користувач є учасником
        user = self.request.user
        return Task.objects.filter(project__members__user=user).select_related(
            'project', 'assignee', 'reporter'
        ).distinct()

    def perform_create(self, serializer):
        # Автоматично ставимо поточного юзера як Автора (Reporter)
        serializer.save(reporter=self.request.user)

    # --- Додатковий метод для додавання коментарів ---
    # POST /tasks/{id}/add_comment/
    @action(detail=True, methods=['post'], serializer_class=TaskCommentSerializer)
    def add_comment(self, request, pk=None):
        task = self.get_object()
        serializer = TaskCommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user, task=task)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # --- Додатковий метод для завантаження файлів ---
    # POST /tasks/{id}/upload_resource/
    @action(detail=True, methods=['post'], serializer_class=TaskResourceSerializer)
    def upload_resource(self, request, pk=None):
        task = self.get_object()
        serializer = TaskResourceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(uploaded_by=request.user, task=task)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

        # --- 1. ПЕРЕВІРКА ЦІЛІСНОСТІ (History Protection) ---
        # Якщо статус 'done', видаляти не можна нікому.
        if instance.status == Task.STATUS_DONE:
            raise ValidationError(
                {"error": "Неможливо видалити завершену задачу. Це порушить історію проєкту."}
            )

        # --- 2. ЛОГІКА ВЛАСНИКА (Super Access) ---
        # Власник проєкту може видалити задачу в будь-якому статусі (крім Done)
        if is_owner:
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