/**
 * kanban.js — Dulce Arte
 * Drag & drop Kanban con SortableJS + auto-refresh opcional
 * Dependencia: SortableJS (cargar vía CDN en el template que use este script)
 * <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.3/Sortable.min.js"></script>
 */

'use strict';

// ─── Configuración ────────────────────────────────────────────────────────────
const KANBAN_CONFIG = {
    autoRefreshInterval: 60000, // ms (0 = desactivado)
    apiBase: '/api/pedidos/',
    estadoAttr: 'data-estado',
    pedidoIdAttr: 'data-pedido-id',
    versionAttr: 'data-version',
};

// ─── Utilidades ───────────────────────────────────────────────────────────────

/**
 * Obtiene el valor de una cookie por nombre (necesario para CSRF).
 * @param {string} name
 * @returns {string|null}
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Muestra un toast de Bootstrap con el mensaje y estilo indicados.
 * @param {string} mensaje
 * @param {'success'|'danger'|'warning'|'info'} tipo
 */
function mostrarToast(mensaje, tipo = 'info') {
    const toastEl = document.getElementById('toastPrincipal');
    const toastMsg = document.getElementById('toastMensaje');
    if (!toastEl || !toastMsg) return;

    // Limpiar clases de color anteriores
    toastEl.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-warning', 'text-bg-info');
    toastEl.classList.add(`text-bg-${tipo}`);
    toastMsg.textContent = mensaje;

    const toast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 4000 });
    toast.show();
}

/**
 * Envía PATCH a /api/pedidos/{id}/estado/ con el nuevo estado y version.
 * @param {string|number} pedidoId
 * @param {string} nuevoEstado
 * @param {string|number} version
 * @returns {Promise<Response>}
 */
async function actualizarEstadoPedido(pedidoId, nuevoEstado, version) {
    const url = `${KANBAN_CONFIG.apiBase}${pedidoId}/estado/`;
    const response = await fetch(url, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ estado: nuevoEstado, version: parseInt(version, 10) }),
    });
    return response;
}

// ─── Inicialización Kanban ────────────────────────────────────────────────────

/**
 * Inicializa SortableJS en todas las columnas del kanban.
 * Maneja drag & drop entre columnas, rollback en caso de error 409.
 */
function inicializarKanban() {
    const columnas = document.querySelectorAll('.kanban-lista');
    if (columnas.length === 0) return;

    columnas.forEach((columna) => {
        Sortable.create(columna, {
            group: 'kanban',                 // permite mover entre columnas
            animation: 200,
            ghostClass: 'sortable-ghost',
            dragClass: 'sortable-drag',
            handle: '.kanban-tarjeta',
            forceFallback: false,

            onEnd: async function (evt) {
                const tarjeta = evt.item;
                const columnaDestino = evt.to;
                const columnaOrigen = evt.from;

                // Si no cambió de columna, nada que hacer
                if (columnaOrigen === columnaDestino) return;

                const pedidoId = tarjeta.getAttribute(KANBAN_CONFIG.pedidoIdAttr);
                const version  = tarjeta.getAttribute(KANBAN_CONFIG.versionAttr);
                const nuevoEstado = columnaDestino.getAttribute(KANBAN_CONFIG.estadoAttr);

                if (!pedidoId || !nuevoEstado) {
                    mostrarToast('Error: datos de tarjeta incompletos.', 'danger');
                    rollbackTarjeta(tarjeta, columnaOrigen, evt.oldIndex);
                    return;
                }

                // Feedback visual inmediato (optimistic update)
                tarjeta.style.opacity = '0.6';

                try {
                    const response = await actualizarEstadoPedido(pedidoId, nuevoEstado, version);

                    if (response.ok) {
                        const data = await response.json();
                        // Actualizar version en la tarjeta para futuros movimientos
                        if (data.version !== undefined) {
                            tarjeta.setAttribute(KANBAN_CONFIG.versionAttr, data.version);
                        }
                        tarjeta.style.opacity = '1';
                        actualizarContadoresColumnas();
                        mostrarToast(`Pedido #${pedidoId} movido a "${nuevoEstado}".`, 'success');

                    } else if (response.status === 409) {
                        // Conflicto de versión: otro usuario ya modificó el pedido
                        rollbackTarjeta(tarjeta, columnaOrigen, evt.oldIndex);
                        mostrarToast(
                            `Conflicto: el pedido #${pedidoId} fue modificado por otro usuario. Recargando...`,
                            'warning'
                        );
                        setTimeout(() => window.location.reload(), 2000);

                    } else {
                        const errorData = await response.json().catch(() => ({}));
                        rollbackTarjeta(tarjeta, columnaOrigen, evt.oldIndex);
                        mostrarToast(
                            `Error al mover pedido #${pedidoId}: ${errorData.detail || response.statusText}`,
                            'danger'
                        );
                    }
                } catch (err) {
                    console.error('[Kanban] Error de red:', err);
                    rollbackTarjeta(tarjeta, columnaOrigen, evt.oldIndex);
                    mostrarToast('Error de conexión. La tarjeta fue revertida.', 'danger');
                }
            },
        });
    });

    console.info('[Kanban] Inicializado correctamente en', columnas.length, 'columnas.');
}

/**
 * Revierte una tarjeta a su columna y posición originales.
 * @param {HTMLElement} tarjeta
 * @param {HTMLElement} columnaOrigen
 * @param {number} oldIndex
 */
function rollbackTarjeta(tarjeta, columnaOrigen, oldIndex) {
    tarjeta.style.opacity = '1';
    const referencia = columnaOrigen.children[oldIndex] || null;
    columnaOrigen.insertBefore(tarjeta, referencia);
    actualizarContadoresColumnas();
}

/**
 * Actualiza los contadores numéricos en el header de cada columna.
 */
function actualizarContadoresColumnas() {
    document.querySelectorAll('.kanban-columna').forEach((col) => {
        const lista = col.querySelector('.kanban-lista');
        const contador = col.querySelector('.kanban-contador');
        if (lista && contador) {
            contador.textContent = lista.querySelectorAll('.kanban-tarjeta').length;
        }
    });
}

// ─── Auto-refresh ─────────────────────────────────────────────────────────────

let autoRefreshTimer = null;

/**
 * Activa o desactiva el auto-refresh del Kanban.
 * @param {boolean} activar
 */
function toggleAutoRefresh(activar) {
    if (activar && KANBAN_CONFIG.autoRefreshInterval > 0) {
        autoRefreshTimer = setInterval(() => {
            // Solo recarga si no hay ninguna tarjeta siendo arrastrada
            if (!document.querySelector('.sortable-drag')) {
                window.location.reload();
            }
        }, KANBAN_CONFIG.autoRefreshInterval);
        console.info('[Kanban] Auto-refresh activado cada', KANBAN_CONFIG.autoRefreshInterval / 1000, 's');
    } else {
        clearInterval(autoRefreshTimer);
        console.info('[Kanban] Auto-refresh desactivado.');
    }
}

// ─── Bootstrap del módulo ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
    inicializarKanban();
    actualizarContadoresColumnas();

    // Iniciar auto-refresh si el usuario lo activa vía checkbox en la UI
    const chkAutoRefresh = document.getElementById('chkAutoRefresh');
    if (chkAutoRefresh) {
        chkAutoRefresh.addEventListener('change', (e) => toggleAutoRefresh(e.target.checked));
        if (chkAutoRefresh.checked) toggleAutoRefresh(true);
    }
});
