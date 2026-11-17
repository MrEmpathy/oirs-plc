"""Anonimiza los datos personales de solicitantes cuyos casos están cerrados y superan el plazo de
retención (sección 6.1). Conserva el caso y sus datos estadísticos (tipo, establecimiento, plazos).

Uso: python manage.py anonimizar_solicitantes [--dias N] [--simular]
Programación sugerida: diaria, después del respaldo de las 02:00 (cron del servidor)."""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.auditoria import servicio as auditoria
from apps.requerimientos.models import Requerimiento, Solicitante


class Command(BaseCommand):
    help = "Anonimiza solicitantes de casos cerrados que superan el plazo de retención."

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=settings.RETENCION_DATOS_PERSONALES_DIAS)
        parser.add_argument("--simular", action="store_true", help="Solo informa cuántos registros se anonimizarían.")

    @transaction.atomic
    def handle(self, *args, dias, simular, **opts):
        limite = timezone.now() - timedelta(days=dias)
        # Un solicitante se anonimiza solo si NINGUNO de sus casos sigue abierto o es reciente.
        pendientes = Requerimiento.objects.filter(solicitante=OuterRef("pk")).exclude(estado="CERRADO", fecha_ingreso__lt=limite)
        candidatos = (Solicitante.objects.filter(anonimizado=False, requerimientos__isnull=False)
                      .exclude(Exists(pendientes)).distinct())
        total = candidatos.count()
        if not simular and total:
            Solicitante.objects.filter(pk__in=list(candidatos.values_list("pk", flat=True))).update(
                nombre="ANONIMIZADO", apellidos="", email="", telefono="", edad=None, sexo="",
                autoriza_respuesta_email=False, anonimizado=True)
            auditoria.registrar("SOLICITANTES_ANONIMIZADOS", cantidad=total, retencion_dias=dias)
        self.stdout.write(self.style.SUCCESS(
            f"{'[simulación] ' if simular else ''}Solicitantes anonimizados: {total} (retención {dias} días)."))
