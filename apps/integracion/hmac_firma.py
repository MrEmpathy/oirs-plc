"""Autenticación servidor-a-servidor WordPress -> API mediante HMAC-SHA256 con marca de tiempo.

Cabeceras: X-OIRS-Timestamp (epoch s) y X-OIRS-Firma = hex(HMAC(secret, f"{ts}.{cuerpo}")).
Mitiga suplantación del origen, alteración del cuerpo y repetición (replay) fuera de ventana."""
import hashlib
import hmac
import time

from django.conf import settings


def firmar(cuerpo: bytes, ts: int, secreto: str) -> str:
    mensaje = str(ts).encode() + b"." + cuerpo
    return hmac.new(secreto.encode(), mensaje, hashlib.sha256).hexdigest()


def verificar(request) -> bool:
    ts = request.headers.get("X-OIRS-Timestamp", "")
    firma = request.headers.get("X-OIRS-Firma", "")
    if not ts.isdigit() or not firma:
        return False
    if abs(time.time() - int(ts)) > settings.WP_HMAC_TOLERANCIA_SEG:
        return False
    esperada = firmar(request.body, int(ts), settings.WP_HMAC_SECRET)
    return hmac.compare_digest(esperada, firma)  # comparación en tiempo constante
