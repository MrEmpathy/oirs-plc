"""Proceso nocturno de consistencia entre bases (sección 6.5, Tabla 16): informa los documentos de la base
documental que apuntan a registros inexistentes en PostgreSQL (referencias huérfanas). No modifica datos.

Uso: python manage.py verificar_referencias   (código de salida 1 si encuentra huérfanos)"""
import sys

from django.core.management.base import BaseCommand

from apps.auditoria import servicio as auditoria
from apps.catalogos.models import Establecimiento
from apps.core.documental import db
from apps.encuestas.models import Encuesta
from apps.requerimientos.models import Requerimiento


class Command(BaseCommand):
    help = "Detecta referencias huérfanas entre la base documental y PostgreSQL."

    def handle(self, *args, **opts):
        d = db()
        est_ok = set(Establecimiento.objects.values_list("id", flat=True))
        enc_ok = set(Encuesta.objects.values_list("id", flat=True))
        hallazgos = {
            "respuestas_encuesta.establecimiento_id": sorted(set(d.respuestas_encuesta.distinct("establecimiento_id")) - est_ok),
            "respuestas_encuesta.encuesta_id": sorted(set(d.respuestas_encuesta.distinct("encuesta_id")) - enc_ok),
            "encuesta_definiciones.encuesta_id": sorted(set(d.encuesta_definiciones.distinct("encuesta_id")) - enc_ok),
        }
        folios = {f for f in d.bitacora_auditoria.distinct("folio") if f}
        existentes = set(Requerimiento.objects.filter(folio__in=folios).values_list("folio", flat=True))
        hallazgos["bitacora_auditoria.folio"] = sorted(folios - existentes)
        total = sum(len(v) for v in hallazgos.values())
        for campo, valores in hallazgos.items():
            estado = "OK" if not valores else f"{len(valores)} huérfano(s): {valores[:10]}"
            self.stdout.write(f"{campo:42} {estado}")
        auditoria.registrar("VERIFICACION_REFERENCIAS", resultado="OK" if not total else "ALERTA", huerfanos=total)
        if total:
            self.stderr.write(self.style.ERROR(f"Se encontraron {total} referencias huérfanas."))
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS("Sin referencias huérfanas."))
