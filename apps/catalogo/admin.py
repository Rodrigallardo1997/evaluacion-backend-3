"""
Personalización del Django Admin para Catálogo (Insumos, Recetas y BOM).
"""
from django.contrib import admin
from django.db.models import F
from django.utils import timezone
from django.utils.html import format_html

from apps.catalogo.models import Insumo, Receta, RecetaInsumo


class StockBajoFilter(admin.SimpleListFilter):
    title = "Estado de Stock"
    parameter_name = "estado_stock"

    def lookups(self, request, model_admin):
        return (
            ("bajo", "Stock Bajo (Crítico)"),
            ("normal", "Stock Normal"),
            ("vencido", "Perecederos Vencidos"),
        )

    def queryset(self, request, queryset):
        hoy = timezone.localdate()
        if self.value() == "bajo":
            return queryset.filter(stock_actual__lte=F("stock_minimo"))
        if self.value() == "normal":
            return queryset.filter(stock_actual__gt=F("stock_minimo"))
        if self.value() == "vencido":
            return queryset.filter(perecedero=True, fecha_vencimiento__lt=hoy)
        return queryset


class RecetaInsumoInline(admin.TabularInline):
    model = RecetaInsumo
    extra = 1
    autocomplete_fields = ["insumo"]
    fields = ["insumo", "cantidad", "merma_porcentaje", "cantidad_neta_display", "costo_linea_display"]
    readonly_fields = ["cantidad_neta_display", "costo_linea_display"]

    def cantidad_neta_display(self, obj):
        if obj.pk:
            return f"{obj.cantidad_neta:.3f} {obj.insumo.unidad}"
        return "-"
    cantidad_neta_display.short_description = "Cant. Neta (con merma)"

    def costo_linea_display(self, obj):
        if obj.pk:
            costo = obj.cantidad_neta * obj.insumo.costo_unitario
            return f"${costo:,.2f}"
        return "-"
    costo_linea_display.short_description = "Costo Línea"


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = [
        "nombre",
        "categoria",
        "unidad",
        "stock_actual_badge",
        "stock_minimo",
        "costo_unitario_format",
        "valor_inventario_format",
        "perecedero",
        "vencimiento_badge",
        "activo",
    ]
    list_filter = ["categoria", "unidad", StockBajoFilter, "perecedero", "activo"]
    search_fields = ["nombre"]
    ordering = ["nombre"]
    list_per_page = 25
    readonly_fields = ["creado_en", "actualizado_en", "valor_inventario_display", "stock_bajo_display"]

    fieldsets = (
        ("Identificación", {"fields": ("nombre", "categoria", "unidad", "activo")}),
        (
            "Inventario y Costos",
            {
                "fields": (
                    "stock_actual",
                    "stock_minimo",
                    "costo_unitario",
                    "valor_inventario_display",
                    "stock_bajo_display",
                )
            },
        ),
        ("Perecibilidad", {"fields": ("perecedero", "fecha_vencimiento")}),
        ("Auditoría", {"fields": ("creado_en", "actualizado_en"), "classes": ("collapse",)}),
    )

    def stock_actual_badge(self, obj):
        if obj.stock_bajo:
            return format_html(
                '<span style="color:white; background:#dc3545; padding:3px 8px; border-radius:4px; font-weight:bold;">{} {} (Bajo)</span>',
                obj.stock_actual,
                obj.unidad,
            )
        return f"{obj.stock_actual} {obj.unidad}"
    stock_actual_badge.short_description = "Stock Actual"

    def vencimiento_badge(self, obj):
        if not obj.perecedero or not obj.fecha_vencimiento:
            return "-"
        if obj.esta_vencido:
            return format_html(
                '<span style="color:white; background:#721c24; padding:3px 8px; border-radius:4px; font-weight:bold;">{} (Vencido)</span>',
                obj.fecha_vencimiento,
            )
        return str(obj.fecha_vencimiento)
    vencimiento_badge.short_description = "Vencimiento"

    def costo_unitario_format(self, obj):
        return f"${obj.costo_unitario:,.2f}"
    costo_unitario_format.short_description = "Costo Unit."

    def valor_inventario_format(self, obj):
        return f"${obj.valor_inventario:,.2f}"
    valor_inventario_format.short_description = "Valor Total"

    def valor_inventario_display(self, obj):
        return f"${obj.valor_inventario:,.2f}"
    valor_inventario_display.short_description = "Valor Total Inventario"

    def stock_bajo_display(self, obj):
        return "Sí (Alerta activa)" if obj.stock_bajo else "No (Stock suficiente)"
    stock_bajo_display.short_description = "Alerta de Stock Bajo"

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return not request.user.es_cliente and not request.user.es_repartidor

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser or request.user.es_admin or request.user.es_cocina:
            return True
        return False

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.es_admin or request.user.es_cocina

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.es_admin


