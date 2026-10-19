"""Casos de uso del ciclo de vida de un requerimiento (capa de servicios / lógica de negocio).

Todas las operaciones de escritura son transaccionales y registran el cambio en historial_estado
(estructurado, inmutable) y en la bitácora de auditoría (documental)."""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.auditoria import servicio as auditoria
from apps.cuentas.models import Rol

from . import plazos
from .models import (CorrelativoFolio, Derivacion, Estado, HistorialEstado, Requerimiento, Respuesta,
                     Solicitante, TIPOS_CON_IDENTIFICACION)

# Máquina de estados: transiciones permitidas
TRANSICIONES = {
    Estado.INGRESADO: {Estado.EN_PROCESO},
    Estado.EN_PROCESO: {Estado.EN_PROCESO, Estado.RESPONDIDO},
    Estado.RESPONDIDO: {Estado.CERRADO},
    Estado.CERRADO: set(),
}


def validar_transicion(actual, nuevo):
    if nuevo not in TRANSICIONES[actual]:
        raise ValidationError(f"Transición de estado no permitida: {actual} → {nuevo}")


def generar_folio(anio=None):
    """Folio único y correlativo por año: PLC-AAAA-NNNNNN. Usa bloqueo de fila (SELECT ... FOR UPDATE)
    para garantizar unicidad con ingresos concurrentes."""
    anio = anio or timezone.localdate().year
    with transaction.atomic():
        fila, _ = CorrelativoFolio.objects.select_for_update().get_or_create(anio=anio)
        fila.ultimo += 1
        fila.save(update_fields=["ultimo"])
        return f"PLC-{anio}-{fila.ultimo:06d}"


def _calcular_vencimiento(fecha_ingreso):
    inicio = timezone.localtime(fecha_ingreso).date()
    feriados = plazos.feriados_bd(inicio, inicio + timedelta(days=60))
    return plazos.sumar_dias_habiles(inicio, settings.PLAZO_DIAS_HABILES, feriados)


def _historial(req, anterior, nuevo, accion, usuario=None, comentario=""):
    HistorialEstado.objects.create(requerimiento=req, estado_anterior=anterior or "", estado_nuevo=nuevo,
                                   accion=accion, usuario=usuario, comentario=comentario[:500])


@transaction.atomic
def registrar_requerimiento(*, tipo, establecimiento, descripcion, canal, datos_solicitante=None,
                            peticion_concreta="", fecha_atencion=None, usuario=None, ip=None):
    """RF01, RF03: registra el requerimiento con folio único y vencimiento legal calculado."""
    if tipo in TIPOS_CON_IDENTIFICACION and not datos_solicitante:
        raise ValidationError("Este tipo de requerimiento requiere datos de contacto para ser respondido.")
    solicitante = None
    if datos_solicitante:
        solicitante = Solicitante(**datos_solicitante)
        solicitante.full_clean()
        solicitante.save()
    ahora = timezone.now()
    req = Requerimiento(folio=generar_folio(), tipo=tipo, canal=canal, establecimiento=establecimiento,
                        solicitante=solicitante, descripcion=descripcion, peticion_concreta=peticion_concreta,
                        fecha_atencion=fecha_atencion, fecha_ingreso=ahora,
                        fecha_vencimiento=_calcular_vencimiento(ahora), creado_por=usuario)
    req.full_clean()
    req.save()
    _historial(req, None, Estado.INGRESADO, "INGRESO", usuario, f"Canal {canal}")
    auditoria.registrar("REQUERIMIENTO_CREADO", usuario=usuario, folio=req.folio, ip=ip,
                        canal=canal, tipo=tipo, establecimiento_id=establecimiento.id)
    return req


def _exigir_gestion(usuario, req):
    """Solo el encargado OIRS del mismo establecimiento gestiona el caso (RNF02)."""
    if usuario.rol != Rol.OIRS_EST or usuario.establecimiento_id != req.establecimiento_id:
        auditoria.registrar("ACCESO_DENEGADO", usuario=usuario, folio=req.folio, resultado="DENEGADO")
        raise PermissionDenied


@transaction.atomic
def clasificar_y_derivar(req, *, usuario, categoria, unidad, instrucciones=""):
    """RF04 + RF05: clasifica por motivo y deriva a una unidad del mismo establecimiento."""
    req = Requerimiento.objects.select_for_update().get(pk=req.pk)
    _exigir_gestion(usuario, req)
    if unidad.establecimiento_id != req.establecimiento_id:
        raise ValidationError("La unidad de destino no pertenece al establecimiento del requerimiento.")
    validar_transicion(req.estado, Estado.EN_PROCESO)
    anterior = req.estado
    req.categoria, req.unidad_derivada, req.estado = categoria, unidad, Estado.EN_PROCESO
    req.save(update_fields=["categoria", "unidad_derivada", "estado"])
    Derivacion.objects.create(requerimiento=req, unidad=unidad, derivado_por=usuario, instrucciones=instrucciones)
    _historial(req, anterior, Estado.EN_PROCESO, "DERIVACION", usuario, f"Derivado a {unidad.nombre}")
    auditoria.registrar("REQUERIMIENTO_DERIVADO", usuario=usuario, folio=req.folio,
                        categoria_id=categoria.id, unidad_id=unidad.id)
    return req


@transaction.atomic
def registrar_respuesta(req, *, usuario, contenido, medio, fecha_emision):
    """RF06 + RF07: registra la respuesta y su fecha, determinando si se emitió dentro de plazo."""
    req = Requerimiento.objects.select_for_update().get(pk=req.pk)
    _exigir_gestion(usuario, req)
    validar_transicion(req.estado, Estado.RESPONDIDO)
    if fecha_emision < timezone.localtime(req.fecha_ingreso).date():
        raise ValidationError("La fecha de emisión no puede ser anterior al ingreso.")
    if medio == Respuesta.Medio.EMAIL and not (req.solicitante and req.solicitante.autoriza_respuesta_email):
        raise ValidationError("El solicitante no autorizó respuesta por correo electrónico.")
    resp = Respuesta(requerimiento=req, contenido=contenido, medio=medio, fecha_emision=fecha_emision,
                     registrado_por=usuario, dentro_plazo=fecha_emision <= req.fecha_vencimiento)
    resp.full_clean()
    resp.save()
    anterior, req.estado = req.estado, Estado.RESPONDIDO
    req.save(update_fields=["estado"])
    _historial(req, anterior, Estado.RESPONDIDO, "RESPUESTA", usuario,
               "Dentro de plazo" if resp.dentro_plazo else "Fuera de plazo")
    auditoria.registrar("RESPUESTA_REGISTRADA", usuario=usuario, folio=req.folio, dentro_plazo=resp.dentro_plazo)
    return resp


@transaction.atomic
def cerrar(req, *, usuario, comentario=""):
    req = Requerimiento.objects.select_for_update().get(pk=req.pk)
    _exigir_gestion(usuario, req)
    validar_transicion(req.estado, Estado.CERRADO)
    anterior, req.estado = req.estado, Estado.CERRADO
    req.save(update_fields=["estado"])
    _historial(req, anterior, Estado.CERRADO, "CIERRE", usuario, comentario)
    auditoria.registrar("REQUERIMIENTO_CERRADO", usuario=usuario, folio=req.folio)
    return req
