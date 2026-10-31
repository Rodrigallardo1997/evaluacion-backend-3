"""
Rutas web para inventario.
"""
from django.urls import path
from apps.inventario import views

app_name = "inventario"

urlpatterns = [
    path("", views.inventario_index, name="index"),
]
