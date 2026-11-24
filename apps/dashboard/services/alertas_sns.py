"""
Servicio de Mensajería y Alertas en la Nube con AWS Lambda + AWS SNS.
Mensajes concisos, limpios y precisos con la información esencial de negocio.
"""
import json
import logging
import sys
import urllib.request
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_LAMBDA_SNS_URL = "https://wsa4lyofyakp3pxazuyg55d7fm0zpsaf.lambda-url.us-east-1.on.aws/"


def emitir_alerta_sns(asunto: str, mensaje: str, tipo: str = "OPERACION") -> bool:
    """
    Envía el mensaje limpio a la función AWS Lambda (dulcearte-mensajeria-sns),
    que lo publica en AWS SNS (dulcearte-alertas-sns).
    """
    if "test" in sys.argv:
        return True

    lambda_url = getattr(settings, "AWS_LAMBDA_SNS_URL", DEFAULT_LAMBDA_SNS_URL)
    if not str(lambda_url).startswith("https://"):
        return False

    payload = {
        "origen": "Dulce Arte",
        "tipo": tipo,
        "asunto": asunto[:90],
        "mensaje": mensaje,
    }
    try:
        req = urllib.request.Request(
            lambda_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=4) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
            logger.info(f"[OK SNS] Alerta enviada (ID: {data.get('message_id')})")
            return True
    except Exception as e:
        logger.warning(f"[WARN SNS] No se pudo enviar alerta: {str(e)}")
        return False


def notificar_nuevo_pedido(pedido) -> bool:
    """Notificación concisa al registrar un nuevo pedido."""
    cliente_nombre = getattr(pedido.cliente, "nombre_completo", str(pedido.cliente))
    fecha_str = pedido.fecha_entrega.strftime("%d/%m/%Y %H:%M") if getattr(pedido, "fecha_entrega", None) else "Por confirmar"
    asunto = f"Nuevo Pedido {pedido.codigo} - {cliente_nombre}"
    mensaje = (
        f"Nuevo pedido registrado en Dulce Arte:\n\n"
        f"• Pedido: {pedido.codigo}\n"
        f"• Cliente: {cliente_nombre}\n"
        f"• Entrega: {fecha_str}\n"
        f"• Total: ${pedido.total:,.0f} CLP ({pedido.get_estado_display()})"
    )
    return emitir_alerta_sns(asunto, mensaje, tipo="PEDIDO")


def notificar_nueva_receta(receta, accion: str = "Creada") -> bool:
    """Notificación concisa al crear o editar un producto del catálogo."""
    accion_limpia = "creado" if accion.upper().startswith("C") else "actualizado"
    asunto = f"Catalogo: {receta.nombre} (${receta.precio_base:,.0f})"
    mensaje = (
        f"Producto {accion_limpia} en el catálogo:\n\n"
        f"• Producto: {receta.nombre}\n"
        f"• Categoría: {receta.get_categoria_display()}\n"
        f"• Precio: ${receta.precio_base:,.0f} CLP\n"
        f"• Preparación: {receta.tiempo_preparacion_min} min"
    )
    return emitir_alerta_sns(asunto, mensaje, tipo="CATALOGO")


def notificar_stock_critico(insumo) -> bool:
    """Notificación concisa cuando un insumo queda bajo el stock mínimo."""
    asunto = f"Stock Bajo: {insumo.nombre}"
    mensaje = (
        f"Insumo en nivel crítico de inventario:\n\n"
        f"• Insumo: {insumo.nombre}\n"
        f"• Disponible: {insumo.stock_actual} {insumo.unidad} (Mínimo: {insumo.stock_minimo} {insumo.unidad})"
    )
    return emitir_alerta_sns(asunto, mensaje, tipo="STOCK")


def notificar_pedido_confirmado(pedido) -> bool:
    """Notificación concisa a cocina cuando un pedido pasa a CONFIRMADO."""
    cliente_nombre = getattr(pedido.cliente, "nombre_completo", str(pedido.cliente))
    asunto = f"A Cocina: Pedido {pedido.codigo} Confirmado"
    mensaje = (
        f"Pedido confirmado y enviado al Tablero Kanban de Cocina:\n\n"
        f"• Pedido: {pedido.codigo}\n"
        f"• Cliente: {cliente_nombre}\n"
        f"• Total: ${pedido.total:,.0f} CLP (Prioridad: {pedido.get_prioridad_display()})"
    )
    return emitir_alerta_sns(asunto, mensaje, tipo="COCINA")
