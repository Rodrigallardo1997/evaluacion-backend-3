"""
Servicio de logística de despachos, asignación de rutas y confirmación de entregas
con evidencia fotográfica o firma digital y enlace dinámico a mapas.
"""
import base64
import re
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.despachos.models import RutaDespacho, Despacho
from apps.pedidos.models import Pedido, HistorialEstadoPedido


def validar_firma_digital(firma_str: str) -> None:
    """
    Valida que el string sea un Data URL válido de imagen PNG o JPEG
    y que su tamaño decodificado sea menor a 2MB.
    """
    if not firma_str:
        return

    patron = r"^data:image\/(png|jpeg|jpg);base64,([A-Za-z0-9+/=]+)$"
    match = re.match(patron, firma_str.strip())
    if not match:
        raise ValidationError(
            "La firma digital debe ser una imagen válida en formato Data URL Base64 (PNG o JPEG)."
        )

    b64_data = match.group(2)
    try:
        raw_bytes = base64.b64decode(b64_data)
    except Exception:
        raise ValidationError("Error al decodificar la firma digital en Base64.")

    if len(raw_bytes) > 2 * 1024 * 1024:
        raise ValidationError("La firma digital excede el tamaño máximo permitido de 2 MB.")


def agregar_parada_ruta(ruta_id: int, pedido_id: int, orden: Optional[int] = None) -> Despacho:
    """
    Agrega una parada de despacho a una ruta existente.
    - Valida que el pedido esté en estado LISTO.
    - Valida regla de unicidad activa: no puede existir otra parada PENDIENTE activa para este pedido.
    - Si orden no viene especificado, asigna el siguiente número disponible.
    """
    with transaction.atomic():
        ruta = RutaDespacho.objects.select_for_update().get(pk=ruta_id)
        pedido = Pedido.objects.select_for_update().get(pk=pedido_id)

        if ruta.estado != RutaDespacho.Estado.PLANIFICADA:
            raise ValidationError(
                f"Solo se pueden agregar paradas a rutas PLANIFICADAS. Estado actual: {ruta.get_estado_display()}."
            )

        if pedido.estado != Pedido.Estado.LISTO:
            raise ValidationError(
                f"El pedido {pedido.codigo or f'#{pedido.id}'} debe estar en estado LISTO para ser despachado. "
                f"Estado actual: {pedido.get_estado_display()}."
            )

        # Regla de unicidad activa
        parada_activa = Despacho.objects.filter(
            pedido=pedido,
            estado=Despacho.Estado.PENDIENTE
        ).exists()
        if parada_activa:
            raise ValidationError(
                f"El pedido {pedido.codigo or f'#{pedido.id}'} ya tiene una parada pendiente asignada en una ruta."
            )

        if orden is None:
            max_orden = ruta.paradas.count() + 1
            orden = max_orden

        despacho = Despacho.objects.create(
            ruta=ruta,
            pedido=pedido,
            orden=orden,
            estado=Despacho.Estado.PENDIENTE,
        )
        return despacho


def iniciar_ruta(ruta_id: int, usuario) -> RutaDespacho:
    """
    Inicia la ruta de despacho:
    - Valida que la ruta esté en PLANIFICADA.
    - Valida que tenga al menos una parada.
    - Valida que todos los pedidos sigan en estado LISTO.
    - Pasa la ruta a EN_RUTA.
    - Pasa todos los pedidos a EN_DESPACHO con registro en historial.
    """
    with transaction.atomic():
        ruta = RutaDespacho.objects.select_for_update().get(pk=ruta_id)

        if ruta.estado != RutaDespacho.Estado.PLANIFICADA:
            raise ValidationError(
                f"Solo se pueden iniciar rutas en estado PLANIFICADA. Estado actual: {ruta.get_estado_display()}."
            )

        paradas = list(ruta.paradas.select_related("pedido").order_by("orden"))
        if not paradas:
            raise ValidationError("No se puede iniciar una ruta sin paradas asignadas.")

        if not ruta.codigo:
            ruta.generar_codigo()

        # Validar que todos los pedidos estén en LISTO
        pedidos_no_listos = [
            f"{p.pedido.codigo} ({p.pedido.get_estado_display()})"
            for p in paradas
            if p.pedido.estado != Pedido.Estado.LISTO
        ]
        if pedidos_no_listos:
            raise ValidationError(
                f"No se puede iniciar la ruta porque hay pedidos que no están en estado LISTO: {', '.join(pedidos_no_listos)}."
            )

        ruta.estado = RutaDespacho.Estado.EN_RUTA
        ruta.save(update_fields=["estado", "actualizado_en"])

        for parada in paradas:
            pedido = parada.pedido
            estado_anterior = pedido.estado
            pedido.estado = Pedido.Estado.EN_DESPACHO
            pedido.version += 1
            pedido.save(update_fields=["estado", "version", "actualizado_en"])

            HistorialEstadoPedido.objects.create(
                pedido=pedido,
                estado_anterior=estado_anterior,
                estado_nuevo=Pedido.Estado.EN_DESPACHO,
                usuario=usuario if (usuario and usuario.is_authenticated) else None,
                observacion=f"Pedido despachado en la ruta {ruta.codigo} asignada a {ruta.repartidor.get_full_name() or ruta.repartidor.username}.",
            )

        return ruta


