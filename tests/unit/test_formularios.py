"""PU-17..PU-20: validación de entradas del formulario público (lista blanca)."""
import pytest

from apps.integracion.formularios import RequerimientoPublicoForm
from tests.conftest import RECLAMO_VALIDO

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_pu17_reclamo_valido(catalogo):
    assert RequerimientoPublicoForm(RECLAMO_VALIDO).is_valid()


def test_pu18_reclamo_sin_contacto_invalido(catalogo):
    d = {**RECLAMO_VALIDO, "email": "", "telefono": ""}
    f = RequerimientoPublicoForm(d)
    assert not f.is_valid() and "email" in f.errors


def test_pu19_felicitacion_anonima_valida(catalogo):
    d = {"tipo": "FELICITACION", "establecimiento": "CESFAM-PLC", "acepta_tratamiento_datos": True,
         "descripcion": "Excelente atención de la matrona del sector azul."}
    f = RequerimientoPublicoForm(d)
    assert f.is_valid() and f.datos_solicitante() is None


@pytest.mark.parametrize("campo,valor", [("tipo", "HACKEO"), ("establecimiento", "NO-EXISTE"),
                                         ("telefono", "abc'; DROP TABLE x;--"), ("edad", 300),
                                         ("descripcion", "corto"), ("acepta_tratamiento_datos", False)])
def test_pu20_rechaza_valores_fuera_de_lista_blanca(catalogo, campo, valor):
    assert not RequerimientoPublicoForm({**RECLAMO_VALIDO, campo: valor}).is_valid()
