/**
 * app.js — Frontend Desacoplado de Dulce Arte (Evaluación N.º 4)
 * Consume la API REST vía Amazon API Gateway usando JWT (Bearer Token),
 * ejecuta operaciones CRUD (GET, POST, PATCH, DELETE) sobre PostgreSQL RDS
 * e interactúa con AWS Lambda + SNS.
 */
'use strict';

let API_BASE = localStorage.getItem('dulcearte_api_url') || 'https://mczus55xzk.execute-api.us-east-1.amazonaws.com/api';
let LAMBDA_URL = localStorage.getItem('dulcearte_lambda_url') || 'https://wsa4lyofyakp3pxazuyg55d7fm0zpsaf.lambda-url.us-east-1.on.aws/';
let JWT_ACCESS = localStorage.getItem('dulcearte_jwt_access') || '';
let JWT_REFRESH = localStorage.getItem('dulcearte_jwt_refresh') || '';
let AUTH_TOKEN = localStorage.getItem('dulcearte_token') || '';
let USER_INFO = JSON.parse(localStorage.getItem('dulcearte_user') || 'null');
let CATALOGO_DATA = [];

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('inputApiUrl').value = API_BASE;
    document.getElementById('inputLambdaUrl').value = LAMBDA_URL;
    actualizarUIUsuario();
    cargarCatalogo();
});

