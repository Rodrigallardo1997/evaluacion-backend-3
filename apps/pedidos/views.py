"""
Vistas web para la gestión de pedidos, clientes, cotizaciones y Kanban.
"""
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.catalogo.models import Receta
from apps.pedidos.forms import ClienteForm, PedidoForm, PagoForm
from apps.pedidos.models import Cliente, Pedido, DetallePedido, Cotizacion, Pago
from apps.pedidos.services.cotizacion_service import (
    emitir_cotizacion,
    confirmar_pedido,
    cancelar_pedido,
    transicionar_estado,
    registrar_pago_pedido,
    ConflictError,
)
from apps.usuarios.permissions import role_required


# ======================================================================
# CLIENTES
# ======================================================================

@login_required
@role_required("ADMIN", "VENDEDOR", "COCINA", "REPARTIDOR")
def clientes_lista(request):
    """Listado de clientes con búsqueda y paginación."""
    q = request.GET.get("q", "").strip()
    queryset = Cliente.objects.all().order_by("nombre_completo")
    if q:
        queryset = queryset.filter(nombre_completo__icontains=q) | queryset.filter(rut__icontains=q) | queryset.filter(telefono__icontains=q)

    paginator = Paginator(queryset, 15)
    page_number = request.GET.get("page")
    clientes = paginator.get_page(page_number)

    return render(request, "clientes/lista.html", {"clientes": clientes, "q": q})


@login_required
@role_required("ADMIN", "VENDEDOR")
def cliente_crear(request):
    """Creación de nuevo cliente."""
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, f"Cliente {cliente.nombre_completo} creado exitosamente.")
            return redirect("pedidos:clientes")
    else:
        form = ClienteForm()
    return render(request, "clientes/form.html", {"form": form, "titulo": "Nuevo Cliente"})


@login_required
@role_required("ADMIN", "VENDEDOR")
def cliente_editar(request, pk):
    """Edición de cliente existente."""
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cliente {cliente.nombre_completo} actualizado exitosamente.")
            return redirect("pedidos:clientes")
    else:
        form = ClienteForm(instance=cliente)
    return render(request, "clientes/form.html", {"form": form, "cliente": cliente, "titulo": "Editar Cliente"})


# ======================================================================
# PEDIDOS
# ======================================================================

@login_required
def pedidos_lista(request):
    """Listado principal de pedidos con filtros por estado, prioridad y búsqueda."""
    user = request.user
    if user.es_cliente:
        return redirect("pedidos:mis_pedidos")

    queryset = (
        Pedido.objects.select_related("cliente", "vendedor")
        .prefetch_related("detalles__receta")
        .all()
        .order_by("-creado_en")
    )

    if user.es_repartidor:
        queryset = queryset.filter(despachos__ruta__repartidor=user).distinct()

    q = request.GET.get("q", "").strip()
    if q:
        queryset = queryset.filter(codigo__icontains=q) | queryset.filter(cliente__nombre_completo__icontains=q)

    estado = request.GET.get("estado")
    if estado:
        queryset = queryset.filter(estado=estado)

    prioridad = request.GET.get("prioridad")
    if prioridad:
        queryset = queryset.filter(prioridad=prioridad)

    paginator = Paginator(queryset, 15)
    page_number = request.GET.get("page")
    pedidos = paginator.get_page(page_number)

    return render(
        request,
        "pedidos/lista.html",
        {
            "pedidos": pedidos,
            "q": q,
            "estado_actual": estado,
            "prioridad_actual": prioridad,
            "estados": Pedido.Estado.choices,
            "prioridades": Pedido.Prioridad.choices,
        },
    )


