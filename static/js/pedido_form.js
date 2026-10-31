/**
 * pedido_form.js — Dulce Arte
 * Formset dinámico de detalles de pedido:
 *  - Agregar / quitar líneas de receta
 *  - Cálculo en vivo de subtotales, total, descuento, anticipo, saldo
 *  - Validaciones de descuento y anticipo
 *  - Fetch de precio al cambiar receta
 */

'use strict';

// ─── Configuración ────────────────────────────────────────────────────────────
const PEDIDO_FORM_CONFIG = {
    apiRecetaBase:    '/api/catalogo/recetas/',   // GET /<id>/ → { precio_unitario, nombre }
    maxDetalles:      20,
    descuentoMaxPct:  100,
};

// ─── Utilidades ───────────────────────────────────────────────────────────────

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach((c) => {
            c = c.trim();
            if (c.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(c.slice(name.length + 1));
            }
        });
    }
    return cookieValue;
}

/**
 * Formatea un número como moneda CLP (sin decimales, con separador de miles).
 * @param {number} valor
 * @returns {string}
 */
function formatCLP(valor) {
    return new Intl.NumberFormat('es-CL', {
        style: 'currency',
        currency: 'CLP',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(valor || 0);
}

/**
 * Parsea el valor numérico de un input, devuelve 0 si NaN.
 * @param {HTMLInputElement} input
 * @returns {number}
 */
function parseInput(input) {
    return parseFloat((input?.value || '0').replace(/[^0-9.-]/g, '')) || 0;
}

// ─── Cálculos ─────────────────────────────────────────────────────────────────

/**
 * Recalcula subtotal de una fila y actualiza su display.
 * @param {HTMLElement} fila
 * @returns {number} subtotal de esa fila
 */
function calcularFilaSubtotal(fila) {
    const cantidad   = parseInput(fila.querySelector('.det-cantidad'));
    const precio     = parseInput(fila.querySelector('.det-precio'));
    const subtotal   = cantidad * precio;

    const displaySubtotal = fila.querySelector('.det-subtotal-display');
    if (displaySubtotal) displaySubtotal.textContent = formatCLP(subtotal);

    const hiddenSubtotal = fila.querySelector('.det-subtotal-hidden');
    if (hiddenSubtotal) hiddenSubtotal.value = subtotal.toFixed(0);

    return subtotal;
}

/**
 * Recalcula todos los totales del formulario de pedido.
 */
function recalcularTotales() {
    const filas = document.querySelectorAll('.detalle-fila:not([style*="display: none"])');
    let subtotalTotal = 0;

    filas.forEach((fila) => {
        subtotalTotal += calcularFilaSubtotal(fila);
    });

    // Descuento
    const inputDescuento    = document.getElementById('id_descuento');
    const descuento         = parseInput(inputDescuento);
    const errorDescuento    = document.getElementById('error-descuento');

    if (descuento > subtotalTotal) {
        if (errorDescuento) {
            errorDescuento.textContent = `El descuento (${formatCLP(descuento)}) no puede superar el subtotal (${formatCLP(subtotalTotal)}).`;
            errorDescuento.style.display = 'block';
        }
        if (inputDescuento) inputDescuento.classList.add('is-invalid');
    } else {
        if (errorDescuento) errorDescuento.style.display = 'none';
        if (inputDescuento) inputDescuento.classList.remove('is-invalid');
    }

    const total = Math.max(subtotalTotal - descuento, 0);

    // Anticipo
    const inputAnticipo  = document.getElementById('id_anticipo');
    const anticipo       = parseInput(inputAnticipo);
    const errorAnticipo  = document.getElementById('error-anticipo');

    if (anticipo > total) {
        if (errorAnticipo) {
            errorAnticipo.textContent = `El anticipo (${formatCLP(anticipo)}) no puede superar el total (${formatCLP(total)}).`;
            errorAnticipo.style.display = 'block';
        }
        if (inputAnticipo) inputAnticipo.classList.add('is-invalid');
    } else {
        if (errorAnticipo) errorAnticipo.style.display = 'none';
        if (inputAnticipo) inputAnticipo.classList.remove('is-invalid');
    }

    const saldo = Math.max(total - anticipo, 0);

    // Mostrar resultados
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = formatCLP(val);
    };
    set('display-subtotal', subtotalTotal);
    set('display-descuento', descuento);
    set('display-total', total);
    set('display-anticipo', anticipo);
    set('display-saldo', saldo);

    // Campos ocultos para envío
    const setHidden = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val.toFixed(0);
    };
    setHidden('hidden-subtotal', subtotalTotal);
    setHidden('hidden-total', total);
    setHidden('hidden-saldo', saldo);
}

// ─── Fetch de precio al cambiar receta ───────────────────────────────────────

/**
 * Obtiene el precio unitario de una receta desde la API y actualiza la fila.
 * @param {HTMLSelectElement} select
 * @param {HTMLElement} fila
 */
