"""
Vistas API para Pedidos, Clientes, Cotizaciones, Pagos y Tablero Kanban.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Prefetch, Q
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.pedidos.models import (
    Cliente,
    Pedido,
    DetallePedido,
    Cotizacion,
    HistorialEstadoPedido,
    Pago,
)
from apps.pedidos.serializers import (
    ClienteSerializer,
    PedidoListSerializer,
    PedidoDetailSerializer,
    PedidoCreateUpdateSerializer,
    CotizacionSerializer,
    HistorialEstadoPedidoSerializer,
    PagoSerializer,
    TransicionEstadoSerializer,
    CancelarPedidoSerializer,
)
from apps.pedidos.services.cotizacion_service import (
    ConflictError,
    emitir_cotizacion,
    confirmar_pedido,
    cancelar_pedido,
    transicionar_estado,
    registrar_pago_pedido,
)
from apps.usuarios.permissions import RolePermission


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all().order_by("nombre_completo")
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre_completo", "rut", "telefono", "email"]
    ordering_fields = ["nombre_completo", "creado_en"]

    role_action_map = {
        "list": ["ADMIN", "VENDEDOR", "COCINA", "REPARTIDOR"],
        "retrieve": ["ADMIN", "VENDEDOR", "COCINA", "REPARTIDOR", "CLIENTE"],
        "create": ["ADMIN", "VENDEDOR"],
        "update": ["ADMIN", "VENDEDOR"],
        "partial_update": ["ADMIN", "VENDEDOR"],
        "destroy": ["ADMIN"],
    }

    def get_queryset(self):
        user = self.request.user
        if user.es_cliente:
            return Cliente.objects.filter(usuario=user)
        return super().get_queryset()


class PedidoViewSet(viewsets.ModelViewSet):
    queryset = (
        Pedido.objects.select_related("cliente", "vendedor")
        .prefetch_related(
            "detalles__receta",
            "cotizaciones",
            "pagos",
            "historial__usuario",
        )
        .all()
        .order_by("-creado_en")
    )
    permission_classes = [IsAuthenticated, RolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "cliente__nombre_completo", "cliente__rut", "direccion_entrega"]
    ordering_fields = ["creado_en", "fecha_entrega", "total", "prioridad"]

    role_action_map = {
        "list": ["ADMIN", "VENDEDOR", "COCINA", "REPARTIDOR", "CLIENTE"],
        "retrieve": ["ADMIN", "VENDEDOR", "COCINA", "REPARTIDOR", "CLIENTE"],
        "create": ["ADMIN", "VENDEDOR"],
        "update": ["ADMIN", "VENDEDOR"],
        "partial_update": ["ADMIN", "VENDEDOR"],
        "destroy": ["ADMIN"],
        "cotizar": ["ADMIN", "VENDEDOR"],
        "confirmar": ["ADMIN", "VENDEDOR"],
        "cancelar": ["ADMIN", "VENDEDOR", "COCINA"],
        "estado": ["ADMIN", "VENDEDOR", "COCINA", "REPARTIDOR"],
        "kanban": ["ADMIN", "VENDEDOR", "COCINA"],
        "historial": ["ADMIN", "VENDEDOR", "COCINA", "CLIENTE"],
        "pagos": ["ADMIN", "VENDEDOR", "CLIENTE"],
    }

    def get_serializer_class(self):
        if self.action == "create":
            return PedidoCreateUpdateSerializer
        if self.action in ["retrieve", "update", "partial_update"]:
            return PedidoDetailSerializer
        return PedidoListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # Aislamiento por rol
        if user.es_cliente:
            qs = qs.filter(cliente__usuario=user)
        elif user.es_repartidor:
            # Repartidor ve pedidos asignados a sus rutas
            qs = qs.filter(despachos__ruta__repartidor=user).distinct()

        # Filtros por query params
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        prioridad = self.request.query_params.get("prioridad")
        if prioridad:
            qs = qs.filter(prioridad=prioridad)

        cliente_id = self.request.query_params.get("cliente")
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)

        desde = self.request.query_params.get("desde")
        hasta = self.request.query_params.get("hasta")
        if desde:
            qs = qs.filter(fecha_entrega__date__gte=desde)
        if hasta:
            qs = qs.filter(fecha_entrega__date__lte=hasta)

        return qs

    def update(self, request, *args, **kwargs):
        pedido = self.get_object()
        if not pedido.puede_editarse():
            return Response(
                {"detail": "Solo se pueden editar pedidos en estado BORRADOR."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="cotizar")
    def cotizar(self, request, pk=None):
        """Genera cotización formal y pasa pedido a COTIZADO."""
        try:
            cotizacion = emitir_cotizacion(pedido_id=pk, usuario=request.user)
            return Response(
                {
                    "detail": "Cotización emitida exitosamente.",
                    "cotizacion": CotizacionSerializer(cotizacion).data,
                    "pedido": PedidoDetailSerializer(Pedido.objects.get(pk=pk)).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, pk=None):
        """Valida stock con BOM, descuenta materia prima y confirma el pedido."""
        version = request.data.get("version")
        try:
            pedido = confirmar_pedido(pedido_id=pk, usuario=request.user, version=version)
            return Response(
                {
                    "detail": "Pedido confirmado exitosamente e inventario descontado.",
                    "pedido": PedidoDetailSerializer(pedido).data,
                },
                status=status.HTTP_200_OK,
            )
        except ConflictError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except ValidationError as e:
            msg = e.message if hasattr(e, "message") else str(e)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        """Cancela pedido y reintegra materias primas si estaban descontadas."""
        serializer = CancelarPedidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        motivo = serializer.validated_data["motivo"]
        version = serializer.validated_data.get("version")

        try:
            pedido = cancelar_pedido(
                pedido_id=pk, usuario=request.user, motivo=motivo, version=version
            )
            return Response(
                {
                    "detail": "Pedido cancelado y stock revertido.",
                    "pedido": PedidoDetailSerializer(pedido).data,
                },
                status=status.HTTP_200_OK,
            )
        except ConflictError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["patch"], url_path="estado")
    def estado(self, request, pk=None):
        """
        Transición de estado para el tablero Kanban con bloqueo optimista.
        Exige enviar 'estado' y 'version'. Si la versión no coincide, devuelve 409.
        """
        serializer = TransicionEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        nuevo_estado = serializer.validated_data["estado"]
        version = serializer.validated_data["version"]
        observacion = serializer.validated_data.get("observacion", "")

        try:
            pedido = transicionar_estado(
                pedido_id=pk,
                nuevo_estado=nuevo_estado,
                usuario=request.user,
                version=version,
                observacion=observacion,
            )
            return Response(
                {
                    "detail": f"Pedido actualizado a estado {pedido.get_estado_display()}.",
                    "pedido": PedidoListSerializer(pedido).data,
                },
                status=status.HTTP_200_OK,
            )
        except ConflictError as e:
            return Response(
                {"detail": "El pedido fue actualizado por otro usuario.", "error": str(e)},
                status=status.HTTP_409_CONFLICT,
            )
        except ValidationError as e:
            msg = e.message if hasattr(e, "message") else str(e)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="kanban")
    def kanban(self, request):
        """
        Endpoint del Tablero Kanban digital de cocina.
        Retorna exactamente las 5 columnas de cocina:
        1. Recibido (CONFIRMADO)
        2. En Preparación (EN_PREPARACION)
        3. Horneado/Decorado (HORNEADO_DECORADO)
        4. Control de Calidad (CONTROL_CALIDAD)
        5. Listo (LISTO)
        """
        qs = (
            Pedido.objects.filter(
                estado__in=[
                    Pedido.Estado.CONFIRMADO,
                    Pedido.Estado.EN_PREPARACION,
                    Pedido.Estado.HORNEADO_DECORADO,
                    Pedido.Estado.CONTROL_CALIDAD,
                    Pedido.Estado.LISTO,
                ]
            )
            .select_related("cliente")
            .order_by("fecha_entrega")
        )

        desde = request.query_params.get("desde")
        hasta = request.query_params.get("hasta")
        if desde:
            qs = qs.filter(fecha_entrega__date__gte=desde)
        if hasta:
            qs = qs.filter(fecha_entrega__date__lte=hasta)

        prioridad = request.query_params.get("prioridad")
        if prioridad:
            qs = qs.filter(prioridad=prioridad)

        columnas = {
            "recibido": {
                "nombre": "Recibido",
                "estado": Pedido.Estado.CONFIRMADO,
                "pedidos": [],
                "total": 0,
            },
            "en_preparacion": {
                "nombre": "En Preparación",
                "estado": Pedido.Estado.EN_PREPARACION,
                "pedidos": [],
                "total": 0,
            },
            "horneado": {
                "nombre": "Horneado / Decorado",
                "estado": Pedido.Estado.HORNEADO_DECORADO,
                "pedidos": [],
                "total": 0,
            },
            "calidad": {
                "nombre": "Control de Calidad",
                "estado": Pedido.Estado.CONTROL_CALIDAD,
                "pedidos": [],
                "total": 0,
            },
            "listo": {
                "nombre": "Listo para Despacho",
                "estado": Pedido.Estado.LISTO,
                "pedidos": [],
                "total": 0,
            },
        }

        for pedido in qs:
            col_key = pedido.columna_kanban
            if col_key in columnas:
                columnas[col_key]["pedidos"].append(PedidoListSerializer(pedido).data)
                columnas[col_key]["total"] += 1

        return Response(columnas)

    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, pk=None):
        """Timeline de auditoría del pedido."""
        pedido = self.get_object()
        historial = pedido.historial.select_related("usuario").order_by("fecha")
        return Response(HistorialEstadoPedidoSerializer(historial, many=True).data)

    @action(detail=True, methods=["get", "post"], url_path="pagos")
    def pagos(self, request, pk=None):
        """Listar o registrar pagos para el pedido."""
        pedido = self.get_object()

        if request.method == "GET":
            pagos = pedido.pagos.select_related("registrado_por").order_by("-fecha")
            return Response(PagoSerializer(pagos, many=True).data)

        # POST: Registrar nuevo pago
        monto = request.data.get("monto")
        tipo = request.data.get("tipo", Pago.Tipo.ABONO)
        metodo = request.data.get("metodo", Pago.Metodo.TRANSFERENCIA)
        referencia = request.data.get("referencia", "")
        comprobante = request.FILES.get("comprobante")

        if not monto:
            return Response({"detail": "El monto es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            monto_dec = Decimal(str(monto))
            pago = registrar_pago_pedido(
                pedido_id=pedido.id,
                monto=monto_dec,
                tipo=tipo,
                metodo=metodo,
                referencia=referencia,
                comprobante=comprobante,
                usuario=request.user,
            )
            return Response(
                {
                    "detail": "Pago registrado exitosamente.",
                    "pago": PagoSerializer(pago).data,
                    "saldo_actualizado": str(pedido.saldo),
                    "anticipo_actualizado": str(pedido.anticipo),
                },
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
