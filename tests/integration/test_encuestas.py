"""PI-07..PI-09: encuesta anónima almacenada en la base documental."""
import pytest

from tests.conftest import post_firmado

pytestmark = [pytest.mark.integracion, pytest.mark.django_db]
URL = "/api/v1/publico/encuestas/satisfaccion-usuaria/respuestas"
VALIDA = {"establecimiento": "CESFAM-PUL", "respuestas": {"p1": 6, "p2": 3, "p3": 7, "p4": 7, "p5": 5, "p6": "Dental"},
          "comentario": "Muy buena atención dental"}


def test_pi07_respuesta_anonima_sin_datos_identificables(anon, encuesta, catalogo, mdb):
    assert post_firmado(anon, URL, VALIDA).status_code == 201
    doc = mdb.respuestas_encuesta.find_one({"establecimiento_id": catalogo["pul"].id})
    assert set(doc) == {"_id", "encuesta_id", "encuesta_codigo", "version", "establecimiento_id", "fecha",
                        "canal", "respuestas", "comentario"}
    assert len(doc["fecha"]) == 10  # solo fecha (AAAA-MM-DD), sin hora exacta


def test_pi08_rechaza_datos_personales_en_encuesta(anon, encuesta, catalogo):
    malo = {**VALIDA, "respuestas": {**VALIDA["respuestas"], "email": "x@y.cl"}}
    assert post_firmado(anon, URL, malo).status_code == 400


@pytest.mark.parametrize("cambio", [{"p1": 9}, {"p1": "7"}, {"p6": "Cirugía"}, {"pX": 3}])
def test_pi09_rechaza_respuestas_fuera_de_definicion(anon, encuesta, catalogo, cambio):
    malo = {**VALIDA, "respuestas": {**VALIDA["respuestas"], **cambio}}
    assert post_firmado(anon, URL, malo).status_code == 400


def test_pi10_rechaza_faltantes_obligatorias_y_establecimiento_inexistente(anon, encuesta, catalogo):
    assert post_firmado(anon, URL, {**VALIDA, "respuestas": {"p1": 5}}).status_code == 400
    assert post_firmado(anon, URL, {**VALIDA, "establecimiento": "X"}).status_code == 400
