"""Menú lateral construido desde la misma matriz de permisos que usa el servidor (sección 5.2):
la interfaz nunca ofrece una acción que el servidor rechazaría."""
from apps.cuentas.permisos import tiene_permiso

OPCIONES = [
    ("web:bandeja", "Bandeja de casos", "requerimiento.ver", "bandeja"),
    ("web:ingreso_presencial", "Ingreso presencial", "requerimiento.ingresar_presencial", "presencial"),
    ("web:panel_plazos", "Panel de plazos", "plazos.panel_red", "plazos"),
    ("web:reportes", "Reportes", "reportes.ver", "reportes"),
    ("web:usuarios", "Usuarios", "usuarios.administrar", "usuarios"),
    ("web:catalogos", "Catálogos", "catalogos.administrar", "catalogos"),
]


def menu(request):
    usuario = getattr(request, "user", None)
    if not usuario or not usuario.is_authenticated:
        return {"menu": []}
    return {"menu": [{"url": url, "texto": texto, "clave": clave}
                     for url, texto, permiso, clave in OPCIONES if tiene_permiso(usuario, permiso)]}
