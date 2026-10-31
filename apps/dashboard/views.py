"""
Vistas web para Dashboard, Reportes y Página Pública de Servicios (Landing Page).
"""
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Q
from django.shortcuts import render, redirect
from django.utils import timezone

from apps.catalogo.models import Insumo, Receta
from apps.despachos.models import RutaDespacho
from apps.pedidos.models import Pedido, DetallePedido, Pago
from apps.usuarios.permissions import role_required


def landing_view(request):
    """
    Página pública de presentación de servicios, catálogo de especialidades
    y showcase de trazabilidad para visitantes y evaluación docente.
    """
    q = request.GET.get("q", "").strip()
    categoria_filtro = request.GET.get("categoria", "").strip()

    recetas = Receta.objects.filter(activo=True).order_by("categoria", "nombre")

    if q:
        recetas = recetas.filter(
            Q(nombre__icontains=q)
            | Q(descripcion__icontains=q)
        )
    if categoria_filtro and categoria_filtro in Receta.Categoria.values:
        recetas = recetas.filter(categoria=categoria_filtro)

    # Métricas públicas de la plataforma
    total_recetas = Receta.objects.filter(activo=True).count()
    total_insumos = Insumo.objects.filter(activo=True).count()
    pedidos_completados = Pedido.objects.filter(estado=Pedido.Estado.ENTREGADO).count()

    context = {
        "recetas": recetas,
        "categorias": Receta.Categoria.choices,
        "q": q,
        "categoria_filtro": categoria_filtro,
        "total_recetas": total_recetas,
        "total_insumos": total_insumos,
        "pedidos_completados": pedidos_completados,
    }
    return render(request, "dashboard/landing.html", context)


def index(request):
    """
    Ruta raíz '/':
    - Si el usuario NO está autenticado, muestra la página pública de servicios (Landing).
    - Si el usuario está autenticado, muestra el Panel de Control interno (Dashboard).
    """
    if not request.user.is_authenticated:
        return landing_view(request)

    # Si es cliente, redirigir directamente a su Portal de Cliente personalizado
    if request.user.es_cliente:
        return redirect("pedidos:mis_pedidos")

    user = request.user
    hoy = timezone.localdate()

    # Pedidos en distintas etapas
    pedidos_pendientes = Pedido.objects.filter(estado__in=[Pedido.Estado.BORRADOR, Pedido.Estado.COTIZADO]).count()
    pedidos_en_produccion = Pedido.objects.filter(
        estado__in=[
            Pedido.Estado.CONFIRMADO,
            Pedido.Estado.EN_PREPARACION,
            Pedido.Estado.HORNEADO_DECORADO,
            Pedido.Estado.CONTROL_CALIDAD,
        ]
    ).count()
    pedidos_listos = Pedido.objects.filter(estado=Pedido.Estado.LISTO).count()
    pedidos_entregados_hoy = Pedido.objects.filter(
        estado=Pedido.Estado.ENTREGADO, fecha_entrega_real__date=hoy
    ).count()

    # Insumos bajo stock o vencidos
    alertas_stock = Insumo.objects.filter(
        activo=True
    ).filter(
        stock_actual__lte=F("stock_minimo")
    ).order_by("stock_actual")[:6]

    # Pedidos urgentes o próximos
    pedidos_urgentes = Pedido.objects.exclude(
        estado__in=[Pedido.Estado.ENTREGADO, Pedido.Estado.CANCELADO]
    ).order_by("fecha_entrega")[:5]

    # Ventas de los últimos 7 días para el gráfico Chart.js
    dias_grafico = []
    montos_grafico = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        dias_grafico.append(dia.strftime("%d/%m"))
        monto_dia = Pago.objects.filter(fecha__date=dia).aggregate(total=Sum("monto"))["total"] or Decimal("0")
        montos_grafico.append(float(monto_dia))

    context = {
        "titulo": "Dashboard — Dulce Arte",
        "pedidos_pendientes": pedidos_pendientes,
        "pedidos_en_produccion": pedidos_en_produccion,
        "pedidos_listos": pedidos_listos,
        "pedidos_entregados_hoy": pedidos_entregados_hoy,
        "alertas_stock": alertas_stock,
        "pedidos_urgentes": pedidos_urgentes,
        "dias_grafico": dias_grafico,
        "montos_grafico": montos_grafico,
    }
    return render(request, "dashboard/index.html", context)


@login_required
@role_required("ADMIN", "VENDEDOR")
def reportes(request):
    """Vista de reportes de ventas, productos y consumo."""
    desde = request.GET.get("desde")
    hasta = request.GET.get("hasta")

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
        .order_by("-total_vendido")[:8]
    )

    context = {
        "desde": desde,
        "hasta": hasta,
        "total_ventas": total_ventas,
        "total_pedidos": total_pedidos,
        "pedidos_por_estado": pedidos_por_estado,
        "top_productos": top_productos,
    }
    return render(request, "dashboard/reportes.html", context)
