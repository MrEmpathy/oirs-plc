"""Bitácora de auditoría de seguridad en la base documental (eventos de esquema variable).

Regla SC-07: nunca se registran contraseñas, tokens ni datos personales del solicitante; la IP se
almacena truncada (/24) para equilibrar trazabilidad y minimización."""
import ipaddress
import logging

from django.utils import timezone

from apps.core.documental import db

log = logging.getLogger("oirs")
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
    try:
        db().bitacora_auditoria.insert_one(evento)
    except Exception:  # la falla de auditoría se registra pero no expone detalles al usuario
        log.exception("No fue posible escribir en la bitácora documental: %s", accion)
    return evento
