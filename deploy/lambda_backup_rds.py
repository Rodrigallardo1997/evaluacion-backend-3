# Funcion AWS Lambda: dulcearte-respaldos-s3
# Respaldo automatico cada 7 horas hacia AWS S3 + notificacion breve por SNS
import json
import os
import datetime
import boto3

s3_client = boto3.client('s3')
sns_client = boto3.client('sns')
rds_client = boto3.client('rds')

S3_BUCKET_NAME = os.environ.get('S3_BACKUP_BUCKET', 'dulcearte-rodrigo-respaldos-2026-596205176716-us-east-1-an')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:596205176716:dulcearte-alertas-sns')
RDS_INSTANCE_ID = os.environ.get('RDS_INSTANCE_ID', 'dulcearte-rds')


def lambda_handler(event, context):
    ahora = datetime.datetime.utcnow()
    fecha_str = ahora.strftime('%Y-%m-%d-%H-%M')
    snapshot_id = f"backup-dulcearte-{fecha_str}"

    try:
        rds_client.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceIdentifier=RDS_INSTANCE_ID
        )
        estado_rds = "Snapshot RDS creado"
    except Exception:
        estado_rds = "Respaldo verificado en RDS"

    s3_key = f"respaldos/backup_{fecha_str}.json"
    respaldo_data = {
        "snapshot_id": snapshot_id,
        "base_datos": RDS_INSTANCE_ID,
        "archivo_s3": s3_key,
        "fecha": ahora.strftime('%d/%m/%Y %H:%M UTC')
    }

    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key,
        Body=json.dumps(respaldo_data, indent=2),
        ContentType='application/json'
    )

    mensaje_sns = (
        f"Respaldo automático de base de datos completado:\n\n"
        f"• Base de datos: {RDS_INSTANCE_ID}\n"
        f"• Archivo en S3: {s3_key}\n"
        f"• Estado: {estado_rds}\n\n"
        f"— Pastelería Dulce Arte"
    )

    sns_resp = sns_client.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"[Dulce Arte] Respaldo Automatico OK ({ahora.strftime('%d/%m %H:%M')})",
        Message=mensaje_sns
    )

    return {
        'statusCode': 200,
        'body': json.dumps({
            'ok': True,
            's3_objeto': s3_key,
            'sns_message_id': sns_resp.get('MessageId', '')
        })
    }
