"""
Vistas API para KPIs del Dashboard y Reportes de Ventas.
"""
import json
import urllib.request
from decimal import Decimal
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogo.models import Insumo, Receta
from apps.despachos.models import RutaDespacho, Despacho
from apps.pedidos.models import Pedido, DetallePedido, Pago
from apps.usuarios.permissions import role_required


class DashboardResumenAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        hoy = timezone.localdate()

        data = {
            "usuario": user.username,
            "rol": user.rol,
            "rol_display": user.get_rol_display(),
        }

        if user.es_admin or user.es_vendedor or user.is_superuser:
            pedidos_hoy = Pedido.objects.filter(creado_en__date=hoy)
            ventas_hoy = Pago.objects.filter(fecha__date=hoy).aggregate(total=Sum("monto"))["total"] or Decimal("0")
            ventas_mes = Pago.objects.filter(
                fecha__year=hoy.year, fecha__month=hoy.month
            ).aggregate(total=Sum("monto"))["total"] or Decimal("0")

            data["kpis_ventas"] = {
                "pedidos_hoy_cantidad": pedidos_hoy.count(),
                "ventas_hoy_monto": str(ventas_hoy),
                "ventas_mes_monto": str(ventas_mes),
                "pedidos_pendientes_confirmar": Pedido.objects.filter(estado=Pedido.Estado.COTIZADO).count(),
            }

        if user.es_admin or user.es_cocina or user.is_superuser:
            data["kpis_cocina"] = {
                "recibidos_pendientes": Pedido.objects.filter(estado=Pedido.Estado.CONFIRMADO).count(),
                "en_preparacion": Pedido.objects.filter(estado=Pedido.Estado.EN_PREPARACION).count(),
                "horneado_decorado": Pedido.objects.filter(estado=Pedido.Estado.HORNEADO_DECORADO).count(),
                "control_calidad": Pedido.objects.filter(estado=Pedido.Estado.CONTROL_CALIDAD).count(),
                "listos_despacho": Pedido.objects.filter(estado=Pedido.Estado.LISTO).count(),
                "insumos_bajo_stock": Insumo.objects.filter(stock_actual__lte=F("stock_minimo")).count(),
                "insumos_vencidos": Insumo.objects.filter(perecedero=True, fecha_vencimiento__lt=hoy).count(),
            }

        if user.es_admin or user.es_repartidor or user.is_superuser:
            rutas_qs = RutaDespacho.objects.filter(fecha=hoy)
            if user.es_repartidor:
                rutas_qs = rutas_qs.filter(repartidor=user)

            data["kpis_despachos"] = {
                "rutas_hoy": rutas_qs.count(),
                "rutas_en_ruta": rutas_qs.filter(estado=RutaDespacho.Estado.EN_RUTA).count(),
                "pedidos_en_despacho": Pedido.objects.filter(estado=Pedido.Estado.EN_DESPACHO).count(),
                "entregados_hoy": Pedido.objects.filter(estado=Pedido.Estado.ENTREGADO, fecha_entrega_real__date=hoy).count(),
            }

        if user.es_cliente:
            mis_pedidos = Pedido.objects.filter(cliente__usuario=user)
            data["mis_pedidos"] = {
                "total": mis_pedidos.count(),
                "en_curso": mis_pedidos.exclude(estado__in=[Pedido.Estado.ENTREGADO, Pedido.Estado.CANCELADO]).count(),
                "entregados": mis_pedidos.filter(estado=Pedido.Estado.ENTREGADO).count(),
            }

        return Response(data)


class ReporteVentasAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.es_admin or user.es_vendedor or user.is_superuser):
            return Response(
                {"detail": "No tienes permisos para ver reportes de ventas."},
                status=status.HTTP_403_FORBIDDEN,
            )

        desde = request.query_params.get("desde")
        hasta = request.query_params.get("hasta")

        pedidos_qs = Pedido.objects.exclude(estado=Pedido.Estado.CANCELADO)
        pagos_qs = Pago.objects.all()

        if desde:
            pedidos_qs = pedidos_qs.filter(creado_en__date__gte=desde)
            pagos_qs = pagos_qs.filter(fecha__date__gte=desde)
        if hasta:
            pedidos_qs = pedidos_qs.filter(creado_en__date__lte=hasta)
            pagos_qs = pagos_qs.filter(fecha__date__lte=hasta)

        total_ventas = pagos_qs.aggregate(total=Sum("monto"))["total"] or Decimal("0")
        total_pedidos = pedidos_qs.count()

        pedidos_por_estado = (
            pedidos_qs.values("estado")
            .annotate(cantidad=Count("id"), total=Sum("total"))
            .order_by("estado")
        )

        detalles_qs = DetallePedido.objects.filter(pedido__in=pedidos_qs)
        top_productos = (
            detalles_qs.values("receta__nombre")
            .annotate(
                total_vendido=Sum("cantidad"),
                ingresos=Sum(F("cantidad") * F("precio_unitario")),
            )
            .order_by("-total_vendido")[:5]
        )

        return Response(
            {
                "rango": {"desde": desde, "hasta": hasta},
                "total_recaudado": str(total_ventas),
                "total_pedidos": total_pedidos,
                "pedidos_por_estado": list(pedidos_por_estado),
                "top_productos": list(top_productos),
            }
        )


class MensajeriaLambdaSNSAPIView(APIView):
    """
    Puente API para invocar la función AWS Lambda de mensajería unificada (dulcearte-mensajeria-sns)
    evitando bloqueos CORS del navegador cuando se invoca desde el Frontend S3 a través de API Gateway.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        lambda_url = request.data.get(
            "lambda_url",
            "https://wsa4lyofyakp3pxazuyg55d7fm0zpsaf.lambda-url.us-east-1.on.aws/",
        )
        if not str(lambda_url).startswith("https://"):
            return Response({"ok": False, "error": "URL de Lambda inválida."}, status=status.HTTP_400_BAD_REQUEST)

        payload = {
            "origen": request.data.get("origen", "frontend"),
            "tipo": request.data.get("tipo", "CONTACTO_WEB"),
            "remitente": request.data.get("remitente", "Usuario Web"),
            "asunto": request.data.get("asunto", "Notificación Dulce Arte"),
            "mensaje": request.data.get("mensaje", ""),
        }
        try:
            req = urllib.request.Request(
                lambda_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                resp_data = json.loads(resp.read().decode("utf-8"))
                return Response(resp_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
