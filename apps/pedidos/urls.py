"""
Rutas web para pedidos, clientes y kanban.
"""
from django.urls import path
from apps.pedidos import views

app_name = "pedidos"

urlpatterns = [
    # Pedidos
    path("", views.pedidos_lista, name="index"),
    path("nuevo/", views.pedido_nuevo, name="nuevo"),
    path("<int:pk>/", views.pedido_detalle, name="detalle"),
    path("<int:pk>/cotizar/", views.accion_cotizar, name="cotizar"),
    path("<int:pk>/confirmar/", views.accion_confirmar, name="confirmar"),
    path("<int:pk>/cancelar/", views.accion_cancelar, name="cancelar"),
    path("<int:pk>/pagos/", views.registrar_pago_view, name="registrar_pago"),
    path("<int:pk>/imprimir-cotizacion/", views.imprimir_cotizacion, name="imprimir_cotizacion"),
    # Kanban
    path("kanban/", views.kanban_view, name="kanban"),
    # Clientes
    path("clientes/", views.clientes_lista, name="clientes"),
    path("clientes/nuevo/", views.cliente_crear, name="cliente_nuevo"),
    path("clientes/<int:pk>/editar/", views.cliente_editar, name="cliente_editar"),
    # Portal Cliente
    path("mis-pedidos/", views.mis_pedidos, name="mis_pedidos"),
]
