"""PU-01..PU-08: cálculo de días hábiles y semáforo (funciones puras, sin BD)."""
from datetime import date

import holidays
import pytest

from apps.requerimientos import plazos

pytestmark = pytest.mark.unit
FERIADOS = set(holidays.Chile(years=[2026]).keys())


def test_pu01_quince_habiles_sin_feriados():
    # Lunes 05-10-2026 + 15 hábiles = lunes 26-10-2026 (sin feriados intermedios relevantes)
    assert plazos.sumar_dias_habiles(date(2026, 10, 5), 15, set()) == date(2026, 10, 26)


def test_pu02_excluye_fines_de_semana():
    # Viernes + 1 hábil = lunes siguiente
    assert plazos.sumar_dias_habiles(date(2026, 10, 16), 1, set()) == date(2026, 10, 19)


def test_pu03_excluye_feriados_fiestas_patrias():
    # Ingreso 14-09-2026: 18 y 19 de septiembre son feriados → el plazo se extiende 1 día hábil (18 es viernes)
    sin = plazos.sumar_dias_habiles(date(2026, 9, 14), 15, set())
    con = plazos.sumar_dias_habiles(date(2026, 9, 14), 15, FERIADOS)
    assert (con - sin).days >= 1 and plazos.es_habil(con, FERIADOS)


def test_pu04_ingreso_en_fin_de_semana():
    # Ingreso sábado 17-10-2026: el conteo parte el lunes 19
    assert plazos.sumar_dias_habiles(date(2026, 10, 17), 1, set()) == date(2026, 10, 19)


def test_pu05_dias_negativos_lanza_error():
    with pytest.raises(ValueError):
        plazos.sumar_dias_habiles(date(2026, 10, 5), -1, set())


@pytest.mark.parametrize("hoy,venc,esperado", [
    (date(2026, 10, 19), date(2026, 10, 23), 4),
    (date(2026, 10, 23), date(2026, 10, 23), 0),
    (date(2026, 10, 26), date(2026, 10, 23), -1),   # lunes, venció el viernes
    (date(2026, 10, 30), date(2026, 10, 23), -5),
])
def test_pu06_dias_restantes(hoy, venc, esperado):
    assert plazos.dias_habiles_restantes(hoy, venc, set()) == esperado


@pytest.mark.parametrize("restantes,color", [(10, "VERDE"), (6, "VERDE"), (5, "AMARILLO"), (0, "AMARILLO"), (-1, "ROJO")])
def test_pu07_semaforo(restantes, color):
    assert plazos.semaforo(restantes) == color


def test_pu08_vencimiento_siempre_habil():
    for dia in range(1, 29):
        venc = plazos.sumar_dias_habiles(date(2026, 2, dia), 15, FERIADOS)
        assert plazos.es_habil(venc, FERIADOS)
