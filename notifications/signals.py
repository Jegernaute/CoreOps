from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from tasks.models import Task
from .models import Notification
from .tasks import send_email_async

@receiver(post_save, sender=Task)
def notify_assignee(sender, instance, created, **kwargs):
    """
    Відправляє сповіщення та Email, коли користувача призначають на задачу.
    """
    # Якщо виконавця немає - нічого не робимо
    if not instance.assignee:
        return

    # Логіка: Перевіряємо, чи змінився виконавець (або це нова задача)
    # На жаль, у post_save ми не бачимо "старого" значення,
    # але для MVP ми будемо слати повідомлення завжди при створенні
    # або якщо це update і є виконавець.
    # (Для ідеальної перевірки "чи змінився" треба pre_save, але це ускладнить код).

    # Щоб не слати повідомлення самому собі (якщо я створив і призначив на себе)
    # if instance.assignee == instance.reporter:
    #     return  # Розкоментувати, якщо треба вимкнути сповіщення собі

    title = f"Ви призначені на задачу: {instance.title}"
    message = f"Проєкт: {instance.project.name}\nПріоритет: {instance.priority}\nДедлайн: {instance.due_date}"

    # 1. Створюємо In-App сповіщення (Дзвіночок)
    Notification.objects.create(
        recipient=instance.assignee,
        title="Нова задача!",
        message=title,
        notification_type=Notification.TYPE_INFO
    )

    # 2. Асинхронна відправка Email

    email_subject = f"CoreOps: {instance.title}"
    email_body = (
        f"Вітаємо, {instance.assignee.first_name}!\n\n"
        f"Ви призначені на задачу: {instance.title}\n"
        f"Проєкт: {instance.project.name}\n"
        f"Пріоритет: {instance.priority}\n"
        f"Дедлайн: {instance.due_date}"
    )

    # .delay() - магічна команда, яка відправляє лист в редіс для подальшої обробки
    send_email_async.delay(
        subject=email_subject,
        message=email_body,
        recipient_list=[instance.assignee.email]
    )