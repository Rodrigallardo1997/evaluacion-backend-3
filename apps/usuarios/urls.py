"""
Rutas web para gestión de usuarios y roles.
"""
from django.urls import path
from apps.usuarios import views

app_name = "usuarios"

urlpatterns = [
    path("", views.usuarios_lista, name="lista"),
    path("crear/", views.usuario_crear, name="crear"),
    path("<int:pk>/editar/", views.usuario_editar, name="editar"),
    path("<int:pk>/cambiar-rol/", views.usuario_cambiar_rol, name="cambiar_rol"),
]
