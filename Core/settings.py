import os
from pathlib import Path
from dotenv import load_dotenv

from celery.schedules import crontab
from datetime import timedelta
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'), encoding='utf-8')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '10.0.2.2']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'projects',
    'tasks',
    'planning',
    'analytics' ,
    'notifications',
    'rest_framework',
    'drf_spectacular',
    'django_celery_beat',
    'django_filters',
    'corsheaders',
]

# --- CELERY SETTINGS ---
# Використовує localhost, бо порт 6379 прокинутий з докера на машину
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
# Часовий пояс для Django
TIME_ZONE = 'Europe/Kyiv'
CELERY_TIMEZONE = 'Europe/Kyiv'

AUTH_USER_MODEL = 'users.CustomUser'  # Вказує модель для авторезування

# --- CACHE SETTINGS (Redis) ---
# Використовує базу 1 (redis://localhost:6379/1) для кешу та Throttling,
# щоб не змішувати з чергами Celery (які на базі 0)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://localhost:6379/1",
    }
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware', # ВАЖЛИВО: має бути якомога вище, над CommonMiddleware
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'Core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# --- MEDIA SETTINGS ---
# Налаштовано шляхи для збереження та віддачі завантажених користувачами медіафайлів (аватари, ресурси задач).
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    # Вказуємо клас для генерації схеми
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',

        # (Опціонально) Залишити це якщо треба щоб працювала адмінка через браузер
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'Core.pagination.CoreCursorPagination',
    'PAGE_SIZE': 20,

'DEFAULT_THROTTLE_RATES': {
        'login': '5/min',             # Максимум 5 спроб входу на хвилину з однієї IP
        'register': '3/min',          # Захист від масового створення акаунтів ботами
        'password_reset': '3/min',    # Захист від спаму листами на пошту
    }
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,

    'AUTH_HEADER_TYPES': ('Bearer',),
}

# --- Email Configuration (Gmail) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
#  логін у Gmail
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
#  SMTP-ключ
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
# Від кого приходитимуть листи
DEFAULT_FROM_EMAIL = f'CoreOps System <{EMAIL_HOST_USER}>'


CELERY_BEAT_SCHEDULE = {
    'check-deadlines-every-minute': {
        'task': 'tasks.tasks.check_deadlines_periodic',
        # Запускати щодня о 9:00 ранку
        'schedule': crontab(hour=9, minute=0),
    },
}

# Для етапу розробки (MVP) дозволяє запити з будь-яких джерел
CORS_ALLOW_ALL_ORIGINS = True