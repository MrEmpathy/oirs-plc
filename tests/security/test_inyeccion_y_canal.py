"""PS-13..PS-20: inyección SQL, XSS, CSRF, integridad del canal WordPress y mínimo privilegio en BD."""
import time

import psycopg
import pytest
from django.db import connection
from django.test import Client

from apps.requerimientos.models import Requerimiento
from tests.conftest import RECLAMO_VALIDO, login, post_firmado

pytestmark = [pytest.mark.seguridad]
URL = "/api/v1/publico/requerimientos"


@pytest.mark.django_db
@pytest.mark.parametrize("payload", ["' OR '1'='1", "'; DROP TABLE requerimiento;--", "1 UNION SELECT password FROM usuario"])
def test_ps13_inyeccion_sql_en_busqueda(anon, client, catalogo, usuarios, payload):
    post_firmado(anon, URL, RECLAMO_VALIDO)
    login(client, usuarios["oirs_plc"])
    r = client.get("/api/v1/requerimientos", {"q": payload})
    assert r.status_code == 200 and r.json()["total"] == 0
    assert Requerimiento.objects.count() == 1  # la tabla sigue intacta


@pytest.mark.django_db
def test_ps14_xss_almacenado_se_devuelve_como_dato_no_ejecutable(anon, client, catalogo, usuarios):
    xss = "<script>alert('xss')</script> espera excesiva en SOME"
    folio = post_firmado(anon, URL, {**RECLAMO_VALIDO, "descripcion": xss}).json()["folio"]
    login(client, usuarios["oirs_plc"])
    r = client.get(f"/api/v1/requerimientos/{folio}")
    assert r["Content-Type"] == "application/json" and "script-src 'self'" in r["Content-Security-Policy"]
    assert b"<script>" not in r.content  # JSON escapa '<' como <


@pytest.mark.django_db
def test_ps15_csrf_obligatorio_en_operaciones_de_sesion(anon, catalogo, usuarios):
    folio = post_firmado(anon, URL, RECLAMO_VALIDO).json()["folio"]
    c = Client(enforce_csrf_checks=True)
    c.force_login(usuarios["oirs_plc"])
    r = c.post(f"/api/v1/requerimientos/{folio}/cerrar")
    assert r.status_code == 403


@pytest.mark.django_db
def test_ps16_firma_hmac_invalida_o_cuerpo_alterado(anon, catalogo):
    assert post_firmado(anon, URL, RECLAMO_VALIDO, secreto="otro").status_code == 401
    assert post_firmado(anon, URL, RECLAMO_VALIDO, alterar=True).status_code == 401
    assert anon.post(URL, RECLAMO_VALIDO, content_type="application/json").status_code == 401


@pytest.mark.django_db
def test_ps17_replay_con_marca_de_tiempo_antigua(anon, catalogo):
    assert post_firmado(anon, URL, RECLAMO_VALIDO, ts=int(time.time()) - 3600).status_code == 401


@pytest.mark.django_db
def test_ps18_errores_no_exponen_trazas(anon, catalogo):
    r = post_firmado(anon, URL, {**RECLAMO_VALIDO, "edad": "x" * 5000})
    assert r.status_code == 400 and b"Traceback" not in r.content and b"psycopg" not in r.content


@pytest.mark.django_db(transaction=True)
def test_ps19_usuario_app_sin_privilegio_update_delete_en_historial(anon, catalogo):
    post_firmado(anon, URL, RECLAMO_VALIDO)
    nombre_bd = connection.settings_dict["NAME"]
    with psycopg.connect(host="127.0.0.1", dbname=nombre_bd, user="oirs_app", password="app_dev_only") as c:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("DELETE FROM historial_estado")


@pytest.mark.django_db(transaction=True)
def test_ps20_trigger_impide_modificar_historial_incluso_al_propietario(anon, catalogo):
    post_firmado(anon, URL, RECLAMO_VALIDO)
    with pytest.raises(Exception, match="solo inserción"):
        with connection.cursor() as cur:
            cur.execute("UPDATE historial_estado SET comentario = 'alterado'")
