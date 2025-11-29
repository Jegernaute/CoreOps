from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from tasks.models import Task


class Command(BaseCommand):
    help = 'Перевіряє прострочені задачі та відправляє нагадування виконавцям'

    def handle(self, *args, **kwargs):
        self.stdout.write("⏳ Починаю перевірку дедлайнів...")

        now = timezone.now()

        # 1. Шукаємо задачі:
        # - Статус НЕ Done і НЕ Archived
        # - Дедлайн минув (due_date < now)
        # - Є виконавець (assignee != None)
        # - (Опціонально) Можна додати поле "reminder_sent", щоб не спамити щохвилини,
        #   але для MVP будемо слати щоразу при запуску.

        overdue_tasks = Task.objects.filter(
            status__in=[Task.STATUS_TODO, Task.STATUS_IN_PROGRESS, Task.STATUS_REVIEW],
            due_date__lt=now,
            assignee__isnull=False
        )

        if not overdue_tasks.exists():
            self.stdout.write(self.style.SUCCESS("✅ Прострочених задач немає."))
            return

        count = 0
        for task in overdue_tasks:
            # Формуємо лист
            user = task.assignee
            subject = f"🔥 УВАГА: Прострочено дедлайн по задачі '{task.title}'"
            message = (
                f"Вітаємо, {user.first_name}!\n\n"
                f"Нагадуємо, що дедлайн по задачі минув.\n"
                f"Задача: {task.title}\n"
                f"Проєкт: {task.project.name}\n"
                f"Дедлайн був: {task.due_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"Будь ласка, актуалізуйте статус або зв'яжіться з менеджером."
            )

            try:
                # Відправка
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                self.stdout.write(f"  -> Надіслано лист для {user.email} (Task {task.id})")
                count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> Помилка відправки для {user.email}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"🏁 Перевірку завершено. Надіслано нагадувань: {count}"))