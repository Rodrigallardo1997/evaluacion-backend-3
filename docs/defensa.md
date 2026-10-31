# Guion y Estrategia de Defensa Oral — Dulce Arte

**Estudiante:** Rodrigo Alejandro Gallardo Martínez  
**Asignatura:** Desarrollo Backend | Evaluación Parcial N°3 (30%)  
**Proyecto:** Sistema de Trazabilidad y Pedidos para Pastelería Artesanal "Dulce Arte"

---

## 1. Mapeo Rúbrica — Evidencia del Proyecto

| Criterio Evaluado | Evidencia en el Código y Sistema | Cómo Demostrarlo en Vivo |
|---|---|---|
| **1. PostgreSQL y Migraciones** | `DATABASE_URL` con psycopg3 en `settings.py`, migraciones con constraints, índices y tipos Decimal. | Mostrar `\dt` en psql, constraints de stock no negativo, y persistencia tras reiniciar Gunicorn. |
| **2. Django Admin Personalizado** | `templates/admin/base_site.html`, `static/css/admin.css`, inlines de BOM, filtros personalizados y acciones masivas. | Entrar a `/admin/` con `admin`, `cocina` y `vendedor`, demostrando permisos acotados y diseño corporativo. |
| **3. CRUD y Reglas de Negocio** | 4 funcionalidades completas: cotizaciones, Kanban con bloqueo optimista, BOM/stock atómico y rutas con firma. | Ejecutar en vivo el ciclo completo: nuevo pedido → cotizar → confirmar (descuenta stock) → mover Kanban → ruta → firmar entrega. |
| **4. Seguridad, Sesiones e IA** | `RolePermission`, `RoleRequiredMixin`, cookies `HttpOnly`/`SameSite=Lax`, sin contraseñas en plano, `prompts_ia.md`. | Mostrar que `cocina` no puede ver pagos ni confirmar pedidos (403), y exhibir la bitácora de IA. |
| **5. Despliegue en AWS EC2** | Instancia EC2 con Elastic IP, Nginx como proxy inverso, Gunicorn systemd y PostgreSQL local. | Abrir la app desde el celular mediante la IP pública y reiniciar el servicio para probar la persistencia. |

---

## 2. Guion de Demostración en Vivo (8 a 10 Minutos)

### Minuto 0:00 - 1:30 | Introducción y Arquitectura General
- Saludar al docente y contextualizar el problema: *"Dulce Arte enfrentaba desajustes entre pedidos personalizados, tiempos de cocina y stock de materias primas perecibles"*.
- Mencionar la arquitectura en capas: Modelos → Servicios de Dominio (`services/`) → API REST / Vistas Web → Templates responsivos.
- Resaltar la restricción técnica: *"Cero SQLite, PostgreSQL 16 estricto tanto en desarrollo como en producción en AWS EC2 con Gunicorn y Nginx"*.

### Minuto 1:30 - 3:30 | Flujo 1: Registro de Pedido Personalizado y Cotización (RF1)
- Iniciar sesión como `vendedor` (`vendedor` / `Vendedor123!`).
- Crear un nuevo pedido personalizado: seleccionar cliente, fecha de entrega, dedicatoria de diseño y agregar productos con el wizard.
- Mostrar el cálculo dinámico de subtotales y descuento.
- Guardar en estado `BORRADOR` y pulsar **"Emitir Cotización"**.
- Mostrar la cotización formal con número correlativo único `COT-2024-NNNN` y abrir la vista imprimible (`@media print`).

### Minuto 3:30 - 5:30 | Flujo 2: Confirmación y Descuento Atómico de Stock con BOM (RF3)
- Demostrar el stock de un insumo clave (ej: *Harina Especial* o *Chocolate Belga*).
- Pulsar **"Confirmar Pedido (BOM)"**.
- Explicar la lógica técnica: *"Se ejecuta `transaction.atomic()` con `select_for_update()` ordenando insumos por ID para prevenir deadlocks. Se calcula la merma porcentual de cada receta y se verifica que no haya insumos vencidos ni sobreventa"*.
- Mostrar cómo el pedido pasa a `CONFIRMADO` y se generan los registros de auditoría en `MovimientoInventario` (tipo `SALIDA`).
- Registrar un anticipo de pago para ilustrar el recálculo en tiempo real del saldo pendiente.

