"""API pública consumida por el plugin de WordPress (servidor a servidor, firmada con HMAC)."""
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.catalogos.models import Categoria, Establecimiento
from apps.core.http import JsonSeguro, ip_cliente, leer_json, manejar_errores
from apps.encuestas import servicio as encuestas
from apps.requerimientos import servicios
from apps.requerimientos.models import Canal

from .formularios import RequerimientoPublicoForm
from .hmac_firma import verificar


def _firmado(vista):
    def envoltura(request, *args, **kwargs):
        if not verificar(request):
            return JsonSeguro({"error": "Firma inválida"}, status=401)
        return vista(request, *args, **kwargs)
    envoltura.__name__ = vista.__name__
    return envoltura


# csrf_exempt se justifica: no hay cookies de sesión en este canal; la autenticidad la da la firma HMAC.
@csrf_exempt
@require_POST
@_firmado
@manejar_errores
def crear_requerimiento(request):
    form = RequerimientoPublicoForm(leer_json(request))
    if not form.is_valid():
        raise ValidationError([f"{campo}: {m}" for campo, msgs in form.errors.items() for m in msgs])
    d = form.cleaned_data
    req = servicios.registrar_requerimiento(
        tipo=d["tipo"], establecimiento=d["establecimiento"], descripcion=d["descripcion"],
        peticion_concreta=d.get("peticion_concreta", ""), fecha_atencion=d.get("fecha_atencion"),
        canal=Canal.WEB, datos_solicitante=form.datos_solicitante(), ip=ip_cliente(request))
    return JsonSeguro({"folio": req.folio, "fecha_vencimiento": req.fecha_vencimiento.isoformat(),
                         "estado": req.estado}, status=201)


@csrf_exempt
@require_POST
@_firmado
@manejar_errores
def responder_encuesta(request, codigo):
    d = leer_json(request)
    encuestas.registrar_respuesta(codigo=codigo, establecimiento_codigo=d.get("establecimiento"),
                                  respuestas=d.get("respuestas"), comentario=d.get("comentario", ""))
    return JsonSeguro({"ok": True}, status=201)


@require_GET
@_firmado
def catalogos(request):
    return JsonSeguro({
        "establecimientos": list(Establecimiento.objects.filter(activo=True).values("codigo", "nombre")),
        "categorias": list(Categoria.objects.filter(activa=True).values("id", "nombre")),
    })
