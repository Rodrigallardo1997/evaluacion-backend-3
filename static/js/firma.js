/**
 * firma.js — Dulce Arte
 * Captura de firma digital con signature_pad + GPS opcional
 *
 * Dependencia (cargar en el template):
 * <script src="https://cdn.jsdelivr.net/npm/signature_pad@4.2.0/dist/signature_pad.umd.min.js"></script>
 *
 * El template debe contener:
 *   - <canvas id="firmaCanvas"></canvas>
 *   - <button id="btnLimpiarFirma">Limpiar</button>
 *   - <button id="btnGuardarFirma">Guardar firma</button>
 *   - <input type="hidden" id="firmaDataInput" name="firma_data">
 *   - <input type="hidden" id="firmaLatInput" name="firma_lat">
 *   - <input type="hidden" id="firmaLngInput" name="firma_lng">
 *   - <img id="firmaPreview" style="display:none" alt="Vista previa firma">
 *   - <div id="firmaEstado"></div>    (feedback de estado)
 */

'use strict';

// ─── Configuración ────────────────────────────────────────────────────────────
const FIRMA_CONFIG = {
    maxSizeBytes:   2 * 1024 * 1024,   // 2 MB máximo para la imagen en base64
    canvasMinWidth: 400,
    penColor:       '#1a1a1a',
    penWidth:       2,
    gpsTimeout:     8000,              // ms de espera por GPS
    urlSubirFirma:  null,              // si es null, no hace fetch automático (usa formulario)
};

// ─── Variables de módulo ──────────────────────────────────────────────────────
let signaturePad = null;
let coordenadasGPS = { lat: null, lng: null };

// ─── Utilidades ───────────────────────────────────────────────────────────────

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach((cookie) => {
            const c = cookie.trim();
            if (c.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(c.slice(name.length + 1));
            }
        });
    }
    return cookieValue;
}

function mostrarEstado(mensaje, tipo = 'info') {
    const el = document.getElementById('firmaEstado');
    if (!el) return;
    el.innerHTML = `<div class="alert alert-${tipo} py-2 mt-2 mb-0">${mensaje}</div>`;
}

function limpiarEstado() {
    const el = document.getElementById('firmaEstado');
    if (el) el.innerHTML = '';
}

/**
 * Hace el canvas responsivo al ancho del contenedor padre.
 */
function ajustarCanvas(canvas) {
    const ratio = Math.max(window.devicePixelRatio || 1, 1);
    const parent = canvas.parentElement;
    const width  = Math.max(parent.offsetWidth || FIRMA_CONFIG.canvasMinWidth, FIRMA_CONFIG.canvasMinWidth);
    canvas.width  = width * ratio;
    canvas.height = 200 * ratio;
    canvas.style.width  = width + 'px';
    canvas.style.height = '200px';
    canvas.getContext('2d').scale(ratio, ratio);
    if (signaturePad) signaturePad.clear();
}

// ─── GPS opcional ─────────────────────────────────────────────────────────────

function obtenerGPS() {
    if (!('geolocation' in navigator)) {
        console.info('[Firma] Geolocalización no disponible en este dispositivo.');
        return;
    }
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            coordenadasGPS.lat = pos.coords.latitude.toFixed(6);
            coordenadasGPS.lng = pos.coords.longitude.toFixed(6);

            const latInput = document.getElementById('firmaLatInput');
            const lngInput = document.getElementById('firmaLngInput');
            if (latInput) latInput.value = coordenadasGPS.lat;
            if (lngInput) lngInput.value = coordenadasGPS.lng;

            console.info('[Firma] GPS obtenido:', coordenadasGPS);
        },
        (err) => {
            console.warn('[Firma] No se pudo obtener GPS:', err.message);
        },
        { timeout: FIRMA_CONFIG.gpsTimeout, enableHighAccuracy: true }
    );
}

// ─── Exportar y validar firma ─────────────────────────────────────────────────

/**
 * Exporta la firma como PNG base64, valida tamaño y la coloca en el input oculto.
 * @returns {string|null} dataURL o null si hay error
 */
function exportarFirma() {
    if (!signaturePad || signaturePad.isEmpty()) {
        mostrarEstado('<i class="bi bi-exclamation-triangle me-1"></i>Por favor dibuja tu firma antes de guardar.', 'warning');
        return null;
    }

    const dataURL = signaturePad.toDataURL('image/png');

    // Validar tamaño (~= base64 a bytes)
    const base64Data  = dataURL.split(',')[1] || '';
    const sizeBytes   = Math.ceil((base64Data.length * 3) / 4);

    if (sizeBytes > FIRMA_CONFIG.maxSizeBytes) {
        mostrarEstado(
            `<i class="bi bi-x-circle me-1"></i>La firma es demasiado grande (${(sizeBytes / 1024).toFixed(0)} KB). Límite: 2 MB.`,
            'danger'
        );
        return null;
    }

    return dataURL;
}

