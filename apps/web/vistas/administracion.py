"""Administración de usuarios y catálogos (HU07 / CU10). Perfil ADMIN con MFA obligatorio."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalogos import servicios as catalogos
from apps.catalogos.models import Categoria, Establecimiento, Feriado, Unidad
from apps.cuentas import servicios as cuentas
from apps.cuentas.models import Rol, Usuario

from ..formularios import CategoriaForm, EstablecimientoForm, FeriadoForm, UnidadForm, UsuarioForm
from ..permisos import permiso_web


def _errores(request, e):
    messages.error(request, " ".join(e.messages))


@permiso_web("usuarios.administrar")
def usuarios(request):
    q = (request.GET.get("q") or "").strip()[:60]
    rol = request.GET.get("rol") if request.GET.get("rol") in Rol.values else ""
    qs = Usuario.objects.select_related("establecimiento").order_by("-is_active", "apellidos", "nombre")
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(nombre__icontains=q) | Q(apellidos__icontains=q))
    if rol:
        qs = qs.filter(rol=rol)
    pagina = Paginator(qs, 25).get_page(request.GET.get("pagina"))
    return render(request, "web/admin/usuarios.html", {"pagina": pagina, "q": q, "rol": rol, "roles": Rol.choices,
                                                       "form": UsuarioForm()})


@require_POST
@permiso_web("usuarios.administrar")
def usuario_crear(request):
    form = UsuarioForm(request.POST)
    if form.is_valid():
        d = form.cleaned_data
        try:
            usuario, clave = cuentas.crear_usuario(request.user, email=d["email"], nombre=d["nombre"],
                                                   apellidos=d["apellidos"], rol=d["rol"],
                                                   establecimiento=d.get("establecimiento"))
        except ValidationError as e:
            _errores(request, e)
        else:
            return render(request, "web/admin/clave_temporal.html", {"usuario": usuario, "clave": clave, "nuevo": True})
    else:
        messages.error(request, "Revise los datos del nuevo usuario: " +
                       " ".join(f"{form.fields[c].label or c}: {m[0]}" for c, m in form.errors.items() if c != "__all__"))
    return redirect("web:usuarios")


@permiso_web("usuarios.administrar")
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    inicial = {"email": usuario.email, "nombre": usuario.nombre, "apellidos": usuario.apellidos,
               "rol": usuario.rol, "establecimiento": usuario.establecimiento_id}
    form = UsuarioForm(request.POST or None, initial=inicial, edicion=True)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            cuentas.actualizar_usuario(request.user, usuario, nombre=d["nombre"], apellidos=d["apellidos"],
                                       rol=d["rol"], establecimiento=d.get("establecimiento"))
        except ValidationError as e:
            _errores(request, e)
        else:
            messages.success(request, "Usuario actualizado.")
            return redirect("web:usuario_editar", pk=pk)
    return render(request, "web/admin/usuario_editar.html", {"form": form, "u": usuario})


@require_POST
@permiso_web("usuarios.administrar")
def usuario_accion(request, pk, accion):
    usuario = get_object_or_404(Usuario, pk=pk)
    try:
        if accion == "desactivar":
            cuentas.cambiar_estado(request.user, usuario, False)
            messages.success(request, "Cuenta desactivada: el usuario ya no puede ingresar.")
        elif accion == "activar":
            cuentas.cambiar_estado(request.user, usuario, True)
            messages.success(request, "Cuenta activada.")
        elif accion == "desbloquear":
            cuentas.desbloquear(request.user, usuario)
            messages.success(request, "Cuenta desbloqueada.")
        elif accion == "restablecer-mfa":
            cuentas.restablecer_mfa(request.user, usuario)
            messages.success(request, "Segundo factor restablecido: deberá enrolarlo en su próximo ingreso.")
        elif accion == "clave-temporal":
            clave = cuentas.restablecer_clave(request.user, usuario)
            return render(request, "web/admin/clave_temporal.html", {"usuario": usuario, "clave": clave, "nuevo": False})
        else:
            return redirect("web:usuario_editar", pk=pk)
    except ValidationError as e:
        _errores(request, e)
    return redirect("web:usuario_editar", pk=pk)


FORMULARIOS = {"establecimiento": EstablecimientoForm, "unidad": UnidadForm, "categoria": CategoriaForm}


@permiso_web("catalogos.administrar")
def catalogos_vista(request):
    pestana = request.GET.get("p") if request.GET.get("p") in ("establecimientos", "unidades", "categorias", "feriados") \
        else "establecimientos"
    return render(request, "web/admin/catalogos.html", {
        "pestana": pestana,
        "establecimientos": Establecimiento.objects.all(),
        "unidades": Unidad.objects.select_related("establecimiento").order_by("establecimiento__nombre", "nombre"),
        "categorias": Categoria.objects.all(),
        "feriados": Feriado.objects.order_by("-fecha")[:60],
        "forms": {"establecimiento": EstablecimientoForm(), "unidad": UnidadForm(), "categoria": CategoriaForm(),
                  "feriado": FeriadoForm()},
    })


@require_POST
@permiso_web("catalogos.administrar")
def catalogo_crear(request, tipo):
    pestanas = {"establecimiento": "establecimientos", "unidad": "unidades", "categoria": "categorias",
                "feriado": "feriados"}
    if tipo not in pestanas:
        return redirect("web:catalogos")
    try:
        if tipo == "feriado":
            form = FeriadoForm(request.POST)
            if form.is_valid():
                catalogos.agregar_feriado(request.user, form.cleaned_data["fecha"], form.cleaned_data["descripcion"])
                messages.success(request, "Feriado agregado. Se aplicará a los plazos de los casos que ingresen desde ahora.")
            else:
                messages.error(request, "Revise la fecha y la descripción del feriado.")
        else:
            form = FORMULARIOS[tipo](request.POST)
            if form.is_valid():
                catalogos.crear(request.user, tipo, form)
                messages.success(request, "Registro agregado.")
            else:
                messages.error(request, " ".join(m for errs in form.errors.values() for m in errs))
    except ValidationError as e:
        _errores(request, e)
    return redirect(f"/catalogos?p={pestanas[tipo]}")


@require_POST
@permiso_web("catalogos.administrar")
def catalogo_alternar(request, tipo, pk):
    if tipo in FORMULARIOS:
        obj = catalogos.alternar_activo(request.user, tipo, pk)
        messages.success(request, f"«{obj}» {'activado' if getattr(obj, 'activo', getattr(obj, 'activa', False)) else 'desactivado'}.")
    pestanas = {"establecimiento": "establecimientos", "unidad": "unidades", "categoria": "categorias"}
    return redirect(f"/catalogos?p={pestanas.get(tipo, 'establecimientos')}")
