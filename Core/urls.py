from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/users/', include('users.urls')),  # <--- Підключаємо users шляхи
    path('api/v1/projects/', include('projects.urls')), # <--- Підключаємо projects шляхи
    path('api/v1/tasks/', include('tasks.urls')), # <--- Підключаємо tasks шляхи
    path('api/v1/planning/', include('planning.urls')),  # <--- Підключаємо planning шляхи
    path('api/v1/analytics/', include('analytics.urls')), # <--- Підключаємо analytics шляхи

    # --- SWAGGER ---
    # 1. Файл схеми (потрібен для роботи UI)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # 2. Сам інтерфейс Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]