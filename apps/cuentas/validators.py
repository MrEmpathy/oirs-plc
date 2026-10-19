import re

from django.core.exceptions import ValidationError


class ComplejidadValidator:
    """Exige mayúscula, minúscula, dígito y símbolo (política de contraseñas PA-02)."""
    reglas = [(r"[A-Z]", "una mayúscula"), (r"[a-z]", "una minúscula"), (r"\d", "un dígito"), (r"[^\w\s]", "un símbolo")]

    def validate(self, password, user=None):
        faltan = [txt for patron, txt in self.reglas if not re.search(patron, password or "")]
        if faltan:
            raise ValidationError("La contraseña debe incluir " + ", ".join(faltan) + ".", code="complejidad")

    def get_help_text(self):
        return "La contraseña debe incluir mayúscula, minúscula, dígito y símbolo."
