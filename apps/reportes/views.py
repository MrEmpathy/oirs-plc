import csv
from datetime import date

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.auditoria import servicio as auditoria
from apps.core.http import JsonSeguro, manejar_errores
from apps.cuentas.permisos import requiere_permiso
from apps.requerimientos import selectores

from . import servicio


def _rango(request):
    try:
        desde = date.fromisoformat(request.GET.get("desde", "")) if request.GET.get("desde") else timezone.localdate().replace(day=1)
        hasta = date.fromisoformat(request.GET.get("hasta", "")) if request.GET.get("hasta") else timezone.localdate()
    except ValueError:
        raise ValidationError("Rango de fechas inválido.")
    if desde > hasta or (hasta - desde).days > 731:
        raise ValidationError("Rango de fechas inválido (máximo 2 años).")
    return desde, hasta


@require_GET
@requiere_permiso("reportes.ver")
@manejar_errores
def indicadores(request):
    desde, hasta = _rango(request)
    est = request.GET.get("establecimiento")
    datos = servicio.indicadores(request.user, desde, hasta, int(est) if est and est.isdigit() else None)
    return JsonSeguro(datos)


@require_GET
@requiere_permiso("reportes.exportar")
@manejar_errores
def exportar_csv(request):
    desde, hasta = _rango(request)
    qs = selectores.visibles_para(request.user).filter(fecha_ingreso__date__range=(desde, hasta))
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="requerimientos_{desde}_{hasta}.csv"'
    w = csv.writer(resp)
    w.writerow(["folio", "tipo", "estado", "establecimiento", "categoria", "fecha_ingreso", "vencimiento"])
    for r in qs.iterator():  # sin datos personales del solicitante (minimización)
        w.writerow([servicio.celda_segura(v) for v in (r.folio, r.tipo, r.estado, r.establecimiento.nombre,
                    r.categoria.nombre if r.categoria else "", r.fecha_ingreso.date(), r.fecha_vencimiento)])
    auditoria.registrar("REPORTE_EXPORTADO", usuario=request.user, desde=str(desde), hasta=str(hasta))
    return resp
