"""Páginas de error: mensaje genérico y una salida clara. Para rutas /api/ se responde JSON."""
import sys

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from apps.core import disponibilidad
from apps.core.http import JsonSeguro


def _respuesta(request, codigo, titulo, texto):
    if request.path.startswith("/api/"):
        return JsonSeguro({"error": titulo}, status=codigo)
    return render(request, "web/error.html", {"codigo": codigo, "titulo": titulo, "texto": texto}, status=codigo)


def prohibido(request, exception=None):
    return _respuesta(request, 403, "No autorizado", "Su perfil no tiene permiso para esta acción.")


def no_encontrado(request, exception=None):
    return _respuesta(request, 404, "No encontrado", "La página o el caso que busca no existe o no está disponible para su perfil.")


def error_interno(request):
    """Se dibuja sin la petición: los procesadores de contexto (menú, usuario) consultan la sesión en PostgreSQL y,
    si la falla es justamente la base caída, la página de error también fallaría (DEF-16). Ante una caída de una
    base o de la caché responde 503 «Servicio no disponible» con Retry-After."""
    if disponibilidad.es_caida(sys.exc_info()[1]):
        codigo, titulo, texto = 503, disponibilidad.TITULO, disponibilidad.TEXTO
    else:
        codigo, titulo = 500, "Error interno"
        texto = "Ocurrió un problema. Intente nuevamente; si persiste, avise al administrador."
    if request.path.startswith("/api/"):
        resp = JsonSeguro({"error": titulo}, status=codigo)
    else:
        resp = HttpResponse(render_to_string("web/error.html", {"codigo": codigo, "titulo": titulo, "texto": texto}),
                            status=codigo)
    if codigo == 503:
        resp["Retry-After"] = str(disponibilidad.REINTENTAR_EN_SEG)
    return resp
