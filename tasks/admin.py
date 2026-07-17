from django.contrib import admin
from .models import Task, TaskResource, TaskComment, TaskChecklistItem, TaskHistoryEvent


class TaskResourceInline(admin.TabularInline):
    model = TaskResource
    extra = 1


class TaskCommentInline(admin.StackedInline):
    model = TaskComment
    extra = 0
    readonly_fields = ('created_at',)


# --- Інлайн для підзадач (чеклістів) ---
class TaskChecklistItemInline(admin.TabularInline):
    model = TaskChecklistItem
    extra = 1  # Покаже один порожній рядок для швидкого додавання
    fields = ['content', 'is_completed', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'sprint', 'task_type', 'assignee', 'status', 'priority')
    list_filter = ('project', 'sprint', 'status', 'priority', 'task_type')
    search_fields = ('title', 'description')

    # Зручний пошук для полів зв'язку
    autocomplete_fields = ['project', 'assignee', 'reporter', 'milestone', 'sprint']

    # TaskChecklistItemInline до загального списку
    inlines = [TaskChecklistItemInline, TaskResourceInline, TaskCommentInline]

    # Автоматично ставити автора (reporter) як поточного адміна при створенні
    def save_model(self, request, obj, form, change):
        if not obj.reporter_id:
            obj.reporter = request.user
        super().save_model(request, obj, form, change)


@admin.register(TaskComment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'created_at')


# --- Окрема реєстрація для чеклістів (щоб можна було шукати їх окремо) ---
@admin.register(TaskChecklistItem)
class TaskChecklistItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'task', 'content', 'is_completed', 'created_at']
    list_filter = ['is_completed']
    search_fields = ['content', 'task__title']


# --- Реєстрація Історії подій (Тільки для читання) ---
@admin.register(TaskHistoryEvent)
class TaskHistoryEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'task', 'action_type', 'actor', 'timestamp']
    list_filter = ['action_type']
    # Історію в адмінці можна тільки дивитися, щоб ніхто не міг її підробити
    readonly_fields = ['task', 'actor', 'action_type', 'changes', 'timestamp']

    def has_add_permission(self, request):
        return False  # Забороняє створювати історію руками

    def has_change_permission(self, request, obj=None):
        return False  # Забороняє редагувати історію