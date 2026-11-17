from django.http import HttpResponse
from django.urls import path

app_name = "web"


def _pendiente(request, *args, **kwargs):  # reemplazado al construir el front administrativo
    return HttpResponse("OIRS PLC")


urlpatterns = [path(r, _pendiente, name=n) for r, n in [
    ("", "inicio"), ("ingresar", "ingresar"), ("salir", "salir"), ("cuenta/clave", "cambiar_clave"),
    ("bandeja", "bandeja"), ("casos/nuevo", "ingreso_presencial"), ("plazos", "panel_plazos"),
    ("reportes", "reportes"), ("usuarios", "usuarios"), ("catalogos", "catalogos")]]
