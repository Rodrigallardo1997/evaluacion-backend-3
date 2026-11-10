"""
AWS LAMBDA FUNCTION: RESPALDO AUTOMATIZADO DE BASE DE DATOS Y ALERTAS SNS
Asignatura: Desarrollo Backend | Arquitectura Serverless
Autor: Rodrigo Alejandro Gallardo Martínez

Disparador: EventBridge / CloudWatch Events (Cron diario: 'cron(0 5 * * ? *)')
Destino 1: Bucket AWS S3 (dulcearte-backups-s3)
Destino 2: Tópico AWS SNS (dulcearte-alertas-topic)
"""
import os
import json
import gzip
import datetime
import boto3

s3_client = boto3.client('s3')
sns_client = boto3.client('sns')

S3_BUCKET_NAME = os.environ.get('S3_BACKUP_BUCKET', 'dulcearte-backups-s3')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:123456789012:dulcearte-alertas')
RDS_INSTANCE_ID = os.environ.get('RDS_INSTANCE_ID', 'dulcearte-db')


def lambda_handler(event, context):
    """
    Punto de entrada de AWS Lambda para respaldos automáticos y notificaciones SNS.
    """
    fecha_actual = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    snapshot_id = f"snapshot-dulcearte-{fecha_actual}"
    
    print(f"=== [AWS Lambda] Iniciando respaldo automatizado: {snapshot_id} ===")
    
    try:
        # 1. Crear Snapshot automatizado de AWS RDS
        rds_client = boto3.client('rds')
        response = rds_client.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceIdentifier=RDS_INSTANCE_ID,
            Tags=[
                {'Key': 'Proyecto', 'Value': 'DulceArte'},
                {'Key': 'Ambiente', 'Value': 'Produccion'},
                {'Key': 'CreadoPor', 'Value': 'LambdaBackup'},
            ]
        )
        
        # 2. Registrar log y comprobante de respaldo en bucket S3
        log_payload = {
            "snapshot_id": snapshot_id,
            "instancia_rds": RDS_INSTANCE_ID,
            "timestamp": fecha_actual,
            "estado": "INICIADO",
            "detalles": "Respaldo programado ejecutado con éxito por AWS Lambda."
        }
        
        s3_key = f"manifests/{datetime.datetime.now().strftime('%Y/%m')}/backup_{fecha_actual}.json"
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(log_payload, indent=2),
            ContentType='application/json'
        )
        print(f"[OK] Manifiesto guardado en S3: s3://{S3_BUCKET_NAME}/{s3_key}")
        
        # 3. Emitir notificación de éxito a través de AWS SNS
        mensaje_sns = (
            f"✅ [DULCE ARTE - ALERTA AWS] Respaldo Diario Completado\n\n"
            f"• Identificador Snapshot: {snapshot_id}\n"
            f"• Instancia de BD: {RDS_INSTANCE_ID}\n"
            f"• Destino Manifiesto: s3://{S3_BUCKET_NAME}/{s3_key}\n"
            f"• Fecha y Hora: {fecha_actual}\n\n"
            f"Estado: Base de datos resguardada con alta disponibilidad."
        )
        
        if SNS_TOPIC_ARN and not SNS_TOPIC_ARN.endswith('123456789012:dulcearte-alertas'):
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="[AWS SNS] Respaldo de Base de Datos Exitoso - Dulce Arte",
                Message=mensaje_sns
            )
            print("[OK] Alerta emitida exitosamente por AWS SNS.")
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'mensaje': 'Respaldo y notificación ejecutados correctamente.',
                'snapshot_id': snapshot_id,
                's3_manifest': s3_key
            })
        }
        
    except Exception as e:
        error_msg = f"❌ [ERROR AWS Lambda] Falló el respaldo de BD: {str(e)}"
        print(error_msg)
        
        # Emitir alerta de falla crítica por SNS
        try:
            if SNS_TOPIC_ARN and not SNS_TOPIC_ARN.endswith('123456789012:dulcearte-alertas'):
                sns_client.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject="🚨 [CRÍTICO] Falló el Respaldo de Base de Datos - Dulce Arte",
                    Message=error_msg
                )
        except Exception:
            pass
            
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
