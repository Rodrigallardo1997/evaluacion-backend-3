"""
URL configuration for Dulce Arte project.
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Auth
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Dashboard (raíz del sitio)
    path('', include('apps.dashboard.urls', namespace='dashboard')),

    # Apps web
    path('usuarios/', include('apps.usuarios.urls', namespace='usuarios')),
    path('catalogo/', include('apps.catalogo.urls', namespace='catalogo')),
    path('pedidos/', include('apps.pedidos.urls', namespace='pedidos')),
    path('inventario/', include('apps.inventario.urls', namespace='inventario')),
    path('despachos/', include('apps.despachos.urls', namespace='despachos')),

    # API REST consolidada
    path('api/', include('config.urls_api')),

    # API Schema y documentación
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Servir media en modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