async function fetchPrecioReceta(select, fila) {
    const recetaId = select.value;
    if (!recetaId) return;

    const inputPrecio = fila.querySelector('.det-precio');
    if (!inputPrecio) return;

    try {
        const response = await fetch(`${PEDIDO_FORM_CONFIG.apiRecetaBase}${recetaId}/`, {
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Accept': 'application/json',
            },
        });

        if (response.ok) {
            const data = await response.json();
            if (data.precio_unitario !== undefined) {
                inputPrecio.value = parseFloat(data.precio_unitario).toFixed(0);
                inputPrecio.dispatchEvent(new Event('input'));
            }
        } else {
            console.warn('[PedidoForm] No se pudo obtener precio para receta', recetaId);
        }
    } catch (err) {
        console.error('[PedidoForm] Error al obtener precio de receta:', err);
    }
}

// ─── Formset dinámico ─────────────────────────────────────────────────────────

let totalFormsetForms = 0;

/**
 * Actualiza el campo TOTAL_FORMS del management form de Django.
 */
function actualizarManagementForm() {
    const totalFormsInput = document.getElementById('id_detalles-TOTAL_FORMS');
    if (totalFormsInput) totalFormsInput.value = totalFormsetForms;
}

/**
 * Agrega una nueva fila al formset de detalles.
 */
function agregarDetalle() {
    const contenedor = document.getElementById('detalles-container');
    const template   = document.getElementById('detalle-template');

    if (!contenedor || !template) {
        console.error('[PedidoForm] Falta #detalles-container o #detalle-template en el DOM.');
        return;
    }

    const filas = contenedor.querySelectorAll('.detalle-fila:not(.d-none)');
    if (filas.length >= PEDIDO_FORM_CONFIG.maxDetalles) {
        alert(`Máximo ${PEDIDO_FORM_CONFIG.maxDetalles} líneas por pedido.`);
        return;
    }

    // Clonar template y reemplazar __prefix__ con el índice actual
    const idx   = totalFormsetForms;
    const clone = template.content.cloneNode(true);
    const fila  = clone.querySelector('.detalle-fila');

    fila.innerHTML = fila.innerHTML.replaceAll('__prefix__', idx);

    contenedor.appendChild(clone);
    totalFormsetForms++;
    actualizarManagementForm();

    // Bindear eventos en la nueva fila
    const nuevaFila = contenedor.querySelector(`.detalle-fila[data-index="${idx}"]`)
                   || contenedor.lastElementChild;
    bindearFilaEventos(nuevaFila);
    recalcularTotales();
}

/**
 * Marca una fila como eliminada (DELETE=True del formset).
 * @param {HTMLElement} fila
 */
function eliminarDetalle(fila) {
    const deleteInput = fila.querySelector('input[name$="-DELETE"]');
    if (deleteInput) {
        deleteInput.value = 'on';
        deleteInput.checked = true;
    }
    fila.style.display = 'none';
    recalcularTotales();
}

/**
 * Enlaza los eventos de cambio en los inputs de una fila.
 * @param {HTMLElement} fila
 */
function bindearFilaEventos(fila) {
    if (!fila) return;

    // Cambio de receta → fetch precio
    const selectReceta = fila.querySelector('.det-receta');
    if (selectReceta) {
        selectReceta.addEventListener('change', () => fetchPrecioReceta(selectReceta, fila));
    }

    // Cambio de cantidad o precio → recalcular
    fila.querySelectorAll('.det-cantidad, .det-precio').forEach((input) => {
        input.addEventListener('input', recalcularTotales);
    });

    // Botón eliminar
    const btnEliminar = fila.querySelector('.btn-eliminar-detalle');
    if (btnEliminar) {
        btnEliminar.addEventListener('click', () => eliminarDetalle(fila));
    }
}

// ─── Bootstrap del módulo ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
    // Verificar que estamos en la página del formulario de pedido
    const contenedor = document.getElementById('detalles-container');
    if (!contenedor) return;

    // Leer cuántas filas iniciales hay (edición de pedido existente)
    const totalFormsInput = document.getElementById('id_detalles-TOTAL_FORMS');
    totalFormsetForms = parseInt(totalFormsInput?.value || '0', 10);

    // Bindear eventos en filas existentes
    contenedor.querySelectorAll('.detalle-fila').forEach((fila) => {
        bindearFilaEventos(fila);
    });

    // Botón agregar línea
    const btnAgregar = document.getElementById('btn-agregar-detalle');
    if (btnAgregar) {
        btnAgregar.addEventListener('click', agregarDetalle);
    }

    // Recalcular al cambiar descuento o anticipo
    ['id_descuento', 'id_anticipo'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', recalcularTotales);
    });

    // Cálculo inicial
    recalcularTotales();

    console.info('[PedidoForm] Formset dinámico inicializado. Filas iniciales:', totalFormsetForms);
});
