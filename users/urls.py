from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import MeView, CreateInvitationView, RegisterByInviteView, PasswordResetRequestView, \
    PasswordResetConfirmView, UserViewSet

# --- ЛОКАЛЬНИЙ РОУТЕР ---
# Він створить шляхи:
# GET / (список)
# POST / (створення - хоча ми це заборонили правами)
# GET /:id/ (деталі юзера)
# PATCH /:id/ (редагування юзера)
# DELETE /:id/ (видалення)
router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    # Auth (JWT)
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # Логін
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # Оновлення токена

    # Users Logic
    path('me/', MeView.as_view(), name='user_me'), # Мій профіль
    path('invite/', CreateInvitationView.as_view(), name='create_invite'), # Створити інвайт
    path('register/', RegisterByInviteView.as_view(), name='register_by_invite'), # Реєстрація
    # Password Reset
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]

# --- Підключаємо шляхи від Роутера ---
# Якщо URL не підійшов під жоден з верхніх (не 'me', не 'token'),
# Django перевірить, чи це ID (наприклад '6/'), і віддасть роутеру.
urlpatterns += router.urls