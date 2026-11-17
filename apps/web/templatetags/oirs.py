from django import forms, template
from django.utils.html import format_html

register = template.Library()

SEMAFORO = {"VERDE": ("En plazo", "verde"), "AMARILLO": ("Por vencer", "amarillo"), "ROJO": ("Vencido", "rojo")}


@register.filter
def control(campo):
    """Dibuja el control de un campo con las clases de Bootstrap y los atributos ARIA de validación."""
    w = campo.field.widget
    if isinstance(w, forms.CheckboxInput):
        clase = "form-check-input"
    elif isinstance(w, (forms.Select, forms.SelectMultiple)):
        clase = "form-select"
    else:
        clase = "form-control"
    attrs = {"class": clase + (" is-invalid" if campo.errors else "")}
    describe = []
    if campo.help_text:
        describe.append(f"{campo.auto_id}_ayuda")
    if campo.errors:
        attrs["aria-invalid"] = "true"
        describe.append(f"{campo.auto_id}_error")
    if describe:
        attrs["aria-describedby"] = " ".join(describe)
    return campo.as_widget(attrs=attrs)


@register.simple_tag
def semaforo(color, restantes=None):
    if not color:
        return ""
    texto, clase = SEMAFORO[color]
    detalle = ""
    if restantes is not None:
        if restantes < 0:
            detalle = f" · {-restantes} d. hábiles de atraso"
        elif restantes == 0:
            detalle = " · vence hoy"
        else:
            detalle = f" · {restantes} d. hábiles"
    return format_html('<span class="chip chip--{}"><span class="chip__punto" aria-hidden="true"></span>{}{}</span>',
                       clase, texto, detalle)


@register.simple_tag
def estado(valor, etiqueta):
    return format_html('<span class="chip chip--estado chip--{}">{}</span>', valor.lower(), etiqueta)
