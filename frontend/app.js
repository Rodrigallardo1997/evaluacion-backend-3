/**
 * app.js — Frontend Dulce Arte (Diseño EVA-3 con Integración Cloud EVA-4)
 * Consume la API REST vía Amazon API Gateway usando JWT (Bearer Token),
 * ejecuta operaciones CRUD (GET, POST, PATCH, DELETE) sobre PostgreSQL RDS
 * y dispara notificaciones automáticas por correo vía AWS Lambda -> SNS.
 */
'use strict';

let API_BASE = localStorage.getItem('dulcearte_api_url') || 'https://mczus55xzk.execute-api.us-east-1.amazonaws.com/api';
let LAMBDA_URL = localStorage.getItem('dulcearte_lambda_url') || 'https://wsa4lyofyakp3pxazuyg55d7fm0zpsaf.lambda-url.us-east-1.on.aws/';
let JWT_ACCESS = localStorage.getItem('dulcearte_jwt_access') || '';
let JWT_REFRESH = localStorage.getItem('dulcearte_jwt_refresh') || '';
let AUTH_TOKEN = localStorage.getItem('dulcearte_token') || '';
let USER_INFO = JSON.parse(localStorage.getItem('dulcearte_user') || 'null');
let CATALOGO_DATA = [];

const CATEGORIA_LABELS = {
    'TORTA': 'Tortas Clásicas y Especiales',
    'POSTRE': 'Postres y Pies Artesanales',
    'GALLETA': 'Galletas Decoradas',
    'DULCE': 'Opciones Dulces',
    'CAFETERIA': 'Cafetería de Especialidad'
};

document.addEventListener('DOMContentLoaded', () => {
    const inApi = document.getElementById('inputApiUrl');
    const inLam = document.getElementById('inputLambdaUrl');
    if (inApi) inApi.value = API_BASE;
    if (inLam) inLam.value = LAMBDA_URL;
    actualizarUIUsuario();
    cargarCatalogo();
});

function getAuthHeader() {
    if (JWT_ACCESS) return { 'Authorization': `Bearer ${JWT_ACCESS}` };
    if (AUTH_TOKEN) return { 'Authorization': `Token ${AUTH_TOKEN}` };
    return {};
}

function mostrarAlerta(texto) {
    const el = document.getElementById('alertaFlotante');
    const txt = document.getElementById('alertaFlotanteTexto');
    if (el && txt) {
        txt.textContent = texto;
        el.classList.remove('d-none');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function logCrudJson(metodo, endpoint, statusHttp, payload) {
    const box = document.getElementById('crudJsonBox');
    if (!box) return;
    const timestamp = new Date().toLocaleTimeString('es-CL');
    box.textContent = `[${timestamp}] ${metodo} ${endpoint} ➔ HTTP ${statusHttp}\n` + JSON.stringify(payload, null, 2);
}

function decodificarPayloadJwt(token) {
    try {
        const parts = token.split('.');
        if (parts.length !== 3) return null;
        return JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    } catch {
        return null;
    }
}

function guardarConfig() {
    API_BASE = document.getElementById('inputApiUrl').value.trim().replace(/\/+$/, '');
    LAMBDA_URL = document.getElementById('inputLambdaUrl').value.trim();
    localStorage.setItem('dulcearte_api_url', API_BASE);
    localStorage.setItem('dulcearte_lambda_url', LAMBDA_URL);
    cargarCatalogo();
    if (JWT_ACCESS || AUTH_TOKEN) cargarPedidos();
}

function limpiarFiltros() {
    document.getElementById('buscarProducto').value = '';
    document.getElementById('filtroCategoria').value = '';
    renderCatalogo();
}

function cerrarModalBootstrap(id) {
    const el = document.getElementById(id);
    if (!el || typeof bootstrap === 'undefined') return;
    const inst = bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el);
    inst.hide();
}

function abrirModalBootstrap(id) {
    const el = document.getElementById(id);
    if (!el || typeof bootstrap === 'undefined') return;
    const inst = bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el);
    inst.show();
}

