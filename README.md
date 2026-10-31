# 🎂 Dulce Arte — Sistema de Trazabilidad y Pedidos para Pastelería Artesanal

[![Django](https://img.shields.io/badge/Django-5.0.9-092E20?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15.2-red)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04_LTS-E95420?logo=ubuntu)](https://ubuntu.com/)
[![AWS EC2](https://img.shields.io/badge/AWS-EC2_Monolito-FF9900?logo=amazonec2)](https://aws.amazon.com/ec2/)

**Evaluación Parcial N°3 (30% de la nota final)**  
**Asignatura:** Desarrollo Backend  
**Autor:** Rodrigo Alejandro Gallardo Martínez  
**Despliegue en Producción:** `http://TU_IP_PUBLICA/` (Reemplazar con la Elastic IP asignada en AWS EC2)  
**Documentación Swagger UI:** `http://TU_IP_PUBLICA/api/docs/`  
**Panel Django Admin:** `http://TU_IP_PUBLICA/admin/`

---

## 1. Descripción del Proyecto

**Dulce Arte** es una solución integral diseñada para resolver la desarticulación operativa entre la toma de pedidos personalizados, la disponibilidad en bodega de materias primas perecibles y los tiempos de cocina. El sistema ofrece trazabilidad completa de punta a punta: desde la cotización inicial, pasando por la Lista de Materiales (BOM) y el tablero Kanban de producción, hasta la entrega final en terreno con firma digital táctil.

### Las 4 Funcionalidades Clave

1. **Cotización y registro de pedidos personalizados:** Wizard en 3 pasos con cálculo en vivo de subtotales, descuentos, cotizaciones formales con número correlativo único y vista imprimible (`@media print`).
2. **Tablero Kanban digital de cocina:** 5 columnas exactas (*Recibido*, *En Preparación*, *Horneado/Decorado*, *Control de Calidad*, *Listo*) con drag & drop con SortableJS, control de concurrencia optimista (`version` -> HTTP 409) y auto-refresh.
3. **Descuento e inventario de insumos mediante Lista de Materiales (BOM):** Al confirmar un pedido se descuenta automáticamente la materia prima según receta y porcentaje de merma en una transacción atómica con `select_for_update()` para evitar sobreventa.
4. **Gestión de rutas de despacho y confirmación móvil:** Agrupación de pedidos listos en rutas, cálculo de itinerario con enlace directo a Google Maps y confirmación en terreno mediante canvas de firma digital (`signature_pad`) o comprobante fotográfico.

---

## 2. Diagrama Entidad-Relación (Mermaid)

```mermaid
erDiagram
    USUARIO ||--o{ PEDIDO : "vende"
    USUARIO ||--o{ RUTA_DESPACHO : "reparte"
    USUARIO |o--o| CLIENTE : "accede como"
    CLIENTE ||--o{ PEDIDO : "solicita"
    PEDIDO ||--|{ DETALLE_PEDIDO : "contiene"
    RECETA ||--o{ DETALLE_PEDIDO : "referenciada en"
    RECETA ||--|{ RECETA_INSUMO : "BOM"
    INSUMO ||--o{ RECETA_INSUMO : "utilizado en"
    PEDIDO ||--o{ COTIZACION : "emite"
    PEDIDO ||--o{ PAGO : "recibe"
    PEDIDO ||--o{ HISTORIAL_ESTADO : "audita"
    INSUMO ||--o{ MOVIMIENTO_INVENTARIO : "registra"
    PEDIDO ||--o{ MOVIMIENTO_INVENTARIO : "origina"
    RUTA_DESPACHO ||--|{ DESPACHO : "contiene paradas"
    PEDIDO ||--o{ DESPACHO : "entregado en"
```

---

## 3. Stack Tecnológico y Versiones

- **Lenguaje:** Python 3.12+
- **Framework Web:** Django 5.0.9
- **API REST:** Django REST Framework 3.15.2 + drf-spectacular 0.28.0 (OpenAPI 3.0)
- **Base de Datos:** PostgreSQL 16 (con `psycopg` 3.2.3 en desarrollo y producción; **prohibido SQLite**)
- **Servidor Web y WSGI:** Nginx + Gunicorn 23.0.0 (en instancia única AWS EC2)
- **Frontend:** Django Templates + Bootstrap 5.3 + SortableJS 1.15.2 + SignaturePad 4.1.7 + Chart.js 4.4.0

---

## 4. Usuarios Demo y Credenciales

El comando `python manage.py seed_demo` genera de forma idempotente las siguientes cuentas de prueba:

| Rol | Usuario | Contraseña | Nombre | Acceso Admin | Propósito de Demostración |
|---|---|---|---|---|---|
| **ADMIN** | `admin` | `Admin123!` | Rodrigo Gallardo | Total | Superusuario con acceso global a reportes, usuarios y configuración. |
| **VENDEDOR** | `vendedor` | `Vendedor123!` | Valentina Pérez | Limitado | Crea clientes, pedidos, emite cotizaciones y registra pagos. |
| **COCINA** | `cocina` | `Cocina123!` | Claudio Muñoz | Limitado | Opera el tablero Kanban de cocina y gestiona recetas (BOM). |
| **REPARTIDOR** | `repartidor` | `Reparto123!` | Carlos Soto | Limitado | Visualiza sus rutas asignadas, mapas y confirma entregas con firma. |
| **CLIENTE** | `cliente` | `Cliente123!` | Camila Silva | Sin acceso | Consulta el portal de clientes con el estado y evidencia de sus pedidos. |

*Nota: Para entornos públicos o de producción, cambie estas contraseñas inmediatamente.*

---

## 5. Instalación Local Paso a Paso

### Requisitos Previos
- Python 3.12 o superior instalado.
- Servidor PostgreSQL 16 en ejecución.
- Git.

### Procedimiento
1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/TU_USUARIO/dulcearte.git
   cd dulcearte
   ```

2. **Crear y activar el entorno virtual:**
   ```bash
   python -m venv venv
   # En Linux / macOS:
   source venv/bin/activate
   # En Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   ```

3. **Instalar dependencias:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Crear base de datos en PostgreSQL:**
   ```sql
   CREATE DATABASE dulcearte_db;
   CREATE USER dulcearte_user WITH PASSWORD 'password';
   ALTER ROLE dulcearte_user SET client_encoding TO 'utf8';
   ALTER ROLE dulcearte_user SET default_transaction_isolation TO 'read committed';
   ALTER ROLE dulcearte_user SET timezone TO 'America/Santiago';
   GRANT ALL PRIVILEGES ON DATABASE dulcearte_db TO dulcearte_user;
   \c dulcearte_db
   GRANT ALL ON SCHEMA public TO dulcearte_user;
   ```

5. **Configurar variables de entorno (`.env`):**
   ```bash
   cp .env.example .env
   ```
   Editar `.env` asegurando la conexión a PostgreSQL:
   ```env
   DEBUG=True
   SECRET_KEY=clave-secreta-para-desarrollo-local-1234567890
   ALLOWED_HOSTS=localhost,127.0.0.1
   CSRF_TRUSTED_ORIGINS=http://localhost:8000
   DATABASE_URL=postgres://dulcearte_user:password@localhost:5432/dulcearte_db
   ```

6. **Ejecutar migraciones y sembrar datos demo:**
   ```bash
   python manage.py migrate
   python manage.py seed_demo
   ```

7. **Iniciar servidor de desarrollo:**
   ```bash
   python manage.py runserver
   ```
   Ingresar a `http://127.0.0.1:8000/`.

---

## 6. Variables de Entorno

| Variable | Tipo | Descripción | Ejemplo Producción |
|---|---|---|---|
| `DEBUG` | Boolean | Activa/desactiva el modo de depuración. | `False` |
| `SECRET_KEY` | String | Clave criptográfica para firmas de sesión y CSRF. | `xK9#m$L2p@vQ8!zW5...` |
| `ALLOWED_HOSTS` | List | Dominios e IPs autorizadas para responder peticiones. | `54.210.123.45,localhost` |
| `CSRF_TRUSTED_ORIGINS` | List | Orígenes autorizados para peticiones POST/PATCH con CSRF. | `http://54.210.123.45` |
| `DATABASE_URL` | String | Cadena de conexión PostgreSQL parseada por django-environ. | `postgres://usr:pwd@localhost:5432/db` |

---

## 7. Los 4 Flujos Principales Explicados

### Flujo 1: Cotización y Registro de Pedido
1. El vendedor accede a `/pedidos/nuevo/` y completa el wizard en 3 pasos (cliente, recetas y diseño).
2. El sistema calcula en vivo el subtotal y descuento, guardando el pedido en estado `BORRADOR`.
3. El vendedor pulsa *"Emitir Cotización"*; el servicio genera la cotización con snapshot inmutable y número `COT-2024-NNNN`.
4. El pedido pasa a estado `COTIZADO` y se habilita la vista de impresión en limpio (`@media print`).

### Flujo 2: Confirmación y Descuento Atómico de Stock (BOM)
1. El vendedor pulsa *"Confirmar Pedido (BOM)"* tras acordar el anticipo con el cliente.
2. El servicio abre `transaction.atomic()` y bloquea con `select_for_update()` los insumos de la receta ordenados por ID.
3. Se verifica que haya stock suficiente para cada insumo (considerando porcentaje de merma) y que ninguno esté vencido.
4. Si todo es correcto, se descuenta el stock, se registran los movimientos de `SALIDA` y el pedido pasa a `CONFIRMADO` (ingresando al Kanban de cocina). Si falta stock, la operación revierte en su totalidad sin alterar la base de datos.

### Flujo 3: Tablero Kanban de Cocina
1. El equipo de cocina abre `/pedidos/kanban/` visualizando las 5 columnas: *Recibido*, *En Preparación*, *Horneado/Decorado*, *Calidad* y *Listo*.
2. El pastelero arrastra la tarjeta a la siguiente etapa utilizando SortableJS.
3. El frontend envía un `PATCH /api/pedidos/{id}/estado/` incluyendo la `version` actual para control de concurrencia optimista.
4. Si otro usuario movió la tarjeta en paralelo, la API responde `HTTP 409 Conflict` y la tarjeta vuelve automáticamente a su posición original con un toast de advertencia.

### Flujo 4: Rutas de Despacho y Entrega con Firma Digital
1. Desde `/despachos/rutas/nueva/`, el administrador agrupa pedidos en estado `LISTO` y asigna un repartidor y vehículo.
2. El repartidor inicia la ruta (`iniciar_ruta`), pasando todos los pedidos a estado `EN_DESPACHO` de forma masiva.
3. En terreno, el repartidor consulta su itinerario y abre el enlace directo a Google Maps para navegar hacia el destino.
4. Al entregar, abre `/despachos/paradas/{id}/confirmar/`, captura la firma digital en pantalla con `SignaturePad` (o foto de respaldo) y confirma: el pedido pasa a `ENTREGADO` y la ruta se completa automáticamente.

---

## 8. Pruebas Automatizadas

El proyecto incluye 16 pruebas automatizadas con `django.test.TestCase` que verifican de forma exhaustiva las reglas de negocio, rollback atómico, bloqueo de versiones y aislamiento por rol:

```bash
python manage.py test
```

Resultado esperado:
```text
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
................
----------------------------------------------------------------------
Ran 16 tests in 1.842s

OK
Destroying test database for alias 'default'...
```

---

## 9. Despliegue en AWS EC2 (Resumen)

El despliegue se ejecuta en una única instancia **AWS EC2 Ubuntu 24.04 LTS** (tipo `t3.micro` o `t3.small`) en AWS Academy, sin Docker ni RDS.

Consulte la guía completa en [docs/despliegue.md](docs/despliegue.md).

Pasos resumidos:
1. Crear instancia EC2 y Security Group (puertos 22 a tu IP, puerto 80 a 0.0.0.0/0).
2. Asociar Elastic IP para que la IP pública sea permanente.
3. Conectar vía SSH, clonar el proyecto y configurar PostgreSQL 16 con `GRANT ALL ON SCHEMA public`.
4. Ejecutar el script automatizado idempotente `deploy/deploy_ec2.sh`.
5. Verificar el servicio systemd (`sudo systemctl status dulcearte`) y Nginx (`sudo systemctl status nginx`).

---

## 10. Documentación Adicional

- [docs/arquitectura.md](docs/arquitectura.md): Paradigma 4+1 Vistas con diagramas Mermaid de procesos, concurrencia y despliegue físico.
- [docs/despliegue.md](docs/despliegue.md): Manual paso a paso de aprovisionamiento en AWS EC2 y troubleshooting.
- [docs/defensa.md](docs/defensa.md): Guion de demostración en vivo (8-10 min) y banco de 20 preguntas y respuestas técnicas.
- [prompts_ia.md](prompts_ia.md): Bitácora real de prompts y evidencia de uso de Inteligencia Artificial (Criterio 4).
