"""
Vistas API para Rutas de Despacho y Paradas de Entrega con Firma/Foto.
"""
from django.core.exceptions import ValidationError, PermissionDenied
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.despachos.models import RutaDespacho, Despacho
from apps.despachos.serializers import (
    RutaDespachoListSerializer,
    RutaDespachoDetailSerializer,
    DespachoSerializer,
    ConfirmarEntregaSerializer,
    FallarEntregaSerializer,
)
from apps.despachos.services.despacho_service import (
    iniciar_ruta,
    confirmar_entrega,
    registrar_entrega_fallida,
    cerrar_ruta,
    agregar_parada_ruta,
)
from apps.usuarios.permissions import RolePermission


class RutaDespachoViewSet(viewsets.ModelViewSet):
    queryset = (
        RutaDespacho.objects.select_related("repartidor", "creado_por")
        .prefetch_related("paradas__pedido__cliente")
        .all()
        .order_by("-fecha")
    )
    permission_classes = [IsAuthenticated, RolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "repartidor__first_name", "repartidor__last_name", "vehiculo"]
    ordering_fields = ["fecha", "creado_en"]

    role_action_map = {
        "list": ["ADMIN", "VENDEDOR", "COCINA", "REPARTIDOR"],
        "retrieve": ["ADMIN", "VENDEDOR", "COCINA", "REPARTIDOR"],
        "create": ["ADMIN", "VENDEDOR"],
        "update": ["ADMIN", "VENDEDOR"],
        "partial_update": ["ADMIN", "VENDEDOR"],
        "destroy": ["ADMIN"],
        "iniciar": ["ADMIN", "REPARTIDOR"],
        "cerrar": ["ADMIN", "REPARTIDOR"],
        "agregar_parada": ["ADMIN", "VENDEDOR"],
    }

    def get_serializer_class(self):
        if self.action in ["retrieve", "update", "partial_update"]:
            return RutaDespachoDetailSerializer
        return RutaDespachoListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.es_repartidor:
            qs = qs.filter(repartidor=user)

        fecha = self.request.query_params.get("fecha")
        if fecha:
            qs = qs.filter(fecha=fecha)

        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        return qs

    def perform_create(self, serializer):
        ruta = serializer.save(creado_por=self.request.user)
        if not ruta.codigo:
            ruta.generar_codigo()

    @action(detail=True, methods=["post"], url_path="iniciar")
    def iniciar(self, request, pk=None):
        """Inicia la ruta y pasa los pedidos a EN_DESPACHO."""
        try:
            ruta = iniciar_ruta(ruta_id=pk, usuario=request.user)
            return Response(
                {
                    "detail": "Ruta iniciada exitosamente. Pedidos pasados a estado En Despacho.",
                    "ruta": RutaDespachoDetailSerializer(ruta).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="cerrar")
    def cerrar(self, request, pk=None):
        """Cierra manualmente una ruta."""
        try:
            ruta = cerrar_ruta(ruta_id=pk, usuario=request.user)
            return Response(
                {
                    "detail": "Ruta cerrada exitosamente.",
                    "ruta": RutaDespachoDetailSerializer(ruta).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="agregar-parada")
    def agregar_parada(self, request, pk=None):
        """Agrega un pedido en estado LISTO a la ruta."""
        pedido_id = request.data.get("pedido_id")
        orden = request.data.get("orden")
        if not pedido_id:
            return Response({"detail": "pedido_id es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            despacho = agregar_parada_ruta(ruta_id=pk, pedido_id=pedido_id, orden=orden)
            return Response(
                {
                    "detail": "Parada agregada a la ruta.",
                    "despacho": DespachoSerializer(despacho).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DespachoViewSet(viewsets.GenericViewSet):
    queryset = Despacho.objects.select_related("ruta", "pedido__cliente").all()
    serializer_class = DespachoSerializer
    permission_classes = [IsAuthenticated, RolePermission]

    role_action_map = {
        "confirmar": ["ADMIN", "REPARTIDOR"],
        "fallar": ["ADMIN", "REPARTIDOR"],
        "retrieve": ["ADMIN", "REPARTIDOR", "VENDEDOR", "CLIENTE"],
    }

    def retrieve(self, request, pk=None):
        despacho = self.get_object()
        return Response(DespachoSerializer(despacho).data)

    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, pk=None):
        """
        Confirma la entrega de la parada con firma digital y/o foto del comprobante.
        """
        serializer = ConfirmarEntregaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        receptor_nombre = serializer.validated_data["receptor_nombre"]
        firma_digital = serializer.validated_data.get("firma_digital")
        foto_comprobante = request.FILES.get("foto_comprobante")
        observaciones = serializer.validated_data.get("observaciones", "")
        latitud = serializer.validated_data.get("latitud")
        longitud = serializer.validated_data.get("longitud")

        try:
            despacho = confirmar_entrega(
                despacho_id=pk,
                receptor_nombre=receptor_nombre,
                firma_digital=firma_digital,
                foto_comprobante=foto_comprobante,
                observaciones=observaciones,
                latitud=latitud,
                longitud=longitud,
                usuario=request.user,
            )
            return Response(
                {
                    "detail": "Entrega confirmada exitosamente. Evidencia guardada.",
                    "despacho": DespachoSerializer(despacho).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            msg = e.message if hasattr(e, "message") else str(e)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="fallar")
    def fallar(self, request, pk=None):
        """
        Registra la entrega como fallida y devuelve el pedido a LISTO.
        """
        serializer = FallarEntregaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        motivo = serializer.validated_data["motivo"]

        try:
            despacho = registrar_entrega_fallida(
                despacho_id=pk, motivo=motivo, usuario=request.user
            )
            return Response(
                {
                    "detail": "Entrega registrada como fallida. Pedido devuelto a estado LISTO para reprogramación.",
                    "despacho": DespachoSerializer(despacho).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            msg = e.message if hasattr(e, "message") else str(e)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
