"""PU-21..PU-24: reglas puras de los servicios agregados en la implementación."""
import pytest
from django.contrib.auth.password_validation import validate_password

from apps.cuentas.servicios import clave_temporal
from apps.web.formularios import DerivarForm, FiltroBandejaForm, ReportesForm

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize("_", range(20))
def test_pu21_clave_temporal_cumple_la_politica(_):
    clave = clave_temporal()
    assert len(clave) == 16
    validate_password(clave)                       # no lanza: mayúscula, minúscula, dígito, símbolo, ≥ 12


def test_pu22_filtro_de_bandeja_rechaza_valores_fuera_de_lista_blanca():
    f = FiltroBandejaForm({"estado": "BORRADO'; --", "q": "x" * 61})
    assert not f.is_valid() and {"estado", "q"} <= set(f.errors)


@pytest.mark.django_db
def test_pu23_derivacion_solo_ofrece_unidades_del_establecimiento(catalogo):
    f = DerivarForm(establecimiento=catalogo["plc"])
    assert list(f.fields["unidad"].queryset) == [catalogo["u_plc"]]
    f = DerivarForm({"categoria": catalogo["cat"].id, "unidad": catalogo["u_pul"].id}, establecimiento=catalogo["plc"])
    assert not f.is_valid() and "unidad" in f.errors


@pytest.mark.parametrize("desde,hasta,valido", [("2026-01-01", "2026-12-31", True), ("2026-12-31", "2026-01-01", False),
                                                ("2023-01-01", "2026-01-01", False)])
@pytest.mark.django_db
def test_pu24_periodo_de_reportes_valido(desde, hasta, valido):
    assert ReportesForm({"desde": desde, "hasta": hasta}).is_valid() is valido
