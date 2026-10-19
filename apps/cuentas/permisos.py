"""Autorización basada en roles (RBAC) a nivel de vista. Deniega por defecto (SC-03)."""
from functools import wraps

from django.http import JsonResponse

from apps.auditoria import servicio as auditoria

# Matriz de permisos: acción -> roles autorizados
PERMISOS = {
    "requerimiento.ver": {"ADMIN", "OIRS_DSM", "OIRS_EST", "DIRECCION"},
    "requerimiento.ingresar_presencial": {"OIRS_EST"},
    "requerimiento.gestionar": {"OIRS_EST"},  # clasificar, derivar, responder, cerrar
    "plazos.panel_red": {"OIRS_DSM", "ADMIN"},
    "reportes.ver": {"OIRS_DSM", "DIRECCION", "OIRS_EST"},
    "reportes.exportar": {"OIRS_DSM"},
    "usuarios.administrar": {"ADMIN"},
    "catalogos.administrar": {"ADMIN"},
}


def tiene_permiso(usuario, accion):
    return bool(usuario and usuario.is_authenticated and usuario.is_active
                and usuario.rol in PERMISOS.get(accion, set()))


def requiere_permiso(accion):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({"error": "No autenticado"}, status=401)
            if not tiene_permiso(request.user, accion):
                auditoria.registrar("ACCESO_DENEGADO", usuario=request.user, resultado="DENEGADO",
                                    accion_solicitada=accion, ruta=request.path)
                return JsonResponse({"error": "No autorizado"}, status=403)
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador
