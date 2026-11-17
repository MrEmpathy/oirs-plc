"""E2E-01..E2E-07: recorridos completos en el navegador (Chromium) sobre el entorno Docker:
WordPress de demostración → API firmada → Sistema de Gestión OIRS (Nginx/TLS → Django → PostgreSQL/MongoDB).
Las capturas se guardan en evidencias/es3/capturas/ como evidencia de ejecución (Informe 3)."""
import re
import time

from conftest import OIRS, WP, captura, limpiar_limite_wordpress, nuevo_contexto


def test_e2e01_reclamo_web_hasta_el_cierre(navegador, sesion_oirs):
    """HU01, HU03, HU04 · CU01, CU04, CU05: el ciudadano ingresa un reclamo y el encargado lo gestiona."""
    marca = f"E2E-{int(time.time())}"
    ctx = nuevo_contexto(navegador)
    pg = ctx.new_page()
    pg.goto(f"{WP}/")
    captura(pg, "E2E-01a_portada_wordpress")
    pg.click("text=OIRS en línea")
    pg.check("input[name=tipo][value=RECLAMO]")
    pg.select_option("#oirs-establecimiento", "CESFAM-PLC")
    pg.fill("#oirs-descripcion", f"Esperé tres horas en el SOME sin información sobre la demora ({marca}).")
    pg.fill("#oirs-peticion_concreta", "Informar los tiempos de espera en la sala.")
    pg.fill("#oirs-nombre", "María")
    pg.fill("#oirs-apellidos", "Pérez (dato ficticio)")
    pg.fill("#oirs-email", "maria.perez@example.com")
    pg.check("input[name=autoriza_respuesta_email]")
    pg.check("input[name=acepta_tratamiento_datos]")
    captura(pg, "E2E-01b_formulario_completo")
    pg.click("text=Enviar solicitud")
    folio = pg.locator(".oirs-folio").inner_text().strip()
    assert re.fullmatch(r"PLC-\d{4}-\d{6}", folio)
    assert "Recibirá una respuesta a más tardar" in pg.content()
    captura(pg, "E2E-01c_confirmacion_folio")
    pg.reload()                                       # POST-redirección-GET: recargar no duplica el caso
    assert pg.locator(".oirs-folio").inner_text().strip() == folio
    ctx.close()

    p = sesion_oirs
    p.goto(f"{OIRS}/bandeja?q={folio}")
    assert p.locator(f"a.folio:text('{folio}')").count() == 1
    captura(p, "E2E-01d_bandeja_encargado")
    p.click(f"a.folio:text('{folio}')")
    assert marca in p.content()
    p.click("text=Clasificar y derivar")
    p.select_option("#id_categoria", label="Tiempos de espera")
    p.select_option("#id_unidad", label="SOME")
    p.fill("#id_instrucciones", "Revisar la señalética de tiempos de espera.")
    captura(p, "E2E-01e_dialogo_derivar", completa=False)
    p.click("#m-derivar button[type=submit]")
    assert "Caso derivado a SOME" in p.content()
    p.click("text=Registrar respuesta")
    p.fill("#id_contenido", "Estimada usuaria: se instaló un panel con el tiempo de espera estimado en el SOME.")
    p.select_option("#id_medio", "EMAIL")
    p.click("#m-responder button[type=submit]")
    assert "dentro del plazo legal" in p.content()
    p.click("button:text('Cerrar caso')")
    p.click("text=Sí, cerrar caso")
    assert f"Caso {folio} cerrado" in p.content()
    historial = p.locator(".historial li").all_inner_texts()
    assert [h.split("\n")[1].split(" ·")[0] for h in historial] == ["Ingresado", "En proceso", "Respondido", "Cerrado"]
    captura(p, "E2E-01f_caso_cerrado_historial")


def test_e2e02_validacion_del_formulario_ciudadano(navegador):
    """CU01 alternativo: reclamo sin datos de contacto → errores por campo y ningún caso creado."""
    ctx = nuevo_contexto(navegador)
    pg = ctx.new_page()
    pg.goto(f"{WP}/oirs/")
    pg.check("input[name=tipo][value=RECLAMO]")
    pg.select_option("#oirs-establecimiento", "CESFAM-PLC")
    pg.fill("#oirs-descripcion", "Texto suficiente para describir la situación.")
    pg.click("text=Enviar solicitud")
    assert pg.locator("#oirs-resumen").is_visible()
    assert pg.locator("#oirs-err-nombre").inner_text().startswith("Indique su nombre")
    assert pg.locator("#oirs-nombre").get_attribute("aria-invalid") == "true"
    assert pg.locator("#oirs-descripcion").input_value() == "Texto suficiente para describir la situación."
    assert pg.locator(".oirs-folio").count() == 0
    captura(pg, "E2E-02_formulario_con_errores")
    ctx.close()


