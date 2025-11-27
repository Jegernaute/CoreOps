from django.db import models
from django.conf import settings
from projects.models import Project


class ProjectActivityLog(models.Model):
    """
    Лог дій користувачів.
    """
    ACTION_CREATED = 'created'
    ACTION_UPDATED = 'updated'
    ACTION_DELETED = 'deleted'
    ACTION_COMMENTED = 'commented'

    ACTION_CHOICES = [
        (ACTION_CREATED, 'Створено'),
        (ACTION_UPDATED, 'Оновлено'),
        (ACTION_DELETED, 'Видалено'),
        (ACTION_COMMENTED, 'Прокоментовано'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='activity_logs')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Хто")

    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target = models.CharField(max_length=255, verbose_name="Об'єкт")  # Напр. "Task: Fix bug"

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Лог активності"

    def __str__(self):
        return f"[{self.project.key}] {self.actor} -> {self.action_type}"