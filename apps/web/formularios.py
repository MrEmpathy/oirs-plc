"""Formularios del front administrativo. Validan en servidor con listas blancas (SC-01); los mensajes
están en lenguaje simple y dicen cómo corregir el error (sección 5.4)."""
from django import forms
from django.utils import timezone

from apps.catalogos.models import Categoria, Establecimiento, Unidad
from apps.cuentas.models import Rol
from apps.integracion.formularios import RequerimientoPublicoForm
from apps.requerimientos.models import Estado, Respuesta


def FechaInput():
    """<input type="date"> exige AAAA-MM-DD; con el formato regional (dd/mm/aaaa) el navegador lo mostraría vacío."""
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class IngresoForm(forms.Form):
    email = forms.EmailField(label="Correo institucional", max_length=254,
                             widget=forms.EmailInput(attrs={"autocomplete": "username", "autofocus": True}))
    password = forms.CharField(label="Contraseña", strip=False,
                               widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class CodigoForm(forms.Form):
    codigo = forms.RegexField(label="Código de 6 dígitos", regex=r"^\s*\d{3}\s?\d{3}\s*$",
                              error_messages={"invalid": "Escriba los 6 dígitos que muestra su aplicación."},
                              widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric",
                                                            "autofocus": True, "maxlength": 7}))


