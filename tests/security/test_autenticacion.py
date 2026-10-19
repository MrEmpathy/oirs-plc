"""PS-01..PS-06: política de autenticación."""
import pyotp
import pytest
from django.contrib.auth.hashers import identify_hasher

from apps.cuentas.models import Usuario
from tests.conftest import CLAVE

pytestmark = [pytest.mark.seguridad, pytest.mark.django_db]
URL = "/api/v1/sesion/iniciar"


def _login(client, email, clave, totp=None):
    return client.post(URL, {"email": email, "password": clave, "codigo_totp": totp}, content_type="application/json")


def test_ps01_contrasena_almacenada_con_argon2(usuarios):
    u = usuarios["oirs_plc"]
    assert identify_hasher(u.password).algorithm == "argon2" and CLAVE not in u.password


def test_ps02_bloqueo_tras_5_intentos_fallidos(client, usuarios, mdb):
    for _ in range(5):
        assert _login(client, "oirs.plc@t.cl", "incorrecta").status_code == 401
    assert Usuario.objects.get(email="oirs.plc@t.cl").esta_bloqueado
    r = _login(client, "oirs.plc@t.cl", CLAVE)  # clave correcta, pero cuenta bloqueada
    assert r.status_code == 401
    assert mdb.bitacora_auditoria.count_documents({"accion": "CUENTA_BLOQUEADA"}) >= 1


def test_ps03_mensaje_generico_no_revela_existencia_de_cuenta(client, usuarios):
    a = _login(client, "noexiste@t.cl", "x").json()["error"]
    b = _login(client, "oirs.plc@t.cl", "x").json()["error"]
    assert a == b


def test_ps04_mfa_obligatorio_para_perfiles_privilegiados(client, usuarios):
    assert _login(client, "dsm@t.cl", CLAVE).json()["requiere_mfa"] is True
    assert _login(client, "dsm@t.cl", CLAVE, "000000").status_code == 401
    codigo = pyotp.TOTP(usuarios["dsm"].mfa_secreto).now()
    assert _login(client, "dsm@t.cl", CLAVE, codigo).status_code == 200


def test_ps05_rota_identificador_de_sesion_al_autenticar(client, usuarios):
    client.get("/api/v1/requerimientos")
    s = client.session
    s["x"] = 1
    s.save()
    antes = s.session_key
    assert _login(client, "oirs.plc@t.cl", CLAVE).status_code == 200
    assert client.session.session_key != antes


def test_ps06_cookies_y_cabeceras_seguras(settings, client, usuarios):
    settings.SESSION_COOKIE_SECURE = True
    r = _login(client, "oirs.plc@t.cl", CLAVE)
    cookie = r.cookies["sessionid"]
    assert cookie["httponly"] and cookie["secure"] and cookie["samesite"] == "Lax"
    assert "frame-ancestors 'none'" in r["Content-Security-Policy"]
    assert r["X-Frame-Options"] == "DENY" and r["X-Content-Type-Options"] == "nosniff"
