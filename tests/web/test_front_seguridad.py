"""PS-21..PS-32: controles de seguridad del front administrativo (sección 7). Cada prueba intenta la acción
no autorizada directamente contra el servidor: ocultar un botón no basta (Guía ES3, indicador 3.1.3.5)."""
import re
from pathlib import Path

import pyotp
import pytest
from django.core import mail
from django.test import Client

from apps.cuentas.models import Usuario
from tests.conftest import CLAVE, crear_caso, login

pytestmark = [pytest.mark.seguridad, pytest.mark.django_db]


def _ingresar(client, email, clave=CLAVE, **extra):
    return client.post("/ingresar" + extra.pop("qs", ""), {"email": email, "password": clave}, **extra)


def test_ps21_contrasena_temporal_obliga_a_cambiarla_antes_de_usar_el_sistema(client, catalogo, usuarios):
    u = usuarios["oirs_plc"]
    u.debe_cambiar_clave = True
    u.save()
    _ingresar(client, u.email)
    assert client.get("/bandeja").url == "/cuenta/clave"            # bloqueado hasta cambiarla
    r = client.post("/cuenta/clave", {"actual": CLAVE, "nueva": "corta", "repetir": "corta"})
    assert "al menos 12" in r.content.decode() or "12" in r.content.decode()
    nueva = "Nueva#Clave2026!"
    client.post("/cuenta/clave", {"actual": CLAVE, "nueva": nueva, "repetir": nueva})
    u.refresh_from_db()
    assert not u.debe_cambiar_clave and u.check_password(nueva)
    assert client.get("/bandeja").status_code == 200


def test_ps22_segundo_factor_obligatorio_en_el_front(client, catalogo, usuarios, mdb):
    dsm = usuarios["dsm"]
    r = _ingresar(client, dsm.email)
    assert r.url == "/ingresar/verificar"
    assert client.get("/plazos").status_code == 302                  # sin el código aún no hay sesión
    r = client.post("/ingresar/verificar", {"codigo": "000000"})
    assert "Código de verificación inválido" in r.content.decode()
    dsm.refresh_from_db()
    assert dsm.intentos_fallidos == 1                               # el código erróneo cuenta como intento
    client.post("/ingresar/verificar", {"codigo": pyotp.TOTP(dsm.mfa_secreto).now()})
    assert client.get("/plazos").status_code == 200
    assert mdb.bitacora_auditoria.count_documents({"accion": "MFA_FALLIDO", "usuario_id": dsm.id}) == 1


def test_ps23_enrolamiento_mfa_solo_guarda_el_secreto_tras_un_codigo_valido(client, catalogo, usuarios):
    admin = usuarios["admin"]
    admin.mfa_secreto = ""
    admin.save()
    r = _ingresar(client, admin.email)
    assert r.url == "/ingresar/segundo-factor"
    r = client.get(r.url)
    assert b"<svg" in r.content                                     # QR generado en el servidor (sin servicios externos)
    # DEF-15: con width/height fijos el CSS recortaba el QR y no se podía escanear; debe escalar con su viewBox.
    assert re.search(rb"<svg[^>]*viewBox=", r.content) and not re.search(rb"<svg[^>]*\swidth=", r.content)
    secreto = client.session["mfa_nuevo"]
    client.post("/ingresar/segundo-factor", {"codigo": "123456"})
    admin.refresh_from_db()
    assert admin.mfa_secreto == ""
    client.post("/ingresar/segundo-factor", {"codigo": pyotp.TOTP(secreto).now()})
    admin.refresh_from_db()
    assert admin.mfa_secreto == secreto and client.get("/usuarios").status_code == 200


def test_ps24_menu_y_servidor_aplican_la_misma_matriz_de_permisos(client, catalogo, usuarios, mdb):
    login(client, usuarios["dir_plc"])
    r = client.get("/bandeja")
    menu = [o["clave"] for o in r.context["menu"]]
    assert menu == ["bandeja", "reportes"]
    assert client.get("/casos/nuevo").status_code == 403            # acceso directo por URL
    assert client.get("/usuarios").status_code == 403
    assert mdb.bitacora_auditoria.count_documents({"accion": "ACCESO_DENEGADO", "usuario_id": usuarios["dir_plc"].id}) == 2


def test_ps25_idor_en_el_front_responde_404(anon, client, catalogo, usuarios):
    req = crear_caso(anon)
    login(client, usuarios["oirs_pul"])
    assert client.get(f"/casos/{req.folio}").status_code == 404
    assert client.post(f"/casos/{req.folio}/cerrar").status_code == 404


