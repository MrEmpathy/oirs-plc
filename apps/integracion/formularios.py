"""Validación de entradas en servidor con listas blancas (SC-01). Nunca se confía en la validación del sitio."""
import re

from django import forms

from apps.catalogos.models import Establecimiento
from apps.requerimientos.models import Solicitante, TipoRequerimiento

RE_TELEFONO = re.compile(r"^\+?56?\s?9?\d{8}$|^\+?\d{8,12}$")


class RequerimientoPublicoForm(forms.Form):
    tipo = forms.ChoiceField(choices=TipoRequerimiento.choices)
    establecimiento = forms.ModelChoiceField(queryset=Establecimiento.objects.filter(activo=True), to_field_name="codigo")
    descripcion = forms.CharField(min_length=10, max_length=4000)
    peticion_concreta = forms.CharField(required=False, max_length=2000)
    fecha_atencion = forms.DateField(required=False)
    nombre = forms.CharField(required=False, max_length=80)
    apellidos = forms.CharField(required=False, max_length=80)
    email = forms.EmailField(required=False)
    telefono = forms.CharField(required=False, max_length=15)
    edad = forms.IntegerField(required=False, min_value=0, max_value=120)
    sexo = forms.ChoiceField(required=False, choices=[("", "")] + list(Solicitante.Sexo.choices))
    autoriza_respuesta_email = forms.BooleanField(required=False)
    acepta_tratamiento_datos = forms.BooleanField(required=True)

    def clean_telefono(self):
        tel = re.sub(r"[\s\-()]", "", self.cleaned_data.get("telefono") or "")
        if tel and not RE_TELEFONO.match(tel):
            raise forms.ValidationError("Teléfono con formato inválido.")
        return tel

    def clean(self):
        datos = super().clean()
        if datos.get("tipo") in ("RECLAMO", "CONSULTA", "SOLICITUD"):
            if not datos.get("nombre"):
                self.add_error("nombre", "Requerido para poder responder.")
            if not (datos.get("email") or datos.get("telefono")):
                self.add_error("email", "Indique correo o teléfono para poder responder.")
        return datos

    def datos_solicitante(self):
        d = self.cleaned_data
        if not d.get("nombre"):
            return None
        return {k: d.get(k) for k in ("nombre", "apellidos", "email", "telefono", "edad", "sexo",
                                      "autoriza_respuesta_email") if d.get(k) not in (None,)}
