from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from projects.models import Project

User = get_user_model()


class ProjectAPITests(APITestCase):

    def setUp(self):
        # Власник проєкту
        self.owner = User.objects.create_user(username='owner_user',email='owner@test.com', password='strongpassword123')
        # Учасник проєкту
        self.dev = User.objects.create_user(username='dev_user',email='dev@test.com', password='strongpassword123')
        # Стороння людина
        self.stranger = User.objects.create_user(username='member_user',email='stranger@test.com', password='strongpassword123')

        # Створюємо проєкт і додаємо Dev в учасники
        self.project = Project.objects.create(
            name="Alpha Project",
            key="ALF",
            owner=self.owner
        )
        # Додаємо учасника через m2m поле
        from projects.models import ProjectMember
        ProjectMember.objects.create(project=self.project, user=self.dev, role='member')

    def test_tc_api_002_stranger_cannot_see_project(self):
        """TC-API-002: Невидимість чужого проєкту"""
        url = f'/api/v1/projects/{self.project.id}/'

        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tc_api_011_remove_member_access(self):
        """TC-API-011: Видалення учасника (Team Management)"""
        # Крок А: Видалення учасника Власником
        url_remove = f'/api/v1/projects/{self.project.id}/remove_member/{self.dev.id}/'
        self.client.force_authenticate(user=self.owner)
        response_remove = self.client.delete(url_remove)

        self.assertIn(response_remove.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])

        # Крок Б: Спроба доступу колишнім учасником
        url_get = f'/api/v1/projects/{self.project.id}/'
        self.client.force_authenticate(user=self.dev)
        response_get = self.client.get(url_get)

        self.assertEqual(response_get.status_code, status.HTTP_404_NOT_FOUND)