### Minuto 5:30 - 7:30 | Flujo 3: Tablero Kanban Digital de Cocina (RF2)
- Iniciar sesión como `cocina` (`cocina` / `Cocina123!`).
- Abrir `/pedidos/kanban/` y mostrar las 5 columnas exactas: *Recibido*, *En Preparación*, *Horneado/Decorado*, *Control de Calidad*, *Listo*.
- Arrastrar la tarjeta con SortableJS.
- Explicar el control de concurrencia: *"El cliente envía la `version` actual. Si otro usuario modificó el registro en paralelo, el backend responde HTTP 409 Conflicto y la tarjeta revierte visualmente a su posición original"*.
- Mover el pedido sucesivamente hasta llegar a la columna **Listo para Despacho**.

### Minuto 7:30 - 9:00 | Flujo 4: Logística, Despacho y Firma Digital (RF4)
- Entrar como `repartidor` (`repartidor` / `Reparto123!`).
- Abrir la ruta asignada, mostrando el orden de paradas y el enlace directo a Google Maps.
- Entrar a la parada pendiente y pulsar **"Confirmar Entrega"**.
- Dibujar la firma digital en el canvas táctil con SignaturePad, registrar el nombre del receptor y capturar la ubicación GPS.
- Confirmar entrega: mostrar que el pedido y la parada pasan a `ENTREGADO`, guardando la imagen PNG de la firma en la base de datos y completando la ruta.

### Minuto 9:00 - 10:00 | Django Admin y Cierre (Criterio 2 y 5)
- Entrar a `/admin/` con el usuario `admin` (`admin` / `Admin123!`).
- Mostrar el template personalizado `base_site.html`, el CSS corporativo en tonos café/rosa y el footer institucional.
- Mostrar la auditoría inmutable de `MovimientoInventario` e `HistorialEstadoPedido`.
- Abrir la app desde el teléfono móvil mediante la IP pública de AWS EC2.

---

## 3. Banco de 20 Preguntas Probables y Respuestas Técnicas

### 1. ¿Por qué separaste la lógica de negocio en una capa `services/` en vez de usar las vistas o modelos?
> **Respuesta:** Para cumplir con el principio de responsabilidad única (SRP) y evitar el antipatrón de *Fat Models* o *Fat Views*. Las reglas de negocio complejas como el descuento de stock con Lista de Materiales o las transiciones de estado son consumidas tanto por la API REST como por las vistas tradicionales y el Django Admin. Centralizarlas en `services/` elimina duplicación de código y facilita las pruebas unitarias.

### 2. ¿Cómo garantizas que dos usuarios no sobrevenda el mismo insumo al mismo tiempo?
> **Respuesta:** Implementamos bloqueo pesimista en base de datos. Dentro de un bloque `transaction.atomic()`, usamos `select_for_update()` sobre los insumos involucrados. Además, ordenamos los IDs de los insumos ascendentemente antes de bloquearlos, lo que previene condiciones de carrera (*race conditions*) y bloqueos mutuos (*deadlocks*).

### 3. ¿Cómo funciona el bloqueo optimista implementado en el Tablero Kanban?
> **Respuesta:** El modelo `Pedido` incluye un campo `version` entero. Al consultar el tablero Kanban, cada tarjeta lleva su versión. Al mover una tarjeta, el frontend envía un `PATCH` con el nuevo estado y la versión. Si en la base de datos la versión ya cambió (porque otro pastelero la movió antes), el servicio detecta la discrepancia y retorna un código `409 Conflict`, forzando el rollback visual de la tarjeta en pantalla.

