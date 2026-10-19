"""API interna del sistema administrativo (sesión + CSRF + RBAC + autorización por registro)."""
from datetime import date

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.catalogos.models import Categoria, Unidad
from apps.core.http import JsonSeguro, leer_json, manejar_errores
from apps.cuentas.permisos import requiere_permiso

from . import plazos, selectores, servicios


def _serializar(req, feriados, hoy):
    restantes = plazos.dias_habiles_restantes(hoy, req.fecha_vencimiento, feriados)
    return {
        "folio": req.folio, "tipo": req.tipo, "estado": req.estado, "canal": req.canal,
        "establecimiento": req.establecimiento.nombre,
        "categoria": req.categoria.nombre if req.categoria else None,
        "unidad": req.unidad_derivada.nombre if req.unidad_derivada else None,
        "fecha_ingreso": timezone.localtime(req.fecha_ingreso).isoformat(),
        "fecha_vencimiento": req.fecha_vencimiento.isoformat(),
        "dias_restantes": restantes if req.estado in ("INGRESADO", "EN_PROCESO") else None,
        "semaforo": plazos.semaforo(restantes) if req.estado in ("INGRESADO", "EN_PROCESO") else None,
    }


def _obtener(request, folio):
    # Si no es visible para el usuario se responde 404 (no se revela su existencia: anti-IDOR)
    return get_object_or_404(selectores.visibles_para(request.user), folio=folio)


@require_GET
@requiere_permiso("requerimiento.ver")
@manejar_errores
def listar(request):
    estab = request.GET.get("establecimiento")
    qs = selectores.buscar(request.user, estado=request.GET.get("estado"),
                           establecimiento_id=int(estab) if estab and estab.isdigit() else None,
                           texto=(request.GET.get("q") or "")[:60])
    hoy = timezone.localdate()
    feriados = plazos.feriados_bd()
    pagina = qs[:100]
    return JsonSeguro({"total": qs.count(), "resultados": [_serializar(r, feriados, hoy) for r in pagina]})


@require_GET
@requiere_permiso("requerimiento.ver")
@manejar_errores
def detalle(request, folio):
    req = _obtener(request, folio)
    datos = _serializar(req, plazos.feriados_bd(), timezone.localdate())
    datos["descripcion"] = req.descripcion
    datos["historial"] = list(req.historial.values("estado_anterior", "estado_nuevo", "accion", "fecha", "usuario_id"))
    return JsonSeguro(datos)


@require_POST
@requiere_permiso("requerimiento.gestionar")
@manejar_errores
def derivar(request, folio):
    req = _obtener(request, folio)
    d = leer_json(request)
    categoria = get_object_or_404(Categoria, pk=d.get("categoria_id"), activa=True)
    unidad = get_object_or_404(Unidad, pk=d.get("unidad_id"), activa=True)
    req = servicios.clasificar_y_derivar(req, usuario=request.user, categoria=categoria, unidad=unidad,
                                         instrucciones=str(d.get("instrucciones", ""))[:1000])
    return JsonSeguro({"folio": req.folio, "estado": req.estado})


@require_POST
@requiere_permiso("requerimiento.gestionar")
@manejar_errores
def responder(request, folio):
    req = _obtener(request, folio)
    d = leer_json(request)
    try:
        fecha = date.fromisoformat(str(d.get("fecha_emision")))
    except ValueError:
        raise ValidationError("Fecha de emisión inválida.")
    resp = servicios.registrar_respuesta(req, usuario=request.user, contenido=str(d.get("contenido", "")),
                                         medio=str(d.get("medio", "")), fecha_emision=fecha)
    return JsonSeguro({"folio": req.folio, "estado": "RESPONDIDO", "dentro_plazo": resp.dentro_plazo})


@require_POST
@requiere_permiso("requerimiento.gestionar")
@manejar_errores
def cerrar(request, folio):
    req = servicios.cerrar(_obtener(request, folio), usuario=request.user)
    return JsonSeguro({"folio": req.folio, "estado": req.estado})
