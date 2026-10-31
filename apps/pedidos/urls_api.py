"""
Rutas API para clientes, pedidos, cotizaciones y pagos.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.pedidos.api_views import ClienteViewSet, PedidoViewSet

app_name = "api-pedidos"

router = DefaultRouter()
router.register(r"clientes", ClienteViewSet, basename="cliente")
router.register(r"pedidos", PedidoViewSet, basename="pedido")

urlpatterns = [
    path("", include(router.urls)),
]
