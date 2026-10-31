"""
Servicio de gestión de stock e inventario con Lista de Materiales (BOM).
Garantiza transacciones atómicas, select_for_update() y trazabilidad total.
"""
from decimal import Decimal
from typing import Dict, Any, List

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import Insumo
from apps.inventario.models import MovimientoInventario


def calcular_consumo_pedido(pedido) -> Dict[int, Dict[str, Any]]:
    """
    Calcula el consumo total de insumos para todos los detalles del pedido
    aplicando la Lista de Materiales (BOM) y el porcentaje de merma.

    Retorna un diccionario:
    {
        insumo_id: {
            'insumo': Insumo,
            'cantidad_requerida': Decimal,
        }
    }
    """
    consumos: Dict[int, Dict[str, Any]] = {}

    detalles = pedido.detalles.select_related("receta").prefetch_related(
        "receta__insumos__insumo"
    ).all()

    for detalle in detalles:
        receta = detalle.receta
        cantidad_pedido = Decimal(str(detalle.cantidad))

        for receta_insumo in receta.insumos.all():
            insumo = receta_insumo.insumo
            # cantidad_neta = cantidad * (1 + merma_porcentaje / 100)
            consumo_unitario = receta_insumo.cantidad_neta
            consumo_linea = consumo_unitario * cantidad_pedido

            if insumo.id not in consumos:
                consumos[insumo.id] = {
                    "insumo": insumo,
                    "cantidad_requerida": Decimal("0"),
                }

            consumos[insumo.id]["cantidad_requerida"] += consumo_linea

    return consumos


def descontar_stock_pedido(pedido, usuario) -> List[MovimientoInventario]:
    """
    Descuenta de forma atómica el stock de insumos requeridos por el pedido.
    Aplica select_for_update() ordenado por id para evitar deadlocks y carreras.
    Es idempotente: si inventario_descontado es True, no vuelve a descontar.
    """
    if pedido.inventario_descontado:
        return []

    consumos = calcular_consumo_pedido(pedido)
    if not consumos:
        # Pedido sin insumos asociados en sus recetas
        pedido.inventario_descontado = True
        pedido.save(update_fields=["inventario_descontado", "actualizado_en"])
        return []

    insumo_ids = sorted(list(consumos.keys()))

    with transaction.atomic():
        # Bloquear insumos ordenados por ID (prevención de deadlocks)
        insumos_db = {
            insumo.id: insumo
            for insumo in Insumo.objects.select_for_update().filter(id__in=insumo_ids).order_by("id")
        }

        # 1. Validar vencimientos y disponibilidad total ANTES de descontar
        faltantes = []
        vencidos = []

        for insumo_id in insumo_ids:
            insumo = insumos_db[insumo_id]
            requerido = consumos[insumo_id]["cantidad_requerida"]

            if insumo.esta_vencido:
                vencidos.append(f"{insumo.nombre} (Vencido el {insumo.fecha_vencimiento})")

            if insumo.stock_actual < requerido:
                faltante = requerido - insumo.stock_actual
                faltantes.append({
                    "insumo": insumo.nombre,
                    "unidad": insumo.unidad,
                    "requerido": str(requerido),
                    "disponible": str(insumo.stock_actual),
                    "faltante": str(faltante),
                })

        if vencidos:
            raise ValidationError(
                f"No se puede confirmar el pedido. Hay insumos vencidos: {', '.join(vencidos)}"
            )

        if faltantes:
            detalles_str = "; ".join(
                f"{f['insumo']}: requiere {f['requerido']} {f['unidad']}, disponible {f['disponible']} {f['unidad']} (falta {f['faltante']})"
                for f in faltantes
            )
            raise ValidationError(
                f"Stock insuficiente para confirmar el pedido: {detalles_str}"
            )

        # 2. Descontar stock y registrar movimientos
        movimientos = []
        for insumo_id in insumo_ids:
            insumo = insumos_db[insumo_id]
            requerido = consumos[insumo_id]["cantidad_requerida"]

            stock_anterior = insumo.stock_actual
            stock_nuevo = stock_anterior - requerido

            insumo.stock_actual = stock_nuevo
            insumo.save(update_fields=["stock_actual", "actualizado_en"])

            mov = MovimientoInventario.objects.create(
                insumo=insumo,
                tipo=MovimientoInventario.Tipo.SALIDA,
                cantidad=requerido,
                stock_anterior=stock_anterior,
                stock_nuevo=stock_nuevo,
                motivo=f"Consumo pedido {pedido.codigo or f'#{pedido.pk}'}",
                pedido=pedido,
                usuario=usuario if (usuario and usuario.is_authenticated) else None,
            )
            movimientos.append(mov)

        # 3. Marcar pedido con inventario descontado
        pedido.inventario_descontado = True
        pedido.save(update_fields=["inventario_descontado", "actualizado_en"])

        return movimientos


