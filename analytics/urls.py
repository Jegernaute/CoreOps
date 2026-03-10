from django.urls import path
from .views import ProjectDashboardView, ProjectActivityLogView

urlpatterns = [
    path('dashboard/<int:project_id>/', ProjectDashboardView.as_view(), name='project_dashboard'),
    path('logs/<int:project_id>/', ProjectActivityLogView.as_view(), name='project_logs'),
]
