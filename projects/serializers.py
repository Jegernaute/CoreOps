from rest_framework import serializers
from .models import Project, ProjectMember, ProjectResource, ProjectMilestone


# --- Допоміжні серіалізатори (для вкладеності) ---

class ProjectResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectResource
        fields = ['id', 'name', 'resource_type', 'url', 'file', 'created_at']


class ProjectMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMilestone
        fields = ['id', 'name', 'deadline', 'is_completed']


class ProjectMemberSerializer(serializers.ModelSerializer):
    # Виводимо не просто ID юзера, а його Email та Ім'я для зручності
    user_email = serializers.ReadOnlyField(source='user.email')
    user_name = serializers.ReadOnlyField(source='user.get_full_name')

    class Meta:
        model = ProjectMember
        fields = ['id', 'user_id', 'user_email', 'user_name', 'role', 'joined_at']


# --- Головний серіалізатор Проєкту ---

class ProjectSerializer(serializers.ModelSerializer):
    # Підключаємо вкладені списки (тільки для читання)
    members = ProjectMemberSerializer(many=True, read_only=True)
    resources = ProjectResourceSerializer(many=True, read_only=True)
    milestones = ProjectMilestoneSerializer(many=True, read_only=True)

    owner_email = serializers.ReadOnlyField(source='owner.email')

    class Meta:
        model = Project
        fields = [
            'id', 'key', 'name', 'description', 'owner', 'owner_email',
            'status', 'priority', 'start_date', 'end_date',
            'members', 'resources', 'milestones',  # <--- Вкладені дані
            'created_at', 'updated_at'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']


class ProjectCreateSerializer(serializers.ModelSerializer):
    """
    Окремий серіалізатор для створення, щоб не вимагати зайвих полів.
    """

    class Meta:
        model = Project
        fields = [
            'key', 'name', 'description',
            'start_date', 'end_date', 'priority'
        ]