/**
 * Muestra una previsualización de la firma capturada.
 * @param {string} dataURL
 */
function mostrarPreview(dataURL) {
    const preview = document.getElementById('firmaPreview');
    if (preview) {
        preview.src = dataURL;
        preview.style.display = 'block';
        preview.style.maxWidth = '100%';
        preview.style.border   = '1px solid #dee2e6';
        preview.style.borderRadius = '0.5rem';
    }
}

// ─── Subir firma vía fetch (opcional) ────────────────────────────────────────

/**
 * Envía la firma al servidor vía fetch PATCH/POST.
 * Solo se llama si FIRMA_CONFIG.urlSubirFirma está configurada.
 * @param {string} dataURL
 * @param {string} pedidoId
 */
async function subirFirma(dataURL, pedidoId) {
    if (!FIRMA_CONFIG.urlSubirFirma) return;

    mostrarEstado('<i class="bi bi-cloud-upload me-1"></i>Subiendo firma…', 'info');

    try {
        const response = await fetch(FIRMA_CONFIG.urlSubirFirma.replace('{id}', pedidoId), {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                firma_data: dataURL,
                firma_lat:  coordenadasGPS.lat,
                firma_lng:  coordenadasGPS.lng,
            }),
        });

        if (response.ok) {
            mostrarEstado('<i class="bi bi-check-circle me-1"></i>Firma guardada correctamente.', 'success');
        } else {
            const err = await response.json().catch(() => ({}));
            mostrarEstado(
                `<i class="bi bi-x-circle me-1"></i>Error al guardar: ${err.detail || response.statusText}`,
                'danger'
            );
        }
    } catch (err) {
        console.error('[Firma] Error de red:', err);
        mostrarEstado('<i class="bi bi-wifi-off me-1"></i>Error de conexión. Intenta nuevamente.', 'danger');
    }
}

// ─── Bootstrap del módulo ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
    const canvas = document.getElementById('firmaCanvas');
    if (!canvas) return; // No hay canvas en esta página

    if (typeof SignaturePad === 'undefined') {
        console.error('[Firma] SignaturePad no está disponible. Carga el CDN antes de este script.');
        mostrarEstado('Error: librería de firma no cargada.', 'danger');
        return;
    }

    // Inicializar SignaturePad
    signaturePad = new SignaturePad(canvas, {
        penColor:     FIRMA_CONFIG.penColor,
        minWidth:     1,
        maxWidth:     FIRMA_CONFIG.penWidth,
        throttle:     16,
    });

    // Hacer canvas responsivo
    ajustarCanvas(canvas);
    window.addEventListener('resize', () => ajustarCanvas(canvas));

    // Intentar obtener GPS al iniciar
    obtenerGPS();

    // ── Botón limpiar ──
    const btnLimpiar = document.getElementById('btnLimpiarFirma');
    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', () => {
            signaturePad.clear();
            limpiarEstado();
            const preview = document.getElementById('firmaPreview');
            if (preview) preview.style.display = 'none';
            const dataInput = document.getElementById('firmaDataInput');
            if (dataInput) dataInput.value = '';
        });
    }

    // ── Botón guardar ──
    const btnGuardar = document.getElementById('btnGuardarFirma');
    if (btnGuardar) {
        btnGuardar.addEventListener('click', async () => {
            limpiarEstado();
            const dataURL = exportarFirma();
            if (!dataURL) return;

            // Guardar en input oculto para envío por formulario
            const dataInput = document.getElementById('firmaDataInput');
            if (dataInput) dataInput.value = dataURL;

            mostrarPreview(dataURL);

            // Si hay URL de API configurada, subir automáticamente
            const pedidoId = btnGuardar.getAttribute('data-pedido-id');
            if (FIRMA_CONFIG.urlSubirFirma && pedidoId) {
                await subirFirma(dataURL, pedidoId);
            } else {
                mostrarEstado('<i class="bi bi-check-circle me-1"></i>Firma lista. Envía el formulario para confirmar.', 'success');
            }
        });
    }

    console.info('[Firma] SignaturePad inicializado correctamente.');
});
