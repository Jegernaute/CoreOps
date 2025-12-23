from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from tasks.models import Task, TaskComment
from users.models import Invitation
from .models import Notification
from .tasks import send_email_async

# --- 1. ЛОГІКА ДЛЯ ЗАДАЧ (Розумне відслідковування змін) ---

@receiver(pre_save, sender=Task)
def store_previous_state(sender, instance, **kwargs):
    """
    Перед збереженням запам'ятовуємо старі дані задачі.
    Це дозволить нам у post_save порівняти "Було" і "Стало".
    """
    if instance.pk:
        try:
            old_instance = Task.objects.get(pk=instance.pk)
            instance._old_assignee = old_instance.assignee
            instance._old_status = old_instance.status
        except Task.DoesNotExist:
            pass # Це створення нової задачі


@receiver(post_save, sender=Task)
def task_notifications(sender, instance, created, **kwargs):
    """
    Головний обробник змін у задачах.
    """
    # НОВА ЗАДАЧА (або зміна виконавця)
    new_assignee = instance.assignee
    old_assignee = getattr(instance, '_old_assignee', None)

    # Якщо виконавця призначили вперше АБО змінили на іншого
    if new_assignee and (created or new_assignee != old_assignee):
        # Не спамимо, якщо я призначив сам себе
        if new_assignee != instance.reporter:
            # In-App
            Notification.objects.create(
                recipient=new_assignee,
                title="Нова задача",
                message=f"Вас призначено на задачу: {instance.title} (Проєкт: {instance.project.name})",
                notification_type=Notification.TYPE_INFO
            )
            # Email
            send_email_async.delay(
                subject=f"CoreOps: Вас призначено на задачу",
                message=f"Задача: {instance.title}\nДедлайн: {instance.due_date}\nПріоритет: {instance.priority}",
                recipient_list=[new_assignee.email]
            )

    #  ЗМІНА СТАТУСУ (Сповіщаємо автора)
    new_status = instance.status
    old_status = getattr(instance, '_old_status', None)

    if not created and new_status != old_status:
        # Сповіщаємо Автора (Reporter), що статус змінився
        # Але тільки якщо статус змінив не сам Автор (щоб не було само-сповіщень)
        # На жаль, у сигналах ми не знаємо 'request.user', тому шлемо завжди, окрім випадку 'done'.

        if instance.reporter:
            Notification.objects.create(
                recipient=instance.reporter,
                title="Зміна статусу",
                message=f"Задача '{instance.title}' змінила статус: {old_status} -> {new_status}",
                notification_type=Notification.TYPE_SUCCESS if new_status == 'done' else Notification.TYPE_INFO
            )
            # Email шлемо тільки якщо задачу виконано (Done)
            if new_status == 'done':
                send_email_async.delay(
                    subject=f"CoreOps: Задача виконана!",
                    message=f"Вітаємо! Задача '{instance.title}' успішно завершена.",
                    recipient_list=[instance.reporter.email]
                )


# --- 2. ЛОГІКА ДЛЯ КОМЕНТАРІВ ---

@receiver(post_save, sender=TaskComment)
def comment_notifications(sender, instance, created, **kwargs):
    """
    При новому коментарі сповіщаємо учасників.
    """
    if created:
        task = instance.task
        author = instance.author

        recipients = set()

        # 1. Додаємо Виконавця (якщо це не він написав комент)
        if task.assignee and task.assignee != author:
            recipients.add(task.assignee)

        # 2. Додаємо Автора задачі (якщо це не він написав комент)
        if task.reporter and task.reporter != author:
            recipients.add(task.reporter)

        # Розсилаємо In-App сповіщення (Без Email, щоб не спамити)
        for user in recipients:
            Notification.objects.create(
                recipient=user,
                title="Новий коментар",
                message=f"{author.get_full_name()} прокоментував задачу '{task.title}': {instance.content[:50]}...",
                notification_type=Notification.TYPE_INFO
            )


# --- 3. ЛОГІКА ДЛЯ ІНВАЙТІВ (Залишаємо як було) ---
@receiver(post_save, sender=Invitation)
def send_invitation_email(sender, instance, created, **kwargs):
    """
    Автоматично відправляє лист із посиланням при створенні інвайту.
    """
    if created and not instance.is_used:
        # Формуємо посилання.
        # У реальному житті тут буде адреса Frontend (React/Vue), наприклад:
        # link = f"http://localhost:3000/register?token={instance.token}"
        # Але поки  тільки API,  посилання буде просто текстом або на Swagger:

        register_link = f"http://127.0.0.1:8000/api/users/register-by-invite/?token={instance.token}"

        subject = "Запрошення до системи CoreOps"
        message = (
            f"Вітаємо!\n\n"
            f"Адміністратор запросив вас приєднатися до робочого простору CoreOps.\n"
            f"Для завершення реєстрації перейдіть за посиланням:\n\n"
            f"{register_link}\n\n"
            f"Або скопіюйте ваш токен вручну: {instance.token}"
        )

        # Відправляємо асинхронно через Celery
        send_email_async.delay(
            subject=subject,
            message=message,
            recipient_list=[instance.email]
        )