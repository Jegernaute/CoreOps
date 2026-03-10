from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from projects.models import Project, ProjectMember
from planning.models import Sprint

User = get_user_model()


class PlanningAPITests(APITestCase):

    def setUp(self):
        # Створюємо двох Власників
        self.boss_a = User.objects.create_user(username='boss_a', email='boss_a@test.com', password='123')
        self.boss_b = User.objects.create_user(username='boss_b', email='boss_b@test.com', password='123')

        # Створюємо Проєкт А (для boss_a)
        self.project_a = Project.objects.create(name="Project A", key="PRA", owner=self.boss_a)
        ProjectMember.objects.create(project=self.project_a, user=self.boss_a, role='owner')

        # Створюємо Проєкт Б (для boss_b)
        self.project_b = Project.objects.create(name="Project B", key="PRB", owner=self.boss_b)
        ProjectMember.objects.create(project=self.project_b, user=self.boss_b, role='owner')

        # Створюємо валідний спринт у Проєкті Б
        self.sprint_b = Sprint.objects.create(
            project=self.project_b,
            name="Sprint B",
            start_date="2026-03-01",
            end_date="2026-03-15"
        )

    def test_tc_api_005_sprint_date_validation(self):
        """TC-API-005: Валідація часових рамок Спринта"""
        url = '/api/v1/planning/'
        self.client.force_authenticate(user=self.boss_a)  # Boss A створює спринт у своєму проєкті

        data = {
            "project": self.project_a.id,
            "name": "Invalid Sprint",
            "start_date": "2026-03-20",
            "end_date": "2026-03-10"  # ПОМИЛКА: Кінець раніше за початок!
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tc_api_013_sprint_filtering_isolation(self):
        """TC-API-013: Фільтрація Спринтів (Ізоляція даних)"""
        # Boss A намагається хитрим шляхом запросити спринти Проєкту Б
        url = f'/api/v1/planning/?project={self.project_b.id}'

        self.client.force_authenticate(user=self.boss_a)
        response = self.client.get(url)

        # Запит проходить (200 OK), але...
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # ...через ізоляцію (get_queryset) список результатів має бути порожнім!
        self.assertEqual(len(response.data['results']), 0)