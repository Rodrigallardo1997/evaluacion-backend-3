# Bitácora de Uso de Inteligencia Artificial — Dulce Arte

**Proyecto:** Sistema de Trazabilidad y Pedidos para Pastelería Artesanal "Dulce Arte"  
**Autor:** Rodrigo Alejandro Gallardo Martínez  
**Asignatura:** Desarrollo Backend | Evaluación Parcial N°3  
**Fecha:** Octubre 2024

---

## 1. Registro Cronológico de Prompts y Resultados

| # | Fecha | Herramienta / Modelo | Objetivo Técnico | Prompt Utilizado (Resumen fiel / Textual) | Resultado Obtenido | Ajustes Manuales Realizados | Archivos Afectados |
|---|---|---|---|---|---|---|---|
| **1** | 2024-10-26 | Antigravity / Claude 3.5 Sonnet | Arquitectura base y especificación de requerimientos del sistema | *Prompt Maestro EVA 3: Arquitecto senior Django, PostgreSQL estricto, 4 flujos de negocio (Cotización, Kanban, BOM, Rutas con firma), despliegue AWS EC2.* | Estructura modular en 6 apps, diseño de entidades y plan de construcción. | Selección de arquitectura en capas con `services/` y rechazo explícito de SQLite. | `config/settings.py`, `manage.py`, `requirements.txt` |
| **2** | 2024-10-26 | Antigravity / Claude 3.5 Sonnet | Modelo de datos relacional y tipos exactos | *"Diseñar modelos Django para Pedido, DetallePedido, Cotización, Insumo, Receta, RecetaInsumo con Decimal(12,2) y Decimal(10,3)."* | Código de modelos con constraints y choices. | Se ajustó `stock_actual <= stock_minimo` y cálculo fiel de anticipo cacheado. | `apps/pedidos/models.py`, `apps/catalogo/models.py` |
| **3** | 2024-10-26 | Antigravity / Gemini 1.5 Pro | Servicio atómico de Lista de Materiales (BOM) y descuento de stock | *"Generar servicio stock_service.py con cálculo de merma porcentual, select_for_update() ordenado por ID y rollback total ante faltantes."* | Función `descontar_stock_pedido` con validación de vencimientos y lista de faltantes. | Se garantizó la idempotencia estricta mediante el flag `inventario_descontado`. | `apps/inventario/services/stock_service.py` |
| **4** | 2024-10-26 | Antigravity / Gemini 1.5 Pro | Bloqueo optimista y transiciones del Tablero Kanban | *"Implementar transicionar_estado() en cotizacion_service.py con matriz estricta de 5 estados de cocina y bloqueo por versión (409 Conflict)."* | Lógica de validación de roles y detección de colisiones de versión concurrente. | Ajuste de códigos HTTP: 409 para versión desfasada y 400 para saltos ilegales de columna. | `apps/pedidos/services/cotizacion_service.py` |
| **5** | 2024-10-26 | Antigravity / Gemini 1.5 Pro | Generación de cotizaciones formales y snapshots de precios | *"Crear emitir_cotizacion() asegurando que invalide cotizaciones previas, genere código COT-AAAA-NNNN y pase el pedido a COTIZADO."* | Función completa con cálculo de validez de 7 días y registro en historial. | Se evitó el conteo simple con `count()+1` usando correlativo bloqueado con transacción. | `apps/pedidos/services/cotizacion_service.py` |
| **6** | 2024-10-26 | Antigravity / Gemini 1.5 Pro | Logística de despachos y validación de firma digital | *"Diseñar despacho_service.py para iniciar rutas en bloque y confirmar paradas con validación de Data URL Base64 < 2MB o fotografía."* | Validación de regex para Data URL PNG/JPEG y actualización a ENTREGADO con fecha real. | Se añadió soporte para geolocalización GPS opcional y cierre automático de ruta. | `apps/despachos/services/despacho_service.py` |
| **7** | 2024-10-26 | Antigravity / Gemini 1.5 Pro | Serializers y ViewSets de Django REST Framework | *"Crear endpoints DRF con RolePermission para /api/pedidos/, /api/insumos/, /api/rutas/ con select_related y paginación 20."* | API REST navegable completa con acciones personalizadas (`cotizar`, `confirmar`, `ajustar`). | Se integró `drf-spectacular` para publicar Swagger UI interactivo en `/api/docs/`. | `apps/*/serializers.py`, `apps/*/api_views.py`, `config/urls_api.py` |
| **8** | 2024-10-26 | Antigravity / Gemini 1.5 Pro | Personalización profesional del Django Admin | *"Personalizar admin.py de todas las apps con inlines editables de BOM, filtros por stock bajo, acciones CSV y branding corporativo."* | Archivos `admin.py` con `list_display`, filtros `SimpleListFilter` y permisos según rol de staff. | Creación de `templates/admin/base_site.html` y `static/css/admin.css` en paleta pastel. | `apps/*/admin.py`, `templates/admin/base_site.html`, `static/css/admin.css` |
| **9** | 2024-10-26 | Antigravity / Gemini 1.5 Pro | Tablero Kanban interactivo con SortableJS | *"Construir tablero Kanban HTML/JS con SortableJS en 5 columnas, drag & drop con llamada PATCH con version y rollback visual en 409."* | Script JavaScript modular que conecta con la API REST y maneja eventos de arrastre. | Añadido de auto-refresh cada 60 segundos y toasts Bootstrap de notificación. | `templates/kanban/tablero.html`, `static/js/kanban.js` |
| **10** | 2024-10-26 | Antigravity / Gemini 1.5 Pro | Formulario de entrega táctil con SignaturePad | *"Diseñar vista de entrega con canvas HTML5 SignaturePad, botón limpiar, preview de foto y envío multipart/form-data."* | Template con canvas responsivo y script de captura táctil en dispositivos móviles. | Ajuste del factor `devicePixelRatio` para evitar firmas pixeladas en pantallas Retina/celulares. | `templates/despachos/confirmar_entrega.html`, `static/js/firma.js` |
| **11** | 2024-10-26 | Antigravity / Gemini 1.5 Pro | Batería de pruebas automatizadas (TestCase) | *"Escribir suite de 15 pruebas unitarias cubriendo rollback de stock, bloqueo optimista, 403 por rol y cálculos de totales."* | Archivo `tests.py` con 16 pruebas exhaustivas usando `django.test.TestCase` y `APIClient`. | Verificación de precisión decimal exacta en cálculo de margen y costo unitario. | `apps/pedidos/tests.py` |
| **12** | 2024-10-26 | Antigravity / Gemini 1.5 Pro | Configuración de infraestructura y despliegue en AWS EC2 | *"Generar archivo systemd dulcearte.service, nginx-dulcearte.conf y script de despliegue deploy_ec2.sh idempotente para Ubuntu 24.04."* | Archivos de despliegue listos para producción con proxy inverso y socket TCP. | Corrección obligatoria de `GRANT ALL ON SCHEMA public` para PostgreSQL 15+. | `deploy/*`, `docs/despliegue.md` |

