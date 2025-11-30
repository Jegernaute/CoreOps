from celery import shared_task
from django.utils import timezone
from .models import Task
from notifications.tasks import send_email_async


@shared_task
def check_deadlines_periodic():
    """
    Періодична задача (Beat).
    Знаходить прострочені задачі і ставить в чергу (Worker) відправку листів.
    """
    now = timezone.now()
    # Шукаємо прострочені задачі
    overdue_tasks = Task.objects.filter(
        status__in=[Task.STATUS_TODO, Task.STATUS_IN_PROGRESS, Task.STATUS_REVIEW],
        due_date__lt=now,
        assignee__isnull=False
    )

    count = 0
    for task in overdue_tasks:
        subject = f"Дедлайн прострочено: {task.title}"
        message = f"Привіт! Дедлайн задачі '{task.title}' у проєкті '{task.project.name}' минув."

        # Викликаємо відправку листа для кожної задачі окремо
        send_email_async.delay(subject, message, [task.assignee.email])
        count += 1

    return f"Checked deadlines. Triggered {count} emails."