from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet

# Router автоматично створить URL:
# GET /projects/
# POST /projects/
# GET /projects/{id}/
router = DefaultRouter()
router.register(r'', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
]