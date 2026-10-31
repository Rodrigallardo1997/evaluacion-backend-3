"""
Personalización del Django Admin para Rutas de Despacho y Entregas.
"""
from django.contrib import admin
from django.utils.html import format_html

from apps.despachos.models import RutaDespacho, Despacho


class DespachoInline(admin.TabularInline):
    model = Despacho
    extra = 0
    fields = ["orden", "pedido", "estado", "receptor_nombre", "fecha_entrega", "evidencia_display"]
    readonly_fields = ["evidencia_display"]
    autocomplete_fields = ["pedido"]

    def evidencia_display(self, obj):
        if not obj.pk:
            return "-"
        items = []
        if obj.firma_digital:
            items.append("Firma ✓")
        if obj.foto_comprobante:
            items.append("Foto ✓")
        return ", ".join(items) if items else "Pendiente"
    evidencia_display.short_description = "Evidencia"


@admin.register(RutaDespacho)
class RutaDespachoAdmin(admin.ModelAdmin):
    list_display = [
        "codigo",
        "fecha",
        "repartidor",
        "vehiculo",
        "estado_badge",
        "total_paradas",
        "entregadas",
        "pendientes",
        "esta_completa_badge",
    ]
    list_filter = ["estado", "fecha", "repartidor"]
    search_fields = ["codigo", "repartidor__first_name", "repartidor__last_name", "vehiculo"]
    ordering = ["-fecha"]
    date_hierarchy = "fecha"
    list_per_page = 25
    autocomplete_fields = ["repartidor"]
    inlines = [DespachoInline]
    readonly_fields = ["codigo", "creado_en", "actualizado_en", "creado_por"]

    fieldsets = (
        ("Identificación de Ruta", {"fields": ("codigo", "fecha", "repartidor", "vehiculo", "estado")}),
        ("Detalles", {"fields": ("observaciones",)}),
        ("Auditoría", {"fields": ("creado_por", "creado_en", "actualizado_en"), "classes": ("collapse",)}),
    )

    def estado_badge(self, obj):
        colores = {
            RutaDespacho.Estado.PLANIFICADA: "#17a2b8",
            RutaDespacho.Estado.EN_RUTA: "#007bff",
            RutaDespacho.Estado.COMPLETADA: "#28a745",
            RutaDespacho.Estado.CANCELADA: "#dc3545",
        }
        color = colores.get(obj.estado, "#6c757d")
        return format_html(
            '<span style="color:white; background:{}; padding:3px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color,
            obj.get_estado_display(),
        )
    estado_badge.short_description = "Estado"

    def esta_completa_badge(self, obj):
        if obj.esta_completa:
            return format_html('<span style="color:#28a745; font-weight:bold;">✓ Completa</span>')
        return format_html('<span style="color:#6c757d;">En progreso</span>')
    esta_completa_badge.short_description = "Cierre"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
        if not obj.codigo:
            obj.generar_codigo()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.es_admin:
            return qs
        if request.user.es_repartidor:
            return qs.filter(repartidor=request.user)
        return qs

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return not request.user.es_cliente


@admin.register(Despacho)
class DespachoAdmin(admin.ModelAdmin):
    list_display = [
        "ruta",
        "orden",
        "pedido",
        "estado_badge",
        "receptor_nombre",
        "fecha_entrega",
        "evidencia_display",
    ]
    list_filter = ["estado", "ruta__fecha", "ruta__repartidor"]
    search_fields = ["pedido__codigo", "receptor_nombre", "ruta__codigo"]
    ordering = ["ruta", "orden"]
    list_per_page = 25
    autocomplete_fields = ["ruta", "pedido"]
    readonly_fields = ["firma_preview", "foto_preview"]

    def estado_badge(self, obj):
        colores = {
            Despacho.Estado.PENDIENTE: "#ffc107",
            Despacho.Estado.ENTREGADO: "#28a745",
            Despacho.Estado.FALLIDO: "#dc3545",
        }
        color = colores.get(obj.estado, "#6c757d")
        return format_html(
            '<span style="color:white; background:{}; padding:3px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color,
            obj.get_estado_display(),
        )
    estado_badge.short_description = "Estado"

    def evidencia_display(self, obj):
        badges = []
        if obj.firma_digital:
            badges.append('<span style="color:#28a745;">Firma ✓</span>')
        if obj.foto_comprobante:
            badges.append('<span style="color:#007bff;">Foto ✓</span>')
        return format_html(" | ".join(badges)) if badges else format_html('<span style="color:#6c757d;">Sin evidencia</span>')
    evidencia_display.short_description = "Evidencia de Entrega"

    def firma_preview(self, obj):
        if obj.firma_digital:
            return format_html('<img src="{}" style="max-width:300px; border:1px solid #ccc; background:#fff; padding:5px; border-radius:4px;"/>', obj.firma_digital)
        return "No registrada"
    firma_preview.short_description = "Vista Previa Firma Digital"

    def foto_preview(self, obj):
        if obj.foto_comprobante:
            return format_html('<img src="{}" style="max-width:200px; border-radius:4px;"/>', obj.foto_comprobante.url)
        return "No adjunta"
    foto_preview.short_description = "Vista Previa Foto"
