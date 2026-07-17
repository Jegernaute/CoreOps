import os
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Task, TaskResource, TaskComment, TaskChecklistItem, TaskHistoryEvent
from projects.models import ProjectMember

User = get_user_model()


# --- допоміжний серіалізатор для користувачів ---
class UserMiniSerializer(serializers.ModelSerializer):
    """
    Міні-серіалізатор для вкладення об'єктів людей (Автора, Виконавця).
    """
    name = serializers.ReadOnlyField(source='get_full_name')

    class Meta:
        model = User
        fields = ['id', 'name', 'avatar']


# --- Допоміжні серіалізатори ---
class TaskResourceSerializer(serializers.ModelSerializer):
    # Додано поля для метаданих файлів
    file_size = serializers.SerializerMethodField()
    file_extension = serializers.SerializerMethodField()

    class Meta:
        model = TaskResource
        fields = ['id', 'task', 'comment', 'name', 'resource_type', 'file', 'url', 'file_size', 'file_extension', 'uploaded_by', 'created_at']
        read_only_fields = ['uploaded_by', 'created_at']

    def get_file_size(self, obj):
        if obj.file and hasattr(obj.file, 'size'):
            return obj.file.size
        return None

    def get_file_extension(self, obj):
        if obj.file and hasattr(obj.file, 'name'):
            return os.path.splitext(obj.file.name)[1].lower()
        return None


class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.get_full_name')
    author_avatar = serializers.ImageField(source='author.avatar', read_only=True)

    attachments = TaskResourceSerializer(many=True, read_only=True)

    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'author', 'author_name', 'author_avatar', 'content', 'attachments', 'created_at']
        read_only_fields = ['author', 'created_at']


class TaskChecklistItemSerializer(serializers.ModelSerializer):
    """
    Серіалізатор для пунктів чекліста.
    """

    class Meta:
        model = TaskChecklistItem
        fields = ['id', 'task', 'content', 'is_completed']


class TaskHistoryEventSerializer(serializers.ModelSerializer):
    """
    Серіалізатор для історії подій (Audit Log).
    """
    actor = UserMiniSerializer(read_only=True)

    class Meta:
        model = TaskHistoryEvent
        fields = ['id', 'actor', 'action_type', 'changes', 'timestamp']


class TaskListSerializer(serializers.ModelSerializer):
    """
    Легкий серіалізатор для списку задач.
    Віддає лічильники замість вкладених масивів.
    """
    task_key = serializers.SerializerMethodField()
    assignee_name = serializers.ReadOnlyField(source='assignee.get_full_name')
    reporter_name = serializers.ReadOnlyField(source='reporter.get_full_name')
    project_name = serializers.ReadOnlyField(source='project.name')
    project_key = serializers.ReadOnlyField(source='project.key')

    # Використовує анотовані поля з бази даних
    comments_count = serializers.IntegerField(read_only=True)
    resources_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'task_key', 'title', 'status', 'priority', 'task_type',
            'assignee_name', 'reporter_name',
            'project_name', 'project_key',
            'comments_count', 'resources_count',
            'sprint', 'estimated_hours', 'due_date'
        ]

    def get_task_key(self, obj):
        return f"{obj.project.key}-{obj.id}"


