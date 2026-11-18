"""Genera los diagramas del Informe 3 como SVG (sin dependencias externas) y, si Playwright está disponible,
los convierte a PNG. Uso: .venv/bin/python docs/es3/diagramas/generar_diagramas.py

- modelo_datos.svg: esquema implementado (PostgreSQL 16 + colecciones de MongoDB 7), tomado de los modelos
  de Django y de apps/core/documental.py.
- arquitectura.svg: componentes desplegados con Docker Compose y canales de comunicación."""
from html import escape
from pathlib import Path

AQUI = Path(__file__).resolve().parent
AZUL, AZUL_OSC, TITULO, TEXTO, SUAVE, BORDE = "#046bd2", "#045cb4", "#1e293b", "#334155", "#f0f5fa", "#d1d5db"
VERDE, VERDE_SUAVE = "#146c43", "#eaf6ef"
FUENTE = "font-family='Arial, Helvetica, sans-serif'"

# ---------------------------------------------------------------- modelo de datos
ANCHO, CAB, FILA = 350, 32, 21


class Caja:
    def __init__(self, nombre, x, y, columnas, mongo=False, nota=""):
        self.nombre, self.x, self.y, self.columnas, self.mongo, self.nota = nombre, x, y, columnas, mongo, nota
        self.alto = CAB + FILA * len(columnas) + 8 + (FILA if nota else 0)

    def svg(self):
        color = VERDE if self.mongo else AZUL
        fondo = VERDE_SUAVE if self.mongo else SUAVE
        trazo = "stroke-dasharray='6 4'" if self.mongo else ""
        s = [f"<rect x='{self.x}' y='{self.y}' width='{ANCHO}' height='{self.alto}' rx='8' fill='#fff' "
             f"stroke='{color}' stroke-width='1.6' {trazo}/>",
             f"<path d='M{self.x} {self.y + 8} a8 8 0 0 1 8 -8 h{ANCHO - 16} a8 8 0 0 1 8 8 v{CAB - 8} h-{ANCHO} z' "
             f"fill='{color}'/>",
             f"<text x='{self.x + 12}' y='{self.y + 21}' fill='#fff' font-weight='bold' font-size='14' {FUENTE}>"
             f"{escape(self.nombre)}</text>"]
        for i, (col, tipo, marca) in enumerate(self.columnas):
            y = self.y + CAB + 16 + i * FILA
            if i % 2:
                s.append(f"<rect x='{self.x + 1}' y='{y - 15}' width='{ANCHO - 2}' height='{FILA}' fill='{fondo}'/>")
            peso = "bold" if "PK" in marca else "normal"
            s.append(f"<text x='{self.x + 12}' y='{y}' font-size='12.5' fill='{TITULO}' font-weight='{peso}' {FUENTE}>"
                     f"{escape(col)}</text>")
            s.append(f"<text x='{self.x + 172}' y='{y}' font-size='11.5' fill='{TEXTO}' {FUENTE}>{escape(tipo)}</text>")
            if marca:
                s.append(f"<text x='{self.x + ANCHO - 10}' y='{y}' font-size='11' text-anchor='end' fill='{color}' "
                         f"font-weight='bold' {FUENTE}>{escape(marca)}</text>")
        if self.nota:
            y = self.y + self.alto - 10
            s.append(f"<text x='{self.x + 12}' y='{y}' font-size='11.5' font-style='italic' fill='{TEXTO}' {FUENTE}>"
                     f"{escape(self.nota)}</text>")
        return "\n".join(s)


def ruta(puntos, etq_a="1", etq_b="N", discontinua=False, texto="", pos_texto=None):
    """Conector ortogonal con ruta explícita (cada uno con su propio corredor) y cardinalidad en los extremos."""
    color = VERDE if discontinua else TEXTO
    trazo = "stroke-dasharray='6 4'" if discontinua else ""
    d = "M" + " L".join(f"{x} {y}" for x, y in puntos)
    s = [f"<path d='{d}' fill='none' stroke='{color}' stroke-width='1.4' {trazo}/>"]

    def etiqueta(p, q, t):
        dx, dy = (q[0] > p[0]) - (q[0] < p[0]), (q[1] > p[1]) - (q[1] < p[1])
        if dx:   # tramo horizontal: sobre la línea
            x, y, ancla = p[0] + 7 * dx, p[1] - 6, "start" if dx > 0 else "end"
        else:    # tramo vertical: a la derecha de la línea
            x, y, ancla = p[0] + 7, p[1] + (16 if dy > 0 else -7), "start"
        return (f"<text x='{x}' y='{y}' font-size='12' font-weight='bold' fill='{color}' text-anchor='{ancla}' "
                f"{FUENTE}>{t}</text>")
    s.append(etiqueta(puntos[0], puntos[1], etq_a))
    s.append(etiqueta(puntos[-1], puntos[-2], etq_b))
    if texto:
        tx, ty = pos_texto
        s.append(f"<text x='{tx}' y='{ty}' font-size='11.5' fill='{color}' font-style='italic' {FUENTE}>"
                 f"{escape(texto)}</text>")
    return "\n".join(s)


