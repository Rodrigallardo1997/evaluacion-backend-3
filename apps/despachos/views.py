"""
Vistas web para Rutas de Despacho, Paradas y Confirmación de Entregas.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.despachos.forms import RutaDespachoForm, ConfirmarEntregaForm
from apps.despachos.models import RutaDespacho, Despacho
from apps.despachos.services.despacho_service import (
    iniciar_ruta,
    confirmar_entrega,
    registrar_entrega_fallida,
    agregar_parada_ruta,
)
from apps.pedidos.models import Pedido
from apps.usuarios.permissions import role_required


@login_required
@role_required("ADMIN", "VENDEDOR", "COCINA", "REPARTIDOR")
def rutas_lista(request):
    """Listado general de rutas de despacho."""
    queryset = RutaDespacho.objects.select_related("repartidor").prefetch_related("paradas").all().order_by("-fecha")
    if request.user.es_repartidor:
        queryset = queryset.filter(repartidor=request.user)

    paginator = Paginator(queryset, 15)
    page_number = request.GET.get("page")
    rutas = paginator.get_page(page_number)

    return render(request, "despachos/lista.html", {"rutas": rutas})


@login_required
@role_required("ADMIN", "VENDEDOR")
def ruta_nueva(request):
    """Creación de nueva ruta y asignación de pedidos en estado LISTO."""
    pedidos_disponibles = Pedido.objects.filter(
        estado=Pedido.Estado.LISTO
    ).exclude(
        despachos__estado=Despacho.Estado.PENDIENTE
    ).order_by("fecha_entrega")

    if request.method == "POST":
        form = RutaDespachoForm(request.POST)
        pedidos_seleccionados = request.POST.getlist("pedidos[]")

        if form.is_valid():
            if not pedidos_seleccionados:
                messages.error(request, "Debe seleccionar al menos un pedido listo para la ruta.")
            else:
                with transaction.atomic():
                    ruta = form.save(commit=False)
                    ruta.creado_por = request.user
                    ruta.save()
                    ruta.generar_codigo()

                    orden = 1
                    for p_id in pedidos_seleccionados:
                        pedido = Pedido.objects.get(pk=p_id)
                        agregar_parada_ruta(ruta_id=ruta.id, pedido_id=pedido.id, orden=orden)
                        orden += 1

                    messages.success(request, f"Ruta {ruta.codigo} creada con {len(pedidos_seleccionados)} paradas.")
                    return redirect("despachos:detalle", pk=ruta.pk)
    else:
        form = RutaDespachoForm(initial={"fecha": timezone.localdate()})

    return render(
        request,
        "despachos/nueva_ruta.html",
        {"form": form, "pedidos_disponibles": pedidos_disponibles},
    )


@login_required
def ruta_detalle(request, pk):
    """Ficha de ruta con paradas ordenadas y mapa."""
    ruta = get_object_or_404(
        RutaDespacho.objects.select_related("repartidor").prefetch_related(
            "paradas__pedido__cliente"
        ),
        pk=pk,
    )
    return render(request, "despachos/detalle_ruta.html", {"ruta": ruta})


@login_required
@role_required("ADMIN", "REPARTIDOR")
def accion_iniciar_ruta(request, pk):
    """Inicia la ruta y pasa los pedidos a EN_DESPACHO."""
    if request.method == "POST":
        try:
            ruta = iniciar_ruta(ruta_id=pk, usuario=request.user)
            messages.success(request, f"Ruta {ruta.codigo} iniciada. Los pedidos están en tránsito.")
        except Exception as e:
            messages.error(request, f"Error al iniciar ruta: {e}")
    return redirect("despachos:detalle", pk=pk)


@login_required
@role_required("ADMIN", "REPARTIDOR")
def mis_rutas(request):
    """Vista específica para repartidores con sus rutas del día y activas."""
    rutas = (
        RutaDespacho.objects.filter(repartidor=request.user)
        .prefetch_related("paradas__pedido__cliente")
        .order_by("-fecha")
    )
    return render(request, "despachos/mis_rutas.html", {"rutas": rutas})


@login_required
@role_required("ADMIN", "REPARTIDOR")
def entregas_pendientes(request):
    """Paradas pendientes del repartidor."""
    paradas = (
        Despacho.objects.filter(
            ruta__repartidor=request.user,
            estado=Despacho.Estado.PENDIENTE,
            ruta__estado=RutaDespacho.Estado.EN_RUTA,
        )
        .select_related("pedido__cliente", "ruta")
        .order_by("ruta", "orden")
    )
    return render(request, "despachos/entregas_pendientes.html", {"paradas": paradas})


@login_required
@role_required("ADMIN", "REPARTIDOR")
def entrega_confirmar(request, pk):
    """
    Vista de entrega con canvas de firma (signature_pad) o subida de foto.
    """
    despacho = get_object_or_404(
        Despacho.objects.select_related("pedido__cliente", "ruta"), pk=pk
    )

    if request.method == "POST":
        form = ConfirmarEntregaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                confirmar_entrega(
                    despacho_id=despacho.id,
                    receptor_nombre=form.cleaned_data["receptor_nombre"],
                    firma_digital=form.cleaned_data.get("firma_digital"),
                    foto_comprobante=form.cleaned_data.get("foto_comprobante"),
                    observaciones=form.cleaned_data.get("observaciones", ""),
                    latitud=form.cleaned_data.get("latitud"),
                    longitud=form.cleaned_data.get("longitud"),
                    usuario=request.user,
                )
                messages.success(
                    request,
                    f"Entrega del pedido {despacho.pedido.codigo} confirmada exitosamente con evidencia registrada.",
                )
                return redirect("despachos:mis_rutas")
            except Exception as e:
                messages.error(request, f"Error al confirmar entrega: {e}")
        else:
            messages.error(request, "Por favor revise los datos del formulario.")
    else:
        form = ConfirmarEntregaForm(
            initial={"receptor_nombre": despacho.pedido.cliente.nombre_completo}
        )

    return render(
        request,
        "despachos/confirmar_entrega.html",
        {"form": form, "despacho": despacho},
    )


@login_required
@role_required("ADMIN", "REPARTIDOR")
def entrega_fallida(request, pk):
    """Registra intento fallido y devuelve el pedido a LISTO."""
    despacho = get_object_or_404(Despacho, pk=pk)
    if request.method == "POST":
        motivo = request.POST.get("motivo", "").strip()
        if not motivo:
            messages.error(request, "Debe especificar un motivo para la entrega fallida.")
            return redirect("despachos:detalle", pk=despacho.ruta_id)
        try:
            registrar_entrega_fallida(
                despacho_id=despacho.id, motivo=motivo, usuario=request.user
            )
            messages.warning(
                request,
                f"Entrega marcada como fallida. Pedido {despacho.pedido.codigo} devuelto a estado LISTO.",
            )
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect("despachos:detalle", pk=despacho.ruta_id)
