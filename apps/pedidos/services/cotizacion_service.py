"""
Servicio de gestión de pedidos, cotizaciones, transiciones Kanban y pagos.
Aplica bloqueos optimistas (version), validaciones de roles y transacciones atómicas.
"""
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.inventario.services.stock_service import (
    descontar_stock_pedido,
    reintegrar_stock_pedido,
)
from apps.pedidos.models import (
    Pedido,
    Cotizacion,
    HistorialEstadoPedido,
    Pago,
)


class ConflictError(Exception):
    """Excepción lanzada cuando la versión optimista no coincide (409 Conflict)."""
    pass


# Matriz estricta de transiciones según RF2
TRANSICIONES_PERMITIDAS = {
    Pedido.Estado.BORRADOR: [Pedido.Estado.COTIZADO, Pedido.Estado.CANCELADO],
    Pedido.Estado.COTIZADO: [Pedido.Estado.CONFIRMADO, Pedido.Estado.CANCELADO],
    Pedido.Estado.CONFIRMADO: [Pedido.Estado.EN_PREPARACION, Pedido.Estado.CANCELADO],
    Pedido.Estado.EN_PREPARACION: [Pedido.Estado.HORNEADO_DECORADO, Pedido.Estado.CANCELADO],
    Pedido.Estado.HORNEADO_DECORADO: [Pedido.Estado.CONTROL_CALIDAD, Pedido.Estado.CANCELADO],
    Pedido.Estado.CONTROL_CALIDAD: [Pedido.Estado.LISTO, Pedido.Estado.CANCELADO],
    Pedido.Estado.LISTO: [Pedido.Estado.EN_DESPACHO, Pedido.Estado.CANCELADO],
    Pedido.Estado.EN_DESPACHO: [Pedido.Estado.ENTREGADO, Pedido.Estado.CANCELADO],
    Pedido.Estado.ENTREGADO: [],
    Pedido.Estado.CANCELADO: [],
}

ROLES_PERMITIDOS_TRANSICION = {
    (Pedido.Estado.BORRADOR, Pedido.Estado.COTIZADO): ["ADMIN", "VENDEDOR"],
    (Pedido.Estado.COTIZADO, Pedido.Estado.CONFIRMADO): ["ADMIN", "VENDEDOR"],
    (Pedido.Estado.CONFIRMADO, Pedido.Estado.EN_PREPARACION): ["ADMIN", "COCINA"],
    (Pedido.Estado.EN_PREPARACION, Pedido.Estado.HORNEADO_DECORADO): ["ADMIN", "COCINA"],
    (Pedido.Estado.HORNEADO_DECORADO, Pedido.Estado.CONTROL_CALIDAD): ["ADMIN", "COCINA"],
    (Pedido.Estado.CONTROL_CALIDAD, Pedido.Estado.LISTO): ["ADMIN", "COCINA"],
    (Pedido.Estado.LISTO, Pedido.Estado.EN_DESPACHO): ["ADMIN", "VENDEDOR", "REPARTIDOR"],
    (Pedido.Estado.EN_DESPACHO, Pedido.Estado.ENTREGADO): ["ADMIN", "REPARTIDOR"],
}


def _generar_numero_cotizacion() -> str:
    """Genera un correlativo único COT-AAAA-NNNN."""
    anio = timezone.now().year
    count = Cotizacion.objects.filter(numero__startswith=f"COT-{anio}-").count() + 1
    numero = f"COT-{anio}-{count:04d}"
    while Cotizacion.objects.filter(numero=numero).exists():
        count += 1
        numero = f"COT-{anio}-{count:04d}"
    return numero


