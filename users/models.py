import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """
    Розширена модель користувача.
    Автентифікація відбувається через email.
    """

    # Глобальні ролі (доступ до системи)
    ROLE_ADMIN = 'admin'
    ROLE_USER = 'user'

    GLOBAL_ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin (Full Access)'),
        (ROLE_USER, 'User (Limited Access)'),
    ]

    # --- Основні поля ---
    # Робимо email унікальним ідентифікатором для входу
    email = models.EmailField(_('email address'), unique=True)

    # Додаткова інфо
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Аватар")
    job_title = models.CharField(max_length=100, blank=True, verbose_name="Посада (Global)")

    # Контакти
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    telegram = models.CharField(max_length=50, blank=True, verbose_name="Telegram (@username)") # пізніше можна переназвати

    # Права доступу (Глобальні)
    global_role = models.CharField(
        # в майбутньому краще прибрати або збільшити максимум довжину
        max_length=10,
        choices=GLOBAL_ROLE_CHOICES,
        default=ROLE_USER,
        verbose_name="Глобальна роль"
    )

    # --- Налаштування Auth ---
    # Вказуємо, що логіном є email, а не username
    USERNAME_FIELD = 'email'
    # Поля, які обов'язкові при створенні суперюзера (крім email та пароля)
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        # Відображення в адмінці: "ivan@test.com (Backend Dev)"
        role_mark = "[A]" if self.global_role == self.ROLE_ADMIN else "[U]"
        return f"{role_mark} {self.email} ({self.job_title or 'No title'})"


class Invitation(models.Model):
    """
    Модель для системи запрошень (Invitation Only).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(verbose_name="Email запрошеного")

    # Хто створив інвайт (тільки існуючий юзер може запросити іншого)
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        verbose_name="Хто запросив"
    )

    token = models.CharField(max_length=255, unique=True, verbose_name="Токен доступу")
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False, verbose_name="Використано")

    def save(self, *args, **kwargs):
        # Якщо токен не задано, генеруємо його з UUID
        if not self.token:
            self.token = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def __str__(self):
        status = "USED" if self.is_used else "ACTIVE"
        return f"Invite to {self.email} [{status}]"

