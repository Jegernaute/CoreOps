import os
import dotenv
from celery import Celery

# Завантажує змінні оточення (паролі) ПЕРЕД усім іншим
dotenv.load_dotenv()

# Вказує стандартний модуль налаштувань Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Core.settings')

app = Celery('Core')

# Завантажує налаштування з settings.py (все, що починається з CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматично знаходить tasks.py у всіх додатках
app.autodiscover_tasks()