from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class UserAPITests(APITestCase):

    def setUp(self):
        """Підготовка даних перед тестами"""
        # Створюємо звичайного користувача (Member)
        self.member = User.objects.create_user(
            username='member_user',
            email='member@test.com',
            password='strongpassword123',
            first_name='Ivan',
            last_name='Member'
        )

        # Створюємо Адміністратора (Boss)
        self.admin = User.objects.create_superuser(
            username='admin_user',
            email='admin@test.com',
            password='adminpassword123',
            first_name='Super',
            last_name='Admin'
        )

    def test_tc_api_001_register_without_token(self):
        """TC-API-001: Спроба реєстрації без інвайт-токена"""
        url = '/api/v1/users/register/'
        data = {
            "password": "123",
            "first_name": "Іван",
            "last_name": "Тест"
        }
        # Робимо POST запит без авторизації
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('token', response.data)  # Перевіряємо, що помилка саме через поле token

    def test_tc_api_006_soft_delete_user(self):
        """TC-API-006: М'яке видалення користувача Адміном та перевірка блокування"""
        # Крок А: Видалення
        url_delete = f'/api/v1/users/{self.member.id}/'
        self.client.force_authenticate(user=self.admin)  # Авторизуємося як Адмін
        response_delete = self.client.delete(url_delete)

        self.assertEqual(response_delete.status_code, status.HTTP_200_OK)

        # Переконуємось, що юзер став неактивним у базі (Soft Delete)
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)

        # Крок Б: Спроба логіну віддаленим користувачем
        self.client.force_authenticate(user=None)  # Скидаємо авторизацію
        url_token = '/api/v1/users/token/'
        data_login = {
            "email": "member@test.com",
            "password": "strongpassword123"
        }
        response_login = self.client.post(url_token, data_login)

        self.assertEqual(response_login.status_code, status.HTTP_401_UNAUTHORIZED)