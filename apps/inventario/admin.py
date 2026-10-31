"""
Personalización del Django Admin para Inventario y Movimientos de Stock.
"""
from django.contrib import admin
from apps.inventario.models import MovimientoInventario


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = [
        "fecha",
        "insumo",
        "tipo",
        "cantidad",
        "stock_anterior",
        "stock_nuevo",
        "motivo",
        "pedido",
        "usuario",
    ]
    list_filter = ["tipo", "fecha", "insumo__categoria"]
    search_fields = ["insumo__nombre", "motivo", "pedido__codigo", "usuario__username"]
    ordering = ["-fecha"]
    date_hierarchy = "fecha"
    list_per_page = 25

    # MovimientoInventario es estrictamente de solo lectura en Admin
    readonly_fields = [
        "insumo",
        "tipo",
        "cantidad",
        "stock_anterior",
        "stock_nuevo",
        "motivo",
        "pedido",
        "usuario",
        "fecha",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return not request.user.es_cliente and not request.user.es_repartidor
