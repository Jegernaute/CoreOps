from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification
from django.contrib.auth import get_user_model

@shared_task
def send_email_async(subject, message, recipient_list):
    """
    Асинхронна задача для відправки листів.
    Виконується окремим процесом (Worker), не блокуючи сайт.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        return f"Email sent to {recipient_list}"
    except Exception as e:
        return f"Email failed: {e}"

User = get_user_model()

@shared_task
def create_notification_async(user_id, title, message, notif_type):
    """Фонове створення In-App сповіщення без блокування основної транзакції"""
    user = User.objects.get(id=user_id)
    Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notif_type
    )