"""Administración de usuarios (HU07 / CU10). Solo el perfil ADMIN la invoca (permiso usuarios.administrar).

Reglas (sección 7.2): cuentas individuales; contraseña temporal aleatoria con cambio obligatorio en el primer
ingreso; las cuentas se desactivan, nunca se eliminan (trazabilidad); el administrador no ve contraseñas ni
secretos MFA, solo puede restablecerlos."""
import secrets
import string

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.auditoria import servicio as auditoria

from .models import Rol, Usuario

SIMBOLOS = "#$%&*+-=?@"


def clave_temporal(largo=16):
    """Contraseña aleatoria que cumple la política (mayúscula, minúscula, dígito y símbolo)."""
    alfabeto = string.ascii_letters + string.digits + SIMBOLOS
    while True:
        clave = "".join(secrets.choice(alfabeto) for _ in range(largo))
        if (any(c.isupper() for c in clave) and any(c.islower() for c in clave)
                and any(c.isdigit() for c in clave) and any(c in SIMBOLOS for c in clave)):
            return clave


def _exigir_admin(admin):
    if admin.rol != Rol.ADMIN:
        raise PermissionDenied


@transaction.atomic
def crear_usuario(admin, *, email, nombre, apellidos, rol, establecimiento=None):
    """Devuelve (usuario, clave_temporal). La clave se muestra una sola vez al administrador."""
    _exigir_admin(admin)
    if Usuario.objects.filter(email__iexact=email).exists():
        raise ValidationError("Ya existe una cuenta con ese correo.")
    clave = clave_temporal()
    usuario = Usuario.objects.create_user(email, clave, nombre=nombre, apellidos=apellidos, rol=rol,
                                          establecimiento=establecimiento if rol in ("OIRS_EST", "DIRECCION") else None,
                                          debe_cambiar_clave=True)
    auditoria.registrar("USUARIO_CREADO", usuario=admin, usuario_afectado=usuario.id, rol_asignado=rol)
    return usuario, clave


@transaction.atomic
def actualizar_usuario(admin, usuario, *, nombre, apellidos, rol, establecimiento=None):
    _exigir_admin(admin)
    if usuario.pk == admin.pk and rol != Rol.ADMIN:
        raise ValidationError("No puede quitarse a sí mismo el perfil de administrador.")
    anterior = usuario.rol
    usuario.nombre, usuario.apellidos, usuario.rol = nombre, apellidos, rol
    usuario.establecimiento = establecimiento if rol in ("OIRS_EST", "DIRECCION") else None
    usuario.full_clean(exclude=["password"])
    usuario.save()
    auditoria.registrar("USUARIO_MODIFICADO", usuario=admin, usuario_afectado=usuario.id,
                        rol_anterior=anterior, rol_nuevo=rol)
    return usuario


def cambiar_estado(admin, usuario, activo):
    _exigir_admin(admin)
    if usuario.pk == admin.pk and not activo:
        raise ValidationError("No puede desactivar su propia cuenta.")
    usuario.is_active = activo
    usuario.save(update_fields=["is_active"])
    auditoria.registrar("USUARIO_ACTIVADO" if activo else "USUARIO_DESACTIVADO", usuario=admin,
                        usuario_afectado=usuario.id)


def desbloquear(admin, usuario):
    _exigir_admin(admin)
    usuario.bloqueado_hasta, usuario.intentos_fallidos = None, 0
    usuario.save(update_fields=["bloqueado_hasta", "intentos_fallidos"])
    auditoria.registrar("USUARIO_DESBLOQUEADO", usuario=admin, usuario_afectado=usuario.id)


def restablecer_mfa(admin, usuario):
    """Borra el secreto TOTP (p. ej., teléfono perdido): el usuario deberá enrolar uno nuevo al ingresar."""
    _exigir_admin(admin)
    usuario.mfa_secreto = ""
    usuario.save(update_fields=["mfa_secreto"])
    auditoria.registrar("MFA_RESTABLECIDO", usuario=admin, usuario_afectado=usuario.id)


def restablecer_clave(admin, usuario):
    _exigir_admin(admin)
    clave = clave_temporal()
    usuario.set_password(clave)
    usuario.debe_cambiar_clave = True
    usuario.save(update_fields=["password", "debe_cambiar_clave"])
    auditoria.registrar("CLAVE_TEMPORAL_EMITIDA", usuario=admin, usuario_afectado=usuario.id)
    return clave


def cambiar_clave_propia(usuario, actual, nueva, ip=None):
    """Cambio de contraseña por el propio usuario (obligatorio tras una contraseña temporal)."""
    if not usuario.check_password(actual):
        raise ValidationError({"actual": "La contraseña actual no es correcta."})
    if actual == nueva:
        raise ValidationError({"nueva": "La nueva contraseña debe ser distinta de la actual."})
    validate_password(nueva, usuario)
    usuario.set_password(nueva)
    usuario.debe_cambiar_clave = False
    usuario.save(update_fields=["password", "debe_cambiar_clave"])
    auditoria.registrar("CLAVE_CAMBIADA", usuario=usuario, ip=ip)