def emitir_cotizacion(pedido_id: int, usuario) -> Cotizacion:
    """
    Emite una cotización para un pedido en BORRADOR.
    - Valida que el pedido esté en BORRADOR.
    - Valida que tenga al menos un detalle.
    - Genera Cotizacion con snapshot de montos y validez de 7 días.
    - Pasa cotizaciones vigentes previas a RECHAZADA.
    - Pasa el pedido a COTIZADO y genera código si no tenía.
    - Registra historial.
    """
    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=pedido_id)

        if pedido.estado != Pedido.Estado.BORRADOR:
            raise ValidationError(
                f"Solo se puede cotizar un pedido en estado BORRADOR. Estado actual: {pedido.get_estado_display()}."
            )

        if not pedido.detalles.exists():
            raise ValidationError("El pedido debe tener al menos un detalle para ser cotizado.")

        # Recalcular totales para asegurar snapshot fiel
        pedido.recalcular_totales()

        if not pedido.codigo:
            pedido.generar_codigo()

        # Marcar cotizaciones vigentes anteriores como RECHAZADA
        pedido.cotizaciones.filter(estado=Cotizacion.Estado.VIGENTE).update(
            estado=Cotizacion.Estado.RECHAZADA
        )

        hoy = timezone.localdate()
        valida_hasta = hoy + timedelta(days=7)

        numero = _generar_numero_cotizacion()

        cotizacion = Cotizacion.objects.create(
            pedido=pedido,
            numero=numero,
            valida_hasta=valida_hasta,
            subtotal=pedido.subtotal,
            descuento=pedido.descuento,
            total=pedido.total,
            estado=Cotizacion.Estado.VIGENTE,
            condiciones=(
                "Cotización válida por 7 días. Requiere anticipo para confirmación y paso a cocina. "
                "Horario de entrega sujeto a coordinación."
            ),
            creado_por=usuario if (usuario and usuario.is_authenticated) else None,
        )

        estado_anterior = pedido.estado
        pedido.estado = Pedido.Estado.COTIZADO
        pedido.version += 1
        pedido.save(update_fields=["estado", "subtotal", "descuento", "total", "saldo", "anticipo", "version", "actualizado_en"])

        HistorialEstadoPedido.objects.create(
            pedido=pedido,
            estado_anterior=estado_anterior,
            estado_nuevo=Pedido.Estado.COTIZADO,
            usuario=usuario if (usuario and usuario.is_authenticated) else None,
            observacion=f"Emisión de cotización {cotizacion.numero} por un total de ${pedido.total:,.0f}.",
        )

        return cotizacion


def confirmar_pedido(pedido_id: int, usuario, version: Optional[int] = None) -> Pedido:
    """
    Confirma un pedido en estado COTIZADO:
    - Valida rol (ADMIN o VENDEDOR).
    - Valida estado actual.
    - Valida cotización vigente y no vencida.
    - Valida bloqueo optimista si se pasa versión.
    - Descuenta stock de insumos usando el BOM de forma atómica.
    - Pasa cotización a ACEPTADA.
    - Pasa pedido a CONFIRMADO (Recibido en Kanban).
    - Registra historial.
    """
    if usuario and usuario.is_authenticated and not (usuario.es_admin or usuario.es_vendedor or usuario.is_superuser):
        raise PermissionDenied("Solo administradores o vendedores pueden confirmar pedidos.")

    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=pedido_id)

        if version is not None and pedido.version != version:
            raise ConflictError("El pedido fue modificado por otro usuario. Recargue la página.")

        if pedido.estado != Pedido.Estado.COTIZADO:
            raise ValidationError(
                f"Solo se puede confirmar un pedido en estado COTIZADO. Estado actual: {pedido.get_estado_display()}."
            )

        cotizacion = pedido.cotizacion_actual
        if not cotizacion:
            raise ValidationError("El pedido no cuenta con una cotización vigente para ser confirmado.")

        if not cotizacion.esta_vigente:
            cotizacion.estado = Cotizacion.Estado.VENCIDA
            cotizacion.save(update_fields=["estado"])
            raise ValidationError("La cotización está vencida. Debe emitir una nueva cotización.")

        if not pedido.detalles.exists():
            raise ValidationError("El pedido no tiene productos/detalles para confirmar.")

        # Descontar stock mediante BOM de forma atómica y verificar disponibilidad
        descontar_stock_pedido(pedido, usuario)

        cotizacion.aceptar(usuario)

        estado_anterior = pedido.estado
        pedido.estado = Pedido.Estado.CONFIRMADO
        pedido.version += 1
        pedido.save(update_fields=["estado", "version", "actualizado_en"])

        HistorialEstadoPedido.objects.create(
            pedido=pedido,
            estado_anterior=estado_anterior,
            estado_nuevo=Pedido.Estado.CONFIRMADO,
            usuario=usuario if (usuario and usuario.is_authenticated) else None,
            observacion=f"Pedido confirmado con cotización {cotizacion.numero}. Insumos descontados de bodega.",
        )

        return pedido


