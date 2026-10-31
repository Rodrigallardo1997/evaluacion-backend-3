"""
Serializers para el módulo de pedidos, cotizaciones, pagos y clientes.
"""
from decimal import Decimal
from rest_framework import serializers

from apps.catalogo.serializers import RecetaListSerializer
from apps.pedidos.models import (
    Cliente,
    Pedido,
    DetallePedido,
    Cotizacion,
    HistorialEstadoPedido,
    Pago,
)


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = [
            "id",
            "nombre_completo",
            "rut",
            "telefono",
            "email",
            "direccion",
            "referencia_direccion",
            "notas",
            "activo",
            "usuario",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]


class DetallePedidoSerializer(serializers.ModelSerializer):
    receta_nombre = serializers.ReadOnlyField(source="receta.nombre")
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DetallePedido
        fields = [
            "id",
            "receta",
            "receta_nombre",
            "cantidad",
            "precio_unitario",
            "personalizacion",
            "subtotal",
        ]
        read_only_fields = ["id"]


class CotizacionSerializer(serializers.ModelSerializer):
    esta_vigente = serializers.BooleanField(read_only=True)
    creado_por_nombre = serializers.ReadOnlyField(source="creado_por.username")

    class Meta:
        model = Cotizacion
        fields = [
            "id",
            "numero",
            "fecha_emision",
            "valida_hasta",
            "subtotal",
            "descuento",
            "total",
            "estado",
            "condiciones",
            "creado_por",
            "creado_por_nombre",
            "esta_vigente",
        ]
        read_only_fields = [
            "id",
            "numero",
            "fecha_emision",
            "subtotal",
            "descuento",
            "total",
            "estado",
            "creado_por",
        ]


class HistorialEstadoPedidoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    estado_anterior_display = serializers.CharField(source="get_estado_anterior_display", read_only=True)
    estado_nuevo_display = serializers.CharField(source="get_estado_nuevo_display", read_only=True)

    class Meta:
        model = HistorialEstadoPedido
        fields = [
            "id",
            "estado_anterior",
            "estado_anterior_display",
            "estado_nuevo",
            "estado_nuevo_display",
            "usuario",
            "usuario_nombre",
            "observacion",
            "fecha",
        ]
        read_only_fields = ["id", "fecha"]

    def get_usuario_nombre(self, obj) -> str:
        if obj.usuario:
            return obj.usuario.get_full_name() or obj.usuario.username
        return "Sistema"


class PagoSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.ReadOnlyField(source="registrado_por.username")
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    metodo_display = serializers.CharField(source="get_metodo_display", read_only=True)

    class Meta:
        model = Pago
        fields = [
            "id",
            "pedido",
            "monto",
            "tipo",
            "tipo_display",
            "metodo",
            "metodo_display",
            "referencia",
            "comprobante",
            "fecha",
            "registrado_por",
            "registrado_por_nombre",
        ]
        read_only_fields = ["id", "fecha", "registrado_por"]


class PedidoListSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.ReadOnlyField(source="cliente.nombre_completo")
    cliente_telefono = serializers.ReadOnlyField(source="cliente.telefono")
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    prioridad_display = serializers.CharField(source="get_prioridad_display", read_only=True)
    columna_kanban = serializers.CharField(read_only=True)

    class Meta:
        model = Pedido
        fields = [
            "id",
            "codigo",
            "cliente",
            "cliente_nombre",
            "cliente_telefono",
            "vendedor",
            "estado",
            "estado_display",
            "prioridad",
            "prioridad_display",
            "columna_kanban",
            "fecha_entrega",
            "direccion_entrega",
            "total",
            "anticipo",
            "saldo",
            "version",
            "inventario_descontado",
            "creado_en",
        ]
        read_only_fields = ["id", "codigo", "version", "inventario_descontado", "creado_en"]


class PedidoDetailSerializer(serializers.ModelSerializer):
    cliente_info = ClienteSerializer(source="cliente", read_only=True)
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    cotizaciones = CotizacionSerializer(many=True, read_only=True)
    pagos = PagoSerializer(many=True, read_only=True)
    historial = HistorialEstadoPedidoSerializer(many=True, read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    columna_kanban = serializers.CharField(read_only=True)

    class Meta:
        model = Pedido
        fields = [
            "id",
            "codigo",
            "cliente",
            "cliente_info",
            "vendedor",
            "estado",
            "estado_display",
            "prioridad",
            "columna_kanban",
            "fecha_entrega",
            "fecha_entrega_real",
            "direccion_entrega",
            "diseno_descripcion",
            "imagen_referencia",
            "observaciones",
            "subtotal",
            "descuento",
            "total",
            "anticipo",
            "saldo",
            "inventario_descontado",
            "version",
            "motivo_cancelacion",
            "cancelado_por",
            "detalles",
            "cotizaciones",
            "pagos",
            "historial",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = [
            "id",
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


class PedidoCreateUpdateSerializer(serializers.ModelSerializer):
    detalles_data = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = Pedido
        fields = [
            "id",
            "cliente",
            "prioridad",
            "fecha_entrega",
            "direccion_entrega",
            "diseno_descripcion",
            "imagen_referencia",
            "observaciones",
            "descuento",
            "detalles_data",
        ]

    def create(self, validated_data):
        detalles_data = validated_data.pop("detalles_data", [])
        request = self.context.get("request")
        vendedor = request.user if (request and request.user.is_authenticated) else None

        pedido = Pedido.objects.create(vendedor=vendedor, **validated_data)
        pedido.generar_codigo()

        from apps.catalogo.models import Receta
        for item in detalles_data:
            receta_id = item.get("receta")
            receta = Receta.objects.get(pk=receta_id)
            cantidad = int(item.get("cantidad", 1))
            precio = Decimal(str(item.get("precio_unitario", receta.precio_base)))
            personalizacion = item.get("personalizacion", "")

            DetallePedido.objects.create(
                pedido=pedido,
                receta=receta,
                cantidad=cantidad,
                precio_unitario=precio,
                personalizacion=personalizacion,
            )

        pedido.recalcular_totales()
        pedido.save(update_fields=["subtotal", "total", "saldo"])
        return pedido


class TransicionEstadoSerializer(serializers.Serializer):
    estado = serializers.CharField(required=True)
    version = serializers.IntegerField(required=True)
    observacion = serializers.CharField(required=False, allow_blank=True, default="")


class CancelarPedidoSerializer(serializers.Serializer):
    motivo = serializers.CharField(required=True)
    version = serializers.IntegerField(required=False)