class CambioClaveForm(forms.Form):
    actual = forms.CharField(label="Contraseña actual", strip=False,
                             widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
    nueva = forms.CharField(label="Nueva contraseña", strip=False,
                            help_text="Mínimo 12 caracteres, con mayúscula, minúscula, número y símbolo.",
                            widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    repetir = forms.CharField(label="Repita la nueva contraseña", strip=False,
                              widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def clean(self):
        d = super().clean()
        if d.get("nueva") and d.get("repetir") and d["nueva"] != d["repetir"]:
            self.add_error("repetir", "Las contraseñas no coinciden.")
        return d


ESTADOS_FILTRO = [("abiertos", "Abiertos"), ("vencidos", "Vencidos"), ("por_vencer", "Por vencer (≤ 5 días hábiles)"),
                  *Estado.choices, ("todos", "Todos")]


class FiltroBandejaForm(forms.Form):
    estado = forms.ChoiceField(choices=ESTADOS_FILTRO, required=False, label="Estado")
    q = forms.CharField(required=False, max_length=60, label="Buscar folio o texto")
    establecimiento = forms.ModelChoiceField(queryset=Establecimiento.objects.exclude(tipo="DSM"), required=False,
                                             label="Establecimiento", empty_label="Todos")


class DerivarForm(forms.Form):
    categoria = forms.ModelChoiceField(queryset=Categoria.objects.filter(activa=True), label="Motivo (categoría)",
                                       empty_label="Seleccione…")
    unidad = forms.ModelChoiceField(queryset=Unidad.objects.none(), label="Unidad de destino", empty_label="Seleccione…")
    instrucciones = forms.CharField(required=False, max_length=1000, label="Instrucciones para la unidad",
                                    widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, establecimiento=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo unidades del mismo establecimiento del caso (regla de integridad PI-04).
        self.fields["unidad"].queryset = Unidad.objects.filter(establecimiento=establecimiento, activa=True).order_by("nombre")
        self.fields["unidad"].label_from_instance = lambda u: u.nombre   # el establecimiento ya es el del caso


class RespuestaForm(forms.Form):
    contenido = forms.CharField(min_length=20, max_length=6000, label="Texto de la respuesta",
                                widget=forms.Textarea(attrs={"rows": 6}))
    medio = forms.ChoiceField(choices=Respuesta.Medio.choices, label="Medio de envío")
    fecha_emision = forms.DateField(label="Fecha de emisión", widget=FechaInput())

    def __init__(self, *args, autoriza_email=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not autoriza_email:  # el correo solo se ofrece si el solicitante lo autorizó (CU05)
            self.fields["medio"].choices = [(Respuesta.Medio.CARTA, Respuesta.Medio.CARTA.label)]
        self.fields["fecha_emision"].initial = timezone.localdate()


class PresencialForm(RequerimientoPublicoForm):
    """CU03: el encargado digitaliza el formulario en papel. Mismas reglas que el canal web; el
    establecimiento es siempre el del encargado y el consentimiento consta en el formulario firmado."""
    acepta_tratamiento_datos = forms.BooleanField(
        required=True, label="El usuario firmó el consentimiento de tratamiento de datos en el formulario en papel")

    def __init__(self, *args, establecimiento=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["establecimiento"].queryset = Establecimiento.objects.filter(pk=getattr(establecimiento, "pk", None))
        self.fields["establecimiento"].initial = getattr(establecimiento, "codigo", None)
        self.fields["establecimiento"].widget = forms.HiddenInput()
        etiquetas = {"tipo": "Tipo de solicitud", "descripcion": "Descripción de la situación",
                     "peticion_concreta": "Petición concreta", "fecha_atencion": "Fecha de la atención",
                     "nombre": "Nombre", "apellidos": "Apellidos", "email": "Correo electrónico",
                     "telefono": "Teléfono", "edad": "Edad", "sexo": "Sexo",
                     "autoriza_respuesta_email": "Autoriza respuesta por correo electrónico"}
        for campo, texto in etiquetas.items():
            self.fields[campo].label = texto
        self.fields["descripcion"].widget = forms.Textarea(attrs={"rows": 5})
        self.fields["peticion_concreta"].widget = forms.Textarea(attrs={"rows": 3})
        self.fields["fecha_atencion"].widget = FechaInput()


class ReportesForm(forms.Form):
    desde = forms.DateField(label="Desde", widget=FechaInput())
    hasta = forms.DateField(label="Hasta", widget=FechaInput())
    establecimiento = forms.ModelChoiceField(queryset=Establecimiento.objects.exclude(tipo="DSM"), required=False,
                                             label="Establecimiento", empty_label="Toda la red")

    def clean(self):
        d = super().clean()
        if d.get("desde") and d.get("hasta"):
            if d["desde"] > d["hasta"]:
                raise forms.ValidationError("La fecha «Desde» debe ser anterior o igual a «Hasta».")
            if (d["hasta"] - d["desde"]).days > 731:
                raise forms.ValidationError("El período máximo es de 2 años.")
        return d


class UsuarioForm(forms.Form):
    email = forms.EmailField(label="Correo institucional", max_length=254)
    nombre = forms.CharField(max_length=80)
    apellidos = forms.CharField(max_length=80)
    rol = forms.ChoiceField(choices=Rol.choices, label="Perfil")
    establecimiento = forms.ModelChoiceField(queryset=Establecimiento.objects.filter(activo=True).exclude(tipo="DSM"),
                                             required=False, empty_label="—",
                                             help_text="Obligatorio para Encargado OIRS de establecimiento y Dirección.")

    def __init__(self, *args, edicion=False, **kwargs):
        super().__init__(*args, **kwargs)
        if edicion:
            self.fields["email"].disabled = True

    def clean(self):
        d = super().clean()
        if d.get("rol") in ("OIRS_EST", "DIRECCION") and not d.get("establecimiento"):
            self.add_error("establecimiento", "Este perfil requiere un establecimiento.")
        return d


class EstablecimientoForm(forms.ModelForm):
    class Meta:
        model = Establecimiento
        fields = ["codigo", "nombre", "tipo", "direccion", "telefono"]
        help_texts = {"codigo": "Usado por WordPress y en los códigos QR (ej. CESFAM-PLC)."}

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip().upper()
        if not codigo.replace("-", "").isalnum():
            raise forms.ValidationError("Use solo letras, números y guiones.")
        return codigo


class UnidadForm(forms.ModelForm):
    class Meta:
        model = Unidad
        fields = ["establecimiento", "nombre"]


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "es_otro"]
        labels = {"es_otro": "Es la categoría abierta «Otro»"}


class FeriadoForm(forms.Form):
    fecha = forms.DateField(widget=FechaInput())
    descripcion = forms.CharField(max_length=120)
