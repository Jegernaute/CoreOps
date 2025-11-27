from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import MeView, CreateInvitationView, RegisterByInviteView

urlpatterns = [
    # Auth (JWT)
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # Логін
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # Оновлення токена

    # Users Logic
    path('me/', MeView.as_view(), name='user_me'), # Мій профіль
    path('invite/', CreateInvitationView.as_view(), name='create_invite'), # Створити інвайт
    path('register/', RegisterByInviteView.as_view(), name='register_by_invite'), # Реєстрація
]