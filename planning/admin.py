from django.contrib import admin
from .models import Sprint

@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'start_date', 'end_date', 'status', 'actual_end_date')
    list_filter = ('project', 'status')
    search_fields = ('name', 'description', 'goal')
    ordering = ('-start_date',)