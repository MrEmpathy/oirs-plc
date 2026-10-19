"""Servicio de autenticación: bloqueo por intentos fallidos, MFA TOTP y mensajes genéricos."""
from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import F
from django.utils import timezone

from apps.auditoria import servicio as auditoria

from .models import Usuario

MENSAJE_GENERICO = "Credenciales inválidas o cuenta no disponible."


class ErrorAutenticacion(Exception):
    def __init__(self, mensaje=MENSAJE_GENERICO, requiere_mfa=False):
        super().__init__(mensaje)
        self.requiere_mfa = requiere_mfa


def autenticar(request, email, password, codigo_totp=None, ip=None):
    email = (email or "").strip().lower()
    usuario = Usuario.objects.filter(email=email).first()
    if usuario and usuario.esta_bloqueado:
        auditoria.registrar("LOGIN_BLOQUEADO", usuario=usuario, ip=ip, resultado="DENEGADO")
        raise ErrorAutenticacion()  # mismo mensaje: no revela si la cuenta existe o está bloqueada

    autenticado = authenticate(request, username=email, password=password)
    if autenticado is None:
        if usuario:
            Usuario.objects.filter(pk=usuario.pk).update(intentos_fallidos=F("intentos_fallidos") + 1)
            usuario.refresh_from_db(fields=["intentos_fallidos"])
            if usuario.intentos_fallidos >= settings.LOGIN_MAX_INTENTOS:
                usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=settings.LOGIN_BLOQUEO_MINUTOS)
                usuario.intentos_fallidos = 0
                usuario.save(update_fields=["bloqueado_hasta", "intentos_fallidos"])
                auditoria.registrar("CUENTA_BLOQUEADA", usuario=usuario, ip=ip, resultado="ALERTA")
        auditoria.registrar("LOGIN_FALLIDO", usuario=usuario, ip=ip, resultado="DENEGADO")
        raise ErrorAutenticacion()

    if autenticado.requiere_mfa:
        if not autenticado.mfa_secreto:
            raise ErrorAutenticacion("Debe enrolar un segundo factor antes de ingresar.", requiere_mfa=True)
        if not codigo_totp or not pyotp.TOTP(autenticado.mfa_secreto).verify(codigo_totp, valid_window=1):
            auditoria.registrar("MFA_FALLIDO", usuario=autenticado, ip=ip, resultado="DENEGADO")
            raise ErrorAutenticacion("Código de verificación requerido o inválido.", requiere_mfa=True)

    autenticado.intentos_fallidos, autenticado.bloqueado_hasta = 0, None
    autenticado.last_login = timezone.now()
    autenticado.save(update_fields=["intentos_fallidos", "bloqueado_hasta", "last_login"])
    auditoria.registrar("LOGIN_OK", usuario=autenticado, ip=ip)
    return autenticado
