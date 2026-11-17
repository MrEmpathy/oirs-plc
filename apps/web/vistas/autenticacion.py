"""CU11: inicio de sesión en dos pasos (contraseña + TOTP), enrolamiento del segundo factor, cambio de
contraseña obligatorio y recuperación por correo (sección 7.2)."""
import time

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.auditoria import servicio as auditoria
from apps.core.http import ip_cliente
from apps.cuentas import autenticacion as aut
from apps.cuentas import servicios as cuentas
from apps.cuentas.models import Usuario
from apps.cuentas.permisos import tiene_permiso

from ..formularios import CambioClaveForm, CodigoForm, IngresoForm

PRE_AUTH_SEG = 5 * 60   # tiempo máximo entre la contraseña y el segundo factor


def destino_inicial(usuario):
    if tiene_permiso(usuario, "requerimiento.ver"):
        return reverse("web:bandeja")
    return reverse("web:usuarios")


def _siguiente_seguro(request, usuario):
    sig = request.session.pop("pre_auth_siguiente", "") or request.GET.get("next", "")
    if sig and url_has_allowed_host_and_scheme(sig, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return sig
    return destino_inicial(usuario)   # evita redirecciones abiertas


def _usuario_pre_auth(request):
    datos = request.session.get("pre_auth")
    if not datos or time.time() - datos["ts"] > PRE_AUTH_SEG:
        request.session.pop("pre_auth", None)
        return None
    return Usuario.objects.filter(pk=datos["id"], is_active=True).first()


def _iniciar(request, usuario):
    siguiente = _siguiente_seguro(request, usuario)
    request.session.pop("pre_auth", None)
    request.session.pop("mfa_nuevo", None)
    aut.completar_inicio(usuario, ip=ip_cliente(request))
    login(request, usuario)   # login() rota el identificador de sesión (anti-fijación)
    return redirect(siguiente)


def ingresar(request):
    if request.user.is_authenticated:
        return redirect(destino_inicial(request.user))
    form = IngresoForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        try:
            usuario = aut.verificar_credenciales(request, form.cleaned_data["email"], form.cleaned_data["password"],
                                                 ip=ip_cliente(request))
        except aut.ErrorAutenticacion as e:
            error = str(e)
        else:
            if not aut.necesita_segundo_factor(usuario):
                return _iniciar(request, usuario)
            request.session.cycle_key()
            request.session["pre_auth"] = {"id": usuario.pk, "ts": time.time()}
            request.session["pre_auth_siguiente"] = request.GET.get("next", "")
            return redirect("web:enrolar_mfa" if not usuario.mfa_secreto else "web:verificar_mfa")
    return render(request, "web/auth/ingresar.html", {"form": form, "error": error})


def verificar_mfa(request):
    usuario = _usuario_pre_auth(request)
    if not usuario:
        messages.warning(request, "La verificación expiró. Ingrese nuevamente.")
        return redirect("web:ingresar")
    form = CodigoForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        try:
            aut.verificar_totp(usuario, form.cleaned_data["codigo"], ip=ip_cliente(request))
        except aut.ErrorAutenticacion as e:
            usuario.refresh_from_db()
            if usuario.esta_bloqueado:
                request.session.pop("pre_auth", None)
                messages.error(request, aut.MENSAJE_GENERICO)
                return redirect("web:ingresar")
            error = str(e)
        else:
            return _iniciar(request, usuario)
    return render(request, "web/auth/verificar_mfa.html", {"form": form, "error": error})


def enrolar_mfa(request):
    usuario = _usuario_pre_auth(request)
    if not usuario:
        messages.warning(request, "La verificación expiró. Ingrese nuevamente.")
        return redirect("web:ingresar")
    secreto = request.session.get("mfa_nuevo") or aut.nuevo_secreto_mfa()
    request.session["mfa_nuevo"] = secreto   # se guarda en la cuenta solo cuando el código es correcto
    form = CodigoForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        try:
            aut.enrolar_mfa(usuario, secreto, form.cleaned_data["codigo"], ip=ip_cliente(request))
        except aut.ErrorAutenticacion as e:
            error = str(e)
        else:
            messages.success(request, "Verificación en dos pasos activada.")
            return _iniciar(request, usuario)
    return render(request, "web/auth/enrolar_mfa.html", {
        "form": form, "error": error, "qr": aut.qr_enrolamiento(usuario, secreto),
        "secreto": " ".join(secreto[i:i + 4] for i in range(0, len(secreto), 4))})


@require_POST
def salir(request):
    if request.user.is_authenticated:
        auditoria.registrar("LOGOUT", usuario=request.user, ip=ip_cliente(request))
    logout(request)
    messages.info(request, "Sesión cerrada.")
    return redirect("web:ingresar")


def cambiar_clave(request):
    if not request.user.is_authenticated:
        return redirect("web:ingresar")
    form = CambioClaveForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            cuentas.cambiar_clave_propia(request.user, form.cleaned_data["actual"], form.cleaned_data["nueva"],
                                         ip=ip_cliente(request))
        except ValidationError as e:
            if hasattr(e, "error_dict"):
                for campo, errores in e.message_dict.items():
                    form.add_error(campo, errores)
            else:
                form.add_error("nueva", e.messages)
        else:
            update_session_auth_hash(request, request.user)  # mantiene esta sesión; invalida las demás
            messages.success(request, "Contraseña actualizada.")
            return redirect(destino_inicial(request.user))
    return render(request, "web/auth/cambiar_clave.html", {"form": form, "obligatorio": request.user.debe_cambiar_clave})


class RecuperarClave(auth_views.PasswordResetView):
    """Enlace de un solo uso al correo, válido 30 min; la respuesta no revela si el correo existe."""
    template_name = "web/auth/recuperar.html"
    email_template_name = "web/auth/correo_recuperacion.txt"
    subject_template_name = "web/auth/correo_recuperacion_asunto.txt"
    success_url = reverse_lazy("web:recuperar_enviado")


class RecuperarClaveConfirmar(auth_views.PasswordResetConfirmView):
    template_name = "web/auth/recuperar_confirmar.html"
    success_url = reverse_lazy("web:recuperar_listo")

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        usuario = form.user
        usuario.debe_cambiar_clave = False
        usuario.bloqueado_hasta, usuario.intentos_fallidos = None, 0
        usuario.save(update_fields=["debe_cambiar_clave", "bloqueado_hasta", "intentos_fallidos"])
        auditoria.registrar("CLAVE_RESTABLECIDA", usuario=usuario, ip=ip_cliente(self.request))
        return respuesta
