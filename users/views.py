from rest_framework import generics, permissions, status, filters, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .models import Invitation
from .serializers import (UserSerializer, InvitationSerializer, RegistrationSerializer, SetNewPasswordSerializer,
                          PasswordResetRequestSerializer, UserSummarySerializer, UserManageSerializer)
from django.db import transaction
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from notifications.tasks import send_email_async


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
                serializer.save()
                return Response({"message": "Користувач створений успішно"}, status=status.HTTP_201_CREATED)
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
            reset_link = f"http://localhost:3000/reset-password/{uidb64}/{token}/"

            # 3. Відправляємо лист
            email_body = f"Привіт, {user.first_name}!\n\nВи (або хтось інший) запросили зміну пароля.\nВикористовуйте це посилання:\n{reset_link}\n\nЯкщо ви цього не робили, просто ігноруйте цей лист."

            send_email_async.delay(
                subject="Відновлення пароля CoreOps",
                message=email_body,
                recipient_list=[email]
            )

            return Response({"message": "Посилання відправлено"}, status=status.HTTP_200_OK)

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
            serializer.save()

            return Response({"message": "Пароль успішно змінено! Тепер ви можете увійти."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserViewSet(viewsets.ModelViewSet):
    """
    Універсальний контролер:
    - GET /users/ : Список (для юзерів - тільки активні, для адміна - всі).
    - PATCH /users/{id}/ : Редагування (Тільки Адмін).
    - DELETE /users/{id}/ : Деактивація (Тільки Адмін).
    """
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [filters.SearchFilter]
    search_fields = ['email', 'first_name', 'last_name', 'job_title', 'phone', 'telegram']

    def get_queryset(self):
        """
        Фільтрація:
        - Адміністратор бачить ВСІХ користувачів (в т.ч. звільнених/заблокованих).
        - Звичайний користувач бачить тільки АКТИВНИХ колег.
        """
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return User.objects.all()
        return User.objects.filter(is_active=True)

    def get_serializer_class(self):
        # Якщо ми змінюємо дані або створюємо (тільки адмін) - повний доступ
        if self.action in ['update', 'partial_update', 'create']:
            return UserManageSerializer
        # Для списку і перегляду - тільки публічні дані
        return UserSummarySerializer

    def get_permissions(self):
        # Адмінські дії
        if self.action in ['update', 'partial_update', 'destroy', 'create']:
            return [permissions.IsAdminUser()]
        # Всі інші (list, retrieve) - для всіх авторизованих
        return [permissions.IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        """
        Soft Delete + Очищення робочих хвостів.
        """
        user = self.get_object()

        # 1. Захист від самовидалення
        if user == request.user:
            return Response(
                {"error": "Ви не можете деактивувати власний акаунт."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- ПОЧАТОК ЛОГІКИ ОЧИЩЕННЯ ---

        # Імпортуємо тут, щоб не було циклічних помилок
        from tasks.models import Task
        from projects.models import ProjectMember

        # 2. Знімаємо юзера з активних задач (Assignee -> None)
        # Шукаємо задачі, які ще НЕ зроблені (To Do, In Progress, Review)
        active_tasks = Task.objects.filter(assignee=user).exclude(status=Task.STATUS_DONE)
        updated_tasks_count = active_tasks.update(assignee=None)

        # 3. Видаляємо його зі списків учасників проєктів
        # (Щоб його не можна было вибрати у нових задачах)
        # Примітка: Це не видаляє проєкти, де він Owner, бо там стоїть on_delete=PROTECT в моделі Project
        deleted_memberships_count, _ = ProjectMember.objects.filter(user=user).delete()

        # 4. Власне деактивація (Soft Delete)
        user.is_active = False
        user.save()

        return Response(
            {
                "message": f"Користувача {user.email} деактивовано.",
                "details": {
                    "unassigned_tasks": updated_tasks_count,  # Скільки задач стало нічийними
                    "removed_from_projects": deleted_memberships_count  # Зі скількох проєктів виключено
                }
            },
            status=status.HTTP_200_OK
        )