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


ESTADOS_ABIERTOS = ("INGRESADO", "EN_PROCESO")


def panel_plazos(usuario, hoy, feriados):
    """HU05 / CU06: situación del plazo legal de los casos abiertos de toda la red, por establecimiento.
    El semáforo se calcula en días hábiles con la misma función pura usada en la bandeja (plazos.semaforo)."""
    from apps.catalogos.models import Establecimiento

    from . import plazos

    filas = {e.id: {"establecimiento": e, "abiertos": 0, "VERDE": 0, "AMARILLO": 0, "ROJO": 0}
             for e in Establecimiento.objects.filter(activo=True).exclude(tipo="DSM")}
    criticos = []
    abiertos = visibles_para(usuario).filter(estado__in=ESTADOS_ABIERTOS).order_by("fecha_vencimiento")
    for req in abiertos:
        restantes = plazos.dias_habiles_restantes(hoy, req.fecha_vencimiento, feriados)
        color = plazos.semaforo(restantes)
        fila = filas.setdefault(req.establecimiento_id, {"establecimiento": req.establecimiento, "abiertos": 0,
                                                         "VERDE": 0, "AMARILLO": 0, "ROJO": 0})
        fila["abiertos"] += 1
        fila[color] += 1
        if restantes <= 2:
            criticos.append({"req": req, "restantes": restantes, "semaforo": color})
    resumen = sorted(filas.values(), key=lambda f: (-f["ROJO"], -f["AMARILLO"], f["establecimiento"].nombre))
    return resumen, criticos
