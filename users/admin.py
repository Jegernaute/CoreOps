from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Invitation

#  admin@example.com , admin, Serge, Vivaldi, admin123

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Налаштування відображення користувача в адмінці.
    Ми розширюємо стандартний UserAdmin, щоб додати наші нові поля.
    """
    model = CustomUser

    # Поля, які відображаються у списку користувачів
    list_display = ('id', 'email', 'first_name', 'last_name', 'global_role', 'job_title', 'is_staff')

    # Поля, по яких можна фільтрувати (справа)
    list_filter = ('global_role', 'is_staff', 'is_active')

    # Поля, по яких працює пошук
    search_fields = ('email', 'first_name', 'last_name', 'telegram')

    # Порядок полів при впорядкуванні
    ordering = ('email',)

    # --- Магія Fieldsets ---
    # Це визначає, як групуються поля на сторінці редагування юзера.
    # Ми беремо стандартні fieldsets від UserAdmin і додаємо свою секцію "Custom Info".
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'avatar')}),
        ('Professional Info', {'fields': ('job_title', 'global_role')}),
        ('Contacts', {'fields': ('phone', 'telegram')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'sender', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('email', 'token')
    readonly_fields = ('token', 'created_at')  # Щоб адмін випадково не змінив токен вручну