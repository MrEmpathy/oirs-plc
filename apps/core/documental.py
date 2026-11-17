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
    _indice_ttl_bitacora(d.bitacora_auditoria)
    d.bitacora_auditoria.create_index([("folio", ASCENDING)], name="ix_bit_folio")
    d.encuesta_definiciones.create_index([("encuesta_id", ASCENDING)], name="ux_def_encuesta", unique=True)


def _indice_ttl_bitacora(coleccion):
    """Retención de la bitácora (sección 4.7): MongoDB elimina los eventos más antiguos que el plazo
    configurado mediante un índice TTL. Si el índice previo no tiene TTL o tiene otro plazo, se recrea."""
    segundos = settings.RETENCION_BITACORA_DIAS * 86400
    for nombre, info in coleccion.index_information().items():
        if info.get("key") == [("ts", 1)] and info.get("expireAfterSeconds") != segundos:
            coleccion.drop_index(nombre)
    coleccion.create_index([("ts", ASCENDING)], name="ttl_bit_ts", expireAfterSeconds=segundos)
