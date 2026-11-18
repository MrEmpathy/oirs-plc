"""Capturas complementarias para el Informe 3 (pantallas que los recorridos E2E no fotografían): inicio de sesión,
segundo factor, ingreso presencial, administración de usuarios y catálogos. No es una prueba (pytest no la recoge).
Uso: .venv/bin/python tests/e2e/capturas_informe.py
Crea usuarios E2E con credenciales aleatorias, igual que conftest.py, y guarda las imágenes en evidencias/es3/capturas/."""
import json
import secrets
import subprocess
import sys
from pathlib import Path

import pyotp
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import OIRS, RAIZ, SCRIPT_USUARIOS, captura, ingresar, nuevo_contexto  # noqa: E402

clave = "E2e#" + secrets.token_urlsafe(12) + "9a"
secreto_admin = pyotp.random_base32()
datos = {"clave": clave, "usuarios": [
    ["e2e.oirs.plc@dsm.test", "OIRS_EST", "CESFAM-PLC", ""],
    ["e2e.admin@dsm.test", "ADMIN", None, secreto_admin],
]}
subprocess.run(["docker", "compose", "exec", "-T", "-e", "E2E_DATOS=" + json.dumps(datos), "app", "python", "manage.py",
                "shell", "-c", SCRIPT_USUARIOS], cwd=RAIZ, check=True, capture_output=True)

with sync_playwright() as p:
    nav = p.chromium.launch()

    ctx = nuevo_contexto(nav)
    pg = ctx.new_page()
    pg.goto(f"{OIRS}/ingresar")
    captura(pg, "INF-01_inicio_sesion", completa=False)
    pg.fill("#id_email", "e2e.admin@dsm.test")
    pg.fill("#id_password", clave)
    pg.click("button[type=submit]")
    pg.wait_for_url("**/ingresar/verificar")
    captura(pg, "INF-02_segundo_factor", completa=False)
    pg.fill("#id_codigo", pyotp.TOTP(secreto_admin).now())
    pg.click("button[type=submit]")
    pg.wait_for_url(lambda u: "/ingresar" not in u)
    pg.goto(f"{OIRS}/usuarios")
    captura(pg, "INF-04_administracion_usuarios")
    pg.goto(f"{OIRS}/catalogos")
    captura(pg, "INF-05_catalogos")
    ctx.close()

    ctx, pg = ingresar(nav, "e2e.oirs.plc@dsm.test", clave)
    pg.goto(f"{OIRS}/casos/nuevo")
    captura(pg, "INF-03_ingreso_presencial")
    # Reclamo incompleto (descripción corta y sin datos del solicitante): validación del servidor.
    pg.fill("textarea[name=descripcion]", "Esperé.")
    pg.check("input[name=acepta_tratamiento_datos]")
    pg.click("text=Registrar y asignar folio")
    pg.wait_for_load_state()
    captura(pg, "INF-03b_ingreso_presencial_errores")
    ctx.close()
    nav.close()
print("Capturas INF-01..05 guardadas en evidencias/es3/capturas/")
