from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .models import Invitation
from .serializers import UserSerializer, InvitationSerializer, RegistrationSerializer, SetNewPasswordSerializer, PasswordResetRequestSerializer
from django.db import transaction
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()


class MeView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /users/me/ -> Отримати свій профіль
    PATCH /users/me/ -> Оновити (аватар, телефон тощо)
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Повертає поточного залогіненого юзера
        return self.request.user

    def perform_destroy(self, instance):
        """
        Юзер хоче видалити свій акаунт.
        Ми не видаляємо запис, а просто деактивуємо його.
        """
        instance.is_active = False
        instance.save()


class CreateInvitationView(generics.CreateAPIView):
    """
    POST /users/invite/ -> Створити інвайт (Тільки для Admins)
    """
    serializer_class = InvitationSerializer
    permission_classes = [permissions.IsAdminUser]  # Тільки адмін може запрошувати

    def perform_create(self, serializer):
        # Автоматично додаємо, хто створив інвайт
        serializer.save(sender=self.request.user)


class RegisterByInviteView(APIView):
    """
    POST /users/register/ -> Реєстрація по токену
    Body: { "token": "...", "password": "...", "first_name": "...", "last_name": "..." }
    """
    permission_classes = [permissions.AllowAny]  # Доступно всім (навіть без логіну)

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                data = serializer.validated_data

                # 1. Знаходимо інвайт
                invite = Invitation.objects.get(token=data['token'])

                # 2. Створюємо юзера
                user = User.objects.create_user(
                    email=invite.email,
                    username=invite.email,  # Технічне поле
                    password=data['password'],
                    first_name=data['first_name'],
                    last_name=data['last_name']
                )

                # 3. Маркуємо інвайт як використаний
                invite.is_used = True
                invite.save()

                return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- Views для відновлення пароля ---

class PasswordResetRequestView(generics.GenericAPIView):
    """
    POST /users/password-reset/
    Генерує посилання на зміну пароля і відправляє його на Email (в консоль).
    """
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)

            # 1. Генеруємо унікальний токен та ID
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = PasswordResetTokenGenerator().make_token(user)

            # 2. Формуємо "посилання" (для фронтенду)
            # У реальності це було б: https://my-frontend.com/reset/{uidb64}/{token}/
            reset_link = f"http://localhost:3000/reset-password/{uidb64}/{token}/"

            # 3. Відправляємо лист (у нашому випадку - в консоль)
            email_body = f"Привіт, {user.first_name}!\n\nВи (або хтось інший) запросили зміну пароля.\nВикористовуйте це посилання:\n{reset_link}\n\nЯкщо ви цього не робили, просто ігноруйте цей лист."

            send_mail(
                subject="Відновлення пароля CoreOps",
                message=email_body,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )

            return Response({"message": "Посилання на відновлення відправлено на Email"},
                            status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    POST /users/password-reset-confirm/
    Приймає token, uidb64 і новий пароль. Змінює пароль.
    """
    serializer_class = SetNewPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            password = serializer.validated_data['password']

            # Змінюємо пароль
            user.set_password(password)
            user.save()

            return Response({"message": "Пароль успішно змінено! Тепер ви можете увійти."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
