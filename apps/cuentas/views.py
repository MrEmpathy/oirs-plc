from django.contrib.auth import login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from apps.auditoria import servicio as auditoria
from apps.core.http import JsonSeguro, ip_cliente, leer_json, manejar_errores

from .autenticacion import ErrorAutenticacion, autenticar


@require_POST
@manejar_errores
def iniciar_sesion(request):
    d = leer_json(request)
    try:
        usuario = autenticar(request, d.get("email"), d.get("password"), d.get("codigo_totp"), ip=ip_cliente(request))
    except ErrorAutenticacion as e:
        return JsonSeguro({"error": str(e), "requiere_mfa": e.requiere_mfa}, status=401)
    request.session.cycle_key()  # previene fijación de sesión
    login(request, usuario)
    return JsonSeguro({"ok": True, "rol": usuario.rol, "debe_cambiar_clave": usuario.debe_cambiar_clave})


@require_POST
def cerrar_sesion(request):
    if request.user.is_authenticated:
        auditoria.registrar("LOGOUT", usuario=request.user, ip=ip_cliente(request))
    logout(request)
    return JsonSeguro({"ok": True})


@require_GET
@ensure_csrf_cookie
def token_csrf(request):
    """Entrega la cookie csrftoken al front administrativo antes del login (patrón double-submit)."""
    return JsonSeguro({"ok": True})