def transicionar_estado(
    pedido_id: int,
    nuevo_estado: str,
    usuario,
    version: Optional[int] = None,
    observacion: str = "",
) -> Pedido:
    """
    Realiza una transición de estado en el flujo Kanban o logística:
    - Valida que la transición esté en la matriz de estados permitidos.
    - Valida los permisos de rol del usuario.
    - Valida bloqueo optimista con select_for_update().
    - Para pasar a EN_DESPACHO valida que exista una parada válida de despacho.
    - Para pasar a ENTREGADO valida que exista evidencia (firma/foto).
    """
    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=pedido_id)

        if version is not None and pedido.version != version:
            raise ConflictError("El pedido fue actualizado por otro usuario. Por favor recarga el tablero.")

        estado_actual = pedido.estado

        # Cancelación se maneja vía cancelar_pedido
        if nuevo_estado == Pedido.Estado.CANCELADO:
            return cancelar_pedido(
                pedido_id=pedido.id,
                usuario=usuario,
                motivo=observacion or "Cancelación desde tablero",
                version=version,
            )

        # Transición a COTIZADO se hace vía emitir_cotizacion
        if nuevo_estado == Pedido.Estado.COTIZADO and estado_actual == Pedido.Estado.BORRADOR:
            emitir_cotizacion(pedido.id, usuario)
            return Pedido.objects.get(pk=pedido.id)

        # Transición a CONFIRMADO se hace vía confirmar_pedido
        if nuevo_estado == Pedido.Estado.CONFIRMADO and estado_actual == Pedido.Estado.COTIZADO:
            return confirmar_pedido(pedido.id, usuario, version=version)

        # Verificar si la transición está permitida
        permitidos = TRANSICIONES_PERMITIDAS.get(estado_actual, [])
        if nuevo_estado not in permitidos:
            raise ValidationError(
                f"Transición no permitida: no se puede pasar de '{pedido.get_estado_display()}' a '{nuevo_estado}'."
            )

        # Validar permisos por rol
        par_transicion = (estado_actual, nuevo_estado)
        roles_permitidos = ROLES_PERMITIDOS_TRANSICION.get(par_transicion, ["ADMIN"])
        if usuario and usuario.is_authenticated and not usuario.is_superuser:
            if usuario.rol not in roles_permitidos and not usuario.es_admin:
                raise PermissionDenied(
                    f"Tu rol ({usuario.get_rol_display()}) no tiene permisos para mover el pedido a {nuevo_estado}."
                )

        # Validaciones de reglas de negocio para estados avanzados
        if nuevo_estado == Pedido.Estado.EN_DESPACHO:
            tiene_despacho_valido = pedido.despachos.filter(
                ruta__estado="EN_RUTA"
            ).exists()
            if not tiene_despacho_valido:
                raise ValidationError(
                    "No se puede pasar a 'En Despacho' sin una ruta de despacho activa iniciada."
                )

        if nuevo_estado == Pedido.Estado.ENTREGADO:
            ultimo_despacho = pedido.despachos.order_by("-id").first()
            if not ultimo_despacho or (not ultimo_despacho.firma_digital and not ultimo_despacho.foto_comprobante):
                raise ValidationError(
                    "No se puede marcar como Entregado sin evidencia de entrega (firma o foto)."
                )

        pedido.estado = nuevo_estado
        pedido.version += 1
        if nuevo_estado == Pedido.Estado.ENTREGADO:
            pedido.fecha_entrega_real = timezone.now()
            pedido.save(update_fields=["estado", "version", "fecha_entrega_real", "actualizado_en"])
        else:
            pedido.save(update_fields=["estado", "version", "actualizado_en"])

        HistorialEstadoPedido.objects.create(
            pedido=pedido,
            estado_anterior=estado_actual,
            estado_nuevo=nuevo_estado,
            usuario=usuario if (usuario and usuario.is_authenticated) else None,
            observacion=observacion or f"Transición de estado a {pedido.get_estado_display()}.",
        )

        return pedido


