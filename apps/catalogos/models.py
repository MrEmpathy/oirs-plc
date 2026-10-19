from django.db import models


class Establecimiento(models.Model):
    class Tipo(models.TextChoices):
        DSM = "DSM", "Departamento de Salud Municipal"
        CESFAM = "CESFAM", "Centro de Salud Familiar"
        CECOSF = "CECOSF", "Centro Comunitario de Salud Familiar"
        POSTA = "POSTA", "Posta de Salud Rural"
        SAPU = "SAPU", "Servicio de Atención Primaria de Urgencia"

    codigo = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=120, unique=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    direccion = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "establecimiento"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Unidad(models.Model):
    """Unidad o responsable dentro de un establecimiento al que se deriva un requerimiento."""
    establecimiento = models.ForeignKey(Establecimiento, on_delete=models.PROTECT, related_name="unidades")
    nombre = models.CharField(max_length=120)
    responsable = models.ForeignKey("cuentas.Usuario", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="unidades_a_cargo")
    activa = models.BooleanField(default=True)

    class Meta:
        db_table = "unidad"
        constraints = [models.UniqueConstraint(fields=["establecimiento", "nombre"], name="uq_unidad_estab_nombre")]

    def __str__(self):
        return f"{self.nombre} ({self.establecimiento.codigo})"


class Categoria(models.Model):
    """Motivo/categoría configurable. Incluye la categoría abierta 'Otro' (RF04)."""
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField(max_length=250, blank=True)
    es_otro = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)

    class Meta:
        db_table = "categoria"
        ordering = ["es_otro", "nombre"]
        constraints = [models.UniqueConstraint(fields=["es_otro"], condition=models.Q(es_otro=True),
                                               name="uq_una_sola_categoria_otro")]

    def __str__(self):
        return self.nombre


class Feriado(models.Model):
    """Feriados nacionales y regionales usados en el cálculo de días hábiles."""
    fecha = models.DateField(primary_key=True)
    descripcion = models.CharField(max_length=120)

    class Meta:
        db_table = "feriado"
        ordering = ["fecha"]
