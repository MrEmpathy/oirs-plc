"""Encuestas de satisfacción anónimas (RF02) almacenadas en la base documental.

Anonimato por diseño: el documento no contiene datos personales, IP, agente de usuario ni hora exacta
(solo la fecha), y está físicamente separado de la base que contiene datos de solicitantes."""
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.catalogos.models import Establecimiento
from apps.core.documental import db

from .models import Encuesta

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
    return documento


def resumen(encuesta_id, establecimiento_id=None, desde=None, hasta=None):
    """Promedio por pregunta (agregación en la base documental), con caché de 5 minutos."""
    clave = f"resumen-enc:{encuesta_id}:{establecimiento_id}:{desde}:{hasta}"
    return cache.get_or_set(clave, lambda: _resumen(encuesta_id, establecimiento_id, desde, hasta),
                            settings.CACHE_TTL_REPORTES)


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
