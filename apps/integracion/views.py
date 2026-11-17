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
@manejar_errores
def definicion_encuesta(request, codigo):
    """Preguntas de la versión activa: el plugin las dibuja sin tenerlas escritas en su código, por lo que
    una nueva versión de la encuesta no requiere modificar WordPress (sección 6.4)."""
    from apps.encuestas.models import Encuesta
    encuesta = Encuesta.objects.filter(codigo=codigo, activa=True).first()
    if not encuesta:
        return JsonSeguro({"error": "Encuesta no disponible"}, status=404)
    d = encuestas.definicion(encuesta)
    return JsonSeguro({"codigo": encuesta.codigo, "version": encuesta.version, "nombre": encuesta.nombre,
                       "preguntas": d["preguntas"]})


@require_GET
@_firmado
def catalogos(request):
    return JsonSeguro({
        "establecimientos": list(Establecimiento.objects.filter(activo=True).values("codigo", "nombre")),
        "categorias": list(Categoria.objects.filter(activa=True).values("id", "nombre")),
    })


@require_GET
def salud(request):
    """Comprobación de disponibilidad para el monitoreo y el botón «Probar conexión» del plugin.
    Responde solo el estado de cada componente, sin versiones ni detalles internos."""
    from django.db import connection
    from apps.core.documental import db as mongo
    estado = {}
    try:
        connection.ensure_connection()
        estado["postgresql"] = "ok"
    except Exception:
        estado["postgresql"] = "error"
    try:
        mongo().command("ping")
        estado["documental"] = "ok"
    except Exception:
        estado["documental"] = "error"
    ok = all(v == "ok" for v in estado.values())
    return JsonSeguro({"estado": "ok" if ok else "degradado", **estado}, status=200 if ok else 503)
