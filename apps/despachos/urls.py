"""
Rutas web para rutas de despacho y entregas.
"""
from django.urls import path
from apps.despachos import views

app_name = "despachos"

urlpatterns = [
    path("", views.rutas_lista, name="index"),
    path("rutas/", views.rutas_lista, name="rutas"),
    path("rutas/nueva/", views.ruta_nueva, name="ruta_nueva"),
    path("rutas/<int:pk>/", views.ruta_detalle, name="detalle"),
    path("rutas/<int:pk>/iniciar/", views.accion_iniciar_ruta, name="iniciar_ruta"),
    path("mis-rutas/", views.mis_rutas, name="mis_rutas"),
    path("entregas/", views.entregas_pendientes, name="entregas"),
    path("paradas/<int:pk>/confirmar/", views.entrega_confirmar, name="confirmar_entrega"),
    path("paradas/<int:pk>/fallar/", views.entrega_fallida, name="entrega_fallida"),
]