def test_ps26_direccion_no_puede_derivar_aunque_envie_el_formulario(anon, client, catalogo, usuarios):
    req = crear_caso(anon)
    login(client, usuarios["dir_plc"])
    assert b"Clasificar y derivar" not in client.get(f"/casos/{req.folio}").content
    r = client.post(f"/casos/{req.folio}/derivar", {"categoria": catalogo["cat"].id, "unidad": catalogo["u_plc"].id})
    req.refresh_from_db()
    assert r.status_code == 403 and req.estado == "INGRESADO"


def test_ps27_formularios_del_front_exigen_token_csrf(anon, catalogo, usuarios):
    req = crear_caso(anon)
    c = Client(enforce_csrf_checks=True)
    login(c, usuarios["oirs_plc"])
    r = c.post(f"/casos/{req.folio}/derivar", {"categoria": catalogo["cat"].id, "unidad": catalogo["u_plc"].id})
    req.refresh_from_db()
    assert r.status_code == 403 and req.estado == "INGRESADO"


def test_ps28_no_hay_redireccion_abierta_tras_el_ingreso(client, catalogo, usuarios):
    r = _ingresar(client, usuarios["oirs_plc"].email, qs="?next=https://sitio-malicioso.example/robo")
    assert r.status_code == 302 and r.url == "/bandeja"
    c2 = Client()
    r = _ingresar(c2, usuarios["oirs_plc"].email, qs="?next=/reportes")
    assert r.url == "/reportes"


def test_ps29_administracion_de_usuarios_solo_admin_y_ciclo_de_cuenta(client, catalogo, usuarios, mdb):
    login(client, usuarios["oirs_plc"])
    assert client.post("/usuarios/nuevo", {}).status_code == 403
    login(client, usuarios["admin"])
    r = client.post("/usuarios/nuevo", {"email": "nuevo@t.cl", "nombre": "Nora", "apellidos": "Nueva",
                                        "rol": "OIRS_EST", "establecimiento": catalogo["plc"].id})
    clave = r.context["clave"]
    nuevo = Usuario.objects.get(email="nuevo@t.cl")
    assert nuevo.debe_cambiar_clave and nuevo.check_password(clave) and clave not in str(list(mdb.bitacora_auditoria.find()))
    r = client.post("/usuarios/nuevo", {"email": "sin.est@t.cl", "nombre": "S", "apellidos": "E", "rol": "DIRECCION"})
    assert not Usuario.objects.filter(email="sin.est@t.cl").exists()   # perfil de establecimiento sin establecimiento
    client.post(f"/usuarios/{nuevo.pk}/desactivar")
    c2 = Client()
    r = _ingresar(c2, "nuevo@t.cl", clave)
    assert "Credenciales inválidas" in r.content.decode()
    r = client.post(f"/usuarios/{usuarios['admin'].pk}/desactivar", follow=True)
    assert "No puede desactivar su propia cuenta" in r.content.decode()


def test_ps30_recuperacion_no_revela_cuentas_y_el_enlace_es_de_un_solo_uso(client, catalogo, usuarios):
    r1 = client.post("/recuperar", {"email": usuarios["oirs_plc"].email})
    r2 = client.post("/recuperar", {"email": "no.existe@t.cl"})
    assert r1.url == r2.url == "/recuperar/enviado" and len(mail.outbox) == 1
    enlace = re.search(r"https?://[^/]+(/recuperar/\S+)", mail.outbox[0].body).group(1)
    r = client.get(enlace, follow=True)
    nueva = "Recuperada#2026!"
    destino = r.redirect_chain[-1][0]
    client.post(destino, {"new_password1": nueva, "new_password2": nueva})
    assert Usuario.objects.get(pk=usuarios["oirs_plc"].pk).check_password(nueva)
    assert b"Enlace no v" in Client().get(enlace, follow=True).content   # segundo uso: rechazado


def test_ps31_paginas_html_con_csp_y_sin_javascript_en_linea(client, catalogo, usuarios):
    login(client, usuarios["oirs_plc"])
    r = client.get("/bandeja")
    assert "script-src 'self'" in r["Content-Security-Policy"] and r["X-Frame-Options"] == "DENY"
    plantillas = Path(__file__).resolve().parents[2] / "apps" / "web" / "templates"
    for archivo in plantillas.rglob("*.html"):
        texto = archivo.read_text(encoding="utf-8")
        assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", texto), f"script en línea en {archivo.name}"
        assert not re.search(r"\son[a-z]+=\"", texto), f"manejador de evento en línea en {archivo.name}"


def test_ps32_errores_del_front_no_exponen_detalles(client, catalogo, usuarios):
    login(client, usuarios["oirs_plc"])
    r = client.get("/casos/PLC-0000-999999")
    assert r.status_code == 404 and b"Traceback" not in r.content and b"No encontrado" in r.content
