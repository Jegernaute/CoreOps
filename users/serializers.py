from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Invitation

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