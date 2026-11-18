"""Infraestructura de las pruebas E2E: usuarios de prueba con credenciales aleatorias creadas en cada
ejecución (nunca escritas en el repositorio) y navegador Chromium headless."""
import json
import os
import secrets
import subprocess
from pathlib import Path

import pyotp
import pytest
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
OIRS = os.environ.get("E2E_OIRS", "https://localhost:8443")
WP = os.environ.get("E2E_WP", "https://localhost:8080")
ENCUESTA = os.environ.get("E2E_ENCUESTA", "https://localhost:8082")
CAPTURAS = RAIZ / "evidencias" / "es3" / "capturas"

SCRIPT_USUARIOS = """
import json, os
from apps.catalogos.models import Establecimiento
from apps.cuentas.models import Usuario
d = json.loads(os.environ["E2E_DATOS"])
for email, rol, est, secreto in d["usuarios"]:
    u = Usuario.objects.filter(email=email).first() or Usuario(email=email)
    u.nombre, u.apellidos, u.rol = "Prueba", "E2E " + rol, rol
    u.establecimiento = Establecimiento.objects.get(codigo=est) if est else None
    u.is_active, u.debe_cambiar_clave, u.intentos_fallidos, u.bloqueado_hasta = True, False, 0, None
    u.mfa_secreto = secreto
    u.set_password(d["clave"])
    u.save()
print("usuarios e2e listos")
"""


def limpiar_limite_wordpress():
    """El plugin limita a 10 envíos por hora por IP (transients). Las pruebas parten y terminan sin contadores."""
    subprocess.run(["docker", "compose", "--profile", "herramientas", "run", "--rm", "-T", "wpcli", "wp", "transient",
                    "delete", "--all"], cwd=RAIZ, check=True, capture_output=True)


@pytest.fixture(scope="session", autouse=True)
def entorno_limpio():
    limpiar_limite_wordpress()
    yield
    limpiar_limite_wordpress()


@pytest.fixture(scope="session")
def credenciales():
    clave = "E2e#" + secrets.token_urlsafe(12) + "9a"
    datos = {"clave": clave, "usuarios": [
        ["e2e.oirs.plc@dsm.test", "OIRS_EST", "CESFAM-PLC", ""],
        ["e2e.dir.plc@dsm.test", "DIRECCION", "CESFAM-PLC", ""],
        ["e2e.dsm@dsm.test", "OIRS_DSM", None, pyotp.random_base32()],
    ]}
    subprocess.run(["docker", "compose", "exec", "-T", "-e", "E2E_DATOS=" + json.dumps(datos), "app",
                    "python", "manage.py", "shell", "-c", SCRIPT_USUARIOS], cwd=RAIZ, check=True, capture_output=True)
    return {"clave": clave, "dsm_secreto": datos["usuarios"][2][3]}


@pytest.fixture(scope="session")
def navegador():
    with sync_playwright() as p:
        nav = p.chromium.launch()
        yield nav
        nav.close()


def nuevo_contexto(navegador, **kw):
    kw.setdefault("viewport", {"width": 1280, "height": 900})
    return navegador.new_context(ignore_https_errors=True, locale="es-CL", **kw)


def captura(pagina, nombre, completa=True):
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    pagina.screenshot(path=str(CAPTURAS / f"{nombre}.png"), full_page=completa)


def ingresar(navegador, email, clave, secreto=None, **kw):
    """Inicia sesión una vez por perfil (cada POST a /ingresar cuenta para el límite de Nginx)."""
    ctx = nuevo_contexto(navegador, **kw)
    pg = ctx.new_page()
    pg.goto(f"{OIRS}/ingresar")
    pg.fill("#id_email", email)
    pg.fill("#id_password", clave)
    pg.click("button[type=submit]")
    if secreto:
        pg.wait_for_url("**/ingresar/verificar")
        pg.fill("#id_codigo", pyotp.TOTP(secreto).now())
        pg.click("button[type=submit]")
    pg.wait_for_url(lambda u: "/ingresar" not in u)
    return ctx, pg


@pytest.fixture(scope="session")
def sesion_oirs(navegador, credenciales):
    ctx, pg = ingresar(navegador, "e2e.oirs.plc@dsm.test", credenciales["clave"])
    yield pg
    ctx.close()


@pytest.fixture(scope="session")
def sesion_dsm(navegador, credenciales):
    ctx, pg = ingresar(navegador, "e2e.dsm@dsm.test", credenciales["clave"], credenciales["dsm_secreto"])
    yield pg
    ctx.close()


@pytest.fixture(scope="session")
def sesion_direccion(navegador, credenciales):
    ctx, pg = ingresar(navegador, "e2e.dir.plc@dsm.test", credenciales["clave"])
    yield pg
    ctx.close()
