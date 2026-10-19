"""Carga catálogos base, usuarios de prueba por perfil y la encuesta inicial (datos de desarrollo)."""
import os
import random
from datetime import date, timedelta

import holidays
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalogos.models import Categoria, Establecimiento, Feriado, Unidad
from apps.core.documental import asegurar_indices, db
from apps.cuentas.models import Usuario
from apps.encuestas.models import Encuesta

ESTABLECIMIENTOS = [
    ("DSM", "Departamento de Salud Municipal", "DSM"),
    ("CESFAM-PLC", "CESFAM Padre Las Casas", "CESFAM"),
    ("CESFAM-PUL", "CESFAM Pulmahue", "CESFAM"),
    ("CESFAM-CON", "CESFAM Conunhuenu", "CESFAM"),
    ("SAPU-PLC", "SAPU Padre Las Casas", "SAPU"),
    ("PSR-01", "Posta de Salud Rural 1 (dato de prueba)", "POSTA"),
]
UNIDADES = ["Dirección", "SOME", "Sector Azul", "Sector Rojo", "Farmacia", "Dental", "Urgencia"]
CATEGORIAS = [
    ("Calidad de la atención", "Resolutividad y calidad técnica de la prestación"),
    ("Tiempos de espera", "Demora en sala de espera o en la asignación de horas"),
    ("Trato recibido", "Amabilidad y respeto del personal"),
    ("Presentación del personal", "Identificación y presentación del funcionario"),
    ("Información e indicaciones", "Claridad de indicaciones, horarios y procedimientos"),
    ("Infraestructura y equipamiento", "Estado de instalaciones, accesibilidad y equipos"),
    ("Gestión administrativa", "Documentos, certificados, derivaciones e interconsultas"),
]
PREGUNTAS = [
    {"id": "p1", "texto": "¿Cómo evalúa la calidad de la atención recibida?", "tipo": "escala", "min": 1, "max": 7, "obligatoria": True},
    {"id": "p2", "texto": "¿Cómo evalúa el tiempo de espera?", "tipo": "escala", "min": 1, "max": 7, "obligatoria": True},
    {"id": "p3", "texto": "¿Cómo evalúa el trato recibido?", "tipo": "escala", "min": 1, "max": 7, "obligatoria": True},
    {"id": "p4", "texto": "¿Cómo evalúa la presentación e identificación del personal?", "tipo": "escala", "min": 1, "max": 7, "obligatoria": True},
    {"id": "p5", "texto": "¿Las indicaciones entregadas fueron claras?", "tipo": "escala", "min": 1, "max": 7, "obligatoria": True},
    {"id": "p6", "texto": "Tipo de atención recibida", "tipo": "opcion", "obligatoria": False,
     "opciones": ["Médica", "Enfermería", "Dental", "Matrona", "Kinesiología", "SOME / administrativa", "Otra"]},
]
CLAVE_DEMO = os.environ.get("CLAVE_DEMO", "Demo#Oirs2026!")


class Command(BaseCommand):
    help = "Siembra datos de desarrollo"

    @transaction.atomic
    def handle(self, *args, **opts):
        ests = {}
        for cod, nom, tipo in ESTABLECIMIENTOS:
            ests[cod], _ = Establecimiento.objects.get_or_create(codigo=cod, defaults={"nombre": nom, "tipo": tipo})
        for e in ests.values():
            if e.tipo != "DSM":
                for u in UNIDADES:
                    Unidad.objects.get_or_create(establecimiento=e, nombre=u)
        for nom, desc in CATEGORIAS:
            Categoria.objects.get_or_create(nombre=nom, defaults={"descripcion": desc})
        Categoria.objects.get_or_create(nombre="Otro", defaults={"descripcion": "Casos no contemplados", "es_otro": True})
        cl = holidays.Chile(years=[2025, 2026, 2027])
        for f, d in cl.items():
            Feriado.objects.get_or_create(fecha=f, defaults={"descripcion": d[:120]})
        usuarios = [
            ("admin@dsm.test", "Ana", "Administradora", "ADMIN", None),
            ("oirs.dsm@dsm.test", "Daniel", "Supervisor", "OIRS_DSM", None),
            ("oirs.plc@dsm.test", "Olga", "Encargada PLC", "OIRS_EST", ests["CESFAM-PLC"]),
            ("oirs.pul@dsm.test", "Pedro", "Encargado Pulmahue", "OIRS_EST", ests["CESFAM-PUL"]),
            ("dir.plc@dsm.test", "Diana", "Directora PLC", "DIRECCION", ests["CESFAM-PLC"]),
        ]
        for email, n, a, rol, est in usuarios:
            if not Usuario.objects.filter(email=email).exists():
                Usuario.objects.create_user(email, CLAVE_DEMO, nombre=n, apellidos=a, rol=rol, establecimiento=est)
        enc, _ = Encuesta.objects.get_or_create(codigo="satisfaccion-usuaria", version=1,
                                                defaults={"nombre": "Encuesta de satisfacción usuaria",
                                                          "activa": True, "fecha_publicacion": date(2026, 10, 1)})
        asegurar_indices()
        db().encuesta_definiciones.update_one(
            {"encuesta_id": enc.id},
            {"$set": {"encuesta_id": enc.id, "codigo": enc.codigo, "version": enc.version,
                      "escala": "1 a 7", "preguntas": PREGUNTAS}}, upsert=True)
        self.stdout.write(self.style.SUCCESS(
            f"Establecimientos={Establecimiento.objects.count()} Unidades={Unidad.objects.count()} "
            f"Categorías={Categoria.objects.count()} Feriados={Feriado.objects.count()} "
            f"Usuarios={Usuario.objects.count()} Encuesta={enc}"))
