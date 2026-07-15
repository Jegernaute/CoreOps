from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/users/', include('users.urls')),  # <--- Підключає users шляхи
    path('api/v1/projects/', include('projects.urls')), # <--- Підключає projects шляхи
    path('api/v1/tasks/', include('tasks.urls')), # <--- Підключає tasks шляхи
    path('api/v1/planning/', include('planning.urls')),  # <--- Підключає planning шляхи
    path('api/v1/analytics/', include('analytics.urls')), # <--- Підключає analytics шляхи
    path('api/v1/notifications/', include('notifications.urls')),# <--- Підключає notifications шляхи

    # --- SWAGGER ---
    # 1. Файл схеми (потрібен для роботи UI)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # 2. Сам інтерфейс Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# роутинг для віддачі медіафайлів у режимі розробки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)