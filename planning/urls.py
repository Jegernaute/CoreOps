from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import SprintViewSet # (Створи стандартний ViewSet для Sprint, як ми робили для Project)

router = DefaultRouter()
router.register(r'', SprintViewSet, basename='sprint')
urlpatterns = [path('', include(router.urls))]