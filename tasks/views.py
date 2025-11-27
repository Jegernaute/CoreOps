from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Task, TaskComment, TaskResource
from .serializers import TaskSerializer, TaskCommentSerializer, TaskResourceSerializer

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