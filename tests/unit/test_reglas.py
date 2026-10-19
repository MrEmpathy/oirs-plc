"""PU-09..PU-16: máquina de estados, validadores y utilidades de seguridad."""
import pytest
from django.core.exceptions import ValidationError

from apps.auditoria.servicio import _ip_truncada
from apps.cuentas.validators import ComplejidadValidator
from apps.integracion.hmac_firma import firmar
from apps.reportes.servicio import celda_segura
from apps.requerimientos.models import Estado
from apps.requerimientos.servicios import validar_transicion

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("a,b", [(Estado.INGRESADO, Estado.EN_PROCESO), (Estado.EN_PROCESO, Estado.RESPONDIDO),
                                 (Estado.EN_PROCESO, Estado.EN_PROCESO), (Estado.RESPONDIDO, Estado.CERRADO)])
def test_pu09_transiciones_validas(a, b):
    validar_transicion(a, b)


@pytest.mark.parametrize("a,b", [(Estado.INGRESADO, Estado.CERRADO), (Estado.INGRESADO, Estado.RESPONDIDO),
                                 (Estado.CERRADO, Estado.EN_PROCESO), (Estado.RESPONDIDO, Estado.EN_PROCESO)])
def test_pu10_transiciones_invalidas(a, b):
    with pytest.raises(ValidationError):
        validar_transicion(a, b)


@pytest.mark.parametrize("clave", ["solominusculas12", "SOLOMAYUSCULAS12", "SinSimbolos1234", "Sin#Numeros_aa"])
def test_pu11_complejidad_rechaza(clave):
    with pytest.raises(ValidationError):
        ComplejidadValidator().validate(clave)


def test_pu12_complejidad_acepta():
    ComplejidadValidator().validate("Prueba#Segura2026")


@pytest.mark.parametrize("entrada,salida", [("=HYPERLINK(\"x\")", "'=HYPERLINK(\"x\")"), ("+1+1", "'+1+1"),
                                            ("@SUM(A1)", "'@SUM(A1)"), ("PLC-2026-000001", "PLC-2026-000001")])
def test_pu13_csv_neutraliza_formulas(entrada, salida):
    assert celda_segura(entrada) == salida


def test_pu14_hmac_determinista_y_sensible_a_cambios():
    a = firmar(b'{"a":1}', 1000, "s")
    assert a == firmar(b'{"a":1}', 1000, "s")
    assert a != firmar(b'{"a":2}', 1000, "s") and a != firmar(b'{"a":1}', 1001, "s")


def test_pu15_ip_truncada_minimiza():
    assert _ip_truncada("200.1.2.3") == "200.1.2.0/24"
    assert _ip_truncada("no-es-ip") is None


def test_pu16_auditoria_descarta_datos_personales(monkeypatch):
    from apps.auditoria import servicio
    capturado = {}

    class Falsa:
        def insert_one(self, doc):
            capturado.update(doc)

    monkeypatch.setattr(servicio, "db", lambda: type("D", (), {"bitacora_auditoria": Falsa()})())
    servicio.registrar("PRUEBA", email="x@y.cl", password="secreta", nombre="Juan", tipo="RECLAMO")
    assert capturado["detalle"] == {"tipo": "RECLAMO"}
