"""
Serializers para el módulo de catálogo (Insumos, Recetas y BOM).
"""
from decimal import Decimal
from rest_framework import serializers

from apps.catalogo.models import Insumo, Receta, RecetaInsumo


class InsumoSerializer(serializers.ModelSerializer):
    stock_bajo = serializers.BooleanField(read_only=True)
    valor_inventario = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    esta_vencido = serializers.BooleanField(read_only=True)

    class Meta:
        model = Insumo
        fields = [
            "id",
            "nombre",
            "categoria",
            "unidad",
            "stock_actual",
            "stock_minimo",
            "costo_unitario",
            "perecedero",
            "fecha_vencimiento",
            "activo",
            "stock_bajo",
            "valor_inventario",
            "esta_vencido",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]


class AjusteInsumoSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=["ENTRADA", "SALIDA", "AJUSTE", "MERMA"])
    cantidad = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"))
    motivo = serializers.CharField(max_length=200, required=True)


class RecetaInsumoSerializer(serializers.ModelSerializer):
    insumo_nombre = serializers.ReadOnlyField(source="insumo.nombre")
    insumo_unidad = serializers.ReadOnlyField(source="insumo.unidad")
    costo_unitario_insumo = serializers.DecimalField(
        source="insumo.costo_unitario", max_digits=10, decimal_places=2, read_only=True
    )
    cantidad_neta = serializers.DecimalField(max_digits=10, decimal_places=3, read_only=True)
    costo_linea = serializers.SerializerMethodField()

    class Meta:
        model = RecetaInsumo
        fields = [
            "id",
            "insumo",
            "insumo_nombre",
            "insumo_unidad",
            "costo_unitario_insumo",
            "cantidad",
            "merma_porcentaje",
            "cantidad_neta",
            "costo_linea",
        ]
        read_only_fields = ["id"]

    def get_costo_linea(self, obj) -> Decimal:
        return (obj.cantidad_neta * obj.insumo.costo_unitario).quantize(Decimal("0.01"))


class RecetaListSerializer(serializers.ModelSerializer):
    costo_insumos = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    costo_unitario_produccion = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_real = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = Receta
        fields = [
            "id",
            "nombre",
            "descripcion",
            "categoria",
            "rendimiento",
            "precio_base",
            "margen_deseado",
            "tiempo_preparacion_min",
            "imagen",
            "activo",
            "costo_insumos",
            "costo_unitario_produccion",
            "margen_real",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]


class RecetaDetailSerializer(serializers.ModelSerializer):
    insumos = RecetaInsumoSerializer(many=True, read_only=True)
    costo_insumos = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    costo_unitario_produccion = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    margen_real = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = Receta
        fields = [
            "id",
            "nombre",
            "descripcion",
            "categoria",
            "rendimiento",
            "precio_base",
            "margen_deseado",
            "tiempo_preparacion_min",
            "imagen",
            "activo",
            "insumos",
            "costo_insumos",
            "costo_unitario_produccion",
            "margen_real",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]
