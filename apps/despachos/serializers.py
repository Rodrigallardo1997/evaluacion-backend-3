"""
Serializers para el módulo de despachos y rutas de entrega.
"""
from rest_framework import serializers

from apps.despachos.models import RutaDespacho, Despacho
from apps.pedidos.serializers import PedidoListSerializer


class DespachoSerializer(serializers.ModelSerializer):
    pedido_codigo = serializers.ReadOnlyField(source="pedido.codigo")
    cliente_nombre = serializers.ReadOnlyField(source="pedido.cliente.nombre_completo")
    cliente_telefono = serializers.ReadOnlyField(source="pedido.cliente.telefono")
    direccion_entrega = serializers.ReadOnlyField(source="pedido.direccion_entrega")
    total_pedido = serializers.DecimalField(
        source="pedido.total", max_digits=12, decimal_places=2, read_only=True
    )
    saldo_pedido = serializers.DecimalField(
        source="pedido.saldo", max_digits=12, decimal_places=2, read_only=True
    )
    mapa_url = serializers.SerializerMethodField()

    class Meta:
        model = Despacho
        fields = [
            "id",
            "ruta",
            "pedido",
            "pedido_codigo",
            "cliente_nombre",
            "cliente_telefono",
            "direccion_entrega",
            "total_pedido",
            "saldo_pedido",
            "orden",
            "estado",
            "receptor_nombre",
            "firma_digital",
            "foto_comprobante",
            "fecha_entrega",
            "latitud",
            "longitud",
            "observaciones",
            "mapa_url",
        ]
        read_only_fields = ["id", "fecha_entrega"]

    def get_mapa_url(self, obj) -> str:
        """Genera enlace directo a Google Maps con la dirección codificada o coordenadas."""
        if obj.latitud and obj.longitud:
            return f"https://www.google.com/maps/dir/?api=1&destination={obj.latitud},{obj.longitud}"
        direccion = obj.pedido.direccion_entrega
        from urllib.parse import quote
        return f"https://www.google.com/maps/dir/?api=1&destination={quote(direccion + ', Santiago, Chile')}"


class RutaDespachoListSerializer(serializers.ModelSerializer):
    repartidor_nombre = serializers.ReadOnlyField(source="repartidor.get_full_name")
    total_paradas = serializers.IntegerField(read_only=True)
    entregadas = serializers.IntegerField(read_only=True)
    pendientes = serializers.IntegerField(read_only=True)
    esta_completa = serializers.BooleanField(read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = RutaDespacho
        fields = [
            "id",
            "codigo",
            "fecha",
            "repartidor",
            "repartidor_nombre",
            "vehiculo",
            "estado",
            "estado_display",
            "total_paradas",
            "entregadas",
            "pendientes",
            "esta_completa",
            "creado_en",
        ]
        read_only_fields = ["id", "codigo", "creado_en"]


class RutaDespachoDetailSerializer(serializers.ModelSerializer):
    paradas = DespachoSerializer(many=True, read_only=True)
    repartidor_nombre = serializers.ReadOnlyField(source="repartidor.get_full_name")
    repartidor_telefono = serializers.ReadOnlyField(source="repartidor.telefono")
    total_paradas = serializers.IntegerField(read_only=True)
    entregadas = serializers.IntegerField(read_only=True)
    pendientes = serializers.IntegerField(read_only=True)
    esta_completa = serializers.BooleanField(read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = RutaDespacho
        fields = [
            "id",
            "codigo",
            "fecha",
            "repartidor",
            "repartidor_nombre",
            "repartidor_telefono",
            "vehiculo",
            "estado",
            "estado_display",
            "observaciones",
            "total_paradas",
            "entregadas",
            "pendientes",
            "esta_completa",
            "paradas",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["id", "codigo", "creado_en", "actualizado_en"]


class ConfirmarEntregaSerializer(serializers.Serializer):
    receptor_nombre = serializers.CharField(required=True, max_length=150)
    firma_digital = serializers.CharField(required=False, allow_blank=True, default="")
    foto_comprobante = serializers.ImageField(required=False, allow_null=True, default=None)
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")
    latitud = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True, default=None)
    longitud = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True, default=None)


class FallarEntregaSerializer(serializers.Serializer):
    motivo = serializers.CharField(required=True)
