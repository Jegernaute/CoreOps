from rest_framework import serializers
from .models import Project, ProjectMember, ProjectResource, ProjectMilestone
from django.contrib.auth import get_user_model

User = get_user_model()

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
    # Виводить не просто ID юзера, а його Email та Ім'я для зручності
    user_email = serializers.ReadOnlyField(source='user.email')
    user_name = serializers.ReadOnlyField(source='user.get_full_name')

    class Meta:
        model = ProjectMember
        fields = ['id', 'user_id', 'user_email', 'user_name', 'role', 'joined_at']


class AddProjectMemberSerializer(serializers.Serializer):
    """
    Валідація даних для додавання учасника.
    Тепер перевіряє ВСЕ: і існування пошти, і дублікати.
    """
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=ProjectMember.ROLE_CHOICES)

    def validate_email(self, value):
        """1. Чи існує юзер?"""
        email = value.lower().strip()
        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError("Користувача з таким email не знайдено.")
        return email

    def validate(self, data):
        """2. Чи юзер вже в команді? (Cross-field validation)"""
        email = data['email']
        # Отримує проєкт з контексту (передасть його з View)
        project = self.context.get('project')

        user = User.objects.get(email=email)

        if project and ProjectMember.objects.filter(project=project, user=user).exists():
            raise serializers.ValidationError({"email": "Цей користувач вже є учасником проєкту."})

        # Додає об'єкт user в дані, щоб View не шукав його знову
        data['user'] = user
        return data

# --- Головний серіалізатор Проєкту ---

class ProjectSerializer(serializers.ModelSerializer):
    # Підключає вкладені списки (тільки для читання)
    members = ProjectMemberSerializer(many=True, read_only=True)
    resources = ProjectResourceSerializer(many=True, read_only=True)
    milestones = ProjectMilestoneSerializer(many=True, read_only=True)

    owner_email = serializers.ReadOnlyField(source='owner.email')

    activeTasksCount = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'key', 'name', 'description', 'owner', 'owner_email',
            'status', 'priority', 'start_date', 'end_date',
            'members', 'resources', 'milestones',
            'activeTasksCount', 'progress',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']

    def get_activeTasksCount(self, obj):
        # Якщо запит йде з get_queryset, де зроблено оптимізований annotate
        if hasattr(obj, 'active_tasks'):
            return obj.active_tasks
        # Фолбек (наприклад, при створенні проєкту POST-запитом)
        return obj.tasks.exclude(status='done').count()

    def get_progress(self, obj):
        # Перевіряє чи є оптимізовані дані з БД
        if hasattr(obj, 'total_tasks') and hasattr(obj, 'completed_tasks'):
            total = obj.total_tasks
            completed = obj.completed_tasks
        else:
            total = obj.tasks.count()
            completed = obj.tasks.filter(status='done').count()

        if total == 0:
            return 0.0
        return round(completed / total, 2)  # Повертає дробове значення 0.0 - 1.0

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