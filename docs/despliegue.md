# Guía de Despliegue en AWS EC2 — Dulce Arte

Esta guía documenta el procedimiento paso a paso para desplegar la aplicación **Dulce Arte** en una única instancia **AWS EC2** (Ubuntu Server 24.04 LTS) con **PostgreSQL 16**, **Gunicorn** y **Nginx**.

---

## 1. Configuración de Instancia y Red en AWS

1. **Crear Instancia:**
   - AMI: Ubuntu Server 24.04 LTS (HVM), SSD Volume Type.
   - Tipo de Instancia: `t3.micro` o `t3.small` (apta para AWS Academy).
   - Disco: 20 GB gp3.
2. **Security Group (Reglas de Entrada):**
   - **SSH (22):** Origen *My IP* (únicamente tu dirección IP de administración).
   - **HTTP (80):** Origen `0.0.0.0/0` (acceso web público).
   - **HTTPS (443):** Opcional (solo con dominio y Let's Encrypt).
   - ⚠️ **PROHIBIDO:** Abrir puertos `5432` (PostgreSQL) o `8000` (Gunicorn) a Internet.
3. **Asignar Elastic IP (IP Elástica):**
   - Asociar una IP elástica a la instancia para que la IP pública permanezca fija tras reinicios.
   - Reemplazar en adelante `TU_IP_PUBLICA` con la IP asignada (ejemplo: `54.210.123.45`).

---

## 2. Instalación de Paquetes Base en el Servidor

Conectarse por SSH a la instancia:

```bash
ssh -i "tu-llave.pem" ubuntu@TU_IP_PUBLICA
```

Ejecutar la actualización del sistema e instalar paquetes esenciales:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip postgresql postgresql-contrib nginx git curl libpq-dev
sudo systemctl enable --now postgresql nginx
```

---

## 3. Configuración de PostgreSQL 16

Acceder a la consola de administración de PostgreSQL:

```bash
sudo -u postgres psql
```

Ejecutar las siguientes sentencias SQL (reemplazar `CAMBIA_ESTA_CLAVE` por una contraseña segura):

```sql
CREATE DATABASE dulcearte_db;
CREATE USER dulcearte_user WITH PASSWORD 'CAMBIA_ESTA_CLAVE';
ALTER ROLE dulcearte_user SET client_encoding TO 'utf8';
ALTER ROLE dulcearte_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE dulcearte_user SET timezone TO 'America/Santiago';
GRANT ALL PRIVILEGES ON DATABASE dulcearte_db TO dulcearte_user;
\c dulcearte_db
GRANT ALL ON SCHEMA public TO dulcearte_user;
\q
```

> **IMPORTANTE:** En PostgreSQL 15+, la sentencia `GRANT ALL ON SCHEMA public TO dulcearte_user;` es obligatoria; de lo contrario las migraciones fallan con `permission denied for schema public`.

---

## 4. Clonación del Proyecto y Entorno Virtual

```bash
cd /home/ubuntu
git clone https://github.com/TU_USUARIO/dulcearte.git
cd dulcearte
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Configuración de Variables de Entorno (`.env`)

Copiar la plantilla y configurar los parámetros reales:

```bash
cp .env.example .env
nano .env
```

Contenido de `.env` para producción en AWS EC2:

```env
DEBUG=False
SECRET_KEY=clave-muy-larga-y-aleatoria-generada-para-produccion-1234567890
ALLOWED_HOSTS=TU_IP_PUBLICA,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://TU_IP_PUBLICA
DATABASE_URL=postgres://dulcearte_user:CAMBIA_ESTA_CLAVE@localhost:5432/dulcearte_db
```

---

## 6. Migraciones, Estáticos y Datos Demo

Con el entorno virtual activo:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_demo
python manage.py check --deploy
```

Asegurar permisos para Nginx sobre las carpetas de estáticos y medios:

```bash
sudo chown -R ubuntu:www-data /home/ubuntu/dulcearte/media
sudo chmod -R 775 /home/ubuntu/dulcearte/media
sudo chown -R ubuntu:www-data /home/ubuntu/dulcearte/staticfiles
sudo chmod -R 755 /home/ubuntu/dulcearte/staticfiles
```

---

## 7. Configuración de Gunicorn como Servicio del Sistema

Copiar la definición del servicio:

```bash
sudo cp deploy/dulcearte.service /etc/systemd/system/dulcearte.service
sudo systemctl daemon-reload
sudo systemctl enable --now dulcearte
sudo systemctl status dulcearte
```

---

## 8. Configuración de Nginx como Proxy Inverso

Editar el archivo de Nginx reemplazando `TU_IP_PUBLICA`:

```bash
sed -i 's/TU_IP_PUBLICA/54.210.123.45/g' deploy/nginx-dulcearte.conf
sudo cp deploy/nginx-dulcearte.conf /etc/nginx/sites-available/dulcearte
sudo ln -sf /etc/nginx/sites-available/dulcearte /etc/nginx/sites-enabled/dulcearte
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

## 9. Verificación de Funcionamiento

1. Abrir en el navegador: `http://TU_IP_PUBLICA/`
2. Iniciar sesión con el usuario `admin` / `Admin123!`.
3. Navegar por los módulos: Dashboard, Clientes, Insumos, Recetas, Pedidos, Kanban y Rutas.
4. Ingresar al Django Admin en `http://TU_IP_PUBLICA/admin/` y verificar el branding institucional.
5. Probar el reinicio de la instancia en la consola AWS y verificar que PostgreSQL, Gunicorn y Nginx inicien automáticamente sin intervención manual.

---

## 10. Solución de Problemas Frecuentes (Troubleshooting)

- **Error 502 Bad Gateway:** Gunicorn no está corriendo o falló al iniciar.
  - Revisar logs: `sudo journalctl -u dulcearte -n 50 --no-pager`
  - Revisar archivo `.env` por errores sintácticos.
- **CSRF verification failed:** La IP pública no está en `CSRF_TRUSTED_ORIGINS`.
  - Asegurar en `.env`: `CSRF_TRUSTED_ORIGINS=http://TU_IP_PUBLICA`
- **Error DisallowedHost:** La IP pública no está en `ALLOWED_HOSTS`.
  - Asegurar en `.env`: `ALLOWED_HOSTS=TU_IP_PUBLICA,localhost,127.0.0.1`
- **Error de permisos en PostgreSQL:** `permission denied for schema public`.
  - Conectar a psql y ejecutar: `GRANT ALL ON SCHEMA public TO dulcearte_user;`
