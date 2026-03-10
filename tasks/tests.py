from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from projects.models import Project, ProjectMember
from tasks.models import Task, TaskComment

User = get_user_model()


class TaskAPITests(APITestCase):

    def setUp(self):
        # Створюємо користувачів
        self.boss = User.objects.create_user(username='boss_user', email='boss@test.com', password='123')
        self.dev = User.objects.create_user(username='dev_user', email='dev@test.com', password='123')

        # Створюємо проєкт і команду
        self.project = Project.objects.create(name="Task Project", key="TSK", owner=self.boss)
        ProjectMember.objects.create(project=self.project, user=self.boss, role='owner')
        ProjectMember.objects.create(project=self.project, user=self.dev, role='member')

        # Створюємо 3 задачі з різними статусами
        self.task_todo = Task.objects.create(
            project=self.project, title="To Do Task", status='to_do', reporter=self.dev
        )
        self.task_done = Task.objects.create(
            project=self.project, title="Done Task", status='done', reporter=self.dev
        )
        self.task_in_progress = Task.objects.create(
            project=self.project, title="In Progress Task", status='in_progress', reporter=self.dev
        )

        # Створюємо коментар від імені Dev
        self.comment = TaskComment.objects.create(
            task=self.task_todo, author=self.dev, content="Це коментар розробника"
        )

    def test_tc_api_003_delete_todo_task_by_author(self):
        """TC-API-003: Видалення задачі Автором (To Do)"""
        url = f'/api/v1/tasks/{self.task_todo.id}/'
        self.client.force_authenticate(user=self.dev)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_tc_api_004_delete_done_task_protection(self):
        """TC-API-004: Захист історії (Спроба видалення Done-задачі)"""
        url = f'/api/v1/tasks/{self.task_done.id}/'
        self.client.force_authenticate(user=self.boss)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tc_api_012_delete_in_progress_task_protection(self):
        """TC-API-012: Захист задачі 'В роботі' від видалення Автором"""
        url = f'/api/v1/tasks/{self.task_in_progress.id}/'
        self.client.force_authenticate(user=self.dev)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tc_api_007_edit_other_person_comment(self):
        """TC-API-007: Редагування незалежних коментарів (Security)"""
        url = f'/api/v1/tasks/comments/{self.comment.id}/'
        self.client.force_authenticate(user=self.boss)  # Boss намагається змінити текст Dev

        data = {"content": "Я хакнув цей коментар"}
        response = self.client.patch(url, data)

        # Тільки автор може змінювати текст
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tc_api_008_delete_comment_moderation(self):
        """TC-API-008: Видалення незалежних коментарів (Модерація Boss)"""
        url = f'/api/v1/tasks/comments/{self.comment.id}/'
        self.client.force_authenticate(user=self.boss)
        response = self.client.delete(url)

        # Boss має права на видалення будь-якого коментаря у своєму проєкті
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)