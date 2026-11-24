# Funcion AWS Lambda: dulcearte-mensajeria-sns
# Envia notificaciones limpias y concisas hacia AWS SNS
import json
import os
import boto3

sns_client = boto3.client('sns')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:596205176716:dulcearte-alertas-sns')


def lambda_handler(event, context):
    http_method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod', 'POST')
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'body': ''}

    try:
        raw_body = event.get('body', event)
        if isinstance(raw_body, str):
            body = json.loads(raw_body) if raw_body.strip() else {}
        else:
            body = raw_body or {}

        asunto = body.get('asunto', 'Aviso Dulce Arte').strip()
        contenido = body.get('mensaje', '').strip()
        remitente = body.get('remitente', '').strip()

        if remitente and remitente not in ('Sistema Dulce Arte', 'Backend Django DRF (AWS EC2 + RDS)'):
            cuerpo_correo = f"{contenido}\n\nEnviado por: {remitente}\n— Pastelería Dulce Arte"
        else:
            cuerpo_correo = f"{contenido}\n\n— Pastelería Dulce Arte"

        message_id = "simulacion-local"
        if SNS_TOPIC_ARN:
            resp = sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"[Dulce Arte] {asunto}"[:100],
                Message=cuerpo_correo,
            )
            message_id = resp.get('MessageId', '')

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'ok': True,
                'message_id': message_id,
                'detalle': 'Notificacion enviada a SNS.'
            }),
        }

    except Exception as e:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'ok': False, 'error': str(e)}),
        }
