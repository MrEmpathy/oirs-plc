"""PS-07..PS-12: autorización por rol y por establecimiento (RNF02)."""
import pytest

from tests.conftest import RECLAMO_VALIDO, login, post_firmado

pytestmark = [pytest.mark.seguridad, pytest.mark.django_db]


@pytest.fixture
def folio_plc(anon, catalogo):
    return post_firmado(anon, "/api/v1/publico/requerimientos", RECLAMO_VALIDO).json()["folio"]


def test_ps07_sin_sesion_responde_401(anon, folio_plc):
    assert anon.get("/api/v1/requerimientos").status_code == 401


def test_ps08_idor_otro_establecimiento_responde_404(client, usuarios, folio_plc):
    login(client, usuarios["oirs_pul"])
    assert client.get(f"/api/v1/requerimientos/{folio_plc}").status_code == 404
    assert client.get("/api/v1/requerimientos").json()["total"] == 0


def test_ps09_direccion_solo_lectura(client, usuarios, catalogo, folio_plc):
    login(client, usuarios["dir_plc"])
    assert client.get(f"/api/v1/requerimientos/{folio_plc}").status_code == 200
    r = client.post(f"/api/v1/requerimientos/{folio_plc}/derivar", {"categoria_id": catalogo["cat"].id,
                    "unidad_id": catalogo["u_plc"].id}, content_type="application/json")
    assert r.status_code == 403


@pytest.mark.parametrize("perfil", ["admin", "dsm"])
def test_ps10_perfiles_de_supervision_no_gestionan_casos(client, usuarios, catalogo, folio_plc, perfil):
    login(client, usuarios[perfil])
    r = client.post(f"/api/v1/requerimientos/{folio_plc}/cerrar")
    assert r.status_code == 403


def test_ps11_reporte_ignora_filtro_de_otro_establecimiento(client, usuarios, catalogo, folio_plc):
    login(client, usuarios["oirs_pul"])
    d = client.get(f"/api/v1/reportes/indicadores?establecimiento={catalogo['plc'].id}").json()
    assert d["total"] == 0


def test_ps12_exportacion_solo_oirs_dsm_y_auditada(client, usuarios, folio_plc, mdb):
    login(client, usuarios["oirs_plc"])
    assert client.get("/api/v1/reportes/requerimientos.csv").status_code == 403
    login(client, usuarios["dsm"])
    r = client.get("/api/v1/reportes/requerimientos.csv")
    assert r.status_code == 200 and folio_plc in r.content.decode()
    assert "maria@example.com" not in r.content.decode()  # sin datos personales
    assert mdb.bitacora_auditoria.count_documents({"accion": "REPORTE_EXPORTADO"}) >= 1
