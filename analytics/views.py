from rest_framework import viewsets, permissions, views, response
from django.db.models import Count, Q
from django.utils import timezone
from .models import ProjectActivityLog
from .serializers import ActivityLogSerializer 
from tasks.models import Task
from projects.models import ProjectMember


class ProjectDashboardView(views.APIView):
    """
    GET /analytics/dashboard/{project_id}/
    Повертає повну статистику для дашборду менеджера.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id):
        # 1. Перевіряємо доступ
        if not ProjectMember.objects.filter(project_id=project_id, user=request.user).exists():
            return response.Response({"error": "Forbidden"}, status=403)

        # 2. Збираємо дані
        tasks = Task.objects.filter(project_id=project_id)
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status=Task.STATUS_DONE).count()

        # Completion Rate (Прогрес)
        progress = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0

        # Розподіл по статусах (Pie Chart)
        # Поверне: [{'status': 'to_do', 'count': 5}, {'status': 'done', 'count': 2}]
        status_distribution = tasks.values('status').annotate(count=Count('id'))

        # KPI ("Пульс")
        overdue_count = tasks.filter(
            due_date__lt=timezone.now(),
            status__in=[Task.STATUS_TODO, Task.STATUS_IN_PROGRESS]
        ).count()

        critical_count = tasks.filter(priority='critical').count()

        data = {
            "project_health": {
                "total_tasks": total_tasks,
                "progress_percent": progress,
                "overdue_tasks": overdue_count,
                "critical_tasks": critical_count
            },
            "charts": {
                "status_distribution": status_distribution
            }
        }
        return response.Response(data)