from django.db import models


class Encuesta(models.Model):
    """Metadatos estructurados de cada versión de encuesta. Las preguntas (estructura flexible) y las
    respuestas anónimas residen en la base documental (colecciones encuesta_definiciones y
    respuestas_encuesta), referenciando este id."""
    codigo = models.SlugField(max_length=40)
    version = models.PositiveSmallIntegerField(default=1)
    nombre = models.CharField(max_length=120)
    activa = models.BooleanField(default=False)
    fecha_publicacion = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "encuesta"
        constraints = [
            models.UniqueConstraint(fields=["codigo", "version"], name="uq_encuesta_codigo_version"),
            models.UniqueConstraint(fields=["codigo"], condition=models.Q(activa=True),
                                    name="uq_encuesta_una_version_activa"),
        ]

    def __str__(self):
        return f"{self.codigo} v{self.version}"
