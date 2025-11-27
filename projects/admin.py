from django.contrib import admin
from .models import Project, ProjectMember, ProjectResource, ProjectMilestone


# --- Вкладені форми (Inlines) ---
class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1
    autocomplete_fields = ['user']  # Працює, якщо в CustomUserAdmin є search_fields


class ProjectResourceInline(admin.TabularInline):
    model = ProjectResource
    extra = 0


class ProjectMilestoneInline(admin.TabularInline):
    model = ProjectMilestone
    extra = 0


# --- Головні адмінки ---
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'owner', 'status', 'priority', 'end_date')
    list_filter = ('status', 'priority')
    search_fields = ('name', 'key', 'description')

    # Додаємо вкладки для швидкого редагування зв'язків
    inlines = [ProjectMemberInline, ProjectResourceInline, ProjectMilestoneInline]


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'role', 'joined_at')
    list_filter = ('role', 'project')


@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    # Без цього рядка autocomplete в Tasks не запрацює
    search_fields = ['name']

    # Це просто для краси, щоб список майлстоунів виглядав нормально
    list_display = ['project', 'name', 'deadline','is_completed', 'created_at']