### 4. ¿Qué es la Lista de Materiales (BOM) y cómo se calcula el consumo con merma?
> **Respuesta:** La BOM (*Bill of Materials*) define la receta estándar a través de `RecetaInsumo`. Cada insumo tiene una cantidad base y un porcentaje de merma esperado por manipulación u horneado. La fórmula aplicada es: `cantidad_neta = cantidad * (1 + merma_porcentaje / 100)`. El consumo total de un pedido multiplica esta cantidad neta por la cantidad de pasteles solicitados.

### 5. ¿Qué ocurre con las materias primas si un pedido confirmado se cancela?
> **Respuesta:** La función `cancelar_pedido` verifica si `inventario_descontado` es verdadero. De ser así, consulta los movimientos históricos de tipo `SALIDA` asociados a ese pedido y crea movimientos de reversa de tipo `ENTRADA` con la cantidad exacta consumida, actualizando el stock atómicamente sin recalcular desde la receta, previniendo errores si la receta fue editada posteriormente.

### 6. ¿Por qué utilizas `Decimal` y no `float` para montos y stock?
> **Respuesta:** El tipo `float` en Python y en base de datos utiliza representación binaria de punto flotante bajo IEEE 754, lo que produce errores de redondeo acumulativos inadmisibles en contabilidad e inventario (por ejemplo `0.1 + 0.2 != 0.3`). `Decimal` maneja aritmética decimal exacta de precisión fija.

### 7. ¿Cómo configuraste las zonas horarias en Django y PostgreSQL?
> **Respuesta:** Configuramos `TIME_ZONE = "America/Santiago"` y `USE_TZ = True` en `settings.py`. En PostgreSQL establecimos `ALTER ROLE dulcearte_user SET timezone TO 'America/Santiago'`. Todas las comparaciones de fechas utilizan `timezone.now()` o `timezone.localdate()`, evitando objetos datetime *naive*.

### 8. ¿Por qué en PostgreSQL 15+ es necesario `GRANT ALL ON SCHEMA public`?
> **Respuesta:** Desde PostgreSQL 15 se revocaron los permisos públicos de creación en el esquema `public` por razones de seguridad. Si el usuario de la base de datos no es propietario del esquema o no tiene este permiso explícito, Django falla en la primera migración con `PermissionDenied: permission denied for schema public`.

### 9. ¿Qué rol cumple Nginx frente a Gunicorn en la instancia EC2?
> **Respuesta:** Nginx actúa como proxy inverso y servidor de contenido estático. Maneja la terminación de conexiones lentas, sirve directamente los archivos estáticos (`/static/`) y medios subidos (`/media/`) con compresión y caché de cabecera, liberando a Gunicorn para dedicarse exclusivamente al procesamiento dinámico de las peticiones WSGI en Python.

### 10. ¿Por qué no debes activar `SECURE_SSL_REDIRECT` si la instancia no tiene certificado HTTPS?
> **Respuesta:** Porque forzaría a todas las peticiones a redirigirse al puerto 443. Si la instancia solo está accesible por IP pública vía HTTP (puerto 80), el navegador quedará en un bucle infinito o mostrará error de conexión rechazada, imposibilitando el inicio de sesión.

### 11. ¿Cómo almacenas y validas la firma digital del cliente?
> **Respuesta:** Se captura en el navegador mediante un canvas HTML5 con `SignaturePad` y se exporta como Data URL en Base64 (`data:image/png;base64,...`). En el backend, el servicio valida la estructura del MIME-type, decodifica el Base64 y comprueba que el tamaño en bytes sea inferior a 2 MB antes de persistirlo.

### 12. ¿Cómo se protegen los datos de clientes respecto a los usuarios con rol CLIENTE?
> **Respuesta:** A nivel de vista y en DRF con `RolePermission`, filtramos los querysets con `get_queryset()`: si `request.user.es_cliente`, la consulta se restringe estrictamente a `cliente__usuario=request.user`. Un cliente nunca puede consultar pedidos de terceros ni acceder al Django Admin.

