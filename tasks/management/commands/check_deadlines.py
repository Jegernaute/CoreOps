from django.core.management.base import BaseCommand
from tasks.tasks import check_deadlines_periodic


class Command(BaseCommand):
    help = 'Ручний запуск перевірки дедлайнів (через Celery Worker)'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Запускаю задачу перевірки дедлайнів у Celery...")

        # Ми просто ставимо задачу в чергу. Вона виконається асинхронно.
        task = check_deadlines_periodic.delay()

        self.stdout.write(self.style.SUCCESS(f"✅ Задача поставлена в чергу! Task ID: {task.id}"))
        self.stdout.write("Перевірте термінал Worker-а, щоб побачити результат.")