def test_e2e03_encuesta_por_qr_y_reporte_de_satisfaccion(navegador, sesion_dsm):
    """HU02, HU08 · CU02, CU08: encuesta anónima con establecimiento preseleccionado y reporte que la integra."""
    sesion_dsm.goto(f"{OIRS}/reportes?desde=2026-01-01&hasta=2026-12-31")
    antes = sesion_dsm.locator("table:has(th:text('Respuestas')) tbody tr td").nth(2)
    n_antes = int(antes.inner_text()) if antes.count() else 0

    ctx = nuevo_contexto(navegador, viewport={"width": 390, "height": 844})
    pg = ctx.new_page()
    pg.goto(f"{WP}/encuesta-de-satisfaccion/?est=CESFAM-PLC")
    assert pg.locator("#oirs-establecimiento").input_value() == "CESFAM-PLC"
    for i, valor in enumerate([6, 5, 7, 6, 6], start=1):
        pg.check(f"input[name=p_p{i}][value='{valor}']", force=True)
    pg.select_option("#oirs-p6", "Dental")
    captura(pg, "E2E-03a_encuesta_movil")
    pg.click("text=Enviar respuesta")
    assert "Gracias por su opinión" in pg.content()
    ctx.close()

    sesion_dsm.goto(f"{OIRS}/reportes?desde=2026-01-01&hasta=2026-12-31")
    celda = sesion_dsm.locator("table:has(th:text('Respuestas')) tbody tr td").nth(2)
    assert int(celda.inner_text()) == n_antes + 1
    sesion_dsm.wait_for_timeout(600)
    captura(sesion_dsm, "E2E-03b_reportes_satisfaccion")


def test_e2e04_panel_de_plazos_y_exportacion_dsm(sesion_dsm):
    """HU05, HU08 · CU06, CU09: panel de la red y exportación CSV sin datos personales."""
    sesion_dsm.goto(f"{OIRS}/plazos")
    assert sesion_dsm.locator("h1").inner_text() == "Panel de plazos de la red"
    captura(sesion_dsm, "E2E-04a_panel_plazos")
    sesion_dsm.goto(f"{OIRS}/reportes?desde=2026-01-01&hasta=2026-12-31")
    with sesion_dsm.expect_download() as descarga:
        sesion_dsm.click("text=Exportar CSV")
    contenido = open(descarga.value.path(), encoding="utf-8").read()
    assert contenido.startswith("folio,tipo,estado,establecimiento") and "@" not in contenido   # sin correos


def test_e2e05_permisos_se_validan_en_el_servidor(sesion_direccion):
    """HU06 · CU07, RNF02: la Dirección no ve acciones de gestión ni accede por URL directa."""
    p = sesion_direccion
    p.goto(f"{OIRS}/bandeja?estado=todos")
    menu = p.locator("nav#menu .menu a").all_inner_texts()
    assert menu == ["Bandeja de casos", "Reportes"]
    respuesta = p.goto(f"{OIRS}/casos/nuevo")
    assert respuesta.status == 403 and "No autorizado" in p.content()
    captura(p, "E2E-05_direccion_403")


def test_e2e06_diseno_adaptable_sin_desplazamiento_horizontal(navegador, sesion_oirs):
    """RNF05/RNF06 (sección 5.4): 390, 820 y 1280 px sin desplazamiento horizontal; tema oscuro."""
    estado = sesion_oirs.context.storage_state()
    for ancho in (390, 820, 1280):
        for esquema in ("light", "dark"):
            ctx = navegador.new_context(ignore_https_errors=True, storage_state=estado, color_scheme=esquema,
                                        viewport={"width": ancho, "height": 900})
            pg = ctx.new_page()
            for url in (f"{OIRS}/bandeja?estado=todos", f"{WP}/oirs/"):
                pg.goto(url)
                assert pg.evaluate("document.documentElement.scrollWidth") <= ancho, f"{url} desborda a {ancho}px"
            if (ancho, esquema) in ((390, "light"), (820, "dark"), (1280, "dark")):
                pg.goto(f"{OIRS}/bandeja?estado=todos")
                captura(pg, f"E2E-06_bandeja_{ancho}px_{esquema}")
            ctx.close()


def test_e2e08_plugin_limita_envios_por_ip(navegador):
    """Amenaza «spam y bots» (Tabla 20): el envío 11 en una hora desde la misma IP se rechaza sin llegar a la API.
    Se usan envíos incompletos (no crean casos); al terminar se limpian los contadores."""
    limpiar_limite_wordpress()
    ctx = nuevo_contexto(navegador)
    pg = ctx.new_page()
    mensajes = []
    for _ in range(11):
        pg.goto(f"{WP}/oirs/")
        pg.check("input[name=tipo][value=SUGERENCIA]")
        pg.click("text=Enviar solicitud")
        mensajes.append(pg.locator("#oirs-resumen strong").inner_text())
    captura(pg, "E2E-08_limite_envios_plugin", completa=False)
    ctx.close()
    limpiar_limite_wordpress()
    assert all(m == "Revise los campos marcados." for m in mensajes[:10])
    assert mensajes[10] == "No fue posible procesar su solicitud. Intente más tarde."


def test_e2e07_nginx_limita_intentos_de_inicio_de_sesion(navegador):
    """PS (sección 7.2): más de 5 intentos por minuto desde una IP reciben 429 en Nginx, antes de Django."""
    ctx = nuevo_contexto(navegador)
    req = ctx.request
    codigos = []
    for _ in range(8):
        r = req.post(f"{OIRS}/api/v1/sesion/iniciar", data={"email": "nadie@dsm.test", "password": "x"})
        codigos.append(r.status)
    ctx.close()
    assert 429 in codigos and codigos.index(429) <= 5, codigos
