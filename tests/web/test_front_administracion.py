"""PI-24..PI-26: administración de catálogos y cuentas desde el front (perfil ADMIN, CU10)."""
from datetime import date

import pyotp
import pytest

from apps.catalogos.models import Categoria, Establecimiento, Feriado, Unidad
from apps.cuentas.models import Usuario
from tests.conftest import CLAVE, login

pytestmark = [pytest.mark.integracion, pytest.mark.django_db]


def test_pi24_catalogos_crear_desactivar_y_reglas_de_unicidad(client, catalogo, usuarios, mdb):
    login(client, usuarios["admin"])
    assert client.get("/catalogos?p=unidades").status_code == 200
    client.post("/catalogos/establecimiento/nuevo", {"codigo": "cecosf-01", "nombre": "CECOSF Demo", "tipo": "CECOSF"})
    nuevo = Establecimiento.objects.get(codigo="CECOSF-01")                 # código normalizado a mayúsculas
    r = client.post("/catalogos/establecimiento/nuevo", {"codigo": "CECOSF-01", "nombre": "Otro nombre", "tipo": "CECOSF"},
                    follow=True)
    assert "ya existe" in r.content.decode().lower() and Establecimiento.objects.filter(codigo="CECOSF-01").count() == 1
    client.post("/catalogos/unidad/nuevo", {"establecimiento": nuevo.id, "nombre": "Dirección"})
    assert Unidad.objects.filter(establecimiento=nuevo, nombre="Dirección").exists()
    r = client.post("/catalogos/categoria/nuevo", {"nombre": "Otro motivo", "es_otro": "on"}, follow=True)
    assert Categoria.objects.filter(es_otro=True).count() == 1                # índice único parcial: un solo «Otro»
    client.post(f"/catalogos/establecimiento/{nuevo.id}/alternar")
    nuevo.refresh_from_db()
    assert nuevo.activo is False
    client.post("/catalogos/feriado/nuevo", {"fecha": "2027-03-15", "descripcion": "Feriado regional de prueba"})
    r = client.post("/catalogos/feriado/nuevo", {"fecha": "2027-03-15", "descripcion": "Duplicado"}, follow=True)
    assert Feriado.objects.filter(fecha=date(2027, 3, 15)).count() == 1 and "ya está registrada" in r.content.decode()
    assert mdb.bitacora_auditoria.count_documents({"accion": {"$in": ["CATALOGO_CREADO", "CATALOGO_MODIFICADO"]},
                                                    "usuario_id": usuarios["admin"].id}) >= 4


def test_pi25_acciones_de_cuenta_bloqueo_mfa_y_clave_temporal(client, catalogo, usuarios):
    from django.test import Client
    login(client, usuarios["admin"])
    dsm = usuarios["dsm"]
    for _ in range(5):                                                       # bloqueo por intentos
        Client().post("/ingresar", {"email": dsm.email, "password": "incorrecta"})
    dsm.refresh_from_db()
    assert dsm.esta_bloqueado
    client.post(f"/usuarios/{dsm.pk}/desbloquear")
    client.post(f"/usuarios/{dsm.pk}/restablecer-mfa")
    r = client.post(f"/usuarios/{dsm.pk}/clave-temporal")
    dsm.refresh_from_db()
    assert not dsm.esta_bloqueado and dsm.mfa_secreto == "" and dsm.debe_cambiar_clave
    assert dsm.check_password(r.context["clave"]) and not dsm.check_password(CLAVE)
    c = Client()                                                             # al ingresar debe enrolar MFA de nuevo
    assert c.post("/ingresar", {"email": dsm.email, "password": r.context["clave"]}).url == "/ingresar/segundo-factor"


def test_pi26_edicion_de_perfil_y_restricciones_sobre_la_propia_cuenta(client, catalogo, usuarios):
    login(client, usuarios["admin"])
    est = usuarios["oirs_pul"]
    r = client.post(f"/usuarios/{est.pk}", {"nombre": "Pedro", "apellidos": "Pérez", "rol": "OIRS_DSM"}, follow=True)
    est.refresh_from_db()
    assert est.rol == "OIRS_DSM" and est.establecimiento is None and "Usuario actualizado" in r.content.decode()
    admin = usuarios["admin"]
    r = client.post(f"/usuarios/{admin.pk}", {"nombre": "A", "apellidos": "B", "rol": "OIRS_EST",
                                              "establecimiento": catalogo["plc"].id}, follow=True)
    admin.refresh_from_db()
    assert admin.rol == "ADMIN" and "No puede quitarse a sí mismo" in r.content.decode()
    assert client.get("/usuarios?q=pul&rol=OIRS_DSM").context["pagina"].paginator.count == 1
    assert Usuario.objects.get(pk=est.pk).email == "oirs.pul@t.cl"           # el correo no se edita
