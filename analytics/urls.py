from django.urls import path
from .views import ProjectDashboardView

urlpatterns = [
    path('dashboard/<int:project_id>/', ProjectDashboardView.as_view(), name='project_dashboard'),
]