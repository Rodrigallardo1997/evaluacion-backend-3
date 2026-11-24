# REGISTRO DE DECISIONES TÉCNICAS Y MEJORAS DE SEGURIDAD (ADR)
## Proyecto: Pastelería Artesanal "Dulce Arte" — Evaluación N.º 4
**Estudiante / Autor:** Rodrigo Alejandro Gallardo Martínez  
**Metodología:** Revisión de Código Senior + Verificación Basada en Evidencia (DevSecOps)  
**Fecha:** 24 de Noviembre de 2026  

---

## 1. Propósito del Documento

Este documento registra y justifica técnicamente las **9 mejoras de seguridad, arquitectura y calidad** aplicadas tras ejecutar una auditoría formal de código (`Bandit SAST`, `Flake8`, `Django check --deploy` y revisión arquitectónica manual) sobre el proyecto. Cada decisión se respalda con estándares de la industria (**OWASP Top 10**, **Documentación Oficial de Django 5**, **DRF** y **AWS Well-Architected Framework**).

---

## 2. Detalle y Argumentación de los 9 Cambios Realizados

### Cambio 1: Eliminación de Vulnerabilidad SSRF en el Puente Lambda (`apps/dashboard/api_views.py`)
* **Qué había antes:** `MensajeriaLambdaSNSAPIView` tenía `permission_classes = [AllowAny]` y aceptaba el parámetro `lambda_url` directamente desde el cuerpo de la petición del cliente (`request.data`).
* **Por qué se cambió (Riesgo OWASP A10:2021 – SSRF):** Permitir que un cliente externo defina la URL destino que el servidor backend consultará con `urllib.request.urlopen()` expone la instancia EC2 a ataques **Server-Side Request Forgery (SSRF)** y permite que terceros no autenticados envíen spam masivo al tópico SNS.
* **Solución implementada:** Se exigió autenticación (`permission_classes = [IsAuthenticated]`), se eliminó la lectura de `lambda_url` desde el cliente y se lee exclusivamente desde la variable de entorno controlada por el servidor (`settings.AWS_LAMBDA_SNS_URL`). Además, se evita exponer `str(exc)` al cliente registrando el error en los logs internos del servidor.

---

### Cambio 2: Mitigación de XSS Almacenado en el Frontend (`frontend/app.js`)
* **Qué había antes:** Los datos provenientes de la API (`r.nombre`, `r.descripcion`, `p.codigo`, `p.cliente_nombre`, `USER_INFO.username`) se insertaban directamente dentro de plantillas `.innerHTML`.
* **Por qué se cambió (Riesgo OWASP A03:2021 – Injection / Cross-Site Scripting):** Si un usuario malicioso lograra almacenar una etiqueta `<script>` o `<img onerror=...>` en un campo de texto, el navegador la ejecutaría al renderizar el catálogo o los pedidos, permitiendo el robo del **token JWT** guardado en `localStorage`.
* **Solución implementada:** Se creó la función sanitizadora `escapeHtml()` (que escapa `&`, `<`, `>`, `"` y `'`) y se aplicó sistemáticamente a todas las variables dinámicas renderizadas en el DOM. Además, `cerrarSesion()` ahora invoca `POST /api/auth/logout/` en el servidor antes de limpiar los tokens locales.

---

### Cambio 3: Restricción Explícita de Orígenes CORS (`config/settings.py`)
* **Qué había antes:** `CORS_ALLOW_ALL_ORIGINS = True` combinado con `CORS_ALLOW_CREDENTIALS = True`.
* **Por qué se cambió (OWASP / DAST):** Permitir todos los orígenes (`*`) junto con credenciales habilitadas debilita la Política del Mismo Origen (*Same-Origin Policy*) del navegador y suele ser reportado como hallazgo crítico en escaneos dinámicos (OWASP ZAP).
* **Solución implementada:** Se cambió el valor por defecto a `CORS_ALLOW_ALL_ORIGINS = False` y se declaró una lista blanca explícita `CORS_ALLOWED_ORIGINS` que autoriza únicamente el bucket S3 del Frontend, la IP pública EC2, el dominio DuckDNS y los entornos locales de desarrollo.

---

### Cambio 4: Reemplazo de Rate Limit Simulado por `ScopedRateThrottle` Real (`apps/catalogo/api_views.py` y `config/settings.py`)
* **Qué había antes:** `CatalogoPublicoAPIView` devolvía `HTTP 429` manualmente cuando recibía el parámetro de consulta `?burst=10`.
* **Por qué se cambió (Defensa Real contra DoS/DDoS):** Un control que depende de un parámetro voluntario del cliente no protege contra ataques reales, pues un atacante simplemente omitiría `?burst=`.
* **Solución implementada:** Se eliminó la condición artificial y se activó el mecanismo nativo **`ScopedRateThrottle`** de Django REST Framework (`throttle_scope = "catalogo_publico"`, tasa `15/minute` por IP) que trabaja en doble capa junto al **Throttling de Amazon API Gateway** (`5 req/s`, ráfaga `10`).

