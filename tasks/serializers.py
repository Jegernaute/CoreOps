from rest_framework import serializers
from .models import Task, TaskResource, TaskComment
from projects.models import ProjectMember


# --- Допоміжні серіалізатори ---
class TaskResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResource
        fields = ['id', 'name', 'resource_type', 'file', 'url', 'created_at']
        read_only_fields = ['uploaded_by']


class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.get_full_name')
    author_avatar = serializers.ImageField(source='author.avatar', read_only=True)

    class Meta:
        model = TaskComment
        fields = ['id', 'author', 'author_name', 'author_avatar', 'content', 'created_at']
        read_only_fields = ['author', 'created_at']


# --- Головний серіалізатор Задачі ---
class TaskSerializer(serializers.ModelSerializer):
    # Виводимо імена, щоб на фронті не показувати просто ID
    assignee_name = serializers.ReadOnlyField(source='assignee.get_full_name')
    reporter_name = serializers.ReadOnlyField(source='reporter.get_full_name')
    project_name = serializers.ReadOnlyField(source='project.name')

    # Вкладені дані (коментарі та файли) - тільки для читання
    resources = TaskResourceSerializer(many=True, read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'project', 'project_name',
            'title', 'description', 'task_type',
            'status', 'priority',
            'assignee', 'assignee_name',
            'reporter', 'reporter_name',
            'milestone',
            'estimated_hours', 'due_date',
            'resources', 'comments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['reporter', 'created_at', 'updated_at']

    def validate(self, data):
        """
        БІЗНЕС-ЛОГІКА:
        Перевіряємо, чи є Assignee (Виконавець) учасником цього проєкту.
        """
        user = data.get('assignee')
        project = data.get('project')

        # Якщо ми оновлюємо задачу (PATCH), project може не прийти, беремо з існуючого
        if not project and self.instance:
            project = self.instance.project

        # Якщо вказано виконавця, перевіряємо його членство
        if user and project:
            is_member = ProjectMember.objects.filter(project=project, user=user).exists()
            if not is_member:
                raise serializers.ValidationError(
                    {"assignee": f"Користувач {user.email} не є учасником проєкту '{project.name}'."}
                )

        return data