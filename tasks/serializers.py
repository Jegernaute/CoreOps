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
        1. Перевіряємо, чи має право АВТОР ЗАПИТУ створювати задачі в цьому проєкті.
        2. Перевіряємо, чи є ASSIGNEE (Виконавець) учасником цього проєкту.
        """
        request = self.context.get('request')
        current_user = request.user

        # Визначаємо проєкт (з вхідних даних або з існуючого об'єкта)
        project = data.get('project')
        if not project and self.instance:
            project = self.instance.project

        # --- ПЕРЕВІРКА 1: Чи "свій" той, хто створює задачу? ---
        if project:
            # Перевіряємо, чи є поточний юзер в таблиці учасників або власником
            is_member = ProjectMember.objects.filter(project=project, user=current_user).exists()
            # Додаткова страховка: власник завжди має доступ, навіть якщо випадково випав з Member
            is_owner = project.owner == current_user

            if not (is_member or is_owner):
                raise serializers.ValidationError(
                    {"project": "Ви не можете створювати задачі в проєкті, учасником якого ви не є."}
                )

        # --- ПЕРЕВІРКА 2: Чи "свій" той, на кого вішають задачу? ---
        assignee = data.get('assignee')
        if assignee and project:
            is_assignee_member = ProjectMember.objects.filter(project=project, user=assignee).exists()
            if not is_assignee_member:
                raise serializers.ValidationError(
                    {"assignee": f"Користувач {assignee.email} не є учасником проєкту '{project.name}'."}
                )

        return data