class TaskDetailSerializer(serializers.ModelSerializer):
    """
    Важкий серіалізатор для конкретної задачі.
    Містить усі поля + вкладені коментарі та ресурси.
    """
    # Додано генерацію ключа
    task_key = serializers.SerializerMethodField()

    project_name = serializers.ReadOnlyField(source='project.name')
    project_key = serializers.ReadOnlyField(source='project.key')

    # Додано вкладені об'єкти користувачів для читання
    assignee_details = UserMiniSerializer(source='assignee', read_only=True)
    reporter_details = UserMiniSerializer(source='reporter', read_only=True)

    # Вкладені масиви
    comments = TaskCommentSerializer(many=True, read_only=True)
    resources = TaskResourceSerializer(many=True, read_only=True)
    checklist = TaskChecklistItemSerializer(source='checklist_items', many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'task_key', 'title', 'description', 'status', 'priority', 'task_type',
            'assignee', 'assignee_details',
            'reporter', 'reporter_details',
            'project', 'project_name', 'project_key',
            'checklist', 'comments', 'resources',
            'sprint', 'estimated_hours', 'due_date', 'created_at', 'updated_at'
        ]

        read_only_fields = ['reporter', 'created_at', 'updated_at']

    def get_task_key(self, obj):
        return f"{obj.project.key}-{obj.id}"

    def validate(self, data):
        """
        БІЗНЕС-ЛОГІКА:
        1. Перевіряє, чи має право АВТОР ЗАПИТУ створювати задачі в цьому проєкті.
        2. Перевіряє, чи є ASSIGNEE (Виконавець) учасником цього проєкту.
        """
        request = self.context.get('request')
        current_user = request.user

        # --- ЛОГІКА СТВОРЕННЯ (Create) ---
        if not self.instance:
            # Визначає проєкт (з вхідних даних або з існуючого об'єкта)
            # При створенні (POST) він у data['project'].
            # При редагуванні (PATCH) він може бути не переданий, тоді береться з instance.
            project = data.get('project')

            # --- ПЕРЕВІРКА 1: Чи "свій" той, хто створює задачу? ---

            # Якщо це Адмін — він пропускає перевірку "свій/чужий".
            if current_user.is_staff or current_user.is_superuser:
                pass
            else:
                if project:
                    # Перевіряє чи є поточний юзер в таблиці учасників або власником
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
                is_assignee_owner = project.owner == assignee  # Страховка: на власника теж можна вішати задачі
                if not (is_assignee_member or is_assignee_owner):
                    raise serializers.ValidationError(
                        {"assignee": f"Користувач {assignee.email} не є учасником проєкту '{project.name}'."}
                    )

        # --- ЛОГІКА РЕДАГУВАННЯ (Update) ---
        else:
            instance = self.instance

            # 1. ЗАХИСТ "DONE" ЗАДАЧ (Immutability)
            if instance.status == Task.STATUS_DONE:
                new_status = data.get('status')

                # Якщо юзер намагається змінити щось, НЕ змінюючи статус з Done на інший
                if new_status == Task.STATUS_DONE or new_status is None:
                    raise serializers.ValidationError(
                        "Завершену задачу не можна редагувати. Спочатку відновіть її (змініть статус)."
                    )

                # Якщо статус змінюється (наприклад, на In Progress) — дозволяється (це Reopen).

            # 2. ПРАВА ДОСТУПУ (Хто може редагувати?)
            # Адмін і Власник — можуть все.
            is_admin = current_user.is_staff or current_user.is_superuser
            is_project_owner = instance.project.owner == current_user

            if is_admin or is_project_owner:
                pass
            else:
                # Визначає ролі
                is_reporter = instance.reporter == current_user
                is_assignee = instance.assignee == current_user

                # Якщо ти "лівий" чувак (не автор, не виконавець, не власник)
                if not (is_reporter or is_assignee):
                    raise serializers.ValidationError("Ви не маєте прав редагувати цю задачу.")

                # Якщо це Виконавець (але не Автор), він не може змінювати Назву і Опис.
                if is_assignee and not is_reporter:
                    # 1. Не можна змінювати суть задачі
                    if 'title' in data or 'description' in data:
                        raise serializers.ValidationError(
                            "Виконавець може змінювати тільки статус. Зверніться до автора для зміни умов."
                        )

                    # 2. Не можна "скидати" задачу (перепризначати)
                    if 'assignee' in data:
                        raise serializers.ValidationError(
                            "Виконавець не має права перепризначати задачу. Зверніться до менеджера."
                        )

            # Якщо при редагуванні змінюють виконавця, перевіряється, чи він з пісочниці
            new_assignee = data.get('assignee')
            if new_assignee:
                project = instance.project
                is_mem = ProjectMember.objects.filter(project=project, user=new_assignee).exists()
                is_own = project.owner == new_assignee
                if not (is_mem or is_own):
                    raise serializers.ValidationError(
                        {"assignee": f"Користувач {new_assignee.email} не є учасником проєкту."}
                    )

        return data