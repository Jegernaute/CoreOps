from rest_framework import permissions

class IsProjectOwnerOrAdmin(permissions.BasePermission):
    """
    Кастомний дозвіл:
    - Читати (GET, HEAD, OPTIONS): Дозволено всім (хто пройшов get_queryset).
    - Змінювати (PUT, PATCH, DELETE): Тільки Власник або Адмін.
    """
    def has_object_permission(self, request, view, obj):
        # 1. Якщо метод безпечний (читання) — пропускаємо
        if request.method in permissions.SAFE_METHODS:
            return True

        # 2. Якщо це Адмін — дозволяємо все
        if request.user.is_staff or request.user.is_superuser:
            return True

        # 3. Універсальна перевірка власника
        # Якщо це Project, беремо obj.owner. Якщо це Sprint/Task, беремо obj.project.owner
        project_owner = getattr(obj, 'owner', None)
        if not project_owner and hasattr(obj, 'project'):
            project_owner = obj.project.owner

        return request.user == project_owner