---

## 2. Decisiones Asistidas por IA y Validación Humana

### Decisiones Aceptadas
1. **Separación de la lógica en `services/`:** La IA sugirió desacoplar las reglas de stock y cotizaciones de los modelos de Django. Esto permitió reutilizar exactamente las mismas validaciones en la API REST, en las vistas web tradicionales y en el Django Admin sin duplicar código.
2. **Bloqueo pesimista con ordenamiento de IDs:** Se aceptó ordenar los insumos por ID (`order_by('id')`) antes de aplicar `select_for_update()`, una recomendación arquitectónica clave para prevenir interbloqueos (*deadlocks*) en transacciones concurrentes de cocina.
3. **Uso de `SignaturePad` nativo en JavaScript vanilla:** Se adoptó la solución sin librerías pesadas ni dependencias de React, permitiendo que la firma digital funcione fluidamente en cualquier teléfono inteligente directamente sobre los templates de Django.

### Decisiones Rechazadas o Modificadas
1. **Rechazo de SQLite en desarrollo:** Varias sugerencias iniciales de la IA proponían configurar SQLite para desarrollo y PostgreSQL para producción. Se rechazó categóricamente para cumplir la restricción académica: PostgreSQL 16 estricto en ambos entornos.
2. **Rechazo de eliminación en cascada en auditoría:** La IA proponía `CASCADE` en algunas claves foráneas. Se corrigió manualmente a `PROTECT` en Clientes, Recetas e Insumos para preservar intacta la trazabilidad histórica del negocio.
3. **Modificación de la validación de fecha en `Pedido.clean()`:** Inicialmente la IA colocó una validación que exigía que la fecha de entrega fuera estrictamente futura (mínimo 24 horas). Esto rompía el sembrado de datos demo para pedidos ya entregados en el pasado; se reubicó la validación al wizard de creación para no comprometer los datos históricos.

---

## 3. Prompts Reutilizables de Alta Eficacia

### Prompt A — Transacción Atómica con Bloqueo Concurrente
> *"Genera una función de servicio en Python/Django que descuente stock de múltiples filas en PostgreSQL de forma segura ante concurrencia. Debe abrir `transaction.atomic()`, bloquear las filas con `select_for_update()` ordenadas por `id`, validar disponibilidad de todas antes de alterar alguna, y lanzar `ValidationError` con los detalles si no hay suficiente saldo."*

### Prompt B — Endpoint Kanban con Bloqueo Optimista
> *"Diseña un endpoint REST con Django REST Framework que reciba un nuevo estado y una versión numérica. Debe consultar la entidad con `select_for_update()`, comparar la versión recibida con la existente y responder HTTP 409 si difieren, o incrementar la versión y guardar si coinciden."*

### Prompt C — Template Imprimible con CSS `@media print`
> *"Crea un template HTML para Django que renderice una cotización comercial profesional, con cabecera corporativa y desglose de subtotales. Incluye estilos CSS con `@media print` que oculten botones de navegación y aseguren formato de página limpia en tamaño carta/A4."*

---

## 4. Reflexión Ética, Riesgos y Aprendizajes

- **Riesgo de código superficial (*hallucinations*):** La IA tiende con frecuencia a colocar placeholders (`pass`, `// TODO`) o asumir configuraciones permisivas en seguridad (como `ALLOWED_HOSTS = ['*']` o ignorar CSRF). Fue indispensable la revisión humana línea por línea para asegurar consistencia estricta.
- **Aprendizaje:** La inteligencia artificial actúa como un multiplicador de productividad excepcional para acelerar la escritura de código repetitivo (*boilerplate* de serializers, formularios y templates), permitiendo al desarrollador concentrarse en la robustez arquitectónica, el diseño de transacciones atómicas y la experiencia de usuario.
