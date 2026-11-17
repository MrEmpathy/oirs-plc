"""Páginas de error: mensaje genérico y una salida clara. Para rutas /api/ se responde JSON."""
from django.shortcuts import render

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
    return _respuesta(request, 500, "Error interno", "Ocurrió un problema. Intente nuevamente; si persiste, avise al administrador.")
