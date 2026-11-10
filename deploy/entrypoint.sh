#!/bin/bash
# ==============================================================================
# ENTRYPOINT PARA CONTENEDOR DOCKER - DULCE ARTE
# Asignatura: Desarrollo Backend | DevSecOps & Containerization
# Autor: Rodrigo Alejandro Gallardo Martínez
# ==============================================================================
set -e

echo "=== [Dulce Arte Docker Entrypoint] Iniciando contenedor ==="

# Esperar a que la base de datos PostgreSQL esté disponible
echo "[1/4] Esperando disponibilidad de PostgreSQL..."
python << 'EOF'
import os
import socket
import sys
import time

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", 5432))
timeout = 60
start = time.time()

while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"[OK] Conexión establecida con PostgreSQL en {host}:{port}")
            sys.exit(0)
    except (socket.timeout, ConnectionRefusedError, OSError):
        if time.time() - start > timeout:
            print(f"[ERROR] Tiempo de espera agotado conectando a PostgreSQL ({host}:{port})")
            sys.exit(1)
        time.sleep(1)
EOF

# Aplicar migraciones pendientes
echo "[2/4] Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

# Recopilar archivos estáticos
echo "[3/4] Recopilando archivos estáticos (collectstatic)..."
python manage.py collectstatic --noinput

# Sembrar datos iniciales si no existen
echo "[4/4] Verificando datos demo..."
python manage.py seed_demo || true

echo "=== [Dulce Arte Docker Entrypoint] Preparación completada. Arrancando servicio ==="
exec "$@"
