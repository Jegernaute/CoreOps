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

        # 3. Якщо це Власник — дозволяємо редагувати
        return obj.owner == request.user