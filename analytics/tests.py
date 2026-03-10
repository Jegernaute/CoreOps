from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from projects.models import Project, ProjectMember
from tasks.models import Task

User = get_user_model()


class AnalyticsAPITests(APITestCase):

    def setUp(self):
        # Створюємо користувача
        self.dev = User.objects.create_user(username='dev_user', email='dev@test.com', password='123')

        # Створюємо проєкт і команду
        self.project = Project.objects.create(name="Analytics Project", key="ANL", owner=self.dev)
        ProjectMember.objects.create(project=self.project, user=self.dev, role='owner')

        # Створюємо дві задачі (одна 'to_do', інша 'done')
        # З двох задач одна виконана, тому прогрес має бути рівно 50%
        self.task1 = Task.objects.create(
            project=self.project, title="Task 1", status='to_do', reporter=self.dev
        )
        self.task2 = Task.objects.create(
            project=self.project, title="Task 2", status='done', reporter=self.dev
        )

    def test_tc_api_009_dashboard_kpi_accuracy(self):
        """TC-API-009: Точність KPI (Агрегація Dashboard)"""
        url = f'/api/v1/analytics/dashboard/{self.project.id}/'

        self.client.force_authenticate(user=self.dev)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Перевіряємо математику (progress_percent має дорівнювати 50)
        self.assertEqual(response.data['project_health']['progress_percent'], 50)

    def test_tc_api_010_activity_log_signals(self):
        """TC-API-010: Activity Log (Перевірка роботи сигналів)"""

        # Крок А: Створюємо нову задачу через API (це має запустити сигнал)
        url_task = '/api/v1/tasks/'
        self.client.force_authenticate(user=self.dev)
        task_data = {
            "project": self.project.id,
            "title": "Task for Log Test",
            "status": "to_do"
        }
        self.client.post(url_task, task_data)

        # Крок Б: Робимо запит на отримання логів проєкту
        url_logs = f'/api/v1/analytics/logs/{self.project.id}/'
        response = self.client.get(url_logs)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Оскільки ми підключили пагінацію (StandardResultsSetPagination), дані будуть в 'results'
        logs = response.data.get('results', [])

        # Перевіряємо, що лог дійсно створився
        self.assertTrue(len(logs) > 0)