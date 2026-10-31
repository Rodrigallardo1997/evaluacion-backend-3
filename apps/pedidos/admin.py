"""
Personalización del Django Admin para Pedidos, Clientes, Cotizaciones y Pagos.
"""
import csv
from decimal import Decimal
from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.html import format_html

from apps.pedidos.models import (
    Cliente,
    Pedido,
    DetallePedido,
    Cotizacion,
    HistorialEstadoPedido,
    Pago,
)
from apps.pedidos.services.cotizacion_service import emitir_cotizacion, transicionar_estado


# ----------------------------------------------------------------------
# Inlines
# ----------------------------------------------------------------------

class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    autocomplete_fields = ["receta"]
    fields = ["receta", "cantidad", "precio_unitario", "personalizacion", "subtotal_display"]
    readonly_fields = ["subtotal_display"]

    def subtotal_display(self, obj):
        if obj.pk:
            return f"${obj.subtotal:,.0f}"
        return "-"
    subtotal_display.short_description = "Subtotal"

    def has_change_permission(self, request, obj=None):
        if obj and obj.estado != Pedido.Estado.BORRADOR:
            return False
        return True

    def has_add_permission(self, request, obj=None):
        if obj and obj.estado != Pedido.Estado.BORRADOR:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj and obj.estado != Pedido.Estado.BORRADOR:
            return False
        return True


