"""
Rutas web para usuarios.
"""
from django.urls import path
from apps.usuarios import views

app_name = "usuarios"

urlpatterns = [
    path("", views.index, name="index"),
]
