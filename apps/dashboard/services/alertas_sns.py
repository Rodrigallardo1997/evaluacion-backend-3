"""
Servicio de Mensajería y Alertas en la Nube con AWS Lambda + AWS SNS.
Permite que tanto el Backend (Django) como el Frontend envíen notificaciones por correo
a través de la función Serverless 'dulcearte-mensajeria-sns' conectada al tópico SNS.
"""
import json
import logging
import sys
import urllib.request
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_LAMBDA_SNS_URL = "https://wsa4lyofyakp3pxazuyg55d7fm0zpsaf.lambda-url.us-east-1.on.aws/"


def emitir_alerta_sns(asunto: str, mensaje: str, tipo: str = "OPERACION_BACKEND") -> bool:
    """
    Envía un evento a la función AWS Lambda (dulcearte-mensajeria-sns),
    la cual publica el correo en el tópico AWS SNS (dulcearte-alertas-sns).
    Durante la ejecución de tests unitarios ('manage.py test') omite la llamada HTTP externa.
    """
    if "test" in sys.argv:
        return True

    lambda_url = getattr(settings, "AWS_LAMBDA_SNS_URL", DEFAULT_LAMBDA_SNS_URL)
    if not str(lambda_url).startswith("https://"):
        return False

    payload = {
        "origen": "backend",
        "tipo": tipo,
        "remitente": "Backend Django DRF (AWS EC2 + RDS)",
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
            logger.info(f"[OK Lambda->SNS] Alerta enviada. MessageId: {data.get('message_id')}")
            return True
    except Exception as e:
        logger.warning(f"[WARN Lambda->SNS] No se pudo enviar alerta externa: {str(e)}")
        return False


def notificar_nuevo_pedido(pedido) -> bool:
    """Dispara correo vía Lambda -> SNS cada vez que se crea un nuevo pedido en RDS."""
    cliente_nombre = getattr(pedido.cliente, "nombre_completo", str(pedido.cliente))
    asunto = f"Nuevo Pedido Creado: {pedido.codigo}"
    mensaje = (
        f"Se ha registrado un nuevo pedido en la base de datos AWS RDS PostgreSQL:\n\n"
        f"- Codigo de Orden : {pedido.codigo}\n"
        f"- Cliente         : {cliente_nombre}\n"
        f"- Estado Inicial  : {pedido.get_estado_display()}\n"
        f"- Total Estimado  : ${pedido.total:,.0f} CLP\n"
        f"- Prioridad       : {pedido.get_prioridad_display()}\n"
    )
    return emitir_alerta_sns(asunto, mensaje, tipo="NUEVO_PEDIDO_RDS")


def notificar_nueva_receta(receta, accion: str = "CREADA") -> bool:
    """Dispara correo vía Lambda -> SNS cada vez que se crea o actualiza un producto/receta en RDS."""
    asunto = f"Receta {accion} en Catalogo: {receta.nombre}"
    mensaje = (
        f"Operacion CRUD persistida en AWS RDS PostgreSQL:\n\n"
        f"- Accion          : {accion}\n"
        f"- ID Producto     : #{receta.id}\n"
        f"- Nombre          : {receta.nombre}\n"
        f"- Categoria       : {receta.get_categoria_display()}\n"
        f"- Precio Base     : ${receta.precio_base:,.0f} CLP\n"
        f"- Tiempo Prep.    : {receta.tiempo_preparacion_min} min\n"
    )
    return emitir_alerta_sns(asunto, mensaje, tipo=f"CRUD_RECETA_{accion}")


def notificar_stock_critico(insumo) -> bool:
    """Emite una alerta cuando un insumo cae por debajo del umbral mínimo."""
    asunto = f"Alerta Stock Critico: {insumo.nombre}"
    mensaje = (
        f"Alerta de inventario en Pasteleria Dulce Arte:\n\n"
        f"- Insumo          : {insumo.nombre}\n"
        f"- Stock Actual    : {insumo.stock_actual} {insumo.unidad}\n"
        f"- Stock Minimo    : {insumo.stock_minimo} {insumo.unidad}\n"
    )
    return emitir_alerta_sns(asunto, mensaje, tipo="ALERTA_STOCK")


def notificar_pedido_confirmado(pedido) -> bool:
    """Emite una alerta a cocina cuando un pedido pasa a estado CONFIRMADO."""
    asunto = f"Pedido Confirmado a Cocina: {pedido.codigo}"
    mensaje = (
        f"Nuevo pedido confirmado para elaboracion en Tablero Kanban:\n\n"
        f"- Codigo          : {pedido.codigo}\n"
        f"- Cliente         : {pedido.cliente.nombre_completo}\n"
        f"- Total           : ${pedido.total:,.0f} CLP\n"
    )
    return emitir_alerta_sns(asunto, mensaje, tipo="PEDIDO_CONFIRMADO")
