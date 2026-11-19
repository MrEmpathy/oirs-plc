"""Fallas de infraestructura (una base de datos o la caché caída) frente a errores de programación.

Una base caída no es un error interno: el sistema responde 503 «Servicio no disponible» con Retry-After, sin
detalles técnicos, y vuelve a funcionar solo cuando la base regresa (E2E-10, DEF-16 a DEF-19)."""
from django.db import InterfaceError, OperationalError
from pymongo.errors import ConnectionFailure

try:
    from redis.exceptions import ConnectionError as _RedisConexion
    from redis.exceptions import TimeoutError as _RedisTiempo
    ERRORES_CACHE = (_RedisConexion, _RedisTiempo)
except ImportError:  # sin Redis instalado la caché es local en memoria y no puede «caerse»
    ERRORES_CACHE = ()

# ConnectionFailure incluye ServerSelectionTimeoutError y AutoReconnect de pymongo.
SERVICIO_CAIDO = (OperationalError, InterfaceError, ConnectionFailure) + ERRORES_CACHE
REINTENTAR_EN_SEG = 30
TITULO = "Servicio no disponible"
TEXTO = ("El sistema no puede atender en este momento por una falla temporal. La información ya guardada está "
         "segura. Intente nuevamente en unos minutos.")


def es_caida(exc):
    return isinstance(exc, SERVICIO_CAIDO)
