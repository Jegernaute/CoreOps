from rest_framework import permissions


class IsAuthorOrProjectOwnerOrAdmin(permissions.BasePermission):
    """
    Кастомний дозвіл для Коментарів та Ресурсів (Файлів):
    - Читання (GET): Дозволено всім (фільтрація відбувається в get_queryset).
    - Редагування (PUT/PATCH): Дозволено ТІЛЬКИ автору об'єкта.
    - Видалення (DELETE): Дозволено Автору, Адміну, Власнику проєкту.
    """

    def has_object_permission(self, request, view, obj):
        # 1. Читання дозволено всім (хто зміг отримати об'єкт через get_queryset)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Визначаємо, хто є автором об'єкта.
        # У TaskComment це поле 'author', а у TaskResource — 'uploaded_by'.
        object_author = getattr(obj, 'author', None) or getattr(obj, 'uploaded_by', None)

        # 2. Редагування (PUT, PATCH) - ТІЛЬКИ АВТОР
        if request.method in ['PUT', 'PATCH']:
            return request.user == object_author

        # 3. Видалення (DELETE) - Автор
        if request.method == 'DELETE':

            # Перевірка на Адміна
            if request.user.is_staff or request.user.is_superuser:
                return True

            # Перевірка на Автора коментаря/файлу
            if request.user == object_author:
                return True

            # Перевірка на Власника проєкту (дістаємося до нього через зв'язок obj -> task -> project)
            if request.user == obj.task.project.owner:
                return True

            return False

        return False