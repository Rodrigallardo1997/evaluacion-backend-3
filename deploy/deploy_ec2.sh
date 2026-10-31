#!/bin/bash
# ==============================================================================
# SCRIPT DE DESPLIEGUE IDEMPOTENTE PARA AWS EC2 - DULCE ARTE
# Asignatura: Desarrollo Backend | Evaluación Parcial N°3
# Autor: Rodrigo Alejandro Gallardo Martínez
# ==============================================================================
# ADVERTENCIA: Este script NO debe ejecutarse a ciegas. Revise las variables y
# asegúrese de tener configurado su archivo .env antes de iniciar los servicios.
# ==============================================================================

set -e

PROJECT_DIR="/home/ubuntu/dulcearte"
VENV_DIR="$PROJECT_DIR/venv"

echo "======================================================================"
echo "Iniciando despliegue de Dulce Arte en AWS EC2 (Ubuntu 24.04 LTS)..."
echo "======================================================================"

# 1. Actualización e instalación de paquetes del sistema
echo "[1/7] Actualizando repositorios e instalando paquetes del SO..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip postgresql postgresql-contrib nginx git curl libpq-dev

# 2. Habilitar servicios de base de datos y servidor web
echo "[2/7] Asegurando inicio automático de PostgreSQL y Nginx..."
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo systemctl enable nginx
sudo systemctl start nginx

# 3. Entorno virtual de Python
echo "[3/7] Configurando entorno virtual Python..."
cd "$PROJECT_DIR"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# 4. Verificación de archivo de entorno .env
echo "[4/7] Verificando archivo de configuración .env..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "¡ATENCIÓN! No existe el archivo .env en $PROJECT_DIR."
    echo "Copie el archivo .env.example a .env y configure la IP pública y credenciales de PostgreSQL:"
    echo "cp .env.example .env && nano .env"
    exit 1
fi

# 5. Ejecutar migraciones del ORM y recolectar estáticos
echo "[5/7] Ejecutando migraciones en PostgreSQL y collectstatic..."
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 6. Configurar permisos de directorios
echo "[6/7] Ajustando permisos de media y staticfiles para Nginx..."
sudo chown -R ubuntu:www-data "$PROJECT_DIR/media"
sudo chmod -R 775 "$PROJECT_DIR/media"
sudo chown -R ubuntu:www-data "$PROJECT_DIR/staticfiles"
sudo chmod -R 755 "$PROJECT_DIR/staticfiles"

# 7. Configuración de servicios systemd y Nginx
echo "[7/7] Configurando Gunicorn (systemd) y Nginx..."
sudo cp "$PROJECT_DIR/deploy/dulcearte.service" /etc/systemd/system/dulcearte.service
sudo systemctl daemon-reload
sudo systemctl enable dulcearte
sudo systemctl restart dulcearte

if [ -f "/etc/nginx/sites-enabled/default" ]; then
    sudo rm -f /etc/nginx/sites-enabled/default
fi
sudo cp "$PROJECT_DIR/deploy/nginx-dulcearte.conf" /etc/nginx/sites-available/dulcearte
sudo ln -sf /etc/nginx/sites-available/dulcearte /etc/nginx/sites-enabled/dulcearte
sudo nginx -t
sudo systemctl reload nginx

echo "======================================================================"
echo "✓ DESPLIEGUE COMPLETADO EXITOSAMENTE"
echo "Verifique el estado con: sudo systemctl status dulcearte"
echo "Para sembrar datos demo: python manage.py seed_demo"
echo "======================================================================"
