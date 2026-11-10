"""
Servicio de Mensajería y Alertas en la Nube con AWS SNS (Simple Notification Service).
Permite notificar eventos operacionales críticos (stock bajo, pedidos confirmados, rutas de despacho).
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def emitir_alerta_sns(asunto: str, mensaje: str) -> bool:
    """
    Publica un mensaje en el tópico de AWS SNS configurado en las variables de entorno.
    Si AWS SNS no está activo o no hay credenciales, registra el evento en el log sin romper la app.
    """
    topic_arn = getattr(settings, "AWS_SNS_TOPIC_ARN", None)
    
    if not topic_arn:
        logger.info(f"[SIMULACIÓN SNS] Asunto: {asunto} | Mensaje: {mensaje}")
        return True

    try:
        import boto3
        sns_client = boto3.client(
            "sns",
            region_name=getattr(settings, "AWS_S3_REGION_NAME", "us-east-1"),
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        )
        response = sns_client.publish(
            TopicArn=topic_arn,
            Subject=asunto[:100],  # Límite de 100 caracteres para asunto SNS
            Message=mensaje,
        )
        logger.info(f"[OK AWS SNS] Mensaje publicado con MessageId: {response.get('MessageId')}")
        return True
    except Exception as e:
        logger.error(f"[ERROR AWS SNS] No se pudo emitir la notificación: {str(e)}")
        return False


def notificar_stock_critico(insumo) -> bool:
    """Emite una alerta cuando un insumo cae por debajo del umbral mínimo."""
    asunto = f"⚠️ [ALERTA STOCK] Insumo Crítico: {insumo.nombre}"
    mensaje = (
        f"Alerta de inventario en Pastelería Dulce Arte:\n\n"
        f"• Insumo: {insumo.nombre}\n"
        f"• Categoría: {insumo.get_categoria_display()}\n"
        f"• Stock Actual: {insumo.stock_actual} {insumo.unidad}\n"
        f"• Stock Mínimo Requerido: {insumo.stock_minimo} {insumo.unidad}\n\n"
        f"Acción requerida: Generar orden de compra a proveedores a la brevedad."
    )
    return emitir_alerta_sns(asunto, mensaje)


def notificar_pedido_confirmado(pedido) -> bool:
    """Emite una alerta a cocina cuando un pedido pasa a estado CONFIRMADO."""
    asunto = f"🎂 [NUEVO PEDIDO] Orden {pedido.codigo} Confirmada"
    mensaje = (
        f"Nuevo pedido confirmado para elaboración en cocina:\n\n"
        f"• Código: {pedido.codigo}\n"
        f"• Cliente: {pedido.cliente.nombre_completo}\n"
        f"• Fecha de Entrega: {pedido.fecha_entrega.strftime('%d-%m-%Y %H:%M')}\n"
        f"• Total: ${pedido.total:,.0f} CLP (Anticipo 50% recibido)\n"
        f"• Prioridad: {pedido.get_prioridad_display()}\n\n"
        f"El pedido ha ingresado automáticamente al Tablero Kanban de cocina."
    )
    return emitir_alerta_sns(asunto, mensaje)
