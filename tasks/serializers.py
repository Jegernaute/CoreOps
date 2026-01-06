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

        # --- ЛОГІКА СТВОРЕННЯ (Create) ---
        if not self.instance:
            # Визначаємо проєкт (з вхідних даних або з існуючого об'єкта)
            # При створенні (POST) він у data['project'].
            # При редагуванні (PATCH) він може бути не переданий, тоді беремо з instance.
            project = data.get('project')

            # --- ПЕРЕВІРКА 1: Чи "свій" той, хто створює задачу? ---

            # Якщо це Адмін — він пропускає перевірку "свій/чужий".
            if current_user.is_staff or current_user.is_superuser:
                pass
            else:
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

                # Якщо статус змінюється (наприклад, на In Progress) — дозволяємо (це Reopen).

            # 2. ПРАВА ДОСТУПУ (Хто може редагувати?)
            # Адмін і Власник — можуть все.
            is_admin = current_user.is_staff or current_user.is_superuser
            is_project_owner = instance.project.owner == current_user

            if is_admin or is_project_owner:
                pass
            else:
                # Визначаємо ролі
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

            # Якщо при редагуванні змінюють виконавця, перевіряємо, чи він з нашої пісочниці
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