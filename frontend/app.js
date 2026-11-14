/**
 * app.js — Frontend Desacoplado de Dulce Arte
 * Consume exclusivamente la API REST del Backend vía API Gateway / CORS + Token Auth
 * e interactúa con AWS Lambda + SNS para mensajería.
 */
'use strict';

let API_BASE = localStorage.getItem('dulcearte_api_url') || 'http://32.196.211.81/api';
let LAMBDA_URL = localStorage.getItem('dulcearte_lambda_url') || '';
let AUTH_TOKEN = localStorage.getItem('dulcearte_token') || '';
let USER_INFO = JSON.parse(localStorage.getItem('dulcearte_user') || 'null');
let CATALOGO_DATA = [];

// Inicialización al cargar el DOM
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('inputApiUrl').value = API_BASE;
    document.getElementById('inputLambdaUrl').value = LAMBDA_URL;
    actualizarUIUsuario();
    cargarCatalogo();
});

function guardarConfig() {
    API_BASE = document.getElementById('inputApiUrl').value.trim().replace(/\/+$/, '');
    LAMBDA_URL = document.getElementById('inputLambdaUrl').value.trim();
    localStorage.setItem('dulcearte_api_url', API_BASE);
    localStorage.setItem('dulcearte_lambda_url', LAMBDA_URL);
    cargarCatalogo();
    if (AUTH_TOKEN) cargarPedidos();
}

function toggleModal(id, show) {
    document.getElementById(id).classList.toggle('hidden', !show);
}

// ============================================================================
// 1. CATÁLOGO PÚBLICO (Consumo GET sin autenticación)
// ============================================================================
async function cargarCatalogo() {
    const statusEl = document.getElementById('apiStatus');
    statusEl.textContent = 'Estado API: Conectando...';
    statusEl.className = 'font-semibold text-amber-700';

    try {
        const res = await fetch(`${API_BASE}/catalogo-publico/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        CATALOGO_DATA = await res.json();

        statusEl.textContent = `Estado API: Conectada (${CATALOGO_DATA.length} productos cargados)`;
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

        return `
        <div class="bg-white rounded-2xl shadow-sm border border-amber-100 overflow-hidden hover:shadow-md transition flex flex-col">
            <img src="${imgUrl}" alt="${p.nombre}" class="h-44 w-full object-cover">
            <div class="p-4 flex-1 flex flex-col justify-between">
                <div>
                    <span class="inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-100 text-cafe mb-2">
                        ${p.categoria_display || p.categoria}
                    </span>
                    <h3 class="font-bold text-lg text-cafe leading-snug">${p.nombre}</h3>
                    <p class="text-xs text-gray-500 mt-1 line-clamp-2">${p.descripcion || 'Elaboración artesanal con ingredientes seleccionados.'}</p>
                </div>
                <div class="mt-4 pt-3 border-t border-amber-50 flex items-center justify-between">
                    <span class="text-lg font-extrabold text-dorado">$${Number(p.precio_base).toLocaleString('es-CL')}</span>
                    <span class="text-xs text-gray-400">⏱ ${p.tiempo_preparacion_min} min</span>
                </div>
            </div>
        </div>`;
    }).join('');
}

// ============================================================================
// 2. AUTENTICACIÓN DESACOPLADA POR TOKEN DRF
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

        AUTH_TOKEN = data.token;
        USER_INFO = data.usuario;
        localStorage.setItem('dulcearte_token', AUTH_TOKEN);
        localStorage.setItem('dulcearte_user', JSON.stringify(USER_INFO));

        toggleModal('modalLogin', false);
        actualizarUIUsuario();
        cargarPedidos();
    } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
    }
}

function cerrarSesion() {
    AUTH_TOKEN = '';
    USER_INFO = null;
    localStorage.removeItem('dulcearte_token');
    localStorage.removeItem('dulcearte_user');
    actualizarUIUsuario();
}

function actualizarUIUsuario() {
    const badge = document.getElementById('userBadge');
    const btnIn = document.getElementById('btnOpenLogin');
    const btnOut = document.getElementById('btnLogout');
    const secPed = document.getElementById('seccionPedidos');

    if (AUTH_TOKEN && USER_INFO) {
        badge.textContent = `👤 ${USER_INFO.first_name || USER_INFO.username} (${USER_INFO.rol})`;
        badge.classList.remove('hidden');
        btnIn.classList.add('hidden');
        btnOut.classList.remove('hidden');
        secPed.classList.remove('hidden');
        cargarPedidos();
    } else {
        badge.classList.add('hidden');
        btnIn.classList.remove('hidden');
        btnOut.classList.add('hidden');
        secPed.classList.add('hidden');
    }
}

// ============================================================================
// 3. CONSUMO DE PEDIDOS AUTENTICADO CON TOKEN
// ============================================================================
async function cargarPedidos() {
    if (!AUTH_TOKEN) return;
    const tbody = document.getElementById('tablaPedidosBody');
    tbody.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-gray-400">Cargando pedidos vía API...</td></tr>';

    try {
        const res = await fetch(`${API_BASE}/pedidos/`, {
            headers: { 'Authorization': `Token ${AUTH_TOKEN}` }
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

    if (!LAMBDA_URL) {
        resEl.innerHTML = `<span class="text-amber-700 font-semibold">⚠️ Configura arriba la URL de tu función AWS Lambda para enviar correos reales vía SNS.</span>`;
        return;
    }

    resEl.innerHTML = `<span class="text-gray-600">Enviando evento a AWS Lambda...</span>`;
    try {
        const res = await fetch(LAMBDA_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ origen: 'frontend', tipo: 'CONTACTO_WEB', remitente, asunto, mensaje }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
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
