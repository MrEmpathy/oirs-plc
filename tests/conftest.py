import json
import os
import time

import holidays
import pyotp
import pytest
from django.test import Client

os.environ.setdefault("MONGO_DB", "oirs_plc_docs_test")

from apps.catalogos.management.commands.sembrar_datos import PREGUNTAS  # noqa: E402
from apps.integracion.hmac_firma import firmar  # noqa: E402

CLAVE = "Prueba#Segura2026"


@pytest.fixture(scope="session", autouse=True)
def mongo_limpio():
    from django.conf import settings
    from apps.core.documental import _cliente, asegurar_indices
    settings.MONGO_DB = "oirs_plc_docs_test"
    _cliente().drop_database("oirs_plc_docs_test")
    asegurar_indices()
    yield
    _cliente().drop_database("oirs_plc_docs_test")


@pytest.fixture
def mdb():
    from apps.core.documental import db
    return db()


@pytest.fixture
def catalogo(db):
    from apps.catalogos.models import Categoria, Establecimiento, Feriado, Unidad
    plc = Establecimiento.objects.create(codigo="CESFAM-PLC", nombre="CESFAM Padre Las Casas", tipo="CESFAM")
    pul = Establecimiento.objects.create(codigo="CESFAM-PUL", nombre="CESFAM Pulmahue", tipo="CESFAM")
    u_plc = Unidad.objects.create(establecimiento=plc, nombre="SOME")
    u_pul = Unidad.objects.create(establecimiento=pul, nombre="SOME")
    cat = Categoria.objects.create(nombre="Tiempos de espera")
    Categoria.objects.create(nombre="Otro", es_otro=True)
    Feriado.objects.bulk_create([Feriado(fecha=f, descripcion=d[:120])
                                 for f, d in holidays.Chile(years=[2026, 2027]).items()])
    return {"plc": plc, "pul": pul, "u_plc": u_plc, "u_pul": u_pul, "cat": cat}


@pytest.fixture
def usuarios(catalogo):
    from apps.cuentas.models import Usuario

    def crear(email, rol, est=None, mfa=False):
        u = Usuario.objects.create_user(email, CLAVE, nombre="N", apellidos="A", rol=rol, establecimiento=est)
        if mfa:
            u.mfa_secreto = pyotp.random_base32()
            u.save()
        return u
    return {
        "admin": crear("admin@t.cl", "ADMIN", mfa=True),
        "dsm": crear("dsm@t.cl", "OIRS_DSM", mfa=True),
        "oirs_plc": crear("oirs.plc@t.cl", "OIRS_EST", catalogo["plc"]),
        "oirs_pul": crear("oirs.pul@t.cl", "OIRS_EST", catalogo["pul"]),
        "dir_plc": crear("dir.plc@t.cl", "DIRECCION", catalogo["plc"]),
    }


@pytest.fixture
def encuesta(catalogo, mdb):
    from apps.encuestas.models import Encuesta
    e = Encuesta.objects.create(codigo="satisfaccion-usuaria", version=1, nombre="Satisfacción", activa=True)
    mdb.encuesta_definiciones.delete_many({"encuesta_id": e.id})
    mdb.encuesta_definiciones.insert_one({"encuesta_id": e.id, "codigo": e.codigo, "version": 1, "preguntas": PREGUNTAS})
    return e


def post_firmado(client, url, datos, secreto="dev-hmac-secret-solo-pruebas", ts=None, alterar=False):
    cuerpo = json.dumps(datos).encode()
    ts = ts or int(time.time())
    firma = firmar(cuerpo, ts, secreto)
    if alterar:
        cuerpo = cuerpo.replace(b"RECLAMO", b"SUGERENCIA")
    return client.post(url, cuerpo, content_type="application/json",
                       HTTP_X_OIRS_TIMESTAMP=str(ts), HTTP_X_OIRS_FIRMA=firma)


def login(client, usuario):
    client.force_login(usuario)
    return client


RECLAMO_VALIDO = {
    "tipo": "RECLAMO", "establecimiento": "CESFAM-PLC",
    "descripcion": "Esperé más de tres horas para ser atendido en el SOME sin información.",
    "peticion_concreta": "Mejorar la información de tiempos de espera.",
    "nombre": "María", "apellidos": "Pérez", "email": "maria@example.com", "telefono": "+56912345678",
    "edad": 45, "sexo": "F", "autoriza_respuesta_email": True, "acepta_tratamiento_datos": True,
}


@pytest.fixture
def anon():
    return Client()
