from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

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