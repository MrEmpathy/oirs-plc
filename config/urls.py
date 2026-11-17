from django.urls import include, path

from apps.cuentas import views as cuentas
from apps.integracion import views as publico
from apps.reportes import views as reportes
from apps.requerimientos import views as req

urlpatterns = [
    # Canal público (WordPress -> API, firmado HMAC)
    path("api/v1/publico/catalogos", publico.catalogos),
    path("api/v1/publico/requerimientos", publico.crear_requerimiento),
    path("api/v1/publico/encuestas/<slug:codigo>", publico.definicion_encuesta),
    path("api/v1/publico/encuestas/<slug:codigo>/respuestas", publico.responder_encuesta),
    # Sistema administrativo (sesión)
    path("api/v1/sesion/csrf", cuentas.token_csrf),
    path("api/v1/sesion/iniciar", cuentas.iniciar_sesion),
    path("api/v1/sesion/cerrar", cuentas.cerrar_sesion),
    path("api/v1/requerimientos", req.listar),
    path("api/v1/requerimientos/<str:folio>", req.detalle),
    path("api/v1/requerimientos/<str:folio>/derivar", req.derivar),
    path("api/v1/requerimientos/<str:folio>/respuesta", req.responder),
    path("api/v1/requerimientos/<str:folio>/cerrar", req.cerrar),
    path("api/v1/reportes/indicadores", reportes.indicadores),
    path("api/v1/reportes/requerimientos.csv", reportes.exportar_csv),
    path("api/v1/salud", publico.salud),
    # Front administrativo (plantillas Django)
    path("", include("apps.web.urls")),
]

# Páginas de error propias, sin trazas ni detalles internos (SC-04).
handler403 = "apps.web.vistas.errores.prohibido"
handler404 = "apps.web.vistas.errores.no_encontrado"
handler500 = "apps.web.vistas.errores.error_interno"