def modelo_datos():
    c = [30, 470, 910, 1350, 1800]
    est = Caja("establecimiento", c[0], 70, [("id", "bigint", "PK"), ("codigo", "varchar(12)", "UK"),
               ("nombre", "varchar(120)", "UK"), ("tipo", "CESFAM, SAPU, PSR…", ""), ("activo", "boolean", "")])
    usu = Caja("usuario", c[0], 420, [("id", "bigint", "PK"), ("email", "varchar", "UK"),
               ("rol", "ADMIN, OIRS_DSM, …", "CHECK"), ("establecimiento_id", "→ establecimiento", "FK"),
               ("intentos_fallidos", "smallint ≥ 0", "CHECK"), ("bloqueado_hasta", "timestamptz", ""),
               ("mfa_secreto", "varchar(64)", ""), ("debe_cambiar_clave", "boolean", ""),
               ("password", "Argon2id", "")], nota="CHECK: OIRS_EST y Dirección exigen establecimiento")
    sol = Caja("solicitante", c[0], 760, [("id", "bigint", "PK"), ("nombre, apellidos", "varchar(80)", ""),
               ("email", "varchar", ""), ("telefono", "varchar(15)", ""), ("edad", "smallint 0..120", "CHECK"),
               ("autoriza_resp_correo", "boolean", ""), ("anonimizado", "boolean", "")],
               nota="CHECK: respuesta por correo exige correo o teléfono")
    uni = Caja("unidad", c[1], 70, [("id", "bigint", "PK"), ("establecimiento_id", "→ establecimiento", "FK"),
               ("nombre", "varchar(120)", "UK*"), ("responsable_id", "→ usuario", "FK"), ("activa", "boolean", "")],
               nota="* único por establecimiento")
    req = Caja("requerimiento", c[1], 330, [("id", "bigint", "PK"), ("folio", "PLC-AAAA-NNNNNN", "UK"),
               ("tipo", "RECLAMO, SUGERENCIA…", ""), ("canal", "WEB, PRESENCIAL", ""),
               ("establecimiento_id", "→ establecimiento", "FK"), ("categoria_id", "→ categoria", "FK"),
               ("solicitante_id", "→ solicitante", "FK"), ("unidad_derivada_id", "→ unidad", "FK"),
               ("creado_por_id", "→ usuario", "FK"), ("descripcion", "text (10..4000)", "NN"),
               ("fecha_ingreso", "timestamptz", ""), ("fecha_vencimiento", "date ≥ ingreso", "CHECK"),
               ("estado", "INGRESADO…CERRADO", "")],
               nota="Índices: (establecimiento, estado), vencimiento, ingreso")
    corr = Caja("correlativo_folio", c[3], 200, [("anio", "smallint", "PK"), ("ultimo", "integer", "")],
                nota="SELECT … FOR UPDATE: folio sin duplicados")
    cat = Caja("categoria", c[2], 70, [("id", "bigint", "PK"), ("nombre", "varchar(80)", "UK"),
               ("es_otro", "boolean", "UK*"), ("activa", "boolean", "")], nota="* una sola categoría «Otro»")
    der = Caja("derivacion", c[2], 290, [("id", "bigint", "PK"), ("requerimiento_id", "→ requerimiento", "FK"),
               ("unidad_id", "→ unidad", "FK"), ("derivado_por_id", "→ usuario", "FK"),
               ("instrucciones", "text", ""), ("fecha", "timestamptz", "")])
    res = Caja("respuesta", c[2], 480, [("id", "bigint", "PK"), ("requerimiento_id", "→ requerimiento", "FK UK"),
               ("contenido", "text (20..6000)", ""), ("medio", "EMAIL, CARTA…", ""),
               ("fecha_emision", "date", ""), ("dentro_plazo", "boolean", ""), ("registrado_por_id", "→ usuario", "FK")])
    his = Caja("historial_estado", c[2], 700, [("id", "bigint", "PK"), ("requerimiento_id", "→ requerimiento", "FK"),
               ("estado_anterior", "varchar", ""), ("estado_nuevo", "varchar", ""), ("accion", "varchar(30)", ""),
               ("usuario_id", "→ usuario", "FK"), ("fecha", "timestamptz", "")],
               nota="Solo inserción: trigger + sin UPDATE/DELETE (RNF07)")
    fer = Caja("feriado", c[3], 70, [("fecha", "date", "PK"), ("descripcion", "varchar(120)", "")],
               nota="Calendario para días hábiles")
    enc = Caja("encuesta", c[3], 360, [("id", "bigint", "PK"), ("codigo", "slug", "UK*"),
               ("version", "smallint ≥ 1", "UK*"), ("nombre", "varchar(120)", ""), ("activa", "boolean", "UK**")],
               nota="* (codigo, version)  ** una versión activa")
    defn = Caja("encuesta_definiciones", c[4], 360, [("encuesta_id", "int", "único"), ("preguntas", "array", ""),
                ("escala", "1..7", "")], mongo=True)
    renc = Caja("respuestas_encuesta", c[4], 520, [("encuesta_id", "int", "idx*"), ("establecimiento_id", "int", "idx*"),
                ("fecha", "AAAA-MM-DD", "idx*"), ("canal", "WEB", ""), ("respuestas", "{p1: 1..7, …}", ""),
                ("comentario", "string", "")], mongo=True, nota="* índice compuesto · sin IP ni hora")
    bit = Caja("bitacora_auditoria", c[4], 760, [("ts", "fecha", "TTL 730 d"), ("accion", "string", ""),
               ("folio", "string", "idx"), ("usuario_id, rol", "int, string", ""), ("red_origen", "IP /24", ""),
               ("detalle", "objeto", "")], mongo=True, nota="Sin datos personales del solicitante")

    cajas = [est, usu, sol, uni, req, corr, cat, der, res, his, fer, enc, defn, renc, bit]
    der_ = lambda b: b.x + ANCHO                                   # borde derecho
    lineas = [
        ruta([(der_(est), 150), (uni.x, 150)]),                                         # establecimiento → unidad
        ruta([(est.x + 175, est.y + est.alto), (est.x + 175, usu.y)]),                   # → usuario
        ruta([(der_(est), 210), (425, 210), (425, req.y + 110), (req.x, req.y + 110)]),  # → requerimiento
        ruta([(der_(sol), sol.y + 60), (445, sol.y + 60), (445, req.y + 250), (req.x, req.y + 250)]),
        ruta([(uni.x + 175, uni.y + uni.alto), (uni.x + 175, req.y)], texto="derivado a",
             pos_texto=(uni.x + 185, (uni.y + uni.alto + req.y) / 2 + 4)),
        ruta([(cat.x, 150), (865, 150), (865, req.y + 16), (der_(req), req.y + 16)]),    # categoria → requerimiento
        ruta([(der_(req), 400), (der.x, 400)]),                                          # → derivacion
        ruta([(der_(req), 570), (res.x, 570)], "1", "0..1"),                             # → respuesta (1:1)
        ruta([(der_(req), req.y + req.alto - 30), (885, req.y + req.alto - 30), (885, his.y + 60), (his.x, his.y + 60)]),
        ruta([(der_(enc), enc.y + 50), (defn.x, enc.y + 50)], "1", "1", True),          # encuesta → definiciones
        ruta([(der_(enc), enc.y + 120), (1765, enc.y + 120), (1765, renc.y + 60), (renc.x, renc.y + 60)], "1", "N", True),
        ruta([(req.x + 175, req.y + req.alto), (req.x + 175, 985), (1775, 985), (1775, bit.y + 100), (bit.x, bit.y + 100)],
             "1", "N", True, "referencia por folio", (1000, 979)),
    ]
    ancho, alto = c[4] + ANCHO + 30, 1010
    grupo_mongo = (f"<rect x='{c[4] - 18}' y='308' width='{ANCHO + 36}' height='{alto - 340}' rx='12' fill='none' "
                   f"stroke='{VERDE}' stroke-dasharray='4 4'/>"
                   f"<text x='{c[4] - 4}' y='332' font-size='14' font-weight='bold' fill='{VERDE}' {FUENTE}>"
                   f"MongoDB 7 · base documental</text>")
    grupo_pg = (f"<text x='{c[0]}' y='42' font-size='14' font-weight='bold' fill='{AZUL_OSC}' {FUENTE}>"
                f"PostgreSQL 16 · base estructurada (3FN)</text>")
    leyenda = (f"<text x='{c[3]}' y='{alto - 150}' font-size='12' fill='{TEXTO}' {FUENTE}>"
               f"PK clave primaria · FK clave foránea · UK única · NN no nulo</text>"
               f"<text x='{c[3]}' y='{alto - 130}' font-size='12' fill='{TEXTO}' {FUENTE}>"
               f"Línea continua: FK en PostgreSQL · discontinua: referencia lógica</text>"
               f"<text x='{c[3]}' y='{alto - 110}' font-size='12' fill='{TEXTO}' {FUENTE}>"
               f"entre bases, verificada con «verificar_referencias»</text>")
    cuerpo = "\n".join([grupo_pg, grupo_mongo] + lineas + [x.svg() for x in cajas] + [leyenda])
    return ancho, alto, cuerpo


