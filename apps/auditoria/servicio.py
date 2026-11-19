"""Bitácora de auditoría de seguridad en la base documental (eventos de esquema variable).

Regla SC-07: nunca se registran contraseñas, tokens ni datos personales del solicitante; la IP se
almacena truncada (/24) para equilibrar trazabilidad y minimización."""
import ipaddress
import json
import logging
import time

from django.utils import timezone

from apps.core.disponibilidad import REINTENTAR_EN_SEG
from apps.core.documental import db_bitacora as db

log = logging.getLogger("oirs")
_documental_caida_hasta = 0.0   # mientras la base documental está caída no se reintenta en cada evento (DEF-19)
CAMPOS_PROHIBIDOS = {"password", "clave", "token", "codigo_totp", "email", "telefono", "nombre", "apellidos"}


def _ip_truncada(ip):
    try:
        red = ipaddress.ip_network(f"{ip}/24", strict=False) if ":" not in ip else ipaddress.ip_network(f"{ip}/48", strict=False)
        return str(red)
    except (ValueError, TypeError):
        return None


def registrar(accion, *, usuario=None, folio=None, ip=None, resultado="OK", **detalle):
    limpio = {k: v for k, v in detalle.items() if k.lower() not in CAMPOS_PROHIBIDOS}
    evento = {
        "ts": timezone.now(),
        "accion": accion,
        "resultado": resultado,
        "usuario_id": getattr(usuario, "id", None),
        "rol": getattr(usuario, "rol", None),
        "folio": folio,
        "red_origen": _ip_truncada(ip) if ip else None,
        "detalle": limpio,
    }
    global _documental_caida_hasta
    if time.monotonic() >= _documental_caida_hasta:
        try:
            db().bitacora_auditoria.insert_one(dict(evento))
            return evento
        except Exception as e:  # la falla de auditoría no se expone al usuario ni interrumpe su operación
            _documental_caida_hasta = time.monotonic() + REINTENTAR_EN_SEG
            log.warning("Bitácora documental no disponible (%s): los eventos se respaldan en el registro de la "
                        "aplicación durante %s s", type(e).__name__, REINTENTAR_EN_SEG)
    # Respaldo (DEF-19): el evento completo (ya sin datos personales) queda en el registro de la aplicación y
    # puede reincorporarse a la bitácora buscando la marca BITACORA_RESPALDO.
    log.warning("BITACORA_RESPALDO %s", json.dumps(evento, default=str, ensure_ascii=False))
    return evento