def confirmar_entrega(
    despacho_id: int,
    receptor_nombre: str,
    firma_digital: Optional[str] = None,
    foto_comprobante=None,
    observaciones: str = "",
    latitud: Optional[Decimal] = None,
    longitud: Optional[Decimal] = None,
    usuario=None,
) -> Despacho:
    """
    Confirma la entrega de una parada:
    - Requiere receptor_nombre.
    - Requiere firma_digital O foto_comprobante (ambas opcionales pero al menos una obligatoria).
    - Valida firma digital si viene presente.
    - Pasa parada a ENTREGADO con fecha y evidencia.
    - Pasa pedido a ENTREGADO con fecha_entrega_real e historial.
    - Si todas las paradas de la ruta quedaron resueltas, completa la ruta.
    """
    receptor_nombre = (receptor_nombre or "").strip()
    if not receptor_nombre:
        raise ValidationError({"receptor_nombre": "El nombre del receptor es obligatorio para confirmar la entrega."})

    tiene_firma = bool(firma_digital and firma_digital.strip())
    tiene_foto = bool(foto_comprobante)

    if not tiene_firma and not tiene_foto:
        raise ValidationError(
            "Debe proporcionar al menos una evidencia de entrega: firma digital o foto del comprobante."
        )

    if tiene_firma:
        validar_firma_digital(firma_digital)

    with transaction.atomic():
        despacho = Despacho.objects.select_for_update().select_related("ruta", "pedido").get(pk=despacho_id)

        if despacho.estado != Despacho.Estado.PENDIENTE:
            raise ValidationError(
                f"Esta parada ya no está pendiente. Estado actual: {despacho.get_estado_display()}."
            )

        ahora = timezone.now()

        despacho.receptor_nombre = receptor_nombre
        if tiene_firma:
            despacho.firma_digital = firma_digital
        if tiene_foto:
            despacho.foto_comprobante = foto_comprobante
        despacho.observaciones = observaciones or ""
        despacho.fecha_entrega = ahora
        if latitud is not None:
            despacho.latitud = latitud
        if longitud is not None:
            despacho.longitud = longitud
        despacho.estado = Despacho.Estado.ENTREGADO
        despacho.save()

        # Actualizar pedido asociado
        pedido = despacho.pedido
        estado_anterior = pedido.estado
        pedido.estado = Pedido.Estado.ENTREGADO
        pedido.fecha_entrega_real = ahora
        pedido.version += 1
        pedido.save(update_fields=["estado", "fecha_entrega_real", "version", "actualizado_en"])

        HistorialEstadoPedido.objects.create(
            pedido=pedido,
            estado_anterior=estado_anterior,
            estado_nuevo=Pedido.Estado.ENTREGADO,
            usuario=usuario if (usuario and usuario.is_authenticated) else None,
            observacion=(
                f"Entrega confirmada a {receptor_nombre}. Evidencia registrada "
                f"({'firma' if tiene_firma else ''}{' y ' if (tiene_firma and tiene_foto) else ''}{'foto' if tiene_foto else ''})."
            ),
        )

        # Verificar si la ruta queda completa
        _verificar_cierre_automatico_ruta(despacho.ruta)

        return despacho


def registrar_entrega_fallida(despacho_id: int, motivo: str, usuario=None) -> Despacho:
    """
    Registra el intento de entrega como fallido:
    - Exige motivo.
    - Pasa la parada a FALLIDO.
    - Devuelve el pedido a LISTO para que pueda ser reprogramado en una nueva ruta.
    - Registra historial en el pedido.
    - Verifica si la ruta queda completa.
    """
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": "Debe especificar un motivo para la entrega fallida."})

    with transaction.atomic():
        despacho = Despacho.objects.select_for_update().select_related("ruta", "pedido").get(pk=despacho_id)

        if despacho.estado != Despacho.Estado.PENDIENTE:
            raise ValidationError(
                f"Esta parada no está en estado PENDIENTE. Estado actual: {despacho.get_estado_display()}."
            )

        despacho.estado = Despacho.Estado.FALLIDO
        despacho.observaciones = f"Entrega fallida: {motivo}"
        despacho.save(update_fields=["estado", "observaciones"])

        # Devolver pedido a LISTO para reprogramación
        pedido = despacho.pedido
        estado_anterior = pedido.estado
        pedido.estado = Pedido.Estado.LISTO
        pedido.version += 1
        pedido.save(update_fields=["estado", "version", "actualizado_en"])

        HistorialEstadoPedido.objects.create(
            pedido=pedido,
            estado_anterior=estado_anterior,
            estado_nuevo=Pedido.Estado.LISTO,
            usuario=usuario if (usuario and usuario.is_authenticated) else None,
            observacion=f"Entrega no concretada en ruta {despacho.ruta.codigo}. Motivo: {motivo}. Pedido devuelto a estado LISTO para reprogramación.",
        )

        _verificar_cierre_automatico_ruta(despacho.ruta)

        return despacho


def _verificar_cierre_automatico_ruta(ruta: RutaDespacho) -> None:
    """
    Si todas las paradas de la ruta fueron resueltas (ENTREGADO o FALLIDO),
    marca la ruta como COMPLETADA.
    """
    paradas_pendientes = ruta.paradas.filter(estado=Despacho.Estado.PENDIENTE).count()
    if paradas_pendientes == 0 and ruta.paradas.count() > 0:
        ruta.estado = RutaDespacho.Estado.COMPLETADA
        ruta.save(update_fields=["estado", "actualizado_en"])


def cerrar_ruta(ruta_id: int, usuario=None) -> RutaDespacho:
    """
    Cierre manual o forzado de una ruta.
    """
    with transaction.atomic():
        ruta = RutaDespacho.objects.select_for_update().get(pk=ruta_id)
        ruta.estado = RutaDespacho.Estado.COMPLETADA
        ruta.save(update_fields=["estado", "actualizado_en"])
        return ruta
