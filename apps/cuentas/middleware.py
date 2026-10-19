class CabecerasSeguridadMiddleware:
    """Agrega Content-Security-Policy y Permissions-Policy a todas las respuestas (mitigación XSS)."""
    CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
           "object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        respuesta.setdefault("Content-Security-Policy", self.CSP)
        respuesta.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        respuesta.setdefault("Cache-Control", "no-store")
        return respuesta