function getAuthHeader() {
    if (JWT_ACCESS) return { 'Authorization': `Bearer ${JWT_ACCESS}` };
    if (AUTH_TOKEN) return { 'Authorization': `Token ${AUTH_TOKEN}` };
    return {};
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

function toggleModal(id, show) {
    document.getElementById(id).classList.toggle('hidden', !show);
}

// ============================================================================
// 1. CATÁLOGO PÚBLICO Y CRUD DE RECETAS (GET / POST / PATCH / DELETE en RDS)
// ============================================================================
async function cargarCatalogo() {
    const statusEl = document.getElementById('apiStatus');
    statusEl.textContent = 'Estado API: Conectando...';
    statusEl.className = 'font-semibold text-amber-700';

    try {
        const res = await fetch(`${API_BASE}/catalogo-publico/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        CATALOGO_DATA = await res.json();

        statusEl.textContent = `Estado API: Conectada (${CATALOGO_DATA.length} productos en RDS)`;
        statusEl.className = 'font-semibold text-green-700';
        renderCatalogo();
    } catch (err) {
        statusEl.textContent = `Error API: ${err.message}`;
        statusEl.className = 'font-semibold text-red-600';
    }
}

function renderCatalogo() {
    const grid = document.getElementById('gridCatalogo');
    const cat = document.getElementById('filtroCategoria').value;
    const q = document.getElementById('buscarProducto').value.toLowerCase().trim();
    const puedeEditar = (JWT_ACCESS || AUTH_TOKEN) && USER_INFO && ['ADMIN', 'COCINA'].includes(USER_INFO.rol);

    const filtrados = CATALOGO_DATA.filter(item => {
        const matchCat = !cat || item.categoria === cat;
        const matchText = !q || item.nombre.toLowerCase().includes(q) || (item.descripcion || '').toLowerCase().includes(q);
        return matchCat && matchText;
    });

    if (filtrados.length === 0) {
        grid.innerHTML = '<p class="text-gray-500 col-span-full text-center py-8">No se encontraron productos con ese filtro.</p>';
        return;
    }

    const baseHost = API_BASE.replace(/\/api$/, '');
    grid.innerHTML = filtrados.map(p => {
        const imgUrl = p.imagen
            ? (p.imagen.startsWith('http') ? p.imagen : `${baseHost}${p.imagen}`)
            : 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=600&q=80';

        const botonesCrud = puedeEditar ? `
            <div class="mt-3 pt-2 border-t border-amber-100 flex items-center justify-end gap-2">
                <button onclick="abrirModalEditar(${p.id})" class="px-2.5 py-1 rounded bg-amber-100 hover:bg-amber-200 text-cafe text-xs font-semibold">
                    ✏️ Editar (PATCH)
                </button>
                <button onclick="eliminarProductoCRUD(${p.id})" class="px-2.5 py-1 rounded bg-red-100 hover:bg-red-200 text-red-700 text-xs font-semibold">
                    🗑️ Eliminar (DELETE)
                </button>
            </div>
        ` : '';

        return `
        <div class="bg-white rounded-2xl shadow-sm border border-amber-100 overflow-hidden hover:shadow-md transition flex flex-col">
            <img src="${imgUrl}" alt="${p.nombre}" class="h-44 w-full object-cover">
            <div class="p-4 flex-1 flex flex-col justify-between">
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-100 text-cafe">
                            ${p.categoria_display || p.categoria}
                        </span>
                        <span class="text-[10px] font-mono text-gray-400">ID #${p.id}</span>
                    </div>
                    <h3 class="font-bold text-lg text-cafe leading-snug">${p.nombre}</h3>
                    <p class="text-xs text-gray-500 mt-1 line-clamp-2">${p.descripcion || 'Elaboración artesanal con ingredientes seleccionados.'}</p>
                </div>
                <div>
                    <div class="mt-4 pt-3 border-t border-amber-50 flex items-center justify-between">
                        <span class="text-lg font-extrabold text-dorado">$${Number(p.precio_base).toLocaleString('es-CL')}</span>
                        <span class="text-xs text-gray-400">⏱ ${p.tiempo_preparacion_min} min</span>
                    </div>
                    ${botonesCrud}
                </div>
            </div>
        </div>`;
    }).join('');
}

function abrirModalCrear() {
    document.getElementById('modalProductoTitulo').textContent = '🎂 Crear Producto en RDS (POST /api/recetas/)';
    document.getElementById('prodId').value = '';
    document.getElementById('prodNombre').value = '';
    document.getElementById('prodCategoria').value = 'TORTA';
    document.getElementById('prodPrecio').value = '25000';
    document.getElementById('prodTiempo').value = '60';
    document.getElementById('prodRendimiento').value = '1';
    document.getElementById('prodDescripcion').value = '';
    document.getElementById('prodError').classList.add('hidden');
    toggleModal('modalProducto', true);
}

function abrirModalEditar(id) {
    const p = CATALOGO_DATA.find(x => x.id === id);
    if (!p) return;
    document.getElementById('modalProductoTitulo').textContent = `✏️ Editar Producto #${p.id} (PATCH /api/recetas/${p.id}/)`;
    document.getElementById('prodId').value = p.id;
    document.getElementById('prodNombre').value = p.nombre;
    document.getElementById('prodCategoria').value = p.categoria;
    document.getElementById('prodPrecio').value = Math.round(Number(p.precio_base));
    document.getElementById('prodTiempo').value = p.tiempo_preparacion_min;
    document.getElementById('prodRendimiento').value = p.rendimiento || 1;
    document.getElementById('prodDescripcion').value = p.descripcion || '';
    document.getElementById('prodError').classList.add('hidden');
    toggleModal('modalProducto', true);
}

async function guardarProductoCRUD(e) {
    e.preventDefault();
    const errEl = document.getElementById('prodError');
    errEl.classList.add('hidden');

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
        toggleModal('modalProducto', false);
        await cargarCatalogo();
    } catch (err) {
        errEl.textContent = `Error: ${err.message}`;
        errEl.classList.remove('hidden');
    }
}

async function eliminarProductoCRUD(id) {
    const p = CATALOGO_DATA.find(x => x.id === id);
    if (!confirm(`¿Eliminar "${p ? p.nombre : id}" de PostgreSQL RDS mediante DELETE /api/recetas/${id}/?`)) return;

    const url = `${API_BASE}/recetas/${id}/`;
    try {
        const res = await fetch(url, {
            method: 'DELETE',
            headers: { ...getAuthHeader() }
        });
        logCrudJson('DELETE', `/api/recetas/${id}/`, res.status, { eliminado_id: id, status: res.status === 204 ? '204 No Content (Eliminado en RDS)' : res.status });
        if (!res.ok && res.status !== 204) throw new Error(`HTTP ${res.status}`);
        await cargarCatalogo();
    } catch (err) {
        alert(`No se pudo eliminar (puede tener pedidos asociados en RDS): ${err.message}`);
    }
}

// ============================================================================
// 2. AUTENTICACIÓN DESACOPLADA CON JWT (Bearer Access & Refresh Token)
// ============================================================================
function fastLogin(username, password) {
    document.getElementById('loginUser').value = username;
    document.getElementById('loginPass').value = password;
    iniciarSesion(new Event('submit'));
}

async function iniciarSesion(e) {
    e.preventDefault();
    const errEl = document.getElementById('loginError');
    errEl.classList.add('hidden');

    const username = document.getElementById('loginUser').value.trim();
    const password = document.getElementById('loginPass').value;

    try {
        const res = await fetch(`${API_BASE}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error de autenticación');

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

        toggleModal('modalLogin', false);
        actualizarUIUsuario();
        renderCatalogo();
    } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
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
    const btnOut = document.getElementById('btnLogout');
    const btnCrear = document.getElementById('btnOpenCrear');
    const secPed = document.getElementById('seccionPedidos');
    const secJwt = document.getElementById('seccionJwtInspector');
    const jwtBox = document.getElementById('jwtTokenBox');

    if ((JWT_ACCESS || AUTH_TOKEN) && USER_INFO) {
        badge.textContent = `👤 ${USER_INFO.first_name || USER_INFO.username} (${USER_INFO.rol}) [JWT Activo]`;
        badge.classList.remove('hidden');
        btnIn.classList.add('hidden');
        btnOut.classList.remove('hidden');
        secPed.classList.remove('hidden');
        secJwt.classList.remove('hidden');

        if (['ADMIN', 'COCINA'].includes(USER_INFO.rol)) {
            btnCrear.classList.remove('hidden');
        } else {
            btnCrear.classList.add('hidden');
        }

        if (JWT_ACCESS) {
            const claims = decodificarPayloadJwt(JWT_ACCESS);
            jwtBox.textContent = `Authorization: Bearer ${JWT_ACCESS}\n\nPayload Decodificado:\n${JSON.stringify(claims, null, 2)}`;
        } else {
            jwtBox.textContent = `Authorization: Token ${AUTH_TOKEN}`;
        }

        cargarPedidos();
    } else {
        badge.classList.add('hidden');
        btnIn.classList.remove('hidden');
        btnOut.classList.add('hidden');
        btnCrear.classList.add('hidden');
        secPed.classList.add('hidden');
        secJwt.classList.add('hidden');
    }
}

// ============================================================================
// 3. CONSUMO DE PEDIDOS AUTENTICADO CON JWT (Bearer Token)
// ============================================================================
async function cargarPedidos() {
    if (!JWT_ACCESS && !AUTH_TOKEN) return;
    const tbody = document.getElementById('tablaPedidosBody');
    tbody.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-gray-400">Cargando pedidos vía API con JWT...</td></tr>';

    try {
        const res = await fetch(`${API_BASE}/pedidos/`, {
            headers: { ...getAuthHeader() }
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const lista = data.results || data;

        if (!lista.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-gray-500">No hay pedidos visibles para este rol.</td></tr>';
            return;
        }

        tbody.innerHTML = lista.map(p => `
            <tr class="hover:bg-amber-50/40">
                <td class="py-2 px-3 font-mono font-bold text-cafe">${p.codigo}</td>
                <td class="py-2 px-3">${p.cliente_nombre || p.cliente}</td>
                <td class="py-2 px-3 text-xs text-gray-500">${new Date(p.fecha_entrega).toLocaleDateString('es-CL')}</td>
                <td class="py-2 px-3"><span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">${p.estado_display || p.estado}</span></td>
                <td class="py-2 px-3 font-bold">$${Number(p.total).toLocaleString('es-CL')}</td>
            </tr>
        `).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="py-4 text-center text-red-600">Error cargando pedidos: ${err.message}</td></tr>`;
    }
}

// ============================================================================
// 4. MENSAJERÍA SERVERLESS (FRONTEND -> AWS LAMBDA -> SNS)
// ============================================================================
async function enviarMensajeLambda(e) {
    e.preventDefault();
    const resEl = document.getElementById('lambdaResultado');
    const remitente = document.getElementById('msgRemitente').value.trim();
    const asunto = document.getElementById('msgAsunto').value.trim();
    const mensaje = document.getElementById('msgContenido').value.trim();

    resEl.innerHTML = `<span class="text-gray-600">Enviando evento a AWS Lambda...</span>`;
    try {
        const res = await fetch(`${API_BASE}/mensajeria-sns/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lambda_url: LAMBDA_URL,
                origen: 'frontend',
                tipo: 'CONTACTO_WEB',
                remitente,
                asunto,
                mensaje
            }),
        });
        const data = await res.json();
        if (!res.ok || data.ok === false) throw new Error(data.error || `HTTP ${res.status}`);
        resEl.innerHTML = `<span class="text-green-700 font-semibold">✅ Notificación enviada vía Lambda ➔ SNS (ID: ${data.message_id || 'OK'})</span>`;
        e.target.reset();
    } catch (err) {
        resEl.innerHTML = `<span class="text-red-600 font-semibold">❌ Error al invocar Lambda: ${err.message}</span>`;
    }
}

// ============================================================================
// 5. DEMOSTRACIÓN EN VIVO DE RATE LIMITING (MITIGACIÓN DOS / DDOS)
// ============================================================================
async function probarRateLimit() {
    const log = document.getElementById('rateLimitLog');
    log.innerHTML = 'Iniciando ráfaga de 25 peticiones rápidas hacia la API...\n';
    let okCount = 0;
    let blockedCount = 0;

    const promesas = Array.from({ length: 25 }, async (_, i) => {
        try {
            const res = await fetch(`${API_BASE}/catalogo-publico/?burst=${i}`);
            if (res.status === 429 || res.status === 503) {
                blockedCount++;
                log.innerHTML += `[Req #${i + 1}] 🛑 BLOQUEADA (HTTP ${res.status} - Rate Limit Activo)\n`;
            } else {
                okCount++;
                log.innerHTML += `[Req #${i + 1}] ✅ Permitida (HTTP ${res.status})\n`;
            }
        } catch (err) {
            blockedCount++;
            log.innerHTML += `[Req #${i + 1}] ⚠️ Rechazada por red/throttling (${err.message})\n`;
        }
        log.scrollTop = log.scrollHeight;
    });

    await Promise.all(promesas);
    log.innerHTML += `\n=== RESUMEN: ${okCount} permitidas | ${blockedCount} frenadas por Rate Limit ===`;
    log.scrollTop = log.scrollHeight;
}
