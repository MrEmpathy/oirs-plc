"""E2E-09: encuesta de satisfacción servida por Nginx sin WordPress (despliegue/encuesta-demo).
Recorre el mismo flujo que E2E-03, pero la página es estática y la firma HMAC la hace Nginx (njs) en el servidor."""
import re
import ssl
import urllib.request
from pathlib import Path

import pytest
from conftest import ENCUESTA, captura, nuevo_contexto

RAIZ = Path(__file__).resolve().parents[2]


def _encuesta_activa():
    try:
        ca = ssl.create_default_context(cafile=str(RAIZ / "despliegue" / "certs" / "ca.crt"))
        with urllib.request.urlopen(f"{ENCUESTA}/", timeout=3, context=ca) as r:   # noqa: S310 (URL local de pruebas)
            return r.status == 200
    except OSError:
        return False


# El servicio es opcional (scripts/instalar.sh --sin-encuesta): si no está levantado, la prueba se omite.
pytestmark = pytest.mark.skipif(not _encuesta_activa(), reason="encuesta de demostración no levantada")


def _secreto():
    texto = (RAIZ / ".env").read_text(encoding="utf-8")
    return re.search(r"^WP_HMAC_SECRET=(.+)$", texto, re.M).group(1).strip()


def test_e2e09_encuesta_sin_wordpress_servida_por_nginx(navegador):
    """HU02 · CU02: el ciudadano responde la encuesta desde la página estática; la respuesta llega a la API."""
    ctx = nuevo_contexto(navegador)
    pg = ctx.new_page()
    respuesta = pg.goto(f"{ENCUESTA}/?est=CESFAM-PUL")             # QR del establecimiento
    assert "script-src 'self'" in respuesta.headers["content-security-policy"]
    pg.wait_for_selector("form[data-oirs-form=encuesta]")
    assert pg.input_value("#oirs-establecimiento") == "CESFAM-PUL"
    assert pg.locator("fieldset.oirs-escala").count() >= 5         # preguntas leídas de la versión activa

    pg.click("text=Enviar respuesta")                              # sin responder: validación accesible
    assert pg.locator("#oirs-resumen").is_visible()
    assert pg.locator("fieldset[aria-invalid=true]").count() >= 5
    captura(pg, "E2E-09a_encuesta_nginx_errores")

    for fs in pg.locator("fieldset.oirs-escala").all():
        fs.locator(".oirs-escala__opcion").nth(5).click()          # nota 6
    pg.select_option("select[name=p_p6]", "Dental")
    pg.fill("#oirs-comentario", "Encuesta respondida desde la demostración sin WordPress (E2E-09).")
    captura(pg, "E2E-09b_encuesta_nginx_completa")
    with pg.expect_response("**/api/respuestas") as envio:
        pg.click("text=Enviar respuesta")
    assert envio.value.status == 201
    assert pg.locator(".oirs-confirmacion").inner_text().startswith("¡Gracias por su opinión!")
    captura(pg, "E2E-09c_encuesta_nginx_gracias")

    for ruta in ("/", "/encuesta.js", "/api/encuesta", "/api/catalogos"):   # el secreto nunca llega al navegador
        assert _secreto() not in pg.request.get(f"{ENCUESTA}{ruta}").text()
    ctx.close()

    movil = nuevo_contexto(navegador, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pm = movil.new_page()
    pm.goto(f"{ENCUESTA}/?est=CESFAM-PLC")
    pm.wait_for_selector("form[data-oirs-form=encuesta]")
    assert pm.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    captura(pm, "E2E-09d_encuesta_nginx_movil")
    movil.close()
