"""Acceso a la base documental (MongoDB). Una sola conexión por proceso (pool interno de pymongo)."""
from functools import lru_cache

from django.conf import settings
from pymongo import ASCENDING, MongoClient


@lru_cache(maxsize=1)
def _cliente():
    return MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000, tz_aware=True)


def db():
    return _cliente()[settings.MONGO_DB]


def asegurar_indices():
    d = db()
    d.respuestas_encuesta.create_index([("encuesta_id", ASCENDING), ("establecimiento_id", ASCENDING),
                                        ("fecha", ASCENDING)], name="ix_resp_enc_estab_fecha")
    d.bitacora_auditoria.create_index([("ts", ASCENDING)], name="ix_bit_ts")
    d.bitacora_auditoria.create_index([("folio", ASCENDING)], name="ix_bit_folio")
    d.encuesta_definiciones.create_index([("encuesta_id", ASCENDING)], name="ux_def_encuesta", unique=True)
