from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from tasks.models import Task, TaskComment
from .models import ProjectActivityLog


# --- Слухаємо зміни в Задачах ---
@receiver(post_save, sender=Task)
def log_task_changes(sender, instance, created, **kwargs):
    """
    Записує лог при створенні або оновленні задачі.
    """
    action = ProjectActivityLog.ACTION_CREATED if created else ProjectActivityLog.ACTION_UPDATED

    # Хто це зробив?
    # (Лайфхак: у сигналах важко дістати юзера request.user,
    # тому для MVP ми будемо брати reporter як автора дії при створенні,
    # або assignee при оновленні, якщо точніше - треба middleware, але для MVP це ок)
    actor = instance.reporter if created else instance.assignee

    ProjectActivityLog.objects.create(
        project=instance.project,
        actor=actor,
        action_type=action,
        target=f"Task: {instance.title}"
    )


# --- Слухаємо коментарі ---
@receiver(post_save, sender=TaskComment)
def log_comments(sender, instance, created, **kwargs):
    if created:
        ProjectActivityLog.objects.create(
            project=instance.task.project,
            actor=instance.author,
            action_type=ProjectActivityLog.ACTION_COMMENTED,
            target=f"Comment on: {instance.task.title}"
        )