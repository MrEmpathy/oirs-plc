"""Consultas de lectura con autorización a nivel de registro (row-level authorization).

Regla SC-03: toda consulta de requerimientos pasa por `visibles_para(usuario)`; nunca se usa
Requerimiento.objects.all() en una vista."""
from django.db.models import Q

from apps.cuentas.models import Rol

from .models import Requerimiento

ESTADOS_VALIDOS = {"INGRESADO", "EN_PROCESO", "RESPONDIDO", "CERRADO"}


def visibles_para(usuario):
    qs = Requerimiento.objects.select_related("establecimiento", "categoria", "unidad_derivada")
    if usuario.rol in (Rol.ADMIN, Rol.OIRS_DSM):
        return qs
    if usuario.rol in (Rol.OIRS_EST, Rol.DIRECCION):
        return qs.filter(establecimiento_id=usuario.establecimiento_id)
    return qs.none()


def buscar(usuario, *, estado=None, establecimiento_id=None, texto=None):
    qs = visibles_para(usuario)
    if estado:
        if estado not in ESTADOS_VALIDOS:
            return qs.none()
        qs = qs.filter(estado=estado)
    if establecimiento_id:
        qs = qs.filter(establecimiento_id=establecimiento_id)
    if texto:
        # Parámetros enlazados por el ORM: no hay concatenación de SQL (SC-02)
        qs = qs.filter(Q(folio__icontains=texto) | Q(descripcion__icontains=texto))
    return qs
