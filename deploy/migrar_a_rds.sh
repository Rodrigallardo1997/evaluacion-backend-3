#!/bin/bash
# ==============================================================================
# SCRIPT DE MIGRACIÓN DE POSTGRESQL LOCAL (EC2) A AWS RDS
# Arquitectura de 3 Capas (Tier-3) & Alta Disponibilidad
# Autor: Rodrigo Alejandro Gallardo Martínez
# ==============================================================================
set -e

echo "=== [Dulce Arte] Asistente de Migración a AWS RDS PostgreSQL ==="

# Parámetros requeridos (modificar o pasar por variables de entorno)
RDS_ENDPOINT="${1:-$RDS_HOST}"
RDS_USER="${2:-dulcearte_admin}"
RDS_DB="${3:-dulcearte_db}"
LOCAL_DB="dulcearte_db"
LOCAL_USER="dulcearte_user"
BACKUP_FILE="/tmp/dulcearte_backup_$(date +%Y%m%d_%H%M%S).sql"

if [ -z "$RDS_ENDPOINT" ]; then
    echo "Uso: ./migrar_a_rds.sh <RDS_ENDPOINT> [RDS_USER] [RDS_DB]"
    echo "Ejemplo: ./migrar_a_rds.sh dulcearte-db.c123456789.us-east-1.rds.amazonaws.com"
    exit 1
fi

echo "[1/4] Generando dump de la base de datos local en EC2..."
sudo -u postgres pg_dump -d "$LOCAL_DB" --clean --no-owner --no-acl > "$BACKUP_FILE"
echo "[OK] Respaldo generado en $BACKUP_FILE ($(du -h $BACKUP_FILE | cut -f1))"

echo "[2/4] Restaurando datos en la instancia AWS RDS ($RDS_ENDPOINT)..."
echo "Por favor ingrese la contraseña de RDS si se le solicita:"
psql -h "$RDS_ENDPOINT" -U "$RDS_USER" -d "$RDS_DB" -f "$BACKUP_FILE"
echo "[OK] Restauración completada exitosamente en AWS RDS."

echo "[3/4] Actualizando archivo de variables de entorno (.env)..."
NEW_DATABASE_URL="postgres://${RDS_USER}:SU_PASSWORD@${RDS_ENDPOINT}:5432/${RDS_DB}?sslmode=require"
echo "Recuerde actualizar DATABASE_URL en /home/ubuntu/dulcearte/.env con:"
echo "DATABASE_URL=$NEW_DATABASE_URL"

echo "[4/4] Limpiando archivo temporal..."
rm -f "$BACKUP_FILE"

echo "=== [Dulce Arte] Migración a AWS RDS finalizada con éxito ==="
