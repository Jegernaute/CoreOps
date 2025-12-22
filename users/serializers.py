from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Invitation
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Серіалізатор для перегляду профілю користувача.
    """
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'avatar', 'job_title', 'phone', 'telegram',
            'global_role'
        ]
        read_only_fields = ['id', 'email', 'global_role']  # Ці поля юзер не може змінити сам

class InvitationSerializer(serializers.ModelSerializer):
    """
    Для створення запрошень адміном.
    """
    class Meta:
        model = Invitation
        fields = ['id', 'email', 'token', 'is_used', 'created_at']
        read_only_fields = ['id', 'token', 'is_used', 'created_at']

class RegistrationSerializer(serializers.Serializer):
    """
    Спеціальний серіалізатор для реєстрації по інвайту.
    Не прив'язаний напряму до моделі, бо приймає вхідні дані для логіки.
    """
    token = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    def validate_token(self, value):
        """Перевіряємо, чи існує такий активний токен"""
        try:
            invite = Invitation.objects.get(token=value, is_used=False)
        except Invitation.DoesNotExist:
            raise serializers.ValidationError("Недійсний або вже використаний токен запрошення.")
        return value

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Крок 1: Юзер вводить Email.
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        # Ми не повинні казати юзеру "такого мейла немає" (з міркувань безпеки),
        # але для MVP можемо просто перевірити існування.
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Користувача з таким email не знайдено.")
        return value


class SetNewPasswordSerializer(serializers.Serializer):
    """
    Крок 2: Юзер відправляє UID, Токен та Новий пароль.
    """
    password = serializers.CharField(min_length=8, write_only=True)
    token = serializers.CharField(write_only=True)
    uidb64 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            # Декодуємо ID юзера
            uid = force_str(urlsafe_base64_decode(attrs.get("uidb64")))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Недійсне посилання для відновлення (UID Error).")

        # Перевіряємо токен
        if not PasswordResetTokenGenerator().check_token(user, attrs.get("token")):
            raise serializers.ValidationError("Посилання недійсне або застаріло.")

        attrs['user'] = user # Зберігаємо юзера, щоб використати у View
        return attrs

class UserSummarySerializer(serializers.ModelSerializer):
    """
    Полегшений серіалізатор для пошуку та списків.
    Повертає тільки публічну інформацію.
    """
    full_name = serializers.ReadOnlyField(source='get_full_name')

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'avatar']