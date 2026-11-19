"""PI-27..PI-30: comportamiento cuando una base de datos o la caché se cae (E2E-10, DEF-16 a DEF-19).

Cada prueba simula la caída con la misma excepción que lanza el controlador real (psycopg/Django, pymongo, redis-py)
y comprueba lo que recibe el usuario. La caída real de los contenedores se verifica en tests/e2e/caida_bases.py."""
import json
import logging

import pytest
from django.conf import settings
from django.db import OperationalError
from django.test import RequestFactory
from pymongo.errors import ServerSelectionTimeoutError
from redis.exceptions import ConnectionError as RedisConnectionError

from tests.conftest import post_firmado

pytestmark = [pytest.mark.integracion, pytest.mark.django_db]


def _respuesta_de_error(ruta, excepcion):
    """Llama al manejador de errores 500 como lo hace Django: dentro del bloque que capturó la excepción."""
    from apps.web.vistas.errores import error_interno
    try:
        raise excepcion
    except Exception:  # noqa: BLE001
        return error_interno(RequestFactory().get(ruta))


def test_pi27_base_caida_responde_503_sin_consultar_la_base(django_assert_num_queries):
    """DEF-16: con PostgreSQL caído la página de error no puede depender de la sesión ni del menú."""
    with django_assert_num_queries(0):
        r = _respuesta_de_error("/bandeja", OperationalError("could not connect to server"))
    html = r.content.decode()
    assert r.status_code == 503 and r["Retry-After"] == "30"
    assert "Servicio no disponible" in html and "could not connect" not in html and "Traceback" not in html
    r = _respuesta_de_error("/api/v1/publico/catalogos", ServerSelectionTimeoutError("mongo:27017"))
    assert r.status_code == 503 and json.loads(r.content) == {"error": "Servicio no disponible"}
    r = _respuesta_de_error("/bandeja", ValueError("error de programación"))
    assert r.status_code == 500 and "Error interno" in r.content.decode()      # un error real sigue siendo 500
    assert settings.DATABASES["default"]["CONN_HEALTH_CHECKS"] is True          # DEF-17: conexión comprobada


def test_pi28_api_con_base_documental_caida_responde_503(anon, encuesta, catalogo, monkeypatch):
    """DEF-16: el plugin recibe 503 y muestra «servicio no disponible», no «revise los campos marcados»."""
    from apps.encuestas import servicio

    def caida(*a, **k):
        raise ServerSelectionTimeoutError("mongo:27017: Name or service not known")
    monkeypatch.setattr(servicio, "definicion", caida)
    r = post_firmado(anon, "/api/v1/publico/encuestas/satisfaccion-usuaria/respuestas",
                     {"establecimiento": "CESFAM-PUL", "respuestas": {"p1": 6, "p2": 6, "p3": 6, "p4": 6, "p5": 6}})
    assert r.status_code == 503 and r["Retry-After"] == "30"
    assert r.json() == {"error": "Servicio no disponible"}


class CacheCaida:
    def __getattr__(self, nombre):
        def falla(*a, **k):
            raise RedisConnectionError("Error -2 connecting to redis:6379. Name or service not known.")
        return falla


def test_pi29_cache_caida_no_impide_responder_la_encuesta_ni_ver_reportes(anon, encuesta, catalogo, mdb,
                                                                          monkeypatch):
    """DEF-18: con Redis caído la respuesta se guarda UNA vez y se confirma; el resumen se calcula sin caché."""
    from apps.encuestas import servicio
    mdb.respuestas_encuesta.delete_many({})
    monkeypatch.setattr(servicio, "cache", CacheCaida())
    r = post_firmado(anon, "/api/v1/publico/encuestas/satisfaccion-usuaria/respuestas",
                     {"establecimiento": "CESFAM-PUL", "respuestas": {"p1": 7, "p2": 5, "p3": 6, "p4": 6, "p5": 6}})
    assert r.status_code == 201 and mdb.respuestas_encuesta.count_documents({}) == 1
    resumen = servicio.resumen(encuesta.id)
    assert resumen[0] == {"_id": "p1", "promedio": 7.0, "n": 1}


def test_pi30_bitacora_caida_respalda_el_evento_completo_sin_demorar(monkeypatch, caplog):
    """DEF-19: con la base documental caída el evento no se pierde (queda en el registro) y, tras la primera
    falla, las siguientes no vuelven a esperar a la base durante 30 s."""
    from apps.auditoria import servicio
    intentos = []

    class Caida:
        def insert_one(self, doc):
            intentos.append(doc)
            raise ServerSelectionTimeoutError("mongo:27017")

    monkeypatch.setattr(servicio, "db", lambda: type("D", (), {"bitacora_auditoria": Caida()})())
    monkeypatch.setattr(servicio, "_documental_caida_hasta", 0.0)
    with caplog.at_level(logging.WARNING, logger="oirs"):
        servicio.registrar("INICIO_SESION", folio="PLC-2026-000001", email="no@debe.verse", tipo="RECLAMO")
        servicio.registrar("CASO_DERIVADO", folio="PLC-2026-000001")
    assert len(intentos) == 1                                   # el segundo evento no espera a la base caída
    respaldos = [r.getMessage() for r in caplog.records if "BITACORA_RESPALDO" in r.getMessage()]
    assert len(respaldos) == 2
    evento = json.loads(respaldos[0].split("BITACORA_RESPALDO ", 1)[1])
    assert evento["accion"] == "INICIO_SESION" and evento["detalle"] == {"tipo": "RECLAMO"}   # sin datos personales
