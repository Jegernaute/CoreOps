from django.contrib import admin
from .models import Task, TaskResource, TaskComment


class TaskResourceInline(admin.TabularInline):
    model = TaskResource
    extra = 1


class TaskCommentInline(admin.StackedInline):
    model = TaskComment
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'sprint', 'task_type', 'assignee', 'status', 'priority')
    list_filter = ('project', 'sprint', 'status', 'priority', 'task_type')
    search_fields = ('title', 'description')

    # Зручний пошук для полів зв'язку
    autocomplete_fields = ['project', 'assignee', 'reporter', 'milestone', 'sprint']

    inlines = [TaskResourceInline, TaskCommentInline]

    # Автоматично ставити автора (reporter) як поточного адміна при створенні
    def save_model(self, request, obj, form, change):
        if not obj.reporter_id:
            obj.reporter = request.user
        super().save_model(request, obj, form, change)


@admin.register(TaskComment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'created_at')