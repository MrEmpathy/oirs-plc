"""Servicio de autenticación: bloqueo por intentos fallidos, MFA TOTP y mensajes genéricos (sección 7.2).

Se divide en pasos para que el front administrativo pida el segundo factor en una pantalla aparte:
    verificar_credenciales() -> verificar_totp() / enrolar_mfa() -> completar_inicio()
`autenticar()` combina los pasos en una sola llamada para la API JSON."""
from datetime import timedelta

import pyotp
import segno
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


def _registrar_fallo(usuario, ip):
    """Suma un intento fallido (contraseña o segundo factor); al quinto bloquea la cuenta 15 minutos."""
    if not usuario:
        return
    Usuario.objects.filter(pk=usuario.pk).update(intentos_fallidos=F("intentos_fallidos") + 1)
    usuario.refresh_from_db(fields=["intentos_fallidos"])
    if usuario.intentos_fallidos >= settings.LOGIN_MAX_INTENTOS:
        usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=settings.LOGIN_BLOQUEO_MINUTOS)
        usuario.intentos_fallidos = 0
        usuario.save(update_fields=["bloqueado_hasta", "intentos_fallidos"])
        auditoria.registrar("CUENTA_BLOQUEADA", usuario=usuario, ip=ip, resultado="ALERTA")


def verificar_credenciales(request, email, password, ip=None):
    """Paso 1: correo y contraseña. Devuelve el usuario sin iniciar sesión todavía."""
    email = (email or "").strip().lower()
    usuario = Usuario.objects.filter(email=email).first()
    if usuario and usuario.esta_bloqueado:
        auditoria.registrar("LOGIN_BLOQUEADO", usuario=usuario, ip=ip, resultado="DENEGADO")
        raise ErrorAutenticacion()  # mismo mensaje: no revela si la cuenta existe o está bloqueada
    autenticado = authenticate(request, username=email, password=password)
    if autenticado is None:
        _registrar_fallo(usuario, ip)
        auditoria.registrar("LOGIN_FALLIDO", usuario=usuario, ip=ip, resultado="DENEGADO")
        raise ErrorAutenticacion()
    return autenticado


def necesita_segundo_factor(usuario):
    """Obligatorio para perfiles con acceso a toda la red; opcional (si lo enroló) para el resto."""
    return usuario.requiere_mfa or bool(usuario.mfa_secreto)


def verificar_totp(usuario, codigo, ip=None, secreto=None):
    """Paso 2: código TOTP (RFC 6238) con tolerancia de ±30 s. Un error cuenta como intento fallido."""
    secreto = secreto or usuario.mfa_secreto
    codigo = (codigo or "").replace(" ", "")
    if usuario.esta_bloqueado:
        raise ErrorAutenticacion()
    if not secreto or not codigo.isdigit() or not pyotp.TOTP(secreto).verify(codigo, valid_window=1):
        _registrar_fallo(usuario, ip)
        auditoria.registrar("MFA_FALLIDO", usuario=usuario, ip=ip, resultado="DENEGADO")
        raise ErrorAutenticacion("Código de verificación inválido.", requiere_mfa=True)


def nuevo_secreto_mfa():
    return pyotp.random_base32()


def qr_enrolamiento(usuario, secreto):
    """Código QR (SVG en línea, sin servicios externos) para registrar el secreto en la app autenticadora."""
    uri = pyotp.TOTP(secreto).provisioning_uri(name=usuario.email, issuer_name=settings.MFA_EMISOR)
    # omitsize: sin width/height fijos y con viewBox, para que el CSS lo escale completo. Con tamaño fijo, el SVG
    # (≈ 250 px) se recortaba a 190 px: perdía el margen y módulos del borde derecho e inferior (DEF-15).
    return segno.make(uri, error="m").svg_inline(omitsize=True, dark="#1e293b", light="#ffffff")


def enrolar_mfa(usuario, secreto, codigo, ip=None):
    """Guarda el secreto solo después de comprobar que el usuario lo registró correctamente."""
    verificar_totp(usuario, codigo, ip=ip, secreto=secreto)
    usuario.mfa_secreto = secreto
    usuario.save(update_fields=["mfa_secreto"])
    auditoria.registrar("MFA_ENROLADO", usuario=usuario, ip=ip)


def completar_inicio(usuario, ip=None):
    usuario.intentos_fallidos, usuario.bloqueado_hasta = 0, None
    usuario.last_login = timezone.now()
    usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta", "last_login"])
    auditoria.registrar("LOGIN_OK", usuario=usuario, ip=ip)
    return usuario


def autenticar(request, email, password, codigo_totp=None, ip=None):
    """Inicio de sesión en un solo paso (API JSON)."""
    usuario = verificar_credenciales(request, email, password, ip=ip)
    if usuario.requiere_mfa and not usuario.mfa_secreto:
        raise ErrorAutenticacion("Debe enrolar un segundo factor antes de ingresar.", requiere_mfa=True)
    if necesita_segundo_factor(usuario):
        if not codigo_totp:
            raise ErrorAutenticacion("Código de verificación requerido.", requiere_mfa=True)
        verificar_totp(usuario, codigo_totp, ip=ip)
    return completar_inicio(usuario, ip=ip)
