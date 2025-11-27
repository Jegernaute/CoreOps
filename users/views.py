from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .models import Invitation
from .serializers import UserSerializer, InvitationSerializer, RegistrationSerializer
from django.db import transaction

User = get_user_model()


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET /users/me/ -> Отримати свій профіль
    PATCH /users/me/ -> Оновити (аватар, телефон тощо)
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Повертає поточного залогіненого юзера
        return self.request.user


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