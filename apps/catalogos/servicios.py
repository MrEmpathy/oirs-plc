"""Administración de catálogos (perfil ADMIN): establecimientos, unidades, categorías y feriados.
Los registros no se eliminan (las FK usan PROTECT y la app no tiene DELETE): se desactivan."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from apps.auditoria import servicio as auditoria
from apps.cuentas.models import Rol

from .models import Categoria, Establecimiento, Feriado, Unidad

MODELOS = {"establecimiento": Establecimiento, "unidad": Unidad, "categoria": Categoria}


def _exigir_admin(usuario):
    if usuario.rol != Rol.ADMIN:
        raise PermissionDenied


def crear(usuario, tipo, form):
    """Guarda un formulario de catálogo validado. Las restricciones de la BD (UNIQUE, «Otro» único) se
    traducen a mensajes comprensibles en lugar de un error 500."""
    _exigir_admin(usuario)
    try:
        with transaction.atomic():
            obj = form.save()
    except IntegrityError:
        raise ValidationError("Ya existe un registro con esos datos (o ya hay una categoría «Otro»).")
    auditoria.registrar("CATALOGO_CREADO", usuario=usuario, catalogo=tipo, registro_id=str(obj.pk))
    return obj


def alternar_activo(usuario, tipo, pk):
    _exigir_admin(usuario)
    modelo = MODELOS[tipo]
    obj = get_object_or_404(modelo, pk=pk)
    campo = "activo" if hasattr(obj, "activo") else "activa"
    setattr(obj, campo, not getattr(obj, campo))
    obj.save(update_fields=[campo])
    auditoria.registrar("CATALOGO_MODIFICADO", usuario=usuario, catalogo=tipo, registro_id=str(pk),
                        activo=getattr(obj, campo))
    return obj


def agregar_feriado(usuario, fecha, descripcion):
    _exigir_admin(usuario)
    if Feriado.objects.filter(fecha=fecha).exists():
        raise ValidationError("Esa fecha ya está registrada como feriado.")
    f = Feriado.objects.create(fecha=fecha, descripcion=descripcion)
    auditoria.registrar("CATALOGO_CREADO", usuario=usuario, catalogo="feriado", registro_id=str(fecha))
    return f
