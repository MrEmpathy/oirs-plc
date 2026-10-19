from django.urls import path

from apps.cuentas import views as cuentas
from apps.integracion import views as publico
from apps.reportes import views as reportes
from apps.requerimientos import views as req

urlpatterns = [
    # Canal público (WordPress -> API, firmado HMAC)
    path("api/v1/publico/catalogos", publico.catalogos),
    path("api/v1/publico/requerimientos", publico.crear_requerimiento),
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
]
