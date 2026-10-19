"""PI-11: unicidad del folio bajo ingresos concurrentes (bloqueo SELECT ... FOR UPDATE)."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection

from apps.requerimientos.servicios import generar_folio

pytestmark = [pytest.mark.integracion, pytest.mark.django_db(transaction=True)]


def _uno(_):
    try:
        return generar_folio(2026)
    finally:
        connection.close()


def test_pi11_folios_unicos_con_40_ingresos_concurrentes():
    with ThreadPoolExecutor(max_workers=10) as ex:
        folios = list(ex.map(_uno, range(40)))
    assert len(set(folios)) == 40
    assert sorted(folios)[-1] == "PLC-2026-000040"