def cancelar_pedido(
    pedido_id: int,
    usuario,
    motivo: str,
    version: Optional[int] = None,
) -> Pedido:
    """
    Cancela un pedido y realiza la reversa de inventario si corresponde.
    - Admin puede cancelar desde cualquier estado (excepto ENTREGADO o ya CANCELADO).
    - Vendedor puede cancelar desde BORRADOR, COTIZADO y CONFIRMADO.
    - Cocina solo si aún no empieza la producción (BORRADOR/COTIZADO).
    - Si el inventario fue descontado, reintegra stock con movimientos ENTRADA.
    """
    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=pedido_id)

        if version is not None and pedido.version != version:
            raise ConflictError("El pedido fue modificado por otro usuario.")

        if pedido.estado == Pedido.Estado.CANCELADO:
            raise ValidationError("El pedido ya se encuentra cancelado.")

        if pedido.estado == Pedido.Estado.ENTREGADO:
            raise ValidationError("No se puede cancelar un pedido que ya fue entregado.")

        if usuario and usuario.is_authenticated and not usuario.is_superuser:
            if usuario.es_admin:
                pass
            elif usuario.es_vendedor:
                if pedido.estado not in [Pedido.Estado.BORRADOR, Pedido.Estado.COTIZADO, Pedido.Estado.CONFIRMADO]:
                    raise PermissionDenied("Vendedores solo pueden cancelar pedidos hasta estado CONFIRMADO.")
            else:
                raise PermissionDenied("No tienes permisos para cancelar este pedido.")

        # Reintegrar stock si fue descontado
        if pedido.inventario_descontado:
            reintegrar_stock_pedido(pedido, usuario)

        estado_anterior = pedido.estado
        pedido.estado = Pedido.Estado.CANCELADO
        pedido.motivo_cancelacion = motivo
        pedido.cancelado_por = usuario if (usuario and usuario.is_authenticated) else None
        pedido.version += 1
        pedido.save(update_fields=["estado", "motivo_cancelacion", "cancelado_por", "version", "actualizado_en"])

        HistorialEstadoPedido.objects.create(
            pedido=pedido,
            estado_anterior=estado_anterior,
            estado_nuevo=Pedido.Estado.CANCELADO,
            usuario=usuario if (usuario and usuario.is_authenticated) else None,
            observacion=f"Pedido cancelado. Motivo: {motivo}",
        )

        return pedido


def registrar_pago_pedido(
    pedido_id: int,
    monto: Decimal,
    tipo: str,
    metodo: str,
    referencia: str = "",
    comprobante=None,
    usuario=None,
) -> Pago:
    """
    Registra un pago para el pedido y recalcula totales (anticipo y saldo).
    """
    if monto <= Decimal("0"):
        raise ValidationError("El monto del pago debe ser mayor a cero.")

    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=pedido_id)

        pago = Pago.objects.create(
            pedido=pedido,
            monto=monto,
            tipo=tipo,
            metodo=metodo,
            referencia=referencia,
            comprobante=comprobante,
            registrado_por=usuario if (usuario and usuario.is_authenticated) else None,
        )

        pedido.recalcular_totales()
        pedido.save(update_fields=["anticipo", "saldo", "actualizado_en"])

        return pago
