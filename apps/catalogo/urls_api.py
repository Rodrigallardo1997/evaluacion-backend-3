"""
Rutas API para catálogo (Insumos y Recetas).
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.catalogo.api_views import InsumoViewSet, RecetaViewSet

app_name = "api-catalogo"

router = DefaultRouter()
router.register(r"insumos", InsumoViewSet, basename="insumo")
router.register(r"recetas", RecetaViewSet, basename="receta")

urlpatterns = [
    path("", include(router.urls)),
]