---

### Cambio 5: Declaración Explícita de `PASSWORD_HASHERS` y Migración a `STORAGES` de Django 5 (`config/settings.py` y `config/storage_backends.py`)
* **Qué había antes:** El hashing dependía del valor implícito de Django; el almacenamiento S3 usaba `DEFAULT_FILE_STORAGE` / `STATICFILES_STORAGE` (deprecados en Django 5) y `default_acl = 'public-read'`.
* **Por qué se cambió:**
  1. Declarar explícitamente `PASSWORD_HASHERS` (`PBKDF2PasswordHasher` con 720.000 iteraciones y salt aleatorio) hace auditable y verificable la política criptográfica exigida en la Actividad 3.
  2. Desde abril de 2023, Amazon S3 crea los buckets con `BucketOwnerEnforced` (ACLs deshabilitadas por defecto), por lo que enviar `ACL: public-read` provoca errores `AccessControlListNotSupported` y además expondría firmas digitales o comprobantes de pago.
* **Solución implementada:** Se migró al diccionario moderno `STORAGES` de Django 5, se eliminó `public-read` (`default_acl = None`), y `MediaStorage` utiliza `querystring_auth = True` (URLs prefirmadas temporales de S3) para proteger archivos privados.

---

### Cambio 6: Política *Fail-Closed* en Control de Acceso RBAC (`apps/usuarios/permissions.py`)
* **Qué había antes:** En `RolePermission.has_permission()`, si una acción de un ViewSet no figuraba en `role_action_map`, el código ejecutaba `if not allowed_roles: return True` (*Fail-Open*).
* **Por qué se cambió (Principio de Mínimo Privilegio — OWASP A01:2021 Broken Access Control):** En seguridad, toda acción no autorizada explícitamente debe ser denegada por defecto (*Fail-Closed*) para evitar fugas de permisos al agregar nuevos endpoints en el futuro.
* **Solución implementada:** Se modificó a `if not allowed_roles: return False`.

---

### Cambio 7: Corrección de Configuración SonarQube (`sonar-project.properties`)
* **Qué había antes:** `sonar.language=py` y solapamiento entre `sonar.sources=apps,config,frontend` y `sonar.tests=apps/pedidos`.
* **Por qué se cambió:** La propiedad `sonar.language` fue eliminada en SonarQube 7.7+ (impedía el análisis multi-lenguaje de Python + JavaScript en `frontend/`), y declarar un archivo simultáneamente en `sources` y `tests` provoca error de indexación duplicada en SonarScanner.
* **Solución implementada:** Se eliminó `sonar.language=py` y se excluyó `apps/pedidos/tests.py` en `sonar.exclusions` para permitir un análisis limpio de Python y JS.

---

### Cambio 8: Hardening de Nginx contra Fuga de Versión (`deploy/nginx_dulcearte.conf`)
* **Qué había antes:** Nginx respondía `Server: nginx/1.24.0 (Ubuntu)` y la ruta `/frontend/` no inyectaba cabeceras de seguridad HTTP.
* **Por qué se cambió (Hallazgo DAST OWASP ZAP `[10036]`):** Exponer el número exacto de versión del servidor web y del sistema operativo facilita a atacantes buscar CVEs específicos para esa versión.
* **Solución implementada:** Se añadió `server_tokens off;` (ocultando la versión exacta y respondiendo únicamente `Server: nginx`) junto con las cabeceras `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` y `Referrer-Policy: same-origin` en todas las rutas, incluyendo `/frontend/`.

---

### Cambio 9: Higiene de Código, Expiración JWT y Compatibilidad Python 3.12 (`config/settings.py`, `deploy/lambda_backup_rds.py`)
* **Qué había antes:** Importación `from datetime import timedelta` a mitad de `settings.py` (warning E402 de `flake8`), `ACCESS_TOKEN_LIFETIME` de 4 horas sin rotación, `BasicAuthentication` innecesario, imports sin usar y uso del método obsoleto `datetime.utcnow()`.
* **Por qué se cambió:** Reducir la ventana de exposición de un JWT comprometido (60 min con `ROTATE_REFRESH_TOKENS = True`), eliminar autenticación básica heredada, limpiar el código para análisis estático (`flake8`/SonarQube) y usar `datetime.now(datetime.timezone.utc)` compatible con Python 3.12+.

---

### Nota Deliberada sobre Accesos Rápidos Demo (`frontend/index.html`)
* Por decisión académica consensuada para agilizar la demostración oral cronometrada de 5 minutos (cambio de rol entre Admin, Vendedor, Cocina, Repartidor y Cliente en 1 clic), se mantuvieron temporalmente los botones de acceso rápido en la interfaz de demostración. En un paso a producción comercial real, dichos accesos deben eliminarse del cliente HTML.
