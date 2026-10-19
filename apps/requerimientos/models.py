from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class TipoRequerimiento(models.TextChoices):
    RECLAMO = "RECLAMO", "Reclamo"
    SUGERENCIA = "SUGERENCIA", "Sugerencia"
    CONSULTA = "CONSULTA", "Consulta"
    SOLICITUD = "SOLICITUD", "Solicitud"
    FELICITACION = "FELICITACION", "Felicitación"


# Tipos que requieren identificar al solicitante para poder responderle (minimización RNF03)
TIPOS_CON_IDENTIFICACION = ("RECLAMO", "CONSULTA", "SOLICITUD")


class Estado(models.TextChoices):
    INGRESADO = "INGRESADO", "Ingresado"
    EN_PROCESO = "EN_PROCESO", "En proceso"
    RESPONDIDO = "RESPONDIDO", "Respondido"
    CERRADO = "CERRADO", "Cerrado"


class Canal(models.TextChoices):
    WEB = "WEB", "Sitio web institucional"
    PRESENCIAL = "PRESENCIAL", "Formulario presencial OIRS"
    TOTEM = "TOTEM", "Tótem de autoservicio"


class Solicitante(models.Model):
    """Datos personales separados del requerimiento: permiten anonimizar al cumplirse el plazo de retención
    sin perder los datos estadísticos del caso."""
    class Sexo(models.TextChoices):
        F = "F", "Femenino"
        M = "M", "Masculino"
        O = "O", "Otro / prefiere no indicar"

    nombre = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=15, blank=True)
    edad = models.PositiveSmallIntegerField(null=True, blank=True,
                                            validators=[MinValueValidator(0), MaxValueValidator(120)])
    sexo = models.CharField(max_length=1, choices=Sexo.choices, blank=True)
    autoriza_respuesta_email = models.BooleanField(default=False)
    anonimizado = models.BooleanField(default=False)

    class Meta:
        db_table = "solicitante"
        constraints = [models.CheckConstraint(name="ck_solicitante_contacto",
                                              condition=~models.Q(email="", telefono="") | models.Q(anonimizado=True))]


class CorrelativoFolio(models.Model):
    anio = models.PositiveSmallIntegerField(primary_key=True)
    ultimo = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "correlativo_folio"


class Requerimiento(models.Model):
    folio = models.CharField(max_length=20, unique=True, editable=False)
    tipo = models.CharField(max_length=12, choices=TipoRequerimiento.choices)
    canal = models.CharField(max_length=10, choices=Canal.choices, default=Canal.WEB)
    establecimiento = models.ForeignKey("catalogos.Establecimiento", on_delete=models.PROTECT,
                                        related_name="requerimientos")
    categoria = models.ForeignKey("catalogos.Categoria", null=True, blank=True, on_delete=models.PROTECT,
                                  related_name="requerimientos")
    solicitante = models.ForeignKey(Solicitante, null=True, blank=True, on_delete=models.PROTECT,
                                    related_name="requerimientos")
    descripcion = models.TextField(validators=[MinLengthValidator(10)], max_length=4000)
    peticion_concreta = models.TextField(blank=True, max_length=2000)
    fecha_atencion = models.DateField(null=True, blank=True)
    fecha_ingreso = models.DateTimeField(default=timezone.now)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.INGRESADO)
    unidad_derivada = models.ForeignKey("catalogos.Unidad", null=True, blank=True, on_delete=models.PROTECT,
                                        related_name="requerimientos")
    creado_por = models.ForeignKey("cuentas.Usuario", null=True, blank=True, on_delete=models.PROTECT,
                                   related_name="requerimientos_creados")

    class Meta:
        db_table = "requerimiento"
        ordering = ["fecha_vencimiento", "id"]
        indexes = [
            models.Index(fields=["establecimiento", "estado"], name="ix_req_estab_estado"),
            models.Index(fields=["fecha_vencimiento"], name="ix_req_vencimiento"),
            models.Index(fields=["fecha_ingreso"], name="ix_req_fecha_ingreso"),
            models.Index(fields=["categoria"], name="ix_req_categoria"),
        ]
        constraints = [
            models.CheckConstraint(name="ck_req_vencimiento_posterior",
                                   condition=models.Q(fecha_vencimiento__gte=models.F("fecha_ingreso__date"))),
        ]

    def __str__(self):
        return self.folio


class Derivacion(models.Model):
    requerimiento = models.ForeignKey(Requerimiento, on_delete=models.PROTECT, related_name="derivaciones")
    unidad = models.ForeignKey("catalogos.Unidad", on_delete=models.PROTECT, related_name="derivaciones")
    derivado_por = models.ForeignKey("cuentas.Usuario", on_delete=models.PROTECT, related_name="derivaciones")
    instrucciones = models.TextField(blank=True, max_length=1000)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "derivacion"
        ordering = ["fecha"]


class Respuesta(models.Model):
    class Medio(models.TextChoices):
        CARTA = "CARTA", "Carta certificada"
        EMAIL = "EMAIL", "Correo electrónico autorizado"

    requerimiento = models.OneToOneField(Requerimiento, on_delete=models.PROTECT, related_name="respuesta")
    contenido = models.TextField(validators=[MinLengthValidator(20)], max_length=6000)
    medio = models.CharField(max_length=5, choices=Medio.choices)
    fecha_emision = models.DateField()
    registrado_por = models.ForeignKey("cuentas.Usuario", on_delete=models.PROTECT, related_name="respuestas")
    dentro_plazo = models.BooleanField()
    fecha_registro = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "respuesta"


class HistorialEstado(models.Model):
    """Bitácora inmutable (append-only) de cambios de estado — RNF07.
    El usuario de BD de la aplicación no tiene privilegios UPDATE/DELETE sobre esta tabla."""
    requerimiento = models.ForeignKey(Requerimiento, on_delete=models.PROTECT, related_name="historial")
    estado_anterior = models.CharField(max_length=10, choices=Estado.choices, blank=True)
    estado_nuevo = models.CharField(max_length=10, choices=Estado.choices)
    accion = models.CharField(max_length=30)
    usuario = models.ForeignKey("cuentas.Usuario", null=True, blank=True, on_delete=models.PROTECT,
                                related_name="+")
    comentario = models.CharField(max_length=500, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "historial_estado"
        ordering = ["fecha", "id"]
