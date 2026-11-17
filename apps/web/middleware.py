from django.shortcuts import redirect
from django.urls import reverse

RUTAS_PERMITIDAS = ("/cuenta/clave", "/salir", "/static/")


class CambioClaveObligatorioMiddleware:
    """Contraseña temporal: obliga a cambiarla en el primer ingreso antes de usar el sistema (sección 7.2).
    Solo actúa sobre el front administrativo; la API JSON informa el estado en la respuesta de inicio de sesión."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        if (usuario is not None and usuario.is_authenticated and usuario.debe_cambiar_clave
                and not request.path.startswith("/api/") and not request.path.startswith(RUTAS_PERMITIDAS)):
            return redirect(reverse("web:cambiar_clave"))
        return self.get_response(request)
