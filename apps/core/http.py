import json
import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, JsonResponse

from django.core.serializers.json import DjangoJSONEncoder

log = logging.getLogger("oirs")


class EncoderSeguro(DjangoJSONEncoder):
    """Escapa <, > y & como secuencias Unicode para que un dato almacenado nunca sea interpretado
    como HTML si un cliente lo inserta en el DOM (defensa en profundidad contra XSS, incidencia INC-01)."""
    def encode(self, o):
        return (super().encode(o).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


class JsonSeguro(JsonResponse):
    def __init__(self, data, encoder=EncoderSeguro, **kwargs):
        super().__init__(data, encoder=encoder, **kwargs)


def ip_cliente(request):
    return request.META.get("REMOTE_ADDR")


def leer_json(request):
    try:
        datos = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        raise ValidationError("Cuerpo JSON inválido.")
    if not isinstance(datos, dict):
        raise ValidationError("Se esperaba un objeto JSON.")
    return datos


def manejar_errores(vista):
    """Gestión centralizada de errores (SC-04): mensajes genéricos al cliente, detalle sólo en el log."""
    def envoltura(request, *args, **kwargs):
        try:
            return vista(request, *args, **kwargs)
        except ValidationError as e:
            return JsonSeguro({"error": "Datos inválidos", "detalle": e.messages}, status=400)
        except Http404:
            return JsonSeguro({"error": "No encontrado"}, status=404)
        except PermissionDenied:
            return JsonSeguro({"error": "No autorizado"}, status=403)
        except Exception:
            log.exception("Error no controlado en %s", request.path)
            return JsonSeguro({"error": "Error interno. Intente nuevamente."}, status=500)
    envoltura.__name__ = vista.__name__
    return envoltura
