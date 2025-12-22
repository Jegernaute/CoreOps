from django.core.management.base import BaseCommand
from tasks.tasks import check_deadlines_periodic


class Command(BaseCommand):
    help = 'Примусовий запуск перевірки дедлайнів (без очікування розкладу)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("⏳ Починаю перевірку дедлайнів..."))

        # Ми викликаємо функцію напряму (без .delay), щоб побачити результат тут і зараз
        # (всередині неї листи все одно підуть через Celery)
        result = check_deadlines_periodic()

        self.stdout.write(self.style.SUCCESS(f"Готово! Результат: {result}"))