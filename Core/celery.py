import os
import dotenv
from celery import Celery

# Завантажуємо змінні оточення (паролі) ПЕРЕД усім іншим
dotenv.load_dotenv()

# Вказуємо стандартний модуль налаштувань Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Core.settings')

app = Celery('Core')

# Завантажуємо налаштування з settings.py (все, що починається з CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматично знаходимо tasks.py у всіх додатках
app.autodiscover_tasks()