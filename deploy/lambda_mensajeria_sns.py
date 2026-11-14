"""
AWS LAMBDA FUNCTION: SERVICIO DE MENSAJERÍA UNIFICADA (FRONTEND & BACKEND -> SNS)
Asignatura: Desarrollo Backend | Arquitectura Serverless & Desacoplada
Autor: Rodrigo Alejandro Gallardo Martínez

Descripción:
  Recibe eventos JSON por HTTP (API Gateway o Lambda Function URL) tanto desde
  el Frontend desacoplado (S3 / EC2 Frontend) como desde el Backend (EC2 Django),
  y los publica en un tópico de AWS SNS para enviar correos/alertas en tiempo real.
"""
import json
import os
import datetime
import boto3

sns_client = boto3.client('sns')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')


def _cors_headers():
    """Cabeceras CORS para permitir peticiones desde el Frontend desacoplado en S3/EC2."""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'OPTIONS,POST',
    }


def lambda_handler(event, context):
    """Punto de entrada de la función Lambda de mensajería."""
    # Responder preflight CORS (OPTIONS)
    http_method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod', 'POST')
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': _cors_headers(), 'body': ''}

    try:
        # Parsear cuerpo JSON (soporta invocación directa o vía API Gateway)
        raw_body = event.get('body', event)
        if isinstance(raw_body, str):
            body = json.loads(raw_body) if raw_body.strip() else {}
        else:
            body = raw_body or {}

        origen = body.get('origen', 'frontend').upper()  # 'FRONTEND' o 'BACKEND'
        tipo = body.get('tipo', 'NOTIFICACION')
        remitente = body.get('remitente', 'Sistema Dulce Arte')
        asunto = body.get('asunto', f'[{origen}] Alerta Dulce Arte')
        contenido = body.get('mensaje', 'Sin contenido adicional.')
        fecha = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

        mensaje_formateado = (
            f"🎂 DULCE ARTE — NOTIFICACIÓN CLOUD ({origen})\n"
            f"==================================================\n"
            f"• Origen del Evento : {origen}\n"
            f"• Tipo de Alerta    : {tipo}\n"
            f"• Remitente         : {remitente}\n"
            f"• Fecha/Hora        : {fecha}\n"
            f"--------------------------------------------------\n"
            f"Mensaje:\n{contenido}\n"
            f"==================================================\n"
        )

        message_id = "simulacion-local"
        if SNS_TOPIC_ARN:
            resp = sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"[Dulce Arte - {origen}] {asunto}"[:100],
                Message=mensaje_formateado,
            )
            message_id = resp.get('MessageId', '')

        return {
            'statusCode': 200,
            'headers': _cors_headers(),
            'body': json.dumps({
                'ok': True,
                'origen': origen,
                'message_id': message_id,
                'detalle': 'Notificación enviada exitosamente vía AWS Lambda -> SNS.'
            }),
        }

    except Exception as e:
        return {
            'statusCode': 400,
            'headers': _cors_headers(),
            'body': json.dumps({'ok': False, 'error': str(e)}),
        }
