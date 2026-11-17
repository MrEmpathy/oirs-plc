"""PI-13..PI-19: front administrativo extremo a extremo sobre bases reales (PostgreSQL + documental).
Cada prueba usa las mismas vistas que un funcionario en el navegador (formularios con CSRF y sesión)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.requerimientos.models import Requerimiento
from tests.conftest import crear_caso, login

pytestmark = [pytest.mark.integracion, pytest.mark.django_db]


def test_pi13_bandeja_muestra_solo_casos_del_establecimiento_ordenados_por_vencimiento(anon, client, catalogo, usuarios):
    a = crear_caso(anon)
    b = crear_caso(anon)
    ajeno = crear_caso(anon, establecimiento="CESFAM-PUL")
    Requerimiento.objects.filter(pk=b.pk).update(fecha_vencimiento=a.fecha_vencimiento - timedelta(days=3))
    login(client, usuarios["oirs_plc"])
    html = client.get("/bandeja").content.decode()
    assert a.folio in html and b.folio in html and ajeno.folio not in html
    assert html.index(b.folio) < html.index(a.folio)   # vence antes → aparece primero


def test_pi14_ciclo_completo_desde_el_front(anon, client, catalogo, usuarios, mdb):
    req = crear_caso(anon)
    inicio = timezone.now()
    login(client, usuarios["oirs_plc"])
    r = client.post(f"/casos/{req.folio}/derivar", {"categoria": catalogo["cat"].id, "unidad": catalogo["u_plc"].id,
                                                     "instrucciones": "Revisar"}, follow=True)
    assert "Caso derivado a SOME" in r.content.decode()
    hoy = timezone.localdate().isoformat()
    r = client.post(f"/casos/{req.folio}/responder", {"contenido": "Respuesta formal con las medidas adoptadas por el CESFAM.",
                                                       "medio": "EMAIL", "fecha_emision": hoy}, follow=True)
    assert "dentro del plazo legal" in r.content.decode()
    r = client.post(f"/casos/{req.folio}/cerrar", {"comentario": "Enviada"}, follow=True)
    req.refresh_from_db()
    assert req.estado == "CERRADO" and f"Caso {req.folio} cerrado" in r.content.decode()
    assert list(req.historial.values_list("estado_nuevo", flat=True)) == ["INGRESADO", "EN_PROCESO", "RESPONDIDO", "CERRADO"]
    # La base documental no se revierte entre pruebas como PostgreSQL: se filtra por la hora de inicio.
    acciones = {d["accion"] for d in mdb.bitacora_auditoria.find({"folio": req.folio, "ts": {"$gte": inicio}})}
    assert acciones == {"REQUERIMIENTO_DERIVADO", "RESPUESTA_REGISTRADA", "REQUERIMIENTO_CERRADO"}


def test_pi15_ingreso_presencial_asigna_folio_canal_y_establecimiento_del_encargado(client, catalogo, usuarios):
    login(client, usuarios["oirs_plc"])
    datos = {"establecimiento": "CESFAM-PLC", "tipo": "CONSULTA", "descripcion": "Consulta por horario de farmacia (papel)",
             "nombre": "Luis", "telefono": "+56987654321", "acepta_tratamiento_datos": "on"}
    r = client.post("/casos/nuevo", datos)
    assert r.status_code == 200 and "registrado" in r.content.decode()
    req = Requerimiento.objects.get()
    assert req.canal == "PRESENCIAL" and req.establecimiento == catalogo["plc"] and req.creado_por == usuarios["oirs_plc"]
    assert req.folio in r.content.decode()


def test_pi16_ingreso_presencial_rechaza_establecimiento_ajeno_y_datos_incompletos(client, catalogo, usuarios):
    login(client, usuarios["oirs_plc"])
    r = client.post("/casos/nuevo", {"establecimiento": "CESFAM-PUL", "tipo": "RECLAMO", "descripcion": "x" * 20,
                                     "acepta_tratamiento_datos": "on"})
    html = r.content.decode()
    assert Requerimiento.objects.count() == 0
    assert "Revise los siguientes campos" in html and "Requerido para poder responder" in html


def test_pi17_panel_de_plazos_cuenta_semaforo_por_establecimiento(anon, client, catalogo, usuarios):
    vencido = crear_caso(anon)
    crear_caso(anon)
    Requerimiento.objects.filter(pk=vencido.pk).update(fecha_vencimiento=timezone.localdate() - timedelta(days=7),
                                                        fecha_ingreso=timezone.now() - timedelta(days=30))
    login(client, usuarios["dsm"])
    r = client.get("/plazos")
    assert r.status_code == 200
    fila = next(f for f in r.context["resumen"] if f["establecimiento"] == catalogo["plc"])
    assert (fila["abiertos"], fila["ROJO"], fila["VERDE"]) == (2, 1, 1)
    assert [c["req"].folio for c in r.context["criticos"]] == [vencido.folio]


def test_pi18_bandeja_filtra_vencidos_con_semaforo_en_dias_habiles(anon, client, catalogo, usuarios):
    vencido = crear_caso(anon)
    vigente = crear_caso(anon)
    Requerimiento.objects.filter(pk=vencido.pk).update(fecha_vencimiento=timezone.localdate() - timedelta(days=7),
                                                        fecha_ingreso=timezone.now() - timedelta(days=30))
    login(client, usuarios["oirs_plc"])
    r = client.get("/bandeja?estado=vencidos")
    folios = [x.folio for x in r.context["pagina"]]
    assert folios == [vencido.folio] and r.context["ind"]["vencidos"] == 1 and vigente.folio not in folios


def test_pi19_reporte_web_integra_casos_y_encuestas(anon, client, catalogo, usuarios, encuesta, mdb):
    from apps.encuestas import servicio as encuestas
    crear_caso(anon)
    for v in (7, 5):
        encuestas.registrar_respuesta(codigo=encuesta.codigo, establecimiento_codigo="CESFAM-PLC",
                                      respuestas={"p1": v, "p2": v, "p3": v, "p4": v, "p5": v})
    login(client, usuarios["dsm"])
    r = client.get("/reportes")
    datos = r.context["datos"]
    assert datos["total"] == 1
    assert datos["satisfaccion_tabla"][0]["promedio"] == 6.0 and "calidad" in datos["satisfaccion_tabla"][0]["pregunta"]
    assert b'id="datos-graficos"' in r.content and b"Exportar CSV" in r.content
