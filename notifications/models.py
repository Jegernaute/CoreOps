from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Сповіщення для користувача (In-App).
    """
    TYPE_INFO = 'info'
    TYPE_WARNING = 'warning'
    TYPE_SUCCESS = 'success'

    TYPE_CHOICES = [
        (TYPE_INFO, 'Інформація'),
        (TYPE_WARNING, 'Увага'),
        (TYPE_SUCCESS, 'Успіх'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Отримувач"
    )

    title = models.CharField(max_length=255, verbose_name="Заголовок")
    message = models.TextField(verbose_name="Текст повідомлення")
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_INFO)

    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # Спочатку нові
        verbose_name = "Сповіщення"
        verbose_name_plural = "Сповіщення"

    def __str__(self):
        status = "Read" if self.is_read else "New"
        return f"[{status}] To {self.recipient.email}: {self.title}"