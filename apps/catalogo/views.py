"""
Vistas web para Catálogo: Recetas, BOM e Insumos con control de stock.
"""
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.catalogo.forms import InsumoForm, AjusteStockForm, RecetaForm
from apps.catalogo.models import Insumo, Receta, RecetaInsumo
from apps.inventario.services.stock_service import registrar_movimiento
from apps.usuarios.permissions import role_required


# ======================================================================
# RECETAS Y LISTA DE MATERIALES (BOM)
# ======================================================================

@login_required
@role_required("ADMIN", "VENDEDOR", "COCINA")
def recetas_lista(request):
    """Listado de recetas con cálculo de costo, margen real y precio base."""
    queryset = Receta.objects.prefetch_related("insumos__insumo").all().order_by("nombre")
    q = request.GET.get("q", "").strip()
    if q:
        queryset = queryset.filter(nombre__icontains=q)
    categoria = request.GET.get("categoria")
    if categoria:
        queryset = queryset.filter(categoria=categoria)

    paginator = Paginator(queryset, 12)
    page_number = request.GET.get("page")
    recetas = paginator.get_page(page_number)

    return render(
        request,
        "recetas/lista.html",
        {
            "recetas": recetas,
            "q": q,
            "categoria_actual": categoria,
            "categorias": Receta.Categoria.choices,
        },
    )


@login_required
@role_required("ADMIN", "COCINA")
def receta_crear(request):
    """Creación de receta junto con sus insumos de BOM."""
    insumos_disponibles = Insumo.objects.filter(activo=True).order_by("nombre")

    if request.method == "POST":
        form = RecetaForm(request.POST, request.FILES)
        insumos_ids = request.POST.getlist("insumo_id[]")
        cantidades = request.POST.getlist("cantidad[]")
        mermas = request.POST.getlist("merma[]")

        if form.is_valid():
            with transaction.atomic():
                receta = form.save()
                for i_id, cant, merma in zip(insumos_ids, cantidades, mermas):
                    if i_id and cant:
                        insumo = Insumo.objects.get(pk=i_id)
                        RecetaInsumo.objects.create(
                            receta=receta,
                            insumo=insumo,
                            cantidad=Decimal(str(cant)),
                            merma_porcentaje=Decimal(str(merma or 0)),
                        )
                messages.success(request, f"Receta '{receta.nombre}' y su Lista de Materiales (BOM) guardadas exitosamente.")
                return redirect("catalogo:index")
    else:
        form = RecetaForm()

    return render(
        request,
        "recetas/form.html",
        {
            "form": form,
            "insumos_disponibles": insumos_disponibles,
            "titulo": "Nueva Receta con BOM",
        },
    )


@login_required
@role_required("ADMIN", "COCINA")
def receta_editar(request, pk):
    """Edición de receta y sus insumos de BOM."""
    receta = get_object_or_404(Receta.objects.prefetch_related("insumos__insumo"), pk=pk)
    insumos_disponibles = Insumo.objects.filter(activo=True).order_by("nombre")

    if request.method == "POST":
        form = RecetaForm(request.POST, request.FILES, instance=receta)
        insumos_ids = request.POST.getlist("insumo_id[]")
        cantidades = request.POST.getlist("cantidad[]")
        mermas = request.POST.getlist("merma[]")

        if form.is_valid():
            with transaction.atomic():
                receta = form.save()
                receta.insumos.all().delete()
                for i_id, cant, merma in zip(insumos_ids, cantidades, mermas):
                    if i_id and cant:
                        insumo = Insumo.objects.get(pk=i_id)
                        RecetaInsumo.objects.create(
                            receta=receta,
                            insumo=insumo,
                            cantidad=Decimal(str(cant)),
                            merma_porcentaje=Decimal(str(merma or 0)),
                        )
                messages.success(request, f"Receta '{receta.nombre}' actualizada exitosamente.")
                return redirect("catalogo:index")
    else:
        form = RecetaForm(instance=receta)

    return render(
        request,
        "recetas/form.html",
        {
            "form": form,
            "receta": receta,
            "insumos_disponibles": insumos_disponibles,
            "titulo": f"Editar Receta: {receta.nombre}",
        },
    )


# ======================================================================
# INSUMOS Y AJUSTES DE STOCK
# ======================================================================

@login_required
@role_required("ADMIN", "VENDEDOR", "COCINA")
def insumos_lista(request):
    """Listado de insumos con alertas de stock bajo y vencimiento."""
    queryset = Insumo.objects.all().order_by("nombre")
    q = request.GET.get("q", "").strip()
    if q:
        queryset = queryset.filter(nombre__icontains=q)
    categoria = request.GET.get("categoria")
    if categoria:
        queryset = queryset.filter(categoria=categoria)
    stock_bajo = request.GET.get("stock_bajo")
    if stock_bajo in ["true", "1"]:
        queryset = queryset.filter(stock_actual__lte=F("stock_minimo"))

    paginator = Paginator(queryset, 15)
    page_number = request.GET.get("page")
    insumos = paginator.get_page(page_number)

    return render(
        request,
        "insumos/lista.html",
        {
            "insumos": insumos,
            "q": q,
            "categoria_actual": categoria,
            "categorias": Insumo.Categoria.choices,
            "stock_bajo": stock_bajo,
        },
    )


@login_required
@role_required("ADMIN", "COCINA")
def insumo_crear(request):
    """Creación de nuevo insumo."""
    if request.method == "POST":
        form = InsumoForm(request.POST)
        if form.is_valid():
            insumo = form.save()
            messages.success(request, f"Insumo '{insumo.nombre}' creado exitosamente.")
            return redirect("catalogo:insumos")
    else:
        form = InsumoForm()
    return render(request, "insumos/form.html", {"form": form, "titulo": "Nuevo Insumo"})


@login_required
@role_required("ADMIN", "COCINA")
def insumo_editar(request, pk):
    """Edición de insumo."""
    insumo = get_object_or_404(Insumo, pk=pk)
    if request.method == "POST":
        form = InsumoForm(request.POST, instance=insumo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Insumo '{insumo.nombre}' actualizado.")
            return redirect("catalogo:insumos")
    else:
        form = InsumoForm(instance=insumo)
    return render(request, "insumos/form.html", {"form": form, "insumo": insumo, "titulo": "Editar Insumo"})


@login_required
@role_required("ADMIN", "COCINA")
def insumo_ajustar(request, pk):
    """Formulario de ajuste manual de stock (entrada, salida, merma, ajuste)."""
    insumo = get_object_or_404(Insumo, pk=pk)
    if request.method == "POST":
        form = AjusteStockForm(request.POST)
        if form.is_valid():
            try:
                mov = registrar_movimiento(
                    insumo=insumo,
                    tipo=form.cleaned_data["tipo"],
                    cantidad=form.cleaned_data["cantidad"],
                    motivo=form.cleaned_data["motivo"],
                    usuario=request.user,
                )
                messages.success(
                    request,
                    f"Movimiento {mov.get_tipo_display()} registrado. Stock actualizado de {mov.stock_anterior} a {mov.stock_nuevo} {insumo.unidad}.",
                )
                return redirect("catalogo:insumos")
            except Exception as e:
                messages.error(request, f"Error al registrar movimiento: {e}")
    else:
        form = AjusteStockForm()

    return render(
        request,
        "insumos/ajuste.html",
        {"form": form, "insumo": insumo},
    )