### 13. ¿Por qué la generación del código de pedido no utiliza `Pedido.objects.count() + 1`?
> **Respuesta:** Porque en entornos concurrentes, dos pedidos creados simultáneamente obtendrían el mismo conteo y violarían la restricción de unicidad (`IntegrityError`). Generamos el código a partir del `pk` auto-incremental de PostgreSQL (`DA-{año}-{pk:04d}`), garantizando unicidad absoluta sin riesgo de colisión.

### 14. ¿Qué ventaja ofrece `drf-spectacular` en la arquitectura API?
> **Respuesta:** Genera un esquema OpenAPI 3.0 dinámico y tipado a partir de los serializers y viewsets de DRF, exponiendo una interfaz interactiva de Swagger UI en `/api/docs/` que facilita la documentación y las pruebas de integración sin necesidad de herramientas externas.

### 15. ¿Cómo garantizas la idempotencia en el comando `seed_demo`?
> **Respuesta:** Usando `update_or_create()` y `get_or_create()` en lugar de `create()`, vinculando llaves naturales como el `username`, `rut`, `nombre` del insumo o `codigo` del pedido. El comando puede ejecutarse múltiples veces consecutivas sin duplicar registros ni romper claves foráneas.

### 16. ¿Qué hace `select_related` y `prefetch_related` en los endpoints de pedidos?
> **Respuesta:** Resuelven el problema de rendimiento N+1 consultas. `select_related` realiza un `SQL JOIN` para relaciones uno-a-uno o claves foráneas simples (`cliente`, `vendedor`), mientras que `prefetch_related` realiza consultas optimizadas por lotes para relaciones de uno-a-muchos (`detalles`, `cotizaciones`, `pagos`).

### 17. ¿Cómo gestionas la expiración y seguridad de las sesiones de usuario?
> **Respuesta:** En `settings.py` configuramos `SESSION_COOKIE_HTTPONLY = True` (evita acceso a la cookie por JavaScript previniendo ataques XSS), `SESSION_COOKIE_SAMESITE = 'Lax'` (mitiga CSRF) y `SESSION_COOKIE_AGE = 28800` (8 horas exactas de validez). El cierre de sesión se ejecuta exclusivamente vía método HTTP POST.

### 18. ¿Por qué `ATOMIC_REQUESTS = False` está configurado en settings?
> **Respuesta:** Envolver toda petición HTTP en una transacción atómica automática genera bloqueos innecesarios en peticiones de solo lectura y oculta el manejo fino de errores. Preferimos transacciones explícitas mediante `with transaction.atomic():` en la capa de servicios, donde se modifican datos críticos.

### 19. ¿Cómo se comporta el sistema si un insumo perecible ya venció?
> **Respuesta:** Al momento de cotizar se muestra una advertencia informativa; sin embargo, al momento de **confirmar el pedido** en `descontar_stock_pedido()`, si algún insumo requerido tiene `esta_vencido == True`, el servicio detiene la operación y lanza un `ValidationError` bloqueando la confirmación y evitando el consumo de materia prima en mal estado.

### 20. ¿Qué contingencia tienes prevista si falla la conectividad a AWS EC2 durante la defensa?
> **Respuesta:** El proyecto cuenta con un entorno local idéntico con PostgreSQL local, script de respaldo SQL generado mediante `pg_dump`, datos demo listos con `seed_demo` y capturas de pantalla de respaldo de cada uno de los 4 flujos y del Django Admin operando en vivo.

---

## 4. Plan de Contingencia Técnico ante Imprevistos

1. **Si la IP pública de EC2 no responde en el navegador:**
   - Verificar si la instancia se detuvo y cambió de IP (usar la Elastic IP asignada).
   - Conectar por SSH y ejecutar: `sudo systemctl restart dulcearte nginx`.
   - Revisar `sudo journalctl -u dulcearte -n 20`.
2. **Si hay corte de Internet en el aula:**
   - Levantar el proyecto en `localhost:8000` con PostgreSQL local en la máquina de presentación.
   - Todo el código es 100% autónomo y reproduce las mismas reglas y templates.
