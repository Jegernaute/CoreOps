from django.contrib import admin
from .models import ProjectActivityLog


@admin.register(ProjectActivityLog)
class ProjectActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'project', 'actor', 'action_type', 'target')
    list_filter = ('action_type', 'project')  # Фільтр по типу дії (Створено/Видалено)
    search_fields = ('target', 'actor__email')  # Пошук по назві задачі або мейлу юзера

    # Робимо поля тільки для читання, щоб адмін не підробив історію
    readonly_fields = ('project', 'actor', 'action_type', 'target', 'timestamp')

    # Забороняємо додавати логи вручну (вони мають писатися тільки автоматично через сигнали)
    def has_add_permission(self, request):
        return False

    # Забороняємо видаляти логи (опціонально)
    def has_delete_permission(self, request, obj=None):
        return False