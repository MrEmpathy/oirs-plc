"""Indicadores de gestión (RF09). Integra datos estructurados (PostgreSQL) y no estructurados (documental)."""
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q

from apps.cuentas.models import Rol
from apps.encuestas import servicio as encuestas
from apps.encuestas.models import Encuesta
from apps.requerimientos.models import Requerimiento


def indicadores(usuario, desde, hasta, establecimiento_id=None):
    qs = Requerimiento.objects.filter(fecha_ingreso__date__gte=desde, fecha_ingreso__date__lte=hasta)
    if usuario.rol in (Rol.OIRS_EST, Rol.DIRECCION):
        establecimiento_id = usuario.establecimiento_id  # se ignora cualquier filtro distinto (RNF02)
    if establecimiento_id:
        qs = qs.filter(establecimiento_id=establecimiento_id)
    respondidos = qs.filter(respuesta__isnull=False)
    tiempo = respondidos.annotate(t=ExpressionWrapper(F("respuesta__fecha_emision") - F("fecha_ingreso__date"),
                                                      output_field=DurationField())).aggregate(p=Avg("t"))["p"]
    datos = {
        "total": qs.count(),
        "por_tipo": list(qs.values("tipo").annotate(n=Count("id")).order_by("-n")),
        "por_estado": list(qs.values("estado").annotate(n=Count("id")).order_by("estado")),
        "por_establecimiento": list(qs.values("establecimiento__nombre").annotate(n=Count("id")).order_by("-n")),
        "por_categoria": list(qs.values("categoria__nombre").annotate(n=Count("id")).order_by("-n")[:10]),
        "dentro_plazo": respondidos.filter(respuesta__dentro_plazo=True).count(),
        "fuera_plazo": respondidos.filter(respuesta__dentro_plazo=False).count(),
        "tiempo_promedio_dias": round(tiempo.days + tiempo.seconds / 86400, 1) if tiempo else None,
        "satisfaccion": [],
    }
    enc = Encuesta.objects.filter(activa=True).first()
    if enc:
        datos["satisfaccion"] = encuestas.resumen(enc.id, establecimiento_id, desde.isoformat(), hasta.isoformat())
    return datos


PREFIJOS_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def celda_segura(valor):
    """Neutraliza inyección de fórmulas en CSV/Excel (CWE-1236)."""
    texto = "" if valor is None else str(valor)
    return "'" + texto if texto.startswith(PREFIJOS_FORMULA) else texto
