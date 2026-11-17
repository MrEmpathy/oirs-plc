"""Autorización en el front administrativo: misma matriz que la API (apps/cuentas/permisos.py).
Sin sesión → página de ingreso; sin permiso → 403 auditado. Ocultar un botón nunca reemplaza esta validación."""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from apps.auditoria import servicio as auditoria
from apps.core.http import ip_cliente
from apps.cuentas.permisos import tiene_permiso


def permiso_web(accion):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not tiene_permiso(request.user, accion):
                auditoria.registrar("ACCESO_DENEGADO", usuario=request.user, resultado="DENEGADO",
                                    accion_solicitada=accion, ruta=request.path, ip=ip_cliente(request))
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador
