"""Panel de plazos de la red (HU05 / CU06) y reportes e indicadores (HU08 / CU08, CU09)."""
from django.shortcuts import render
from django.utils import timezone

from apps.cuentas.models import Rol
from apps.cuentas.permisos import tiene_permiso
from apps.encuestas import servicio as encuestas
from apps.encuestas.models import Encuesta
from apps.reportes import servicio as reportes
from apps.requerimientos import plazos, selectores
from apps.requerimientos.models import Estado, TipoRequerimiento

from ..formularios import ReportesForm
from ..permisos import permiso_web


@permiso_web("plazos.panel_red")
def panel_plazos(request):
    hoy = timezone.localdate()
    resumen, criticos = selectores.panel_plazos(request.user, hoy, plazos.feriados_bd())
    totales = {k: sum(f[k] for f in resumen) for k in ("abiertos", "VERDE", "AMARILLO", "ROJO")}
    return render(request, "web/supervision/panel_plazos.html",
                  {"resumen": resumen, "criticos": criticos, "totales": totales, "hoy": hoy})


@permiso_web("reportes.ver")
def reportes_vista(request):
    hoy = timezone.localdate()
    form = ReportesForm(request.GET or {"desde": hoy.replace(month=1, day=1), "hasta": hoy})
    datos, graficos = None, None
    if form.is_valid():
        d = form.cleaned_data
        estab = d.get("establecimiento")
        datos = reportes.indicadores(request.user, d["desde"], d["hasta"], estab.id if estab else None)
        etiquetas_tipo = dict(TipoRequerimiento.choices)
        etiquetas_estado = dict(Estado.choices)
        textos = {}
        enc = Encuesta.objects.filter(activa=True).first()
        if enc:
            try:
                textos = {p["id"]: p["texto"] for p in encuestas.definicion(enc)["preguntas"]}
            except Exception:  # la falta de la definición no impide ver el resto del reporte
                textos = {}
        for x in datos["por_tipo"]:
            x["etiqueta"] = etiquetas_tipo.get(x["tipo"], x["tipo"])
        for x in datos["por_estado"]:
            x["etiqueta"] = etiquetas_estado.get(x["estado"], x["estado"])
        respondidos = datos["dentro_plazo"] + datos["fuera_plazo"]
        datos["pct_dentro_plazo"] = round(100 * datos["dentro_plazo"] / respondidos, 1) if respondidos else None
        datos["satisfaccion_tabla"] = [{"pregunta": textos.get(s["_id"], s["_id"]), "promedio": s["promedio"], "n": s["n"]}
                                       for s in datos["satisfaccion"]]
        # Datos de los gráficos: se entregan con json_script (sin JavaScript en línea, compatible con la CSP).
        graficos = {
            "por_tipo": {"etiquetas": [etiquetas_tipo.get(x["tipo"], x["tipo"]) for x in datos["por_tipo"]],
                         "valores": [x["n"] for x in datos["por_tipo"]]},
            "por_estado": {"etiquetas": [etiquetas_estado.get(x["estado"], x["estado"]) for x in datos["por_estado"]],
                           "valores": [x["n"] for x in datos["por_estado"]]},
            "por_categoria": {"etiquetas": [x["categoria__nombre"] or "Sin clasificar" for x in datos["por_categoria"]],
                              "valores": [x["n"] for x in datos["por_categoria"]]},
            "satisfaccion": {"etiquetas": [f"P{i + 1}" for i, _ in enumerate(datos["satisfaccion_tabla"])],
                             "valores": [x["promedio"] for x in datos["satisfaccion_tabla"]]},
        }
    return render(request, "web/supervision/reportes.html", {
        "form": form, "datos": datos, "graficos": graficos,
        "puede_exportar": tiene_permiso(request.user, "reportes.exportar"),
        "ve_red": request.user.rol == Rol.OIRS_DSM, "query": request.GET.urlencode()})