@login_required
@role_required("ADMIN", "VENDEDOR", "CLIENTE")
def pedido_nuevo(request):
    """
    Wizard de creación de pedido en 3 pasos:
    1. Datos del cliente y entrega
    2. Recetas con cantidades y personalizaciones
    3. Resumen, descuento y guardado en estado BORRADOR
    """
    recetas = Receta.objects.filter(activo=True).order_by("categoria", "nombre")
    es_cliente = request.user.es_cliente

    cliente_obj = None
    if es_cliente:
        try:
            cliente_obj = request.user.cliente
        except (AttributeError, Cliente.DoesNotExist):
            cliente_obj = Cliente.objects.create(
                usuario=request.user,
                nombre_completo=request.user.get_full_name() or request.user.username,
                telefono=request.user.telefono or "+56 9 1234 5678",
                email=request.user.email or "cliente@dulcearte.cl",
                direccion="Retiro en pastelería / Despacho a acordar",
            )

    if request.method == "POST":
        form = PedidoForm(request.POST, request.FILES, es_cliente=es_cliente)
        # Recibir items dinámicos del formset
        recetas_ids = request.POST.getlist("receta_id[]")
        cantidades = request.POST.getlist("cantidad[]")
        precios = request.POST.getlist("precio_unitario[]")
        personalizaciones = request.POST.getlist("personalizacion[]")

        if form.is_valid():
            if not recetas_ids:
                messages.error(request, "Debe agregar al menos un producto a la orden.")
            else:
                with transaction.atomic():
                    pedido = form.save(commit=False)
                    if es_cliente:
                        pedido.cliente = cliente_obj
                        # Asignar vendedor responsable por defecto para trazabilidad
                        vendedor_asignado = (
                            Usuario.objects.filter(rol=Usuario.Rol.VENDEDOR).first()
                            or Usuario.objects.filter(rol=Usuario.Rol.ADMIN).first()
                        )
                        pedido.vendedor = vendedor_asignado
                    else:
                        pedido.vendedor = request.user
                    pedido.estado = Pedido.Estado.BORRADOR
                    pedido.save()
                    pedido.generar_codigo()

                    for r_id, cant, precio, pers in zip(recetas_ids, cantidades, precios, personalizaciones):
                        if r_id and cant:
                            receta = Receta.objects.get(pk=r_id)
                            DetallePedido.objects.create(
                                pedido=pedido,
                                receta=receta,
                                cantidad=int(cant),
                                precio_unitario=Decimal(str(precio or receta.precio_base)),
                                personalizacion=pers or "",
                            )

                    pedido.recalcular_totales()
                    pedido.save(update_fields=["subtotal", "total", "saldo"])

                    if es_cliente:
                        messages.success(
                            request,
                            f"¡Tu solicitud de pedido {pedido.codigo} fue enviada con éxito! Nuestro equipo de pastelería ya lo tiene registrado.",
                        )
                        return redirect("pedidos:mis_pedidos")
                    else:
                        messages.success(
                            request,
                            f"Pedido {pedido.codigo} registrado exitosamente como BORRADOR. Puede proceder a cotizar.",
                        )
                        return redirect("pedidos:detalle", pk=pedido.pk)
    else:
        form = PedidoForm(es_cliente=es_cliente)

    return render(
        request,
        "pedidos/nuevo.html",
        {"form": form, "recetas": recetas, "es_cliente": es_cliente, "cliente_obj": cliente_obj},
    )


@login_required
def pedido_detalle(request, pk):
    """Ficha completa del pedido: timeline, cotizaciones, pagos y acciones."""
    pedido = get_object_or_404(
        Pedido.objects.select_related("cliente", "vendedor")
        .prefetch_related(
            "detalles__receta",
            "cotizaciones__creado_por",
            "pagos__registrado_por",
            "historial__usuario",
            "despachos__ruta",
        ),
        pk=pk,
    )

    # Aislamiento por rol
    if request.user.es_cliente and pedido.cliente.usuario != request.user:
        raise PermissionDenied("No tiene permiso para ver este pedido.")

    pago_form = PagoForm()
    return render(
        request,
        "pedidos/detalle.html",
        {"pedido": pedido, "pago_form": pago_form},
    )


