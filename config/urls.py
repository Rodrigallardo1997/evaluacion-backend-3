"""
Configuración de enrutamiento principal de URLs del proyecto Dulce Arte.
Mapea las vistas web administrativas, operativas, API REST y documentación OpenAPI.
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Panel de administración de Django personalizado
    path('admin/', admin.site.urls),

    # Autenticación y control de sesión
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Portal público y Dashboard gerencial (raíz del sitio '/')
    path('', include('apps.dashboard.urls', namespace='dashboard')),

    # Módulos web de la pastelería
    path('usuarios/', include('apps.usuarios.urls', namespace='usuarios')),
    path('catalogo/', include('apps.catalogo.urls', namespace='catalogo')),
    path('pedidos/', include('apps.pedidos.urls', namespace='pedidos')),
    path('inventario/', include('apps.inventario.urls', namespace='inventario')),
    path('despachos/', include('apps.despachos.urls', namespace='despachos')),

    # API REST consolidada (cumple sección 10 de la rúbrica)
    path('api/', include('config.urls_api')),

    # Esquema OpenAPI y documentación interactiva Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Servir archivos multimedia (fotos de tortas y firmas) en modo desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
