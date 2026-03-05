from django.db import models
from django.utils import timezone
from projects.models import Project
from django.core.exceptions import ValidationError

class Sprint(models.Model):
    """
    Ітерація розробки.
    """

    STATUS_CHOICES = [
        ('planned', 'Заплановано'),
        ('active', 'В роботі'),
        ('completed', 'Завершено'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sprints', verbose_name="Проєкт")
    name = models.CharField(max_length=100, verbose_name="Назва спринта")
    goal = models.TextField(blank=True, verbose_name="Ціль спринта")

    start_date = models.DateField(verbose_name="Дата початку")
    end_date = models.DateField(verbose_name="Дата завершення")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    actual_end_date = models.DateField(null=True, blank=True, help_text="Коли реально завершили спринт")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-end_date']
        verbose_name = "Спринт"
        verbose_name_plural = "Спринти"

    def __str__(self):
        return f"{self.name} ({self.get_status_display()}) - {self.project.name}"

    def clean(self):
        # Валідація: кінець не може бути раніше початку

        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Дата початку не може бути пізнішою за дату завершення.")