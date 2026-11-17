from django.shortcuts import redirect
from django.urls import path

from .vistas import administracion as adm
from .vistas import autenticacion as aut
from .vistas import casos, supervision

app_name = "web"


def inicio(request):
    if request.user.is_authenticated:
        return redirect(aut.destino_inicial(request.user))
    return redirect("web:ingresar")


urlpatterns = [
    path("", inicio, name="inicio"),
    # Autenticación (CU11)
    path("ingresar", aut.ingresar, name="ingresar"),
    path("ingresar/verificar", aut.verificar_mfa, name="verificar_mfa"),
    path("ingresar/segundo-factor", aut.enrolar_mfa, name="enrolar_mfa"),
    path("salir", aut.salir, name="salir"),
    path("cuenta/clave", aut.cambiar_clave, name="cambiar_clave"),
    path("recuperar", aut.RecuperarClave.as_view(), name="recuperar"),
    path("recuperar/enviado", aut.auth_views.PasswordResetDoneView.as_view(
        template_name="web/auth/recuperar_enviado.html"), name="recuperar_enviado"),
    path("recuperar/<uidb64>/<token>", aut.RecuperarClaveConfirmar.as_view(), name="recuperar_confirmar"),
    path("recuperar/listo", aut.auth_views.PasswordResetCompleteView.as_view(
        template_name="web/auth/recuperar_listo.html"), name="recuperar_listo"),
    # Casos (CU03, CU04, CU05, CU07)
    path("bandeja", casos.bandeja, name="bandeja"),
    path("casos/nuevo", casos.ingreso_presencial, name="ingreso_presencial"),
    path("casos/<str:folio>", casos.detalle, name="detalle"),
    path("casos/<str:folio>/derivar", casos.derivar, name="derivar"),
    path("casos/<str:folio>/responder", casos.responder, name="responder"),
    path("casos/<str:folio>/cerrar", casos.cerrar, name="cerrar"),
    # Supervisión (CU06, CU08, CU09)
    path("plazos", supervision.panel_plazos, name="panel_plazos"),
    path("reportes", supervision.reportes_vista, name="reportes"),
    # Administración (CU10)
    path("usuarios", adm.usuarios, name="usuarios"),
    path("usuarios/nuevo", adm.usuario_crear, name="usuario_crear"),
    path("usuarios/<int:pk>", adm.usuario_editar, name="usuario_editar"),
    path("usuarios/<int:pk>/<slug:accion>", adm.usuario_accion, name="usuario_accion"),
    path("catalogos", adm.catalogos_vista, name="catalogos"),
    path("catalogos/<slug:tipo>/nuevo", adm.catalogo_crear, name="catalogo_crear"),
    path("catalogos/<slug:tipo>/<int:pk>/alternar", adm.catalogo_alternar, name="catalogo_alternar"),
]
