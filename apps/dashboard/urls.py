"""
URLs web para el dashboard y reportes.
"""
from django.urls import path
from apps.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("reportes/", views.reportes, name="reportes"),
]
