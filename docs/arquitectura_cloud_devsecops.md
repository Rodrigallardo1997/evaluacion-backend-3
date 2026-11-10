# ARQUITECTURA CLOUD EMPRESARIAL, DOCKER & DEVSECOPS
## Pastelería Artesanal "Dulce Arte"
**Asignatura:** Desarrollo Backend — Evaluación Parcial N°3  
**Autor:** Rodrigo Alejandro Gallardo Martínez  
**Institución:** Instituto Profesional INACAP  

---

## 1. Visión General de la Arquitectura (El Pizarrón del Docente)

El sistema ha evolucionado desde una arquitectura en una sola máquina virtual hacia una **Arquitectura en 3 Capas (Tier-3) Desacoplada y Altamente Disponible**, siguiendo los principios del *AWS Well-Architected Framework*.

```
+-----------------------------------------------------------------------------------+
|                            CAPA DE ACCESO Y SEGURIDAD                             |
|                                                                                   |
|  [ Usuario / Internet ] ---> [ Nginx Proxy / API Gateway ]                       |
|                                    | Rate Limiting: 15 req/s                      |
|                                    | Delay / Mitiga DoS & DDoS                    |
+------------------------------------+----------------------------------------------+
                                     |
                                     v
+-----------------------------------------------------------------------------------+
|                        CAPA DE CÓMPUTO & CONTENEDORES                             |
|                                                                                   |
|  [ Contenedor Docker: dulcearte_web ]                                             |
|  * Python 3.12-slim (Debian Bookworm)                                             |
|  * Usuario no-root de seguridad: appuser (UID 1001)                               |
|  * Django 5.0.9 + Gunicorn (3 workers, 60s timeout)                               |
|  * Healthcheck activo cada 30 segundos                                            |
+------------------------------------+----------------------------------------------+
                                     |
        +----------------------------+----------------------------+
        |                                                         |
        v                                                         v
+-----------------------------+               +-------------------------------------+
|   CAPA DE ALMACENAMIENTO    |               |          CAPA DE DATOS              |
|                             |               |                                     |
|  [ AWS S3 Bucket ]          |               |  [ AWS RDS PostgreSQL 16 ]          |
|  * /static/ (CSS, JS)       |               |  * Conexión cifrada: sslmode=require|
|  * /media/ (Fotos recetas,  |               |  * Multi-AZ / Alta Disponibilidad   |
|    firmas táctiles despachos|               |  * Respaldo transaccional atómico   |
+-----------------------------+               +------------------+------------------+
                                                                 |
                                                                 v
+-----------------------------------------------------------------------------------+
|                   CAPA SERVERLESS & AUTOMATIZACIÓN DE RESPALDOS                   |
|                                                                                   |
|  [ EventBridge (Cron Diario) ]                                                    |
|         |                                                                         |
|         v                                                                         |
|  [ AWS Lambda Function: lambda_backup_rds ]                                       |
|         |                                                                         |
|         +---> [ AWS S3: Respaldos Automáticos (.json / .sql.gz) ]                 |
|         |                                                                         |
|         +---> [ AWS SNS: Tópico de Alertas por Correo / SMS ]                     |
+-----------------------------------------------------------------------------------+
```

---

## 2. Contenerización y Orquestación (Docker & Compose)

### Archivos Implementados:
* **`Dockerfile`:**
  * Base minimalista: `python:3.12-slim-bookworm`.
  * Hardening de seguridad: usuario de sistema sin privilegios `appuser:appgroup`.
  * Verificación de estado: Directiva `HEALTHCHECK` consultando el endpoint local.
* **`deploy/entrypoint.sh`:**
  * Espera activa de conectividad con la base de datos (socket check).
  * Ejecución automática e idempotente de `migrate`, `collectstatic` y `seed_demo`.
* **`docker-compose.yml`:**
  * Orquesta `db` (PostgreSQL 16), `web` (Django) y `proxy` (Nginx).
* **`deploy/nginx-docker.conf`:**
  * **Rate Limiting:** `limit_req_zone $binary_remote_addr zone=api_rate_limit:10m rate=15r/s;`
  * **Delay de Mitigación DoS:** `burst=25 delay=10;`
  * **Límite de conexiones simultáneas:** `limit_conn conn_limit 15;`

---

## 3. Pipeline CI/CD con Prácticas DevSecOps (GitHub Actions)

Ubicación: `.github/workflows/ci-cd.yml`

El pipeline se activa automáticamente ante cada `push` o `pull_request` a la rama `main`:

### Etapas del Pipeline:
1. **DevSecOps SAST (Static Application Security Testing):**
   * **Bandit:** Analiza el árbol sintáctico (AST) del código fuente buscando inyecciones SQL, datos sensibles o brechas de seguridad.
2. **DevSecOps SCA (Software Composition Analysis):**
   * **pip-audit:** Contrasta las librerías instaladas contra la base mundial de vulnerabilidades conocidas (CVEs).
3. **Pruebas Automatizadas en Entorno Real:**
   * Levanta un contenedor de PostgreSQL 16 idéntico a producción y ejecuta los **16 tests unitarios de Django** (cobertura total de los requerimientos RF1 al RF4).
4. **Validación de Construcción de Contenedores:**
   * Compila la imagen Docker para verificar que no existen errores de dependencias.
5. **Continuous Deployment (CD) a AWS EC2:**
   * Conexión desatendida vía SSH seguro hacia la instancia `32.196.211.81`, sincronizando el código y recargando los servicios Gunicorn y Nginx sin tiempo de inactividad (*zero-downtime reload*).

---

## 4. Almacenamiento en AWS S3 para Archivos Multimedia

Ubicación: `config/storage_backends.py` y `config/settings.py`

* **Librerías:** `boto3` y `django-storages`.
* **Modo Dual:** El sistema opera de forma transparente:
  * Si `USE_S3=False`: Almacena en disco local con WhiteNoise (modo desarrollo y servidores autónomos).
  * Si `USE_S3=True`: Sube fotos de catálogo y firmas digitales de despacho al bucket `AWS S3`.

---

## 5. Base de Datos Administrada: AWS RDS PostgreSQL

Ubicación: `deploy/migrar_a_rds.sh`

* **Ventajas frente a BD en EC2:** Alta disponibilidad, respaldos automáticos gestionados por AWS, escalabilidad vertical inmediata y cifrado en tránsito (`sslmode=require`).
* **Procedimiento de migración:**
  1. Extracción de dump con `pg_dump --clean --no-owner`.
  2. Restauración directa en RDS con `psql -h <RDS_ENDPOINT>`.
  3. Actualización de la variable `DATABASE_URL` en `.env`.

---

## 6. Serverless: AWS Lambda, Respaldos y Alertas con AWS SNS

Ubicación: `deploy/lambda_backup_rds.py` y `apps/dashboard/services/alertas_sns.py`

* **AWS Lambda:**
  * Función activada mediante eventos programados de CloudWatch / EventBridge.
  * Dispara la creación de un snapshot o respaldo comprimido de la base de datos hacia S3.
  * Publica un evento de confirmación o alerta de fallo en el tópico **AWS SNS**.
* **AWS SNS en Django (`alertas_sns.py`):**
  * Emite alertas operacionales ante **Stock Crítico de Insumos** (ej. cuando la harina o el chocolate caen bajo el stock mínimo).
  * Emite alertas inmediatas a cocina cuando un pedido pasa a estado **CONFIRMADO**.
