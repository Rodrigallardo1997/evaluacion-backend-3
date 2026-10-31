"""
Vistas API para Insumos, Recetas y Lista de Materiales (BOM).
"""
from decimal import Decimal
from django.db.models import F, Q
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalogo.models import Insumo, Receta, RecetaInsumo
from apps.catalogo.serializers import (
    InsumoSerializer,
    AjusteInsumoSerializer,
    RecetaListSerializer,
    RecetaDetailSerializer,
    RecetaInsumoSerializer,
)
from apps.inventario.services.stock_service import registrar_movimiento
from apps.usuarios.permissions import RolePermission


class InsumoViewSet(viewsets.ModelViewSet):
    queryset = Insumo.objects.all().order_by("nombre")
    serializer_class = InsumoSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre", "categoria"]
    ordering_fields = ["nombre", "stock_actual", "costo_unitario", "fecha_vencimiento"]

    role_action_map = {
        "list": ["ADMIN", "VENDEDOR", "COCINA"],
        "retrieve": ["ADMIN", "VENDEDOR", "COCINA"],
        "create": ["ADMIN", "COCINA"],
        "update": ["ADMIN", "COCINA"],
        "partial_update": ["ADMIN", "COCINA"],
        "destroy": ["ADMIN"],
        "alertas": ["ADMIN", "VENDEDOR", "COCINA"],
        "ajustar": ["ADMIN", "COCINA"],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        categoria = self.request.query_params.get("categoria")
        if categoria:
            qs = qs.filter(categoria=categoria)
        stock_bajo = self.request.query_params.get("stock_bajo")
        if stock_bajo in ["true", "1", "True"]:
            qs = qs.filter(stock_actual__lte=F("stock_minimo"))
        return qs

    @action(detail=False, methods=["get"], url_path="alertas")
    def alertas(self, request):
        """
        Retorna insumos con stock bajo (stock_actual <= stock_minimo)
        o perecederos vencidos.
        """
        hoy = timezone.localdate()
        insumos = Insumo.objects.filter(activo=True)

        bajo_stock = insumos.filter(stock_actual__lte=F("stock_minimo"))
        vencidos = insumos.filter(perecedero=True, fecha_vencimiento__lt=hoy)
        por_vencer = insumos.filter(
            perecedero=True,
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=hoy + timezone.timedelta(days=7),
        )

        return Response(
            {
                "total_bajo_stock": bajo_stock.count(),
                "total_vencidos": vencidos.count(),
                "total_por_vencer": por_vencer.count(),
                "bajo_stock": InsumoSerializer(bajo_stock, many=True).data,
                "vencidos": InsumoSerializer(vencidos, many=True).data,
                "por_vencer": InsumoSerializer(por_vencer, many=True).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="ajustar")
    def ajustar(self, request, pk=None):
        """
        Registra una entrada, merma o ajuste manual en el insumo.
        """
        insumo = self.get_object()
        serializer = AjusteInsumoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tipo = serializer.validated_data["tipo"]
        cantidad = serializer.validated_data["cantidad"]
        motivo = serializer.validated_data["motivo"]

        try:
            movimiento = registrar_movimiento(
                insumo=insumo,
                tipo=tipo,
                cantidad=cantidad,
                motivo=motivo,
                usuario=request.user,
            )
            return Response(
                {
                    "detail": "Ajuste de inventario realizado exitosamente.",
                    "movimiento_id": movimiento.id,
                    "stock_anterior": str(movimiento.stock_anterior),
                    "stock_nuevo": str(movimiento.stock_nuevo),
                    "insumo": InsumoSerializer(insumo).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RecetaViewSet(viewsets.ModelViewSet):
    queryset = Receta.objects.prefetch_related("insumos__insumo").all().order_by("nombre")
    permission_classes = [IsAuthenticated, RolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre", "categoria", "descripcion"]
    ordering_fields = ["nombre", "precio_base", "categoria", "tiempo_preparacion_min"]

    role_action_map = {
        "list": ["ADMIN", "VENDEDOR", "COCINA"],
        "retrieve": ["ADMIN", "VENDEDOR", "COCINA"],
        "create": ["ADMIN", "COCINA"],
        "update": ["ADMIN", "COCINA"],
        "partial_update": ["ADMIN", "COCINA"],
        "destroy": ["ADMIN", "COCINA"],
        "calcular_costo": ["ADMIN", "VENDEDOR", "COCINA"],
    }

    def get_serializer_class(self):
        if self.action in ["retrieve", "update", "partial_update"]:
            return RecetaDetailSerializer
        return RecetaListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        categoria = self.request.query_params.get("categoria")
        if categoria:
            qs = qs.filter(categoria=categoria)
        activo = self.request.query_params.get("activo")
        if activo is not None:
            qs = qs.filter(activo=(activo.lower() in ["true", "1"]))
        return qs

    @action(detail=True, methods=["post", "get"], url_path="calcular-costo")
    def calcular_costo(self, request, pk=None):
        """
        Calcula el costo actual de insumos, costo unitario de producción,
        margen real y precio de venta sugerido según el margen deseado.
        """
        receta = self.get_object()
        costo_insumos = receta.costo_insumos
        costo_unitario = receta.costo_unitario_produccion
        margen_real = receta.margen_real

        # Precio sugerido = costo_unitario / (1 - margen_deseado / 100)
        margen_deseado = receta.margen_deseado
        factor = Decimal("1") - (margen_deseado / Decimal("100"))
        if factor > Decimal("0"):
            precio_sugerido = (costo_unitario / factor).quantize(Decimal("1"))
        else:
            precio_sugerido = receta.precio_base

        return Response(
            {
                "receta": receta.nombre,
                "rendimiento": receta.rendimiento,
                "costo_total_insumos": str(costo_insumos),
                "costo_unitario_produccion": str(costo_unitario),
                "precio_base_actual": str(receta.precio_base),
                "margen_deseado_pct": str(margen_deseado),
                "margen_real_pct": str(margen_real.quantize(Decimal("0.01"))),
                "precio_sugerido": str(precio_sugerido),
            }
        )
