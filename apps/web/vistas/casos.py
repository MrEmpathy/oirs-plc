"""Bandeja, detalle y gestión de casos (HU01, HU03, HU04, HU06 / CU03, CU04, CU05, CU07).
Toda lectura pasa por selectores.visibles_para(); un caso ajeno responde 404 (no revela su existencia)."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.http import ip_cliente
from apps.cuentas.models import Rol
from apps.cuentas.permisos import tiene_permiso
from apps.requerimientos import plazos, selectores, servicios
from apps.requerimientos.models import Canal, Estado

from ..formularios import DerivarForm, FiltroBandejaForm, PresencialForm, RespuestaForm
from ..permisos import permiso_web

POR_PAGINA = 25


def _decorar(req, hoy, feriados):
    """Agrega días hábiles restantes y semáforo a un caso abierto (mismas funciones que la API)."""
    if req.estado in selectores.ESTADOS_ABIERTOS:
        req.restantes = plazos.dias_habiles_restantes(hoy, req.fecha_vencimiento, feriados)
        req.semaforo = plazos.semaforo(req.restantes)
    else:
        req.restantes, req.semaforo = None, None
    return req


def _indicadores(qs, hoy, feriados):
    abiertos = list(qs.filter(estado__in=selectores.ESTADOS_ABIERTOS).values_list("fecha_vencimiento", flat=True))
    colores = [plazos.semaforo(plazos.dias_habiles_restantes(hoy, v, feriados)) for v in abiertos]
    return {"abiertos": len(abiertos), "por_vencer": colores.count("AMARILLO"), "vencidos": colores.count("ROJO"),
            "respondidos": qs.filter(estado=Estado.RESPONDIDO).count()}


@permiso_web("requerimiento.ver")
def bandeja(request):
    form = FiltroBandejaForm(request.GET or None)
    datos = form.cleaned_data if form.is_valid() else {}
    estado = datos.get("estado") or "abiertos"
    base = selectores.buscar(request.user, texto=datos.get("q") or None,
                             establecimiento_id=datos["establecimiento"].id if datos.get("establecimiento") else None)
    hoy, feriados = timezone.localdate(), plazos.feriados_bd()
    indicadores = _indicadores(base, hoy, feriados)

    if estado in ("abiertos", "vencidos", "por_vencer"):
        qs = base.filter(estado__in=selectores.ESTADOS_ABIERTOS).order_by("fecha_vencimiento", "id")
    elif estado == "todos":
        qs = base.order_by("-fecha_ingreso")
    else:
        qs = base.filter(estado=estado).order_by("-fecha_ingreso")
    if estado in ("vencidos", "por_vencer"):   # filtro por semáforo (días hábiles): se evalúa caso a caso
        color = "ROJO" if estado == "vencidos" else "AMARILLO"
        casos = [r for r in (_decorar(r, hoy, feriados) for r in qs) if r.semaforo == color]
        pagina = Paginator(casos, POR_PAGINA).get_page(request.GET.get("pagina"))
    else:
        pagina = Paginator(qs, POR_PAGINA).get_page(request.GET.get("pagina"))
        for r in pagina:
            _decorar(r, hoy, feriados)

    filtros = request.GET.copy()
    filtros.pop("pagina", None)
    return render(request, "web/casos/bandeja.html", {
        "form": form, "pagina": pagina, "estado": estado, "ind": indicadores,
        "filtros": filtros.urlencode(), "ve_red": request.user.rol in (Rol.ADMIN, Rol.OIRS_DSM)})


def _obtener(request, folio):
    return get_object_or_404(selectores.visibles_para(request.user).select_related("solicitante"), folio=folio)


def _puede_gestionar(usuario, req):
    return tiene_permiso(usuario, "requerimiento.gestionar") and usuario.establecimiento_id == req.establecimiento_id


@permiso_web("requerimiento.ver")
def detalle(request, folio, form_derivar=None, form_respuesta=None):
    req = _decorar(_obtener(request, folio), timezone.localdate(), plazos.feriados_bd())
    gestiona = _puede_gestionar(request.user, req)
    autoriza_email = bool(req.solicitante and req.solicitante.autoriza_respuesta_email)
    contexto = {
        "req": req, "gestiona": gestiona,
        # Datos de contacto solo para los perfiles del propio establecimiento (minimización, sección 7.1).
        "ve_contacto": request.user.rol in (Rol.OIRS_EST, Rol.DIRECCION),
        "historial": req.historial.select_related("usuario").all(),
        "derivaciones": req.derivaciones.select_related("unidad", "derivado_por").all(),
        "respuesta": getattr(req, "respuesta", None) if hasattr(req, "respuesta") else None,
    }
    if gestiona and req.estado in (Estado.INGRESADO, Estado.EN_PROCESO):
        contexto["form_derivar"] = form_derivar or DerivarForm(establecimiento=req.establecimiento, initial={
            "categoria": req.categoria_id, "unidad": req.unidad_derivada_id})
    if gestiona and req.estado == Estado.EN_PROCESO:
        contexto["form_respuesta"] = form_respuesta or RespuestaForm(autoriza_email=autoriza_email)
    return render(request, "web/casos/detalle.html", contexto)


def _aplicar(request, accion, folio):
    """Ejecuta una acción de servicio y convierte las reglas de negocio violadas en mensajes para el usuario."""
    try:
        accion()
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
        return False
    except PermissionDenied:
        raise
    return True


@require_POST
@permiso_web("requerimiento.gestionar")
def derivar(request, folio):
    req = _obtener(request, folio)
    form = DerivarForm(request.POST, establecimiento=req.establecimiento)
    if not form.is_valid():
        messages.error(request, "Revise los datos de la derivación.")
        return detalle(request, folio, form_derivar=form)
    d = form.cleaned_data
    if _aplicar(request, lambda: servicios.clasificar_y_derivar(req, usuario=request.user, categoria=d["categoria"],
                                                                unidad=d["unidad"], instrucciones=d["instrucciones"]),
                folio):
        messages.success(request, f"Caso derivado a {d['unidad'].nombre}. Estado: En proceso.")
    return redirect("web:detalle", folio=folio)


@require_POST
@permiso_web("requerimiento.gestionar")
def responder(request, folio):
    req = _obtener(request, folio)
    autoriza = bool(req.solicitante and req.solicitante.autoriza_respuesta_email)
    form = RespuestaForm(request.POST, autoriza_email=autoriza)
    if not form.is_valid():
        messages.error(request, "Revise los datos de la respuesta.")
        return detalle(request, folio, form_respuesta=form)
    d = form.cleaned_data
    resultado = {}

    def accion():
        resultado["r"] = servicios.registrar_respuesta(req, usuario=request.user, contenido=d["contenido"],
                                                       medio=d["medio"], fecha_emision=d["fecha_emision"])
    if _aplicar(request, accion, folio):
        plazo = "dentro del plazo legal" if resultado["r"].dentro_plazo else "FUERA del plazo legal"
        messages.success(request, f"Respuesta registrada {plazo}. Cuando la envíe, cierre el caso.")
    return redirect("web:detalle", folio=folio)


@require_POST
@permiso_web("requerimiento.gestionar")
def cerrar(request, folio):
    req = _obtener(request, folio)
    if _aplicar(request, lambda: servicios.cerrar(req, usuario=request.user,
                                                  comentario=request.POST.get("comentario", "")[:500]), folio):
        messages.success(request, f"Caso {folio} cerrado.")
    return redirect("web:detalle", folio=folio)


@permiso_web("requerimiento.ingresar_presencial")
def ingreso_presencial(request):
    estab = request.user.establecimiento
    form = PresencialForm(request.POST or None, establecimiento=estab,
                          initial={"establecimiento": estab.codigo if estab else None})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            req = servicios.registrar_requerimiento(
                tipo=d["tipo"], establecimiento=d["establecimiento"], descripcion=d["descripcion"],
                peticion_concreta=d.get("peticion_concreta", ""), fecha_atencion=d.get("fecha_atencion"),
                canal=Canal.PRESENCIAL, datos_solicitante=form.datos_solicitante(), usuario=request.user,
                ip=ip_cliente(request))
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
        else:
            return render(request, "web/casos/comprobante.html", {"req": req})
    return render(request, "web/casos/presencial.html", {"form": form, "establecimiento": estab})