// ============================================================================
// 1. CATÁLOGO ESTILO EVA-3 Y CRUD DE RECETAS EN RDS
// ============================================================================
async function cargarCatalogo() {
    const statusEl = document.getElementById('apiStatus');
    try {
        const res = await fetch(`${API_BASE}/catalogo-publico/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        CATALOGO_DATA = await res.json();

        if (statusEl) {
            statusEl.textContent = `Estado API: Conectada (${CATALOGO_DATA.length} productos en RDS)`;
            statusEl.className = 'badge bg-success-subtle text-success border';
        }
        const kpiEl = document.getElementById('kpiTotalRecetas');
        if (kpiEl) kpiEl.textContent = CATALOGO_DATA.length;
        renderCatalogo();
    } catch (err) {
        if (statusEl) {
            statusEl.textContent = `Error API: ${err.message}`;
            statusEl.className = 'badge bg-danger-subtle text-danger border';
        }
    }
}

function renderCatalogo() {
    const grid = document.getElementById('gridCatalogo');
    const badgeCount = document.getElementById('contadorProductosBadge');
    const cat = document.getElementById('filtroCategoria').value;
    const q = document.getElementById('buscarProducto').value.toLowerCase().trim();
    const autenticado = Boolean(JWT_ACCESS || AUTH_TOKEN);
    const puedeEditar = autenticado && USER_INFO && ['ADMIN', 'COCINA'].includes(USER_INFO.rol);

    const filtrados = CATALOGO_DATA.filter(item => {
        const matchCat = !cat || item.categoria === cat;
        const matchText = !q || item.nombre.toLowerCase().includes(q) || (item.descripcion || '').toLowerCase().includes(q);
        return matchCat && matchText;
    });

    if (badgeCount) {
        badgeCount.textContent = `${filtrados.length} producto${filtrados.length === 1 ? '' : 's'} disponible${filtrados.length === 1 ? '' : 's'}`;
    }

    if (filtrados.length === 0) {
        grid.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="bi bi-search fs-1 text-muted d-block mb-2"></i>
                <h4 class="h5 text-muted">No se encontraron productos con los filtros aplicados.</h4>
                <button onclick="limpiarFiltros()" class="btn btn-outline-dark btn-sm mt-2">Ver todo el catálogo</button>
            </div>`;
        return;
    }

    grid.innerHTML = filtrados.map(r => {
        const imgUrl = r.imagen
            ? (r.imagen.startsWith('http') ? r.imagen : `http://32.196.211.81${r.imagen}`)
            : 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=600&q=80';
        const catLabel = r.categoria_display || CATEGORIA_LABELS[r.categoria] || r.categoria;

        const btnAccion = autenticado
            ? `<a href="http://32.196.211.81/pedidos/nuevo/" class="btn btn-sm btn-outline-dark fw-bold px-3">
                   <i class="bi bi-bag-plus me-1 text-warning"></i>Cotizar
               </a>`
            : `<button type="button" class="btn btn-sm btn-outline-dark fw-bold px-3" data-bs-toggle="modal" data-bs-target="#modalLogin">
                   <i class="bi bi-bag-plus me-1 text-warning"></i>Cotizar
               </button>`;

        const barraCrud = puedeEditar ? `
            <div class="border-top pt-2 mt-2 d-flex justify-content-end gap-1">
                <button type="button" onclick="abrirModalEditar(${r.id})" class="btn btn-sm btn-light border text-dark py-0 px-2" style="font-size: 0.75rem;">
                    <i class="bi bi-pencil-square text-primary me-1"></i>Editar
                </button>
                <button type="button" onclick="eliminarProductoCRUD(${r.id})" class="btn btn-sm btn-light border text-danger py-0 px-2" style="font-size: 0.75rem;">
                    <i class="bi bi-trash3 me-1"></i>Eliminar
                </button>
            </div>` : '';

        return `
        <div class="col-md-6 col-lg-3">
            <div class="receta-card">
                <div class="receta-img-container">
                    <img src="${imgUrl}" class="receta-img" alt="${r.nombre}">
                    <div class="position-absolute top-0 end-0 m-2">
                        <span class="badge bg-white text-dark shadow-sm border small">
                            <i class="bi bi-clock me-1 text-warning"></i>${r.tiempo_preparacion_min} min
                        </span>
                    </div>
                </div>

                <div class="p-3 d-flex flex-column flex-grow-1">
                    <div class="mb-2">
                        <span class="badge px-2 py-1 small" style="background-color: var(--dulce-crema); color: var(--dulce-cafe); border: 1px solid rgba(107,66,38,0.2);">
                            ${catLabel}
                        </span>
                    </div>

                    <h3 class="h6 fw-bold text-dark mb-1" style="min-height: 38px;">${r.nombre}</h3>
                    <p class="text-muted small mb-3 flex-grow-1" style="font-size: 0.8rem; min-height: 48px;">
                        ${r.descripcion || 'Elaboración artesanal con ingredientes seleccionados.'}
                    </p>

                    <div class="border-top pt-2 mt-auto d-flex justify-content-between align-items-center">
                        <div>
                            <small class="text-muted d-block" style="font-size: 0.7rem;">Precio base</small>
                            <span class="price-tag">$${Number(r.precio_base).toLocaleString('es-CL')}</span>
                        </div>
                        ${btnAccion}
                    </div>
                    ${barraCrud}
                </div>
            </div>
        </div>`;
    }).join('');
}

function abrirModalCrear() {
    document.getElementById('modalProductoTitulo').textContent = '🎂 Nueva Receta / Producto';
    document.getElementById('prodId').value = '';
    document.getElementById('prodNombre').value = '';
    document.getElementById('prodCategoria').value = 'TORTA';
    document.getElementById('prodPrecio').value = '25000';
    document.getElementById('prodTiempo').value = '60';
    document.getElementById('prodRendimiento').value = '1';
    document.getElementById('prodDescripcion').value = '';
    document.getElementById('prodError').classList.add('d-none');
    abrirModalBootstrap('modalProducto');
}

function abrirModalEditar(id) {
    const p = CATALOGO_DATA.find(x => x.id === id);
    if (!p) return;
    document.getElementById('modalProductoTitulo').textContent = `✏️ Editar Receta: ${p.nombre}`;
    document.getElementById('prodId').value = p.id;
    document.getElementById('prodNombre').value = p.nombre;
    document.getElementById('prodCategoria').value = p.categoria;
    document.getElementById('prodPrecio').value = Math.round(Number(p.precio_base));
    document.getElementById('prodTiempo').value = p.tiempo_preparacion_min;
    document.getElementById('prodRendimiento').value = p.rendimiento || 1;
    document.getElementById('prodDescripcion').value = p.descripcion || '';
    document.getElementById('prodError').classList.add('d-none');
    abrirModalBootstrap('modalProducto');
}

async function guardarProductoCRUD(e) {
    e.preventDefault();
    const errEl = document.getElementById('prodError');
    errEl.classList.add('d-none');

    const id = document.getElementById('prodId').value;
    const payload = {
        nombre: document.getElementById('prodNombre').value.trim(),
        categoria: document.getElementById('prodCategoria').value,
        precio_base: String(document.getElementById('prodPrecio').value),
        tiempo_preparacion_min: Number(document.getElementById('prodTiempo').value),
        rendimiento: Number(document.getElementById('prodRendimiento').value),
        margen_deseado: "35.00",
        descripcion: document.getElementById('prodDescripcion').value.trim(),
        activo: true
    };

    const metodo = id ? 'PATCH' : 'POST';
    const url = id ? `${API_BASE}/recetas/${id}/` : `${API_BASE}/recetas/`;

    try {
        const res = await fetch(url, {
            method: metodo,
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        logCrudJson(metodo, url.replace(API_BASE, '/api'), res.status, data);

        if (!res.ok) throw new Error(JSON.stringify(data));
        cerrarModalBootstrap('modalProducto');
        mostrarAlerta(`Receta "${payload.nombre}" ${id ? 'actualizada' : 'creada'} en AWS RDS y notificación enviada por correo vía AWS Lambda ➔ SNS.`);
        await cargarCatalogo();
    } catch (err) {
        errEl.textContent = `Error al guardar: ${err.message}`;
        errEl.classList.remove('d-none');
    }
}

async function eliminarProductoCRUD(id) {
    const p = CATALOGO_DATA.find(x => x.id === id);
    if (!confirm(`¿Deseas eliminar "${p ? p.nombre : id}" del catálogo en PostgreSQL RDS?`)) return;

    const url = `${API_BASE}/recetas/${id}/`;
    try {
        const res = await fetch(url, {
            method: 'DELETE',
            headers: { ...getAuthHeader() }
        });
        logCrudJson('DELETE', `/api/recetas/${id}/`, res.status, { eliminado_id: id, status: res.status });
        if (!res.ok && res.status !== 204) throw new Error(`HTTP ${res.status}`);
        mostrarAlerta(`Receta eliminada exitosamente de PostgreSQL RDS.`);
        await cargarCatalogo();
    } catch (err) {
        alert(`No se pudo eliminar (puede tener pedidos asociados en RDS): ${err.message}`);
    }
}

// ============================================================================
// 2. AUTENTICACIÓN CON JWT (Bearer Access & Refresh Token)
// ============================================================================
function fastLogin(username, password) {
    document.getElementById('loginUser').value = username;
    document.getElementById('loginPass').value = password;
    iniciarSesion(new Event('submit'));
}

async function iniciarSesion(e) {
    e.preventDefault();
    const errEl = document.getElementById('loginError');
    errEl.classList.add('d-none');

    const username = document.getElementById('loginUser').value.trim();
    const password = document.getElementById('loginPass').value;

    try {
        const res = await fetch(`${API_BASE}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Credenciales inválidas.');

        JWT_ACCESS = data.access || '';
        JWT_REFRESH = data.refresh || '';
        AUTH_TOKEN = data.token || '';
        USER_INFO = data.usuario;

        localStorage.setItem('dulcearte_jwt_access', JWT_ACCESS);
        localStorage.setItem('dulcearte_jwt_refresh', JWT_REFRESH);
        localStorage.setItem('dulcearte_token', AUTH_TOKEN);
        localStorage.setItem('dulcearte_user', JSON.stringify(USER_INFO));

        logCrudJson('POST', '/api/auth/login/', res.status, {
            detail: data.detail,
            jwt_type: 'Bearer (HS256)',
            usuario: data.usuario
        });

        cerrarModalBootstrap('modalLogin');
        actualizarUIUsuario();
        renderCatalogo();
    } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('d-none');
    }
}

function cerrarSesion() {
    JWT_ACCESS = '';
    JWT_REFRESH = '';
    AUTH_TOKEN = '';
    USER_INFO = null;
    localStorage.removeItem('dulcearte_jwt_access');
    localStorage.removeItem('dulcearte_jwt_refresh');
    localStorage.removeItem('dulcearte_token');
    localStorage.removeItem('dulcearte_user');
    actualizarUIUsuario();
    renderCatalogo();
}

function actualizarUIUsuario() {
    const badge = document.getElementById('userBadge');
    const btnIn = document.getElementById('btnOpenLogin');
    const btnFast = document.getElementById('btnFastAccess');
    const btnOut = document.getElementById('btnLogout');
    const btnCrear = document.getElementById('btnOpenCrear');
    const btnPanel = document.getElementById('btnPanelCompleto');
    const secPed = document.getElementById('seccionPedidos');
    const jwtBox = document.getElementById('jwtTokenBox');

    if ((JWT_ACCESS || AUTH_TOKEN) && USER_INFO) {
        badge.innerHTML = `<i class="bi bi-person-circle text-primary me-1"></i>${USER_INFO.username} (<strong>${USER_INFO.rol_display || USER_INFO.rol}</strong>)`;
        badge.classList.remove('d-none');
        btnIn.classList.add('d-none');
        btnFast.classList.add('d-none');
        btnOut.classList.remove('d-none');
        btnPanel.classList.remove('d-none');
        secPed.classList.remove('d-none');

        if (['ADMIN', 'COCINA'].includes(USER_INFO.rol)) {
            btnCrear.classList.remove('d-none');
        } else {
            btnCrear.classList.add('d-none');
        }

        if (jwtBox && JWT_ACCESS) {
            const claims = decodificarPayloadJwt(JWT_ACCESS);
            jwtBox.textContent = `Authorization: Bearer ${JWT_ACCESS}\n\nPayload:\n${JSON.stringify(claims, null, 2)}`;
        }
        cargarPedidos();
    } else {
        badge.classList.add('d-none');
        btnIn.classList.remove('d-none');
        btnFast.classList.remove('d-none');
        btnOut.classList.add('d-none');
        btnCrear.classList.add('d-none');
        btnPanel.classList.add('d-none');
        secPed.classList.add('d-none');
    }
}

// ============================================================================
// 3. TABLA DE PEDIDOS DESDE AWS RDS (Autenticado con JWT)
// ============================================================================
async function cargarPedidos() {
    if (!JWT_ACCESS && !AUTH_TOKEN) return;
    const tbody = document.getElementById('tablaPedidosBody');
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">Cargando pedidos desde AWS RDS...</td></tr>';

    try {
        const res = await fetch(`${API_BASE}/pedidos/`, {
            headers: { ...getAuthHeader() }
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const lista = data.results || data;

        if (!lista.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No hay pedidos registrados para este rol.</td></tr>';
            return;
        }

        tbody.innerHTML = lista.map(p => `
            <tr>
                <td class="fw-bold font-monospace" style="color: var(--dulce-cafe);">
                    <a href="http://32.196.211.81/pedidos/${p.id}/" class="text-decoration-none" style="color: var(--dulce-cafe);">${p.codigo}</a>
                </td>
                <td>${p.cliente_nombre || p.cliente}</td>
                <td class="text-muted">${new Date(p.fecha_entrega).toLocaleDateString('es-CL')}</td>
                <td><span class="badge bg-primary-subtle text-primary border px-2 py-1">${p.estado_display || p.estado}</span></td>
                <td class="fw-bold">$${Number(p.total).toLocaleString('es-CL')}</td>
            </tr>
        `).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-3">Error cargando pedidos: ${err.message}</td></tr>`;
    }
}

// ============================================================================
// 4. PRUEBA DE RATE LIMIT (API GATEWAY / MITIGACIÓN DOS)
// ============================================================================
async function probarRateLimit() {
    const log = document.getElementById('rateLimitLog');
    log.textContent = 'Lanzando 25 peticiones rápidas...\n';
    let okCount = 0;
    let blockedCount = 0;

    const promesas = Array.from({ length: 25 }, async (_, i) => {
        try {
            const res = await fetch(`${API_BASE}/catalogo-publico/?burst=${i}`);
            if (res.status === 429 || res.status === 503) {
                blockedCount++;
                log.textContent += `[Req #${i + 1}] 🛑 BLOQUEADA (HTTP ${res.status})\n`;
            } else {
                okCount++;
                log.textContent += `[Req #${i + 1}] ✅ Permitida (HTTP ${res.status})\n`;
            }
        } catch (err) {
            blockedCount++;
            log.textContent += `[Req #${i + 1}] ⚠️ Frenada (${err.message})\n`;
        }
        log.scrollTop = log.scrollHeight;
    });

    await Promise.all(promesas);
    log.textContent += `\n=== RESUMEN: ${okCount} permitidas | ${blockedCount} frenadas (HTTP 429) ===`;
    log.scrollTop = log.scrollHeight;
}
