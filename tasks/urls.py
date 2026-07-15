from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TaskViewSet, TaskCommentViewSet,
    TaskResourceViewSet, TaskChecklistViewSet, TaskHistoryViewSet
)

router = DefaultRouter()
router.register(r'comments', TaskCommentViewSet, basename='task-comment')
router.register(r'resources', TaskResourceViewSet, basename='task-resource')
# роутинг для чеклістів та історії
router.register(r'checklists', TaskChecklistViewSet, basename='task-checklist')
router.register(r'history', TaskHistoryViewSet, basename='task-history')
router.register(r'', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
]