from django.db import models
from django.utils import timezone
from projects.models import Project
from django.core.exceptions import ValidationError

class Sprint(models.Model):
    """
    Ітерація розробки.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sprints', verbose_name="Проєкт")
    name = models.CharField(max_length=100, verbose_name="Назва спринта")
    goal = models.TextField(blank=True, verbose_name="Ціль спринта")

    start_date = models.DateField(verbose_name="Дата початку")
    end_date = models.DateField(verbose_name="Дата завершення")

    is_active = models.BooleanField(default=False, verbose_name="Активний")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-end_date']
        verbose_name = "Спринт"
        verbose_name_plural = "Спринти"

    def __str__(self):
        status = "Active" if self.is_active else "💤"
        return f"{status} {self.name}"

    def clean(self):
        # Валідація: кінець не може бути раніше початку

        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError("Дата завершення не може бути раніше дати початку.")