"""PI-20..PI-22: procesos programados de datos (retención y consistencia entre bases, secciones 6.1 y 6.5)."""
from datetime import timedelta

import pytest
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from apps.requerimientos.models import Requerimiento
from tests.conftest import crear_caso

pytestmark = [pytest.mark.integracion, pytest.mark.django_db]


def test_pi20_anonimiza_solo_casos_cerrados_fuera_de_retencion(anon, catalogo):
    antiguo, reciente, abierto_antiguo = crear_caso(anon), crear_caso(anon), crear_caso(anon)
    hace_6_anios = timezone.now() - timedelta(days=6 * 365)
    Requerimiento.objects.filter(pk__in=[antiguo.pk, abierto_antiguo.pk]).update(fecha_ingreso=hace_6_anios,
                                                                                fecha_vencimiento=hace_6_anios.date() + timedelta(days=21))
    Requerimiento.objects.filter(pk__in=[antiguo.pk, reciente.pk]).update(estado="CERRADO")
    call_command("anonimizar_solicitantes", dias=5 * 365)
    for r in (antiguo, reciente, abierto_antiguo):
        r.solicitante.refresh_from_db()
    assert antiguo.solicitante.anonimizado and antiguo.solicitante.email == "" and antiguo.solicitante.nombre == "ANONIMIZADO"
    assert not reciente.solicitante.anonimizado and not abierto_antiguo.solicitante.anonimizado
    antiguo.refresh_from_db()
    assert antiguo.tipo == "RECLAMO" and antiguo.establecimiento == catalogo["plc"]   # se conserva la estadística


def test_pi21_detecta_referencias_huerfanas_entre_bases(catalogo, encuesta, mdb):
    mdb.respuestas_encuesta.delete_many({})
    mdb.respuestas_encuesta.insert_one({"encuesta_id": encuesta.id, "establecimiento_id": 999999, "respuestas": {}})
    with pytest.raises(SystemExit) as salida:
        call_command("verificar_referencias")
    assert salida.value.code == 1
    mdb.respuestas_encuesta.delete_many({})


def test_pi22_bitacora_con_indice_ttl_de_retencion(mdb):
    from apps.core.documental import asegurar_indices
    asegurar_indices()
    ttl = mdb.bitacora_auditoria.index_information()["ttl_bit_ts"]
    assert ttl["expireAfterSeconds"] == settings.RETENCION_BITACORA_DIAS * 86400
