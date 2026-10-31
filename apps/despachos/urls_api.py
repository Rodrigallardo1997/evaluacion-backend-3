"""
Rutas API para despachos y rutas de entrega.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.despachos.api_views import RutaDespachoViewSet, DespachoViewSet

app_name = "api-despachos"

router = DefaultRouter()
router.register(r"rutas", RutaDespachoViewSet, basename="ruta")
router.register(r"despachos", DespachoViewSet, basename="despacho")

urlpatterns = [
    path("", include(router.urls)),
]
