"""
URLs web para el dashboard, reportes y landing page pública.
"""
from django.urls import path
from apps.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("inicio/", views.landing_view, name="landing"),
    path("reportes/", views.reportes, name="reportes"),
]