@login_required
@role_required("ADMIN", "VENDEDOR")
def accion_cotizar(request, pk):
    """Acción para emitir cotización formal."""
    if request.method == "POST":
        try:
            cotizacion = emitir_cotizacion(pedido_id=pk, usuario=request.user)
            messages.success(request, f"Cotización {cotizacion.numero} emitida exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al cotizar: {e}")
    return redirect("pedidos:detalle", pk=pk)


@login_required
@role_required("ADMIN", "VENDEDOR", "COCINA")
def accion_confirmar(request, pk):
    """Acción para confirmar pedido y descontar materias primas."""
    if request.method == "POST":
        version = request.POST.get("version")
        try:
            pedido = confirmar_pedido(
                pedido_id=pk,
                usuario=request.user,
                version=int(version) if version else None,
            )
            messages.success(
                request,
                f"Pedido {pedido.codigo} CONFIRMADO exitosamente. Materias primas descontadas de bodega y enviado al Kanban de cocina.",
            )
        except ConflictError as e:
            messages.warning(request, str(e))
        except Exception as e:
            messages.error(request, f"Error al confirmar pedido: {e}")
    return redirect("pedidos:detalle", pk=pk)


@login_required
@role_required("ADMIN", "VENDEDOR", "COCINA")
def accion_cancelar(request, pk):
    """Acción para cancelar pedido y reintegrar materias primas."""
    if request.method == "POST":
        motivo = request.POST.get("motivo", "").strip()
        if not motivo:
            messages.error(request, "Debe especificar un motivo para cancelar el pedido.")
            return redirect("pedidos:detalle", pk=pk)
        try:
            pedido = cancelar_pedido(pedido_id=pk, usuario=request.user, motivo=motivo)
            messages.success(request, f"Pedido {pedido.codigo} cancelado. Insumos revertidos al inventario.")
        except Exception as e:
            messages.error(request, f"Error al cancelar pedido: {e}")
    return redirect("pedidos:detalle", pk=pk)


@login_required
@role_required("ADMIN", "VENDEDOR")
def registrar_pago_view(request, pk):
    """Registra un pago para el pedido."""
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        form = PagoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pago = registrar_pago_pedido(
                    pedido_id=pedido.id,
                    monto=form.cleaned_data["monto"],
                    tipo=form.cleaned_data["tipo"],
                    metodo=form.cleaned_data["metodo"],
                    referencia=form.cleaned_data["referencia"],
                    comprobante=form.cleaned_data["comprobante"],
                    usuario=request.user,
                )
                messages.success(request, f"Pago de ${pago.monto:,.0f} registrado exitosamente.")
            except Exception as e:
                messages.error(request, f"Error al registrar pago: {e}")
        else:
            messages.error(request, "Datos de pago inválidos.")
    return redirect("pedidos:detalle", pk=pk)


@login_required
def imprimir_cotizacion(request, pk):
    """Vista imprimible (@media print) de la cotización."""
    pedido = get_object_or_404(Pedido, pk=pk)
    cotizacion = pedido.cotizacion_actual or pedido.cotizaciones.order_by("-fecha_emision").first()
    return render(
        request,
        "pedidos/imprimir_cotizacion.html",
        {"pedido": pedido, "cotizacion": cotizacion},
    )


# ======================================================================
# KANBAN DIGITAL DE COCINA
# ======================================================================

@login_required
@role_required("ADMIN", "VENDEDOR", "COCINA")
def kanban_view(request):
    """
    Tablero Kanban digital de cocina interactivo con SortableJS.
    5 columnas exactas: Recibido, En Preparación, Horneado/Decorado, Calidad, Listo.
    """
    return render(request, "kanban/tablero.html")


# ======================================================================
# PORTAL CLIENTE
# ======================================================================

@login_required
def mis_pedidos(request):
    """Portal del cliente: visualización de sus pedidos propios e historial."""
    user = request.user
    pedidos = (
        Pedido.objects.filter(cliente__usuario=user)
        .prefetch_related("detalles__receta", "despachos")
        .order_by("-creado_en")
    )
    return render(request, "pedidos/mis_pedidos.html", {"pedidos": pedidos})