class CotizacionInline(admin.StackedInline):
    model = Cotizacion
    extra = 0
    readonly_fields = [
        "numero",
        "fecha_emision",
        "valida_hasta",
        "subtotal",
        "descuento",
        "total",
        "estado",
        "condiciones",
        "creado_por",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    fields = ["tipo", "metodo", "monto", "referencia", "comprobante", "fecha", "registrado_por"]
    readonly_fields = ["fecha", "registrado_por"]

    def has_module_permission(self, request):
        if request.user.es_cocina:
            return False
        return True


class HistorialEstadoPedidoInline(admin.TabularInline):
    model = HistorialEstadoPedido
    extra = 0
    readonly_fields = ["estado_anterior", "estado_nuevo", "usuario", "observacion", "fecha"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ----------------------------------------------------------------------
# Admins
# ----------------------------------------------------------------------

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["nombre_completo", "rut", "telefono", "email", "direccion_corta", "activo", "pedidos_count"]
    list_filter = ["activo", "creado_en"]
    search_fields = ["nombre_completo", "rut", "telefono", "email"]
    ordering = ["nombre_completo"]
    list_per_page = 25
    autocomplete_fields = ["usuario"]
    actions = ["exportar_clientes_csv"]

    def direccion_corta(self, obj):
        return obj.direccion[:40] + "..." if len(obj.direccion) > 40 else obj.direccion
    direccion_corta.short_description = "Dirección"

    def pedidos_count(self, obj):
        return obj.pedidos.count()
    pedidos_count.short_description = "Total Pedidos"

    @admin.action(description="Exportar clientes seleccionados a CSV")
    def exportar_clientes_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="clientes_dulcearte.csv"'
        writer = csv.writer(response)
        writer.writerow(["ID", "Nombre Completo", "RUT", "Teléfono", "Email", "Dirección", "Activo"])
        for cliente in queryset:
            writer.writerow([
                cliente.id,
                cliente.nombre_completo,
                cliente.rut or "",
                cliente.telefono,
                cliente.email or "",
                cliente.direccion,
                cliente.activo,
            ])
        return response

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return not request.user.es_cliente and not request.user.es_cocina


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = [
        "codigo",
        "cliente",
        "estado_badge",
        "prioridad_badge",
        "fecha_entrega_format",
        "total_format",
        "anticipo_format",
        "saldo_format",
        "inventario_badge",
        "version",
    ]
    list_filter = ["estado", "prioridad", "inventario_descontado", "fecha_entrega", "vendedor"]
    search_fields = ["codigo", "cliente__nombre_completo", "cliente__rut", "direccion_entrega"]
    date_hierarchy = "fecha_entrega"
    ordering = ["-creado_en"]
    list_per_page = 25
    autocomplete_fields = ["cliente", "vendedor"]
    inlines = [DetallePedidoInline, CotizacionInline, PagoInline, HistorialEstadoPedidoInline]
    readonly_fields = [
        "codigo",
        "subtotal",
        "total",
        "anticipo",
        "saldo",
        "inventario_descontado",
        "version",
        "fecha_entrega_real",
        "motivo_cancelacion",
        "cancelado_por",
        "creado_en",
        "actualizado_en",
    ]
    actions = ["marcar_en_preparacion", "generar_cotizaciones", "exportar_pedidos_csv"]

    fieldsets = (
        (
            "Identificación y Cliente",
            {"fields": ("codigo", "cliente", "vendedor", "estado", "prioridad", "version")},
        ),
        (
            "Entrega y Diseño",
            {
                "fields": (
                    "fecha_entrega",
                    "fecha_entrega_real",
                    "direccion_entrega",
                    "diseno_descripcion",
                    "imagen_referencia",
                    "observaciones",
                )
            },
        ),
        (
            "Valores Económicos",
            {
                "fields": (
                    "subtotal",
                    "descuento",
                    "total",
                    "anticipo",
                    "saldo",
                    "inventario_descontado",
                )
            },
        ),
        (
            "Cancelación y Auditoría",
            {
                "fields": (
                    "motivo_cancelacion",
                    "cancelado_por",
                    "creado_en",
                    "actualizado_en",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def estado_badge(self, obj):
        colores = {
            Pedido.Estado.BORRADOR: "#6c757d",
            Pedido.Estado.COTIZADO: "#17a2b8",
            Pedido.Estado.CONFIRMADO: "#007bff",
            Pedido.Estado.EN_PREPARACION: "#fd7e14",
            Pedido.Estado.HORNEADO_DECORADO: "#ffc107",
            Pedido.Estado.CONTROL_CALIDAD: "#20c997",
            Pedido.Estado.LISTO: "#28a745",
            Pedido.Estado.EN_DESPACHO: "#6610f2",
            Pedido.Estado.ENTREGADO: "#198754",
            Pedido.Estado.CANCELADO: "#dc3545",
        }
        color = colores.get(obj.estado, "#6c757d")
        return format_html(
            '<span style="color:white; background:{}; padding:3px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color,
            obj.get_estado_display(),
        )
    estado_badge.short_description = "Estado"

    def prioridad_badge(self, obj):
        colores = {
            Pedido.Prioridad.BAJA: "#6c757d",
            Pedido.Prioridad.MEDIA: "#0d6efd",
            Pedido.Prioridad.ALTA: "#fd7e14",
            Pedido.Prioridad.URGENTE: "#dc3545",
        }
        color = colores.get(obj.prioridad, "#6c757d")
        return format_html(
            '<span style="color:white; background:{}; padding:2px 6px; border-radius:3px; font-size:11px;">{}</span>',
            color,
            obj.get_prioridad_display(),
        )
    prioridad_badge.short_description = "Prioridad"

    def fecha_entrega_format(self, obj):
        return obj.fecha_entrega.strftime("%d-%m-%Y %H:%M")
    fecha_entrega_format.short_description = "Fecha Entrega"

    def total_format(self, obj):
        return f"${obj.total:,.0f}"
    total_format.short_description = "Total"

    def anticipo_format(self, obj):
        return f"${obj.anticipo:,.0f}"
    anticipo_format.short_description = "Anticipo"

    def saldo_format(self, obj):
        color = "#dc3545" if obj.saldo > 0 else "#28a745"
        return format_html('<span style="color:{}; font-weight:bold;">${:,.0f}</span>', color, obj.saldo)
    saldo_format.short_description = "Saldo"

    def inventario_badge(self, obj):
        if obj.inventario_descontado:
            return format_html('<span style="color:#28a745; font-weight:bold;">✓ Descontado</span>')
        return format_html('<span style="color:#6c757d;">—</span>')
    inventario_badge.short_description = "BOM Stock"

    def save_model(self, request, obj, form, change):
        if not change and not obj.vendedor_id:
            obj.vendedor = request.user
        super().save_model(request, obj, form, change)
        if not obj.codigo:
            obj.generar_codigo()
        obj.recalcular_totales()
        Pedido.objects.filter(pk=obj.pk).update(
            subtotal=obj.subtotal,
            total=obj.total,
            anticipo=obj.anticipo,
            saldo=obj.saldo,
        )

    @admin.action(description="Marcar pedidos seleccionados como En Preparación (Cocina)")
    def marcar_en_preparacion(self, request, queryset):
        actualizados = 0
        for pedido in queryset.filter(estado=Pedido.Estado.CONFIRMADO):
            try:
                transicionar_estado(
                    pedido_id=pedido.id,
                    nuevo_estado=Pedido.Estado.EN_PREPARACION,
                    usuario=request.user,
                    version=pedido.version,
                    observacion="Transición masiva desde Django Admin",
                )
                actualizados += 1
            except Exception as e:
                self.message_user(request, f"Error en pedido {pedido.codigo}: {e}", level=messages.ERROR)
        if actualizados:
            self.message_user(request, f"{actualizados} pedidos pasaron a En Preparación.", level=messages.SUCCESS)

    @admin.action(description="Generar cotización para pedidos seleccionados en BORRADOR")
    def generar_cotizaciones(self, request, queryset):
        exitos = 0
        for pedido in queryset.filter(estado=Pedido.Estado.BORRADOR):
            try:
                emitir_cotizacion(pedido_id=pedido.id, usuario=request.user)
                exitos += 1
            except Exception as e:
                self.message_user(request, f"Error en pedido #{pedido.pk}: {e}", level=messages.ERROR)
        if exitos:
            self.message_user(request, f"Se generaron {exitos} cotizaciones exitosamente.", level=messages.SUCCESS)

    @admin.action(description="Exportar pedidos seleccionados a CSV")
    def exportar_pedidos_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="pedidos_dulcearte.csv"'
        writer = csv.writer(response)
        writer.writerow(["Código", "Cliente", "Estado", "Prioridad", "Fecha Entrega", "Total", "Anticipo", "Saldo"])
        for p in queryset:
            writer.writerow([
                p.codigo,
                p.cliente.nombre_completo,
                p.get_estado_display(),
                p.get_prioridad_display(),
                p.fecha_entrega.strftime("%d-%m-%Y %H:%M"),
                p.total,
                p.anticipo,
                p.saldo,
            ])
        return response

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.es_admin:
            return qs
        if request.user.es_repartidor:
            return qs.filter(despachos__ruta__repartidor=request.user).distinct()
        return qs

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return not request.user.es_cliente


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ["pedido", "receta", "cantidad", "precio_unitario", "subtotal"]
    search_fields = ["pedido__codigo", "receta__nombre"]
    autocomplete_fields = ["pedido", "receta"]
    list_per_page = 25


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ["numero", "pedido", "fecha_emision", "valida_hasta", "total_format", "estado_badge", "creado_por"]
    list_filter = ["estado", "valida_hasta", "fecha_emision"]
    search_fields = ["numero", "pedido__codigo", "pedido__cliente__nombre_completo"]
    ordering = ["-fecha_emision"]
    list_per_page = 25
    readonly_fields = ["numero", "fecha_emision", "subtotal", "descuento", "total", "creado_por"]

    def total_format(self, obj):
        return f"${obj.total:,.0f}"
    total_format.short_description = "Total"

    def estado_badge(self, obj):
        colores = {
            Cotizacion.Estado.VIGENTE: "#28a745",
            Cotizacion.Estado.ACEPTADA: "#007bff",
            Cotizacion.Estado.RECHAZADA: "#dc3545",
            Cotizacion.Estado.VENCIDA: "#6c757d",
        }
        color = colores.get(obj.estado, "#6c757d")
        return format_html(
            '<span style="color:white; background:{}; padding:3px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color,
            obj.get_estado_display(),
        )
    estado_badge.short_description = "Estado"


@admin.register(HistorialEstadoPedido)
class HistorialEstadoPedidoAdmin(admin.ModelAdmin):
    list_display = ["pedido", "estado_anterior", "estado_nuevo", "usuario", "fecha", "observacion_corta"]
    list_filter = ["estado_nuevo", "fecha"]
    search_fields = ["pedido__codigo", "observacion", "usuario__username"]
    ordering = ["-fecha"]
    list_per_page = 25
    readonly_fields = ["pedido", "estado_anterior", "estado_nuevo", "usuario", "observacion", "fecha"]

    def observacion_corta(self, obj):
        return obj.observacion[:50] + "..." if len(obj.observacion) > 50 else obj.observacion
    observacion_corta.short_description = "Observación"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ["pedido", "tipo", "metodo", "monto_format", "referencia", "fecha", "registrado_por"]
    list_filter = ["tipo", "metodo", "fecha"]
    search_fields = ["pedido__codigo", "referencia"]
    ordering = ["-fecha"]
    list_per_page = 25
    autocomplete_fields = ["pedido"]
    readonly_fields = ["fecha", "registrado_por"]

    def monto_format(self, obj):
        return f"${obj.monto:,.0f}"
    monto_format.short_description = "Monto"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)
        obj.pedido.recalcular_totales()
        obj.pedido.save(update_fields=["anticipo", "saldo"])

    def delete_model(self, request, obj):
        pedido = obj.pedido
        super().delete_model(request, obj)
        pedido.recalcular_totales()
        pedido.save(update_fields=["anticipo", "saldo"])

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        # Cocina no ve pagos
        return not request.user.es_cliente and not request.user.es_cocina and not request.user.es_repartidor
