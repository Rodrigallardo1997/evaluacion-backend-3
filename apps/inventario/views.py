"""
Vistas web para inventario y trazabilidad de movimientos de stock.
"""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from apps.inventario.models import MovimientoInventario
from apps.usuarios.permissions import role_required


@login_required
@role_required("ADMIN", "VENDEDOR", "COCINA")
def inventario_index(request):
    """Listado histórico de trazabilidad de movimientos de stock."""
    queryset = (
        MovimientoInventario.objects.select_related("insumo", "pedido", "usuario")
        .all()
        .order_by("-fecha")
    )

    tipo = request.GET.get("tipo")
    if tipo:
        queryset = queryset.filter(tipo=tipo)

    insumo_id = request.GET.get("insumo")
    if insumo_id:
        queryset = queryset.filter(insumo_id=insumo_id)

    paginator = Paginator(queryset, 20)
    page_number = request.GET.get("page")
    movimientos = paginator.get_page(page_number)

    return render(
        request,
        "inventario/lista.html",
        {
            "movimientos": movimientos,
            "tipo_actual": tipo,
            "tipos": MovimientoInventario.Tipo.choices,
        },
    )
