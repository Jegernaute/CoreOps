from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, TaskCommentViewSet, TaskResourceViewSet

router = DefaultRouter()
router.register(r'comments', TaskCommentViewSet, basename='task-comment')
router.register(r'resources', TaskResourceViewSet, basename='task-resource')
router.register(r'', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
]