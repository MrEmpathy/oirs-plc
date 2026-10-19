"""Genera volumen sintético para pruebas de rendimiento: ~3 años de operación de la red.
Uso: python manage.py shell < tests/performance/cargar_volumen.py"""
import random
from datetime import timedelta

from django.utils import timezone

from apps.catalogos.models import Categoria, Establecimiento, Unidad
from apps.core.documental import db
from apps.encuestas.models import Encuesta
from apps.requerimientos.models import HistorialEstado, Requerimiento

random.seed(42)
N = 20000
ests = list(Establecimiento.objects.exclude(tipo="DSM"))
cats = list(Categoria.objects.all())
unidades = {e.id: list(Unidad.objects.filter(establecimiento=e)) for e in ests}
tipos = ["RECLAMO"] * 5 + ["SUGERENCIA"] * 2 + ["CONSULTA"] * 2 + ["SOLICITUD", "FELICITACION"]
ahora = timezone.now()
reqs = []
for i in range(1, N + 1):
    e = random.choice(ests)
    ingreso = ahora - timedelta(days=random.randint(0, 1000), minutes=random.randint(0, 1440))
    estado = random.choices(["INGRESADO", "EN_PROCESO", "RESPONDIDO", "CERRADO"], [3, 7, 10, 80])[0]
    reqs.append(Requerimiento(
        folio=f"PLC-HIST-{i:06d}", tipo=random.choice(tipos), canal=random.choice(["WEB", "PRESENCIAL"]),
        establecimiento=e, categoria=random.choice(cats) if estado != "INGRESADO" else None,
        descripcion="Requerimiento sintético para prueba de volumen " + str(i), fecha_ingreso=ingreso,
        fecha_vencimiento=(ingreso + timedelta(days=21)).date(), estado=estado,
        unidad_derivada=random.choice(unidades[e.id]) if estado != "INGRESADO" else None))
Requerimiento.objects.bulk_create(reqs, batch_size=2000)
creados = Requerimiento.objects.filter(folio__startswith="PLC-HIST-")
HistorialEstado.objects.bulk_create([HistorialEstado(requerimiento=r, estado_nuevo="INGRESADO", accion="INGRESO",
                                                     fecha=r.fecha_ingreso) for r in creados], batch_size=5000)
enc = Encuesta.objects.get(codigo="satisfaccion-usuaria", activa=True)
docs = [{"encuesta_id": enc.id, "encuesta_codigo": enc.codigo, "version": 1,
         "establecimiento_id": random.choice(ests).id,
         "fecha": (ahora - timedelta(days=random.randint(0, 365))).date().isoformat(), "canal": "WEB",
         "respuestas": {f"p{k}": random.randint(3, 7) for k in range(1, 6)}, "comentario": ""} for _ in range(5000)]
db().respuestas_encuesta.insert_many(docs)
print("Requerimientos:", Requerimiento.objects.count(), "Encuestas:", db().respuestas_encuesta.count_documents({}))
