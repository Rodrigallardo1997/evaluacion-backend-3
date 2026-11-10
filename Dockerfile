# ==============================================================================
# DOCKERFILE - DULCE ARTE (PASTELERÍA ARTESANAL)
# Arquitectura Contenerizada & DevSecOps
# Autor: Rodrigo Alejandro Gallardo Martínez
# ==============================================================================

# Imagen base oficial y ligera basada en Debian Bookworm
FROM python:3.12-slim-bookworm

# Variables de entorno de Python y Django
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema operativo y herramientas necesarias
# (curl para healthcheck, libpq5 para conexión nativa con PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario y grupo de sistema sin privilegios de root (Buenas prácticas DevSecOps)
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup --no-create-home appuser

# Copiar archivo de requerimientos e instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente completo del proyecto
COPY . /app/

# Crear directorios para estáticos y multimedia, y asignar permisos al usuario no root
RUN mkdir -p /app/staticfiles /app/media && \
    chmod +x /app/deploy/entrypoint.sh && \
    chown -R appuser:appgroup /app

# Cambiar al usuario no privilegiado para ejecución segura
USER appuser

# Exponer el puerto del servidor WSGI Gunicorn
EXPOSE 8000

# Healthcheck para verificar el estado de salud del contenedor
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/ || exit 1

# Entrypoint y comando por defecto para arrancar Gunicorn
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
