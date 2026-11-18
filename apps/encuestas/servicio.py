"""Encuestas de satisfacción anónimas (RF02) almacenadas en la base documental.

Anonimato por diseño: el documento no contiene datos personales, IP, agente de usuario ni hora exacta
(solo la fecha), y está físicamente separado de la base que contiene datos de solicitantes."""
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.catalogos.models import Establecimiento
from apps.core.disponibilidad import ERRORES_CACHE
from apps.core.documental import db

from .models import Encuesta

log = logging.getLogger("oirs")
CLAVES_PII = {"nombre", "apellidos", "rut", "run", "email", "correo", "telefono", "fono", "direccion", "ip"}


def definicion(encuesta):
    doc = db().encuesta_definiciones.find_one({"encuesta_id": encuesta.id}, {"_id": 0})
    if not doc:
        raise ValidationError("La encuesta no tiene definición publicada.")
    return doc


def registrar_respuesta(*, codigo, establecimiento_codigo, respuestas: dict, comentario="", canal="WEB"):
    encuesta = Encuesta.objects.filter(codigo=codigo, activa=True).first()
    if not encuesta:
        raise ValidationError("Encuesta no disponible.")
    estab = Establecimiento.objects.filter(codigo=establecimiento_codigo, activo=True).first()
    if not estab:  # integridad referencial validada en la aplicación (cruce entre bases)
        raise ValidationError("Establecimiento inválido.")
    if not isinstance(respuestas, dict) or CLAVES_PII & {k.lower() for k in respuestas}:
        raise ValidationError("La encuesta es anónima: no se aceptan datos personales.")
    preguntas = {p["id"]: p for p in definicion(encuesta)["preguntas"]}
    limpias = {}
    for pid, valor in respuestas.items():
        p = preguntas.get(pid)
        if p is None:
            raise ValidationError(f"Pregunta desconocida: {pid}")
        if p["tipo"] == "escala":
            if not isinstance(valor, int) or not (p["min"] <= valor <= p["max"]):
                raise ValidationError(f"Valor fuera de escala en {pid}")
        elif p["tipo"] == "opcion" and valor not in p["opciones"]:
            raise ValidationError(f"Opción inválida en {pid}")
        limpias[pid] = valor
    faltantes = [pid for pid, p in preguntas.items() if p.get("obligatoria") and pid not in limpias]
    if faltantes:
        raise ValidationError(f"Faltan respuestas obligatorias: {', '.join(faltantes)}")
    documento = {
        "encuesta_id": encuesta.id, "encuesta_codigo": encuesta.codigo, "version": encuesta.version,
        "establecimiento_id": estab.id, "fecha": timezone.localdate().isoformat(), "canal": canal,
        "respuestas": limpias, "comentario": (comentario or "")[:1000],
    }
    db().respuestas_encuesta.insert_one(documento)
    _invalidar_resumen(encuesta.id)
    return documento


def _clave_generacion(encuesta_id):
    return f"resumen-enc-gen:{encuesta_id}"


def _invalidar_resumen(encuesta_id):
    """DEF-06: cada respuesta nueva cambia la «generación» de la clave de caché, de modo que el reporte
    la refleja de inmediato sin renunciar a la caché de 5 minutos entre respuestas (INC-04).
    DEF-18: si la caché está caída, la respuesta YA quedó guardada: no se informa un error (el ciudadano la
    reenviaría y quedaría duplicada). El resumen puede verse desactualizado hasta 5 min tras volver la caché."""
    try:
        try:
            cache.incr(_clave_generacion(encuesta_id))
        except ValueError:                  # la clave aún no existe (o expiró)
            cache.set(_clave_generacion(encuesta_id), 1, None)
    except ERRORES_CACHE as e:
        log.warning("Caché no disponible al invalidar el resumen de la encuesta %s: %s", encuesta_id, type(e).__name__)


def resumen(encuesta_id, establecimiento_id=None, desde=None, hasta=None):
    """Promedio por pregunta (agregación en la base documental), con caché de 5 minutos.
    Si la caché está caída se calcula directamente (DEF-18): más lento, pero el reporte sigue disponible."""
    try:
        generacion = cache.get_or_set(_clave_generacion(encuesta_id), 0, None)
        clave = f"resumen-enc:{encuesta_id}:{generacion}:{establecimiento_id}:{desde}:{hasta}"
        return cache.get_or_set(clave, lambda: _resumen(encuesta_id, establecimiento_id, desde, hasta),
                                settings.CACHE_TTL_REPORTES)
    except ERRORES_CACHE as e:
        log.warning("Caché no disponible; resumen de la encuesta %s calculado sin caché: %s", encuesta_id,
                    type(e).__name__)
        return _resumen(encuesta_id, establecimiento_id, desde, hasta)


def _resumen(encuesta_id, establecimiento_id=None, desde=None, hasta=None):
    filtro = {"encuesta_id": encuesta_id}
    if establecimiento_id:
        filtro["establecimiento_id"] = establecimiento_id
    if desde or hasta:
        filtro["fecha"] = {k: v for k, v in (("$gte", desde), ("$lte", hasta)) if v}
    escalas = [p["id"] for p in db().encuesta_definiciones.find_one({"encuesta_id": encuesta_id})["preguntas"]
               if p["tipo"] == "escala"]
    col = db().respuestas_encuesta
    n = col.count_documents(filtro)
    if not n:
        return []
    resultado = []
    for pid in escalas:  # una agregación por pregunta: portable entre motores compatibles con MongoDB
        suma = list(col.aggregate([{"$match": filtro},
                                   {"$group": {"_id": None, "s": {"$sum": f"$respuestas.{pid}"}}}]))
        resultado.append({"_id": pid, "promedio": round(suma[0]["s"] / n, 2), "n": n})
    return resultado
