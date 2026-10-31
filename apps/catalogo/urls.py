"""
Rutas web para catálogo de recetas e insumos.
"""
from django.urls import path
from apps.catalogo import views

app_name = "catalogo"

urlpatterns = [
    # Recetas
    path("", views.recetas_lista, name="index"),
    path("recetas/nueva/", views.receta_crear, name="receta_nueva"),
    path("recetas/<int:pk>/editar/", views.receta_editar, name="receta_editar"),
    # Insumos
    path("insumos/", views.insumos_lista, name="insumos"),
    path("insumos/nuevo/", views.insumo_crear, name="insumo_nuevo"),
    path("insumos/<int:pk>/editar/", views.insumo_editar, name="insumo_editar"),
    path("insumos/<int:pk>/ajustar/", views.insumo_ajustar, name="insumo_ajustar"),
]
