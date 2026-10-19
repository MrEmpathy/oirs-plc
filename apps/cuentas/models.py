from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Rol(models.TextChoices):
    ADMIN = "ADMIN", "Administrador del sistema"
    OIRS_DSM = "OIRS_DSM", "Encargado OIRS Departamento de Salud"
    OIRS_EST = "OIRS_EST", "Encargado OIRS de establecimiento"
    DIRECCION = "DIRECCION", "Dirección de establecimiento"


ROLES_CON_ESTABLECIMIENTO = (Rol.OIRS_EST, Rol.DIRECCION)


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password, **extra):
        if not email:
            raise ValueError("El correo es obligatorio")
        usuario = self.model(email=self.normalize_email(email).lower(), **extra)
        usuario.set_password(password)
        usuario.full_clean(exclude=["password"])
        usuario.save(using=self._db)
        return usuario


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Funcionario con acceso al sistema administrativo. Cuentas individuales, nunca compartidas."""
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    rol = models.CharField(max_length=10, choices=Rol.choices)
    establecimiento = models.ForeignKey("catalogos.Establecimiento", null=True, blank=True,
                                        on_delete=models.PROTECT, related_name="funcionarios")
    is_active = models.BooleanField(default=True)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    mfa_secreto = models.CharField(max_length=64, blank=True)  # cifrado en reposo a nivel de volumen
    fecha_creacion = models.DateTimeField(default=timezone.now)
    debe_cambiar_clave = models.BooleanField(default=True)

    objects = UsuarioManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre", "apellidos", "rol"]

    class Meta:
        db_table = "usuario"
        constraints = [
            # Integridad: los perfiles de establecimiento DEBEN tener establecimiento asignado
            models.CheckConstraint(
                name="ck_usuario_rol_establecimiento",
                condition=(models.Q(rol__in=["OIRS_EST", "DIRECCION"], establecimiento__isnull=False)
                           | models.Q(rol__in=["ADMIN", "OIRS_DSM"])),
            )
        ]

    def clean(self):
        if self.rol in ROLES_CON_ESTABLECIMIENTO and not self.establecimiento_id:
            raise ValidationError("Este perfil requiere un establecimiento asignado.")

    @property
    def esta_bloqueado(self):
        return bool(self.bloqueado_hasta and self.bloqueado_hasta > timezone.now())

    @property
    def requiere_mfa(self):
        from django.conf import settings
        return self.rol in settings.ROLES_CON_MFA

    def __str__(self):
        return f"{self.nombre} {self.apellidos} <{self.email}>"
