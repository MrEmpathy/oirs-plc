// Intermediario firmado para la encuesta de demostración (njs, se ejecuta dentro de Nginx).
// Equivale a includes/api.php y includes/encuesta.php del plugin: firma HMAC-SHA256("<ts>.<cuerpo>") con el
// secreto compartido, filtra lo que se envía y devuelve al navegador solo lo necesario.
import crypto from 'crypto';

const API = (process.env.OIRS_API_URL || 'https://nginx/').replace(/\/?$/, '/') + 'api/v1/publico/';
const ENCUESTA = 'satisfaccion-usuaria';
const JSON_UTF8 = 'application/json; charset=utf-8';

function responder(r, codigo, datos) {
    r.headersOut['Content-Type'] = JSON_UTF8;
    r.headersOut['Cache-Control'] = 'no-store';
    r.return(codigo, JSON.stringify(datos));
}

async function llamarApi(metodo, ruta, cuerpo) {
    const secreto = process.env.OIRS_HMAC_SECRET || '';
    if (!secreto) {
        throw new Error('OIRS_HMAC_SECRET no definido');
    }
    const ts = String(Math.floor(Date.now() / 1000));
    const firma = crypto.createHmac('sha256', secreto).update(ts + '.' + cuerpo).digest('hex');
    const opciones = {
        method: metodo,
        headers: { 'Accept': 'application/json', 'X-OIRS-Timestamp': ts, 'X-OIRS-Firma': firma },
    };
    if (metodo === 'POST') {
        opciones.headers['Content-Type'] = 'application/json';
        opciones.body = cuerpo;
    }
    const resp = await ngx.fetch(API + ruta, opciones);
    const texto = await resp.text();
    let datos = {};
    try { datos = JSON.parse(texto); } catch (e) { datos = {}; }
    return { codigo: resp.status, datos: datos };
}

function noDisponible(r, e) {
    ngx.log(ngx.ERR, 'API OIRS no disponible: ' + e.message);   // sin contexto de petición: no registra la IP
    responder(r, 502, { error: 'El servicio no está disponible en este momento. Intente más tarde.' });
}

function soloMetodo(r, metodo) {
    if (r.method !== metodo) {
        r.headersOut['Allow'] = metodo;
        responder(r, 405, { error: 'Método no permitido' });
        return false;
    }
    return true;
}

/** Establecimientos activos (sin el DSM, que no atiende público). No expone el resto del catálogo. */
async function catalogos(r) {
    if (!soloMetodo(r, 'GET')) { return; }
    try {
        const res = await llamarApi('GET', 'catalogos', '');
        if (res.codigo !== 200) { return responder(r, 502, { error: 'Catálogo no disponible' }); }
        const lista = (res.datos.establecimientos || [])
            .filter((e) => e && e.codigo && e.codigo !== 'DSM')
            .map((e) => ({ codigo: String(e.codigo), nombre: String(e.nombre) }));
        responder(r, 200, { establecimientos: lista });
    } catch (e) { noDisponible(r, e); }
}

/** Preguntas de la versión activa: la página las dibuja sin tenerlas escritas en su código. */
async function definicion(r) {
    if (!soloMetodo(r, 'GET')) { return; }
    try {
        const res = await llamarApi('GET', 'encuestas/' + ENCUESTA, '');
        if (res.codigo !== 200) { return responder(r, 503, { error: 'La encuesta no está disponible en este momento.' }); }
        const d = res.datos;
        responder(r, 200, { nombre: d.nombre, version: d.version, preguntas: d.preguntas || [] });
    } catch (e) { noDisponible(r, e); }
}

/** Registra una respuesta anónima: solo establecimiento, respuestas y comentario (sin IP ni datos personales). */
async function responder_(r) {
    if (!soloMetodo(r, 'POST')) { return; }
    if (r.headersIn['Sec-Fetch-Site'] === 'cross-site') {          // envíos desde otros sitios
        return responder(r, 403, { error: 'Origen no permitido' });
    }
    let entrada;
    try { entrada = JSON.parse(r.requestText || ''); } catch (e) { entrada = null; }
    if (!entrada || typeof entrada !== 'object' || Array.isArray(entrada)) {
        return responder(r, 400, { error: 'Solicitud inválida' });
    }
    if (entrada.web) {                                              // trampa para bots (honeypot)
        return responder(r, 400, { error: 'No fue posible registrar su respuesta. Intente más tarde.' });
    }
    const respuestas = {};
    if (entrada.respuestas && typeof entrada.respuestas === 'object' && !Array.isArray(entrada.respuestas)) {
        Object.keys(entrada.respuestas).slice(0, 50).forEach((k) => {
            const v = entrada.respuestas[k];
            if (typeof v === 'number' || typeof v === 'string') { respuestas[String(k)] = v; }
        });
    }
    const cuerpo = JSON.stringify({
        establecimiento: String(entrada.establecimiento || ''),
        respuestas: respuestas,
        comentario: String(entrada.comentario || '').slice(0, 1000),
    });
    try {
        const res = await llamarApi('POST', 'encuestas/' + ENCUESTA + '/respuestas', cuerpo);
        if (res.codigo === 201) { return responder(r, 201, { ok: true }); }
        if (res.codigo === 401) {
            return responder(r, 502, { error: 'No fue posible verificar el origen de la solicitud. Avise al administrador del sitio.' });
        }
        const detalle = [].concat(res.datos.detalle || res.datos.error || []).map(String);
        responder(r, res.codigo >= 500 ? 502 : 400, { error: 'No fue posible registrar su respuesta.', detalle: detalle });
    } catch (e) { noDisponible(r, e); }
}

export default { catalogos, definicion, responder: responder_ };