def reintegrar_stock_pedido(pedido, usuario) -> List[MovimientoInventario]:
    """
    Reintegra al inventario las cantidades exactas registradas en los movimientos
    SALIDA de este pedido.
    No recalcula desde la receta para evitar inconsistencias si la receta fue editada.
    """
    if not pedido.inventario_descontado:
        return []

    with transaction.atomic():
        movimientos_salida = pedido.movimientos_inventario.filter(
            tipo=MovimientoInventario.Tipo.SALIDA
        ).select_related("insumo").order_by("insumo_id")

        if not movimientos_salida.exists():
            pedido.inventario_descontado = False
            pedido.save(update_fields=["inventario_descontado", "actualizado_en"])
            return []

        insumo_ids = sorted(list(set(m.insumo_id for m in movimientos_salida)))
        insumos_db = {
            insumo.id: insumo
            for insumo in Insumo.objects.select_for_update().filter(id__in=insumo_ids).order_by("id")
        }

        movimientos_entrada = []
        for mov_salida in movimientos_salida:
            insumo = insumos_db[mov_salida.insumo_id]
            cantidad = mov_salida.cantidad

            stock_anterior = insumo.stock_actual
            stock_nuevo = stock_anterior + cantidad

            insumo.stock_actual = stock_nuevo
            insumo.save(update_fields=["stock_actual", "actualizado_en"])

            mov = MovimientoInventario.objects.create(
                insumo=insumo,
                tipo=MovimientoInventario.Tipo.ENTRADA,
                cantidad=cantidad,
                stock_anterior=stock_anterior,
                stock_nuevo=stock_nuevo,
                motivo=f"Reversa por cancelación pedido {pedido.codigo or f'#{pedido.pk}'}",
                pedido=pedido,
                usuario=usuario if (usuario and usuario.is_authenticated) else None,
            )
            movimientos_entrada.append(mov)

        pedido.inventario_descontado = False
        pedido.save(update_fields=["inventario_descontado", "actualizado_en"])

        return movimientos_entrada


def registrar_movimiento(
    insumo: Insumo,
    tipo: str,
    cantidad: Decimal,
    motivo: str,
    usuario=None,
    pedido=None,
) -> MovimientoInventario:
    """
    Registra un movimiento manual (ENTRADA, SALIDA, MERMA, AJUSTE) de forma atómica.
    - ENTRADA: stock_nuevo = stock_anterior + cantidad
    - SALIDA, MERMA: stock_nuevo = stock_anterior - cantidad
    - AJUSTE: cantidad representa el nuevo stock absoluto o el ajuste
    """
    if cantidad <= Decimal("0"):
        raise ValidationError("La cantidad del movimiento debe ser mayor a cero.")

    with transaction.atomic():
        insumo_lock = Insumo.objects.select_for_update().get(pk=insumo.pk)
        stock_anterior = insumo_lock.stock_actual

        if tipo == MovimientoInventario.Tipo.ENTRADA:
            stock_nuevo = stock_anterior + cantidad
        elif tipo in (MovimientoInventario.Tipo.SALIDA, MovimientoInventario.Tipo.MERMA):
            if stock_anterior < cantidad:
                raise ValidationError(
                    f"No hay stock suficiente para realizar la salida. Disponible: {stock_anterior}, Solicitado: {cantidad}"
                )
            stock_nuevo = stock_anterior - cantidad
        elif tipo == MovimientoInventario.Tipo.AJUSTE:
            # En ajuste, la cantidad recibida se interpreta como la corrección directa
            stock_nuevo = cantidad
            # cantidad registrada es la diferencia absoluta
            cantidad = abs(stock_nuevo - stock_anterior)
        else:
            raise ValidationError(f"Tipo de movimiento '{tipo}' inválido.")

        if stock_nuevo < Decimal("0"):
            raise ValidationError("El stock resultante no puede ser negativo.")

        insumo_lock.stock_actual = stock_nuevo
        insumo_lock.save(update_fields=["stock_actual", "actualizado_en"])

        mov = MovimientoInventario.objects.create(
            insumo=insumo_lock,
            tipo=tipo,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=stock_nuevo,
            motivo=motivo,
            pedido=pedido,
            usuario=usuario if (usuario and usuario.is_authenticated) else None,
        )
        return mov
