from django.contrib import admin
from .models import Sprint

@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'start_date', 'end_date', 'is_active')
    list_filter = ('project', 'is_active') # Фільтр справа (Активні/Неактивні)
    search_fields = ('name', 'description')
    ordering = ('-start_date',)