# ---------------------------------------------------------------- arquitectura
def nodo(x, y, w, h, titulo, lineas, color=AZUL, fondo="#fff", cilindro=False, discontinuo=False):
    trazo = "stroke-dasharray='6 4'" if discontinuo else ""
    if cilindro:
        s = [f"<path d='M{x} {y + 10} v{h - 20} a{w / 2} 10 0 0 0 {w} 0 v-{h - 20}' fill='{fondo}' stroke='{color}' stroke-width='1.6'/>",
             f"<ellipse cx='{x + w / 2}' cy='{y + 10}' rx='{w / 2}' ry='10' fill='{fondo}' stroke='{color}' stroke-width='1.6'/>"]
        ty = y + 36
    else:
        s = [f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='10' fill='{fondo}' stroke='{color}' stroke-width='1.6' {trazo}/>"]
        ty = y + 24
    s.append(f"<text x='{x + w / 2}' y='{ty}' text-anchor='middle' font-size='14' font-weight='bold' fill='{TITULO}' {FUENTE}>{escape(titulo)}</text>")
    for i, l in enumerate(lineas):
        s.append(f"<text x='{x + w / 2}' y='{ty + 20 + i * 17}' text-anchor='middle' font-size='12' fill='{TEXTO}' {FUENTE}>{escape(l)}</text>")
    return "\n".join(s)


def flecha(puntos, texto="", color=TEXTO, discontinua=False, pos_texto=None, ancla="middle"):
    d = "M" + " L".join(f"{x} {y}" for x, y in puntos)
    trazo = "stroke-dasharray='6 4'" if discontinua else ""
    s = [f"<path d='{d}' fill='none' stroke='{color}' stroke-width='1.6' marker-end='url(#punta)' {trazo}/>"]
    if texto:
        tx, ty = pos_texto or ((puntos[0][0] + puntos[-1][0]) / 2, (puntos[0][1] + puntos[-1][1]) / 2 - 8)
        for i, linea in enumerate(texto.split("\n")):
            s.append(f"<text x='{tx}' y='{ty + i * 15}' text-anchor='{ancla}' font-size='11.5' fill='{color}' {FUENTE}>{escape(linea)}</text>")
    return "\n".join(s)


def arquitectura():
    s = []
    # Zonas
    s.append(f"<rect x='300' y='20' width='1080' height='680' rx='14' fill='#fafcff' stroke='{BORDE}'/>")
    s.append(f"<text x='320' y='46' font-size='14' font-weight='bold' fill='{AZUL_OSC}' {FUENTE}>Servidor · Docker Compose (Linux x86-64 o arm64)</text>")
    s.append(f"<rect x='330' y='440' width='400' height='240' rx='12' fill='none' stroke='{BORDE}' stroke-dasharray='5 4'/>")
    s.append(f"<text x='345' y='670' font-size='12' fill='{TEXTO}' {FUENTE}>red «wp» (interna)</text>")
    s.append(f"<rect x='860' y='300' width='500' height='380' rx='12' fill='none' stroke='{BORDE}' stroke-dasharray='5 4'/>")
    s.append(f"<text x='875' y='670' font-size='12' fill='{TEXTO}' {FUENTE}>red «datos» (interna, sin salida a Internet)</text>")
    # Usuarios
    s.append(nodo(20, 90, 230, 90, "Usuario de la red", ["sin cuenta · navegador o móvil", "QR por establecimiento"], fondo=SUAVE))
    s.append(nodo(20, 470, 230, 90, "Funcionarios", ["4 perfiles · sesión + 2FA", "(Admin, OIRS DSM, OIRS est.,", "Dirección)"], fondo=SUAVE))
    # Nginx, encuesta y WordPress
    s.append(nodo(380, 90, 320, 150, "Nginx 1.27 (proxy inverso)", ["TLS 1.2/1.3 · HSTS", ":8443 sistema · :8080 sitio web",
                                                               "límite: 5 inicios de sesión/min por IP", "único punto expuesto"], color=AZUL_OSC))
    s.append(nodo(380, 300, 190, 90, "encuesta (opcional)", ["Nginx + njs · :8082", "página estática"], discontinuo=True))
    s.append(nodo(360, 470, 350, 80, "WordPress 6.9 + plugin DSM OIRS", ["PHP 8.3 · formularios y encuesta", "límite 10 envíos/h por IP"]))
    s.append(nodo(465, 575, 140, 60, "MariaDB 11.4", [], cilindro=True))
    # Aplicación y datos
    s.append(nodo(880, 90, 470, 160, "Sistema de Gestión OIRS", ["Django 5.2 LTS + gunicorn (Python 3.13)",
                                                              "cuentas · requerimientos · encuestas · reportes",
                                                              "catalogos · auditoria · web (front) · integracion (API)",
                                                              "usuario sin privilegios (uid 10001)"], color=AZUL_OSC))
    s.append(nodo(880, 330, 145, 120, "PostgreSQL 16", ["casos, usuarios,", "catálogos (3FN)"], cilindro=True))
    s.append(nodo(1045, 330, 145, 120, "MongoDB 7", ["encuestas,", "bitácora (TTL)"], cilindro=True, color=VERDE))
    s.append(nodo(1210, 330, 130, 120, "Redis 7", ["caché de", "indicadores"], cilindro=True, color=TEXTO))
    s.append(nodo(880, 530, 460, 90, "Operación (anfitrión)", ["respaldo.sh: PostgreSQL + MongoDB cifrados (AES-256)",
                                                            "anonimización y verificación de referencias diarias"], fondo=SUAVE, color=TEXTO))
    # Flujos
    s.append(flecha([(250, 130), (380, 130)], "HTTPS", pos_texto=(315, 122)))
    s.append(flecha([(250, 160), (320, 160), (320, 345), (380, 345)], "HTTPS", discontinua=True, pos_texto=(350, 337)))
    s.append(flecha([(250, 515), (290, 515), (290, 210), (380, 210)], "HTTPS", pos_texto=(270, 507)))
    s.append(flecha([(610, 240), (610, 470)], ":8080", pos_texto=(603, 455), ancla="end"))
    s.append(flecha([(680, 470), (680, 240)], "HTTPS + HMAC-SHA256\n/api/v1/publico", color=AZUL_OSC, pos_texto=(690, 330), ancla="start"))
    s.append(flecha([(475, 300), (475, 240)], "HMAC", color=AZUL_OSC, discontinua=True, pos_texto=(483, 275), ancla="start"))
    s.append(flecha([(535, 550), (535, 575)]))
    s.append(flecha([(700, 160), (880, 160)], "HTTP interno (red «web»)", pos_texto=(790, 150)))
    s.append(flecha([(950, 250), (950, 330)]))
    s.append(flecha([(1115, 250), (1115, 330)]))
    s.append(flecha([(1275, 250), (1275, 330)]))
    s.append(flecha([(950, 530), (950, 452)], color=TEXTO, discontinua=True))
    s.append(flecha([(1115, 530), (1115, 452)], color=TEXTO, discontinua=True))
    return 1400, 720, "\n".join(s)


def svg(ancho, alto, cuerpo):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{ancho}' height='{alto}' viewBox='0 0 {ancho} {alto}'>"
            f"<defs><marker id='punta' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='8' markerHeight='8' "
            f"orient='auto-start-reverse'><path d='M0 0 L10 5 L0 10 z' fill='{TEXTO}'/></marker></defs>"
            f"<rect width='100%' height='100%' fill='#fff'/>{cuerpo}</svg>")


if __name__ == "__main__":
    salidas = {"modelo_datos": svg(*modelo_datos()), "arquitectura": svg(*arquitectura())}
    for nombre, contenido in salidas.items():
        (AQUI / f"{nombre}.svg").write_text(contenido, encoding="utf-8")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SVG generados (Playwright no disponible: sin PNG)")
        raise SystemExit
    with sync_playwright() as p:
        nav = p.chromium.launch()
        for nombre, contenido in salidas.items():
            pg = nav.new_page(device_scale_factor=2)
            pg.set_content(f"<html><body style='margin:0'>{contenido}</body></html>")
            pg.locator("svg").screenshot(path=str(AQUI / f"{nombre}.png"))
            print(AQUI / f"{nombre}.png")
        nav.close()