@admin.register(Receta)
class RecetaAdmin(admin.ModelAdmin):
    list_display = [
        "nombre",
        "categoria",
        "rendimiento",
        "precio_base_format",
        "costo_produccion_format",
        "margen_real_badge",
        "tiempo_preparacion_min",
        "activo",
    ]
    list_filter = ["categoria", "activo", "creado_en"]
    search_fields = ["nombre", "descripcion"]
    ordering = ["nombre"]
    list_per_page = 25
    inlines = [RecetaInsumoInline]
    readonly_fields = [
        "creado_en",
        "actualizado_en",
        "costo_insumos_display",
        "costo_unitario_display",
        "margen_real_display",
    ]

    fieldsets = (
        ("Información Básica", {"fields": ("nombre", "categoria", "descripcion", "imagen", "activo")}),
        (
            "Costos y Precios",
            {
                "fields": (
                    "rendimiento",
                    "precio_base",
                    "margen_deseado",
                    "costo_insumos_display",
                    "costo_unitario_display",
                    "margen_real_display",
                )
            },
        ),
        ("Tiempos", {"fields": ("tiempo_preparacion_min",)}),
        ("Auditoría", {"fields": ("creado_en", "actualizado_en"), "classes": ("collapse",)}),
    )

    def precio_base_format(self, obj):
        return f"${obj.precio_base:,.0f}"
    precio_base_format.short_description = "Precio Base"

    def costo_produccion_format(self, obj):
        return f"${obj.costo_unitario_produccion:,.2f}"
    costo_produccion_format.short_description = "Costo Unit. Prod."

    def margen_real_badge(self, obj):
        margen = obj.margen_real
        color = "#28a745" if margen >= obj.margen_deseado else "#e0a800"
        return format_html(
            '<span style="color:white; background:{}; padding:3px 8px; border-radius:4px; font-weight:bold;">{:.1f}%</span>',
            color,
            margen,
        )
    margen_real_badge.short_description = "Margen Real"

    def costo_insumos_display(self, obj):
        return f"${obj.costo_insumos:,.2f}"
    costo_insumos_display.short_description = "Costo Total Insumos (BOM)"

    def costo_unitario_display(self, obj):
        return f"${obj.costo_unitario_produccion:,.2f}"
    costo_unitario_display.short_description = "Costo Unitario Producción"

    def margen_real_display(self, obj):
        return f"{obj.margen_real:.2f}% (Margen deseado: {obj.margen_deseado}%)"
    margen_real_display.short_description = "Margen Real vs Deseado"

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return not request.user.es_cliente and not request.user.es_repartidor

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.es_admin or request.user.es_cocina

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.es_admin or request.user.es_cocina

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.es_admin


@admin.register(RecetaInsumo)
class RecetaInsumoAdmin(admin.ModelAdmin):
    list_display = ["receta", "insumo", "cantidad", "merma_porcentaje", "cantidad_neta"]
    list_filter = ["receta__categoria", "insumo__categoria"]
    search_fields = ["receta__nombre", "insumo__nombre"]
    autocomplete_fields = ["receta", "insumo"]
    list_per_page = 25
