from django.db import models
from django.conf import settings
from projects.models import Project, ProjectMilestone


class Task(models.Model):
    """
    Основна сутність задачі.
    """
    # --- Типи задач (Категоризація) ---
    TYPE_BUG = 'bug'
    TYPE_FEATURE = 'feature'
    TYPE_TASK = 'task'

    TYPE_CHOICES = [
        (TYPE_BUG, 'Bug (Помилка)'),
        (TYPE_FEATURE, 'Feature (Нова функція)'),
        (TYPE_TASK, 'Task (Технічна задача)'),
    ]

    # --- Статуси (Workflow) ---
    STATUS_TODO = 'to_do'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_REVIEW = 'review'
    STATUS_DONE = 'done'

    STATUS_CHOICES = [
        (STATUS_TODO, 'To Do'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_REVIEW, 'Code Review'),
        (STATUS_DONE, 'Done'),
    ]

    # --- Пріоритети ---
    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_CRITICAL = 'critical'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_CRITICAL, 'Critical'),
    ]

    # --- Зв'язки ---
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks', verbose_name="Проєкт")

    sprint = models.ForeignKey(
        'planning.Sprint',
        on_delete=models.SET_NULL,  # Якщо спринт видалять, задача не зникне, а просто випаде в Backlog
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name="Спринт"
    )

    milestone = models.ForeignKey(
        ProjectMilestone,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tasks',
        verbose_name="Етап (Milestone)"
    )

    # Люди
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_tasks',
        verbose_name="Виконавець"
    )

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reported_tasks',
        verbose_name="Автор"
    )

    # --- Контент ---
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    description = models.TextField(blank=True, verbose_name="Опис (Markdown)")

    # --- Атрибути ---
    task_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_TASK, verbose_name="Тип")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO, verbose_name="Статус")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM,
                                verbose_name="Пріоритет")

    # --- Планування ---
    estimated_hours = models.FloatField(null=True, blank=True, verbose_name="Оцінка (год)")
    due_date = models.DateTimeField(null=True, blank=True, verbose_name="Дедлайн")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.project.key}-{self.id}] {self.title}"


class TaskResource(models.Model):
    """
    Вкладення до задачі.
    """
    TYPE_URL = 'url'
    TYPE_FILE = 'file'

    TYPE_CHOICES = [
        (TYPE_URL, 'Посилання'),
        (TYPE_FILE, 'Файл'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='resources')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    name = models.CharField(max_length=255, blank=True, verbose_name="Назва")
    resource_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_FILE)

    file = models.FileField(upload_to='task_attachments/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)


class TaskComment(models.Model):
    """
    Коментарі.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(verbose_name="Текст коментаря")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.email}"