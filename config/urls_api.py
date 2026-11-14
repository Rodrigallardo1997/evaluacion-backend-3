"""
Rutas consolidadas de la API REST de Dulce Arte.
Mapea exactamente los endpoints especificados en la sección 10 de la rúbrica.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.catalogo.api_views import InsumoViewSet, RecetaViewSet, CatalogoPublicoAPIView
from apps.dashboard.api_views import DashboardResumenAPIView, ReporteVentasAPIView
from apps.despachos.api_views import RutaDespachoViewSet, DespachoViewSet
from apps.pedidos.api_views import ClienteViewSet, PedidoViewSet
from apps.usuarios.api_views import LoginAPIView, LogoutAPIView, MeAPIView

router = DefaultRouter()
# /api/clientes/
router.register(r"clientes", ClienteViewSet, basename="cliente")
# /api/insumos/
router.register(r"insumos", InsumoViewSet, basename="insumo")
# /api/recetas/
router.register(r"recetas", RecetaViewSet, basename="receta")
# /api/pedidos/
router.register(r"pedidos", PedidoViewSet, basename="pedido")
# /api/rutas/
router.register(r"rutas", RutaDespachoViewSet, basename="ruta")
# /api/despachos/
router.register(r"despachos", DespachoViewSet, basename="despacho")

urlpatterns = [
    # Auth
    path("auth/login/", LoginAPIView.as_view(), name="api-login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="api-logout"),
    path("auth/me/", MeAPIView.as_view(), name="api-me"),
    # Catálogo público (Frontend desacoplado)
    path("catalogo-publico/", CatalogoPublicoAPIView.as_view(), name="api-catalogo-publico"),
    # Dashboard & Reportes
    path("dashboard/resumen/", DashboardResumenAPIView.as_view(), name="api-dashboard-resumen"),
    path("reportes/ventas/", ReporteVentasAPIView.as_view(), name="api-reportes-ventas"),
    # ViewSets
    path("", include(router.urls)),
]
