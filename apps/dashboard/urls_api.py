"""
Rutas API para Dashboard y Reportes.
"""
from django.urls import path
from apps.dashboard.api_views import DashboardResumenAPIView, ReporteVentasAPIView

app_name = "api-dashboard"

urlpatterns = [
    path("dashboard/resumen/", DashboardResumenAPIView.as_view(), name="resumen"),
    path("reportes/ventas/", ReporteVentasAPIView.as_view(), name="reportes-ventas"),
]
