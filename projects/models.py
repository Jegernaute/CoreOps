from django.db import models
from django.conf import settings
# можна буде додати переклад
from django.utils.translation import gettext_lazy as _


class Project(models.Model):
    """
    Основна сутність проєкту.
    """
    # --- Статуси (Workflow) згідно ТЗ ---
    STATUS_BACKLOG = 'backlog'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_ON_HOLD = 'on_hold'
    STATUS_COMPLETED = 'completed'
    STATUS_ARCHIVED = 'archived'

    STATUS_CHOICES = [
        (STATUS_BACKLOG, 'Backlog (В планах)'),
        (STATUS_IN_PROGRESS, 'In Progress (В роботі)'),
        (STATUS_ON_HOLD, 'On Hold (На паузі)'),
        (STATUS_COMPLETED, 'Completed (Завершено)'),
        (STATUS_ARCHIVED, 'Archived (Архів)'),
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

    # --- Основні поля ---
    key = models.CharField(max_length=10, unique=True, verbose_name="Project Key (ID)",
                           help_text="Унікальний ключ, напр. MYPRJ")
    name = models.CharField(max_length=255, verbose_name="Назва проєкту")
    description = models.TextField(blank=True, verbose_name="Детальний опис")

    # Власник (Owner) - той, хто створив
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_projects',
        verbose_name="Власник"
    )

    # Атрибути
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_BACKLOG, verbose_name="Статус")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM,
                                verbose_name="Пріоритет")

    # Часові рамки
    start_date = models.DateField(null=True, blank=True, verbose_name="Дата початку")
    end_date = models.DateField(null=True, blank=True, verbose_name="Дедлайн (План)")
    actual_end_date = models.DateField(null=True, blank=True, verbose_name="Фактичне завершення")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.key}] {self.name}"


class ProjectMember(models.Model):
    """
    Проміжна таблиця для зв'язку Users <-> Projects (Context Roles).
    """
    ROLE_OWNER = 'owner'
    ROLE_MEMBER = 'member'
    ROLE_VIEWER = 'viewer'

    ROLE_CHOICES = [
        (ROLE_OWNER, 'Project Owner (Manager)'),
        (ROLE_MEMBER, 'Member (Contributor)'),
        (ROLE_VIEWER, 'Viewer (Read Only)'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER, verbose_name="Роль у проєкті")

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')  # Один юзер не може бути двічі в одному проєкті
        verbose_name = "Учасник проєкту"
        verbose_name_plural = "Учасники проєкту"

    def __str__(self):
        return f"{self.user.email} -> {self.project.key} ({self.role})"


class ProjectResource(models.Model):
    """
    Матеріали проєкту: посилання або файли.
    """
    TYPE_URL = 'url'
    TYPE_FILE = 'file'

    TYPE_CHOICES = [
        (TYPE_URL, 'URL Посилання'),
        (TYPE_FILE, 'Файл'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='resources')
    name = models.CharField(max_length=255, verbose_name="Назва ресурсу")
    resource_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_URL)

    url = models.URLField(blank=True, null=True, verbose_name="URL")
    file = models.FileField(upload_to='project_resources/', blank=True, null=True, verbose_name="Файл")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.resource_type})"


class ProjectMilestone(models.Model):
    """
    Етапи проєкту (Milestones).
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=255, verbose_name="Назва етапу")
    deadline = models.DateField(verbose_name="Дедлайн етапу")
    is_completed = models.BooleanField(default=False, verbose_name="Завершено")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Good" if self.is_completed else "In Progress"
        return f"{status} {self.name} ({self.deadline})"