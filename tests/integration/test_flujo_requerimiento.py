"""PI-01..PI-06: integración WordPress → API → PostgreSQL → base documental → reportes."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.requerimientos.models import HistorialEstado, Requerimiento
from tests.conftest import RECLAMO_VALIDO, login, post_firmado

pytestmark = [pytest.mark.integracion, pytest.mark.django_db]
URL = "/api/v1/publico/requerimientos"


def test_pi01_ingreso_web_genera_folio_y_plazo(anon, catalogo, mdb):
    r = post_firmado(anon, URL, RECLAMO_VALIDO)
    assert r.status_code == 201, r.content
    folio = r.json()["folio"]
    assert folio.startswith(f"PLC-{timezone.localdate().year}-")
    req = Requerimiento.objects.get(folio=folio)
    assert req.estado == "INGRESADO" and req.solicitante.email == "maria@example.com"
    assert req.fecha_vencimiento > timezone.localdate()
    assert HistorialEstado.objects.filter(requerimiento=req, estado_nuevo="INGRESADO").count() == 1
    assert mdb.bitacora_auditoria.count_documents({"folio": folio, "accion": "REQUERIMIENTO_CREADO"}) == 1


def test_pi02_ciclo_completo_ingreso_derivacion_respuesta_cierre(anon, client, catalogo, usuarios, mdb):
    folio = post_firmado(anon, URL, RECLAMO_VALIDO).json()["folio"]
    login(client, usuarios["oirs_plc"])
    base = f"/api/v1/requerimientos/{folio}"
    r = client.post(f"{base}/derivar", {"categoria_id": catalogo["cat"].id, "unidad_id": catalogo["u_plc"].id,
                                         "instrucciones": "Revisar flujo SOME"}, content_type="application/json")
    assert r.status_code == 200 and r.json()["estado"] == "EN_PROCESO"
    r = client.post(f"{base}/respuesta", {"contenido": "Estimada usuaria, se reforzó la señalética de tiempos de espera.",
                                           "medio": "EMAIL", "fecha_emision": timezone.localdate().isoformat()},
                    content_type="application/json")
    assert r.status_code == 200 and r.json()["dentro_plazo"] is True
    assert client.post(f"{base}/cerrar").json()["estado"] == "CERRADO"
    det = client.get(base).json()
    assert [h["estado_nuevo"] for h in det["historial"]] == ["INGRESADO", "EN_PROCESO", "RESPONDIDO", "CERRADO"]
    acciones = {d["accion"] for d in mdb.bitacora_auditoria.find({"folio": folio})}
    assert {"REQUERIMIENTO_CREADO", "REQUERIMIENTO_DERIVADO", "RESPUESTA_REGISTRADA", "REQUERIMIENTO_CERRADO"} <= acciones


def test_pi03_respuesta_fuera_de_plazo_queda_registrada(anon, client, catalogo, usuarios):
    folio = post_firmado(anon, URL, RECLAMO_VALIDO).json()["folio"]
    req = Requerimiento.objects.get(folio=folio)
    login(client, usuarios["oirs_plc"])
    client.post(f"/api/v1/requerimientos/{folio}/derivar", {"categoria_id": catalogo["cat"].id,
                "unidad_id": catalogo["u_plc"].id}, content_type="application/json")
    tarde = (req.fecha_vencimiento + timedelta(days=3)).isoformat()
    r = client.post(f"/api/v1/requerimientos/{folio}/respuesta", {"contenido": "Respuesta emitida con atraso por licencia.",
                    "medio": "CARTA", "fecha_emision": tarde}, content_type="application/json")
    assert r.json()["dentro_plazo"] is False


def test_pi04_derivacion_a_unidad_de_otro_establecimiento_rechazada(anon, client, catalogo, usuarios):
    folio = post_firmado(anon, URL, RECLAMO_VALIDO).json()["folio"]
    login(client, usuarios["oirs_plc"])
    r = client.post(f"/api/v1/requerimientos/{folio}/derivar", {"categoria_id": catalogo["cat"].id,
                    "unidad_id": catalogo["u_pul"].id}, content_type="application/json")
    assert r.status_code == 400


def test_pi05_panel_lista_con_semaforo_y_dias_restantes(anon, client, catalogo, usuarios):
    for _ in range(3):
        post_firmado(anon, URL, RECLAMO_VALIDO)
    post_firmado(anon, URL, {**RECLAMO_VALIDO, "establecimiento": "CESFAM-PUL"})
    login(client, usuarios["dsm"])
    datos = client.get("/api/v1/requerimientos").json()
    assert datos["total"] == 4
    assert all(r["semaforo"] == "VERDE" and r["dias_restantes"] >= 14 for r in datos["resultados"])


def test_pi06_reporte_integra_postgresql_y_documental(anon, client, catalogo, usuarios, encuesta):
    post_firmado(anon, URL, RECLAMO_VALIDO)
    post_firmado(anon, URL, {**RECLAMO_VALIDO, "tipo": "SUGERENCIA"})
    for nota in (7, 5, 6):
        post_firmado(anon, "/api/v1/publico/encuestas/satisfaccion-usuaria/respuestas",
                     {"establecimiento": "CESFAM-PLC", "respuestas": {"p1": nota, "p2": 4, "p3": 7, "p4": 6, "p5": 6}})
    login(client, usuarios["dsm"])
    d = client.get("/api/v1/reportes/indicadores").json()
    assert d["total"] == 2 and {t["tipo"] for t in d["por_tipo"]} == {"RECLAMO", "SUGERENCIA"}
    p1 = next(s for s in d["satisfaccion"] if s["_id"] == "p1")
    assert p1["n"] == 3 and round(p1["promedio"], 2) == 6.0
