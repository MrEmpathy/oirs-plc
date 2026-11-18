"""E2E-10: caída de las bases de datos en mitad de una sesión (prueba destructiva, no la recoge pytest).

Con una sesión abierta en el sistema y formularios a medio enviar, detiene uno a uno PostgreSQL, MongoDB, Redis y
MariaDB, observa lo que ve el usuario, vuelve a levantarlos y comprueba que la sesión sigue viva, que no quedaron
datos a medias y que el sistema se recupera solo. Registra esperado, obtenido y si cumple.

Uso:  .venv/bin/python tests/e2e/caida_bases.py ETAPA        (ETAPA: antes | despues; solo nombra la evidencia)
Requiere el entorno Docker en marcha. Interrumpe el servicio durante unos segundos por cada base.
Evidencia: evidencias/es3/caida_bases_<ETAPA>.txt y capturas E2E-10*_<ETAPA>.png. Sale con código 1 si algo no cumple."""
import json
import secrets
from contextlib import contextmanager
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import OIRS, RAIZ, SCRIPT_USUARIOS, WP, captura, ingresar, limpiar_limite_wordpress, nuevo_contexto  # noqa: E402

ETAPA = sys.argv[1] if len(sys.argv) > 1 else "prueba"
RESULTADOS = []


def dc(*args, check=True):
    return subprocess.run(["docker", "compose", *args], cwd=RAIZ, check=check, capture_output=True, text=True)


def psql(sql):
    return dc("exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "oirs_plc", "-Atc", sql).stdout.strip()


def mongo(js):
    return dc("exec", "-T", "mongo", "sh", "-c",
              f"mongosh -u root -p \"$MONGO_INITDB_ROOT_PASSWORD\" --quiet --eval '{js}'").stdout.strip()


def detener(servicio):
    dc("stop", servicio)
    time.sleep(2)     # Docker cambia las interfaces de red del equipo y Chromium aborta lo que esté en curso


def ir(pagina, url):
    """Navega reintentando si Chromium informa un cambio de red (efecto de detener o levantar contenedores,
    no de la aplicación)."""
    for intento in range(3):
        try:
            return pagina.goto(url)
        except Exception as e:  # noqa: BLE001
            if "ERR_NETWORK_CHANGED" not in str(e) or intento == 2:
                raise
            time.sleep(1)


def levantar(servicio, listo):
    dc("start", servicio)
    for _ in range(60):
        if subprocess.run(["docker", "compose", *listo], cwd=RAIZ, capture_output=True).returncode == 0:
            time.sleep(2)
            return
        time.sleep(1)
    raise RuntimeError(f"{servicio} no volvió")


LISTO = {
    "postgres": ["exec", "-T", "postgres", "pg_isready", "-U", "postgres"],
    "mongo": ["exec", "-T", "mongo", "mongosh", "--quiet", "--eval", "db.runCommand({ping:1})"],
    "redis": ["exec", "-T", "redis", "redis-cli", "ping"],
    "mariadb": ["exec", "-T", "mariadb", "healthcheck.sh", "--connect"],
}


@contextmanager
def caido(servicio):
    """Detiene el servicio y lo vuelve a levantar SIEMPRE, aunque la prueba falle a mitad de camino."""
    detener(servicio)
    try:
        yield
    finally:
        levantar(servicio, LISTO[servicio])


def registrar(ident, escenario, esperado, obtenido, cumple):
    RESULTADOS.append((ident, escenario, esperado, obtenido, "Sí" if cumple else "NO"))
    print(f"[{'OK' if cumple else 'NO'}] {ident} {escenario}: {obtenido}")


def visitar(pagina, url):
    """Devuelve (código HTTP, título de la página, si muestra una traza o un error sin formato)."""
    t0 = time.perf_counter()
    r = ir(pagina, url)
    dt = time.perf_counter() - t0
    contenido = pagina.content()
    crudo = "Traceback" in contenido or "<h1>Server Error (500)</h1>" in contenido or \
        "Internal Server Error" in contenido
    return (r.status if r else 0), pagina.title(), crudo, dt


def enviar_formulario_oirs(pagina, marca):
    ir(pagina, f"{WP}/oirs/")
    pagina.check("input[name=tipo][value=SUGERENCIA]")
    pagina.select_option("#oirs-establecimiento", "CESFAM-PLC")
    pagina.fill("#oirs-descripcion", f"Sugerencia escrita durante la caída de la base ({marca}).")
    pagina.check("input[name=acepta_tratamiento_datos]")


def abrir_encuesta(pagina):
    """El ciudadano abre la encuesta (con la base en marcha) y marca sus notas."""
    ir(pagina, f"{WP}/encuesta-de-satisfaccion/?est=CESFAM-PLC")
    for fs in pagina.locator("fieldset.oirs-escala").all():
        fs.locator(".oirs-escala__opcion").nth(5).click()


def enviar_encuesta(pagina):
    pagina.click("text=Enviar respuesta")
    pagina.wait_for_load_state()
    if pagina.locator(".oirs-confirmacion").count():
        return "confirmación «¡Gracias por su opinión!»"
    aviso = pagina.locator(".oirs-aviso--error")
    return "error: " + (aviso.first.inner_text().strip().splitlines()[0] if aviso.count() else "sin mensaje")


def main():
    clave = "E2e#" + secrets.token_urlsafe(12) + "9a"
    datos = {"clave": clave, "usuarios": [["e2e.oirs.plc@dsm.test", "OIRS_EST", "CESFAM-PLC", ""],
                                          ["e2e.dir.plc@dsm.test", "DIRECCION", "CESFAM-PLC", ""]]}
    dc("exec", "-T", "-e", "E2E_DATOS=" + json.dumps(datos), "app", "python", "manage.py", "shell", "-c",
       SCRIPT_USUARIOS)
    limpiar_limite_wordpress()
    marca = f"E2E-10-{int(time.time())}"

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx, pg = ingresar(nav, "e2e.oirs.plc@dsm.test", clave)        # sesión abierta del encargado OIRS
        form = ctx.new_page()                                            # otra pestaña, misma sesión
        ciu = nuevo_contexto(nav).new_page()                             # ciudadano en el sitio web

        # ---------------------------------------------------------------- PostgreSQL
        visitar(pg, f"{OIRS}/bandeja")
        casos_antes = int(psql("select count(*) from requerimiento;"))
        ir(form, f"{OIRS}/casos/nuevo")                                # formulario presencial a medio llenar
        form.select_option("select[name=tipo]", "SUGERENCIA")
        form.fill("textarea[name=descripcion]", f"Ingreso presencial durante la caída de la base ({marca}).")
        form.check("input[name=acepta_tratamiento_datos]")
        enviar_formulario_oirs(ciu, marca)                              # ciudadano con el formulario listo
        with caido("postgres"):
            cod, titulo, crudo, _ = visitar(pg, f"{OIRS}/bandeja")
            captura(pg, f"E2E-10a_postgres_caido_{ETAPA}", completa=False)
            registrar("E2E-10.1", "PostgreSQL caído: el funcionario navega a la bandeja",
                      "Página «Servicio no disponible» (503) sin detalles técnicos", f"HTTP {cod} · «{titulo}»"
                      + (" · error sin formato" if crudo else ""), cod == 503 and not crudo)
            t0 = time.perf_counter()
            try:
                with form.expect_response(lambda r: "/casos/nuevo" in r.url and r.request.method == "POST",
                                          timeout=60000) as rp:
                    form.click("text=Registrar y asignar folio", timeout=60000)
                cod2 = rp.value.status
                contenido = form.content()
                crudo2 = "Internal Server Error" in contenido or "Traceback" in contenido
                titulo2 = form.title()
            except Exception as e:  # noqa: BLE001
                cod2, titulo2, crudo2 = 0, f"sin respuesta ({type(e).__name__})", True
            dt2 = time.perf_counter() - t0
            registrar("E2E-10.2", "PostgreSQL caído: el funcionario envía un ingreso presencial",
                      "«Servicio no disponible» (503) en menos de 5 s; el caso no se crea a medias",
                      f"HTTP {cod2} en {dt2:.1f} s · «{titulo2}»" + (" · error sin formato" if crudo2 else ""),
                      cod2 == 503 and not crudo2 and dt2 < 5)
            ciu.click("text=Enviar solicitud")
            ciu.wait_for_load_state()
            aviso = ciu.locator(".oirs-aviso--error")
            texto = aviso.first.inner_text().strip().splitlines()[0] if aviso.count() else "sin aviso"
            conserva = ciu.locator("#oirs-descripcion").count() > 0 and marca in ciu.input_value("#oirs-descripcion")
            captura(ciu, f"E2E-10b_wordpress_api_caida_{ETAPA}", completa=False)
            registrar("E2E-10.3", "PostgreSQL caído: el ciudadano envía el formulario OIRS",
                      "Aviso de servicio no disponible y el texto escrito se conserva",
                      f"«{texto}» · texto conservado: {'sí' if conserva else 'no'}",
                      "no está disponible" in texto and conserva)
        fallos, redirigido = 0, False
        for _ in range(12):                                             # 3 procesos × 4 hilos de gunicorn
            r = ir(pg, f"{OIRS}/bandeja")
            fallos += 0 if r and r.status == 200 else 1
            redirigido = redirigido or "/ingresar" in pg.url
        registrar("E2E-10.4", "PostgreSQL de vuelta: 12 peticiones seguidas con la misma sesión",
                  "Todas 200, sin volver a iniciar sesión", f"{12 - fallos}/12 con 200; "
                  f"{'pidió iniciar sesión' if redirigido else 'la sesión siguió activa'}", fallos == 0 and not redirigido)
        casos_despues = int(psql("select count(*) from requerimiento;"))
        huerfanos = psql("select count(*) from requerimiento r where not exists "
                         "(select 1 from historial_estado h where h.requerimiento_id = r.id);")
        registrar("E2E-10.5", "Integridad tras la caída", "Ningún caso nuevo ni caso sin historial",
                  f"casos antes {casos_antes}, después {casos_despues}; casos sin historial: {huerfanos}",
                  casos_despues == casos_antes and huerfanos == "0")
        if ciu.locator("text=Enviar solicitud").count():
            ciu.click("text=Enviar solicitud")                           # el ciudadano reintenta
            ciu.wait_for_load_state()
        folio = ciu.locator(".oirs-folio")
        aviso = ciu.locator(".oirs-aviso--error, .oirs-campo__error")
        sin_folio = "sin folio · " + " | ".join(a.inner_text().strip().replace("\n", " ") for a in aviso.all())
        registrar("E2E-10.6", "Reintento del ciudadano con la base de vuelta", "Folio asignado, una sola vez",
                  f"folio {folio.inner_text().strip()}" if folio.count() else sin_folio,
                  folio.count() == 1 and int(psql("select count(*) from requerimiento;")) == casos_antes + 1)

        # ---------------------------------------------------------------- MongoDB
        abrir_encuesta(ciu)                                             # el ciudadano ya tiene la encuesta abierta
        with caido("mongo"):
            ctx2 = nuevo_contexto(nav)
            p2 = ctx2.new_page()
            ir(p2, f"{OIRS}/ingresar")
            p2.fill("#id_email", "e2e.dir.plc@dsm.test")
            p2.fill("#id_password", clave)
            t0 = time.perf_counter()
            p2.click("button[type=submit]")
            p2.wait_for_load_state()
            dt = time.perf_counter() - t0
            ok = "/bandeja" in p2.url
            registrar("E2E-10.7", "MongoDB caído: la Dirección inicia sesión",
                      "Ingresa sin demora perceptible (< 2 s)", f"{'ingresó' if ok else 'no ingresó'} en {dt:.1f} s",
                      ok and dt < 2)
            ctx2.close()
            cod, titulo, crudo, dt = visitar(pg, f"{OIRS}/bandeja")
            registrar("E2E-10.8", "MongoDB caído: el encargado sigue trabajando con los casos",
                      "Bandeja disponible (200) sin demora", f"HTTP {cod} en {dt:.1f} s", cod == 200 and dt < 2)
            resultado = enviar_encuesta(ciu)
            registrar("E2E-10.9", "MongoDB caído: el ciudadano envía la encuesta",
                      "Aviso de servicio no disponible", resultado, "no está disponible" in resultado)
        respaldo = dc("logs", "--since", "5m", "app", check=False).stdout.count("BITACORA_RESPALDO")
        registrar("E2E-10.10", "Bitácora durante la caída de MongoDB",
                  "Los eventos quedan completos en el registro de la aplicación (no se pierden)",
                  f"{respaldo} evento(s) completos en el registro", respaldo > 0)

        # ---------------------------------------------------------------- Redis
        docs_antes = int(mongo('print(db.getSiblingDB("oirs_plc_docs").respuestas_encuesta.countDocuments())'))
        abrir_encuesta(ciu)
        with caido("redis"):
            cod, titulo, crudo, _ = visitar(pg, f"{OIRS}/reportes")
            captura(pg, f"E2E-10c_reportes_sin_redis_{ETAPA}", completa=False)
            registrar("E2E-10.11", "Redis caído: el encargado abre los reportes",
                      "Reportes disponibles (200), calculados sin caché", f"HTTP {cod} · «{titulo}»", cod == 200)
            resultado = enviar_encuesta(ciu)
            docs = int(mongo('print(db.getSiblingDB("oirs_plc_docs").respuestas_encuesta.countDocuments())'))
            registrar("E2E-10.12", "Redis caído: el ciudadano envía la encuesta",
                      "Confirmación y exactamente una respuesta guardada",
                      f"{resultado}; respuestas guardadas: {docs - docs_antes}",
                      "Gracias" in resultado and docs - docs_antes == 1)

        # ---------------------------------------------------------------- MariaDB (WordPress)
        with caido("mariadb"):
            r = ir(ciu, f"{WP}/")
            sitio = r.status if r else 0
            cod, _, _, _ = visitar(pg, f"{OIRS}/bandeja")
            registrar("E2E-10.13", "MariaDB caído: sitio público y sistema",
                      "El sitio WordPress cae; el sistema de funcionarios sigue disponible",
                      f"sitio HTTP {sitio}; sistema HTTP {cod}", sitio >= 500 and cod == 200)
        time.sleep(2)
        r = ir(ciu, f"{WP}/")
        registrar("E2E-10.14", "MariaDB de vuelta", "El sitio vuelve sin intervención", f"HTTP {r.status if r else 0}",
                  bool(r) and r.status == 200)
        ref = dc("exec", "-T", "app", "python", "manage.py", "verificar_referencias", check=False).stdout
        registrar("E2E-10.15", "Consistencia entre bases al final", "Sin referencias huérfanas",
                  "sin referencias huérfanas" if "Sin referencias huérfanas" in ref else ref.strip()[-80:],
                  "Sin referencias huérfanas" in ref)
        ctx.close()
        nav.close()
    limpiar_limite_wordpress()

    salida = RAIZ / "evidencias" / "es3" / f"caida_bases_{ETAPA}.txt"
    lineas = [f"# E2E-10 · caída de las bases durante una sesión · etapa «{ETAPA}» · "
              f"{datetime.now():%d-%m-%Y %H:%M}", ""]
    for ident, esc, esp, obt, cumple in RESULTADOS:
        lineas += [f"{ident} · {esc}", f"   Esperado: {esp}", f"   Obtenido: {obt}", f"   Cumple:   {cumple}", ""]
    fallidos = [r[0] for r in RESULTADOS if r[4] == "NO"]
    lineas.append(f"Resultado: {len(RESULTADOS) - len(fallidos)}/{len(RESULTADOS)} cumplen"
                  + (f" · no cumplen: {', '.join(fallidos)}" if fallidos else ""))
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(lineas[-1], "→", salida)
    return 1 if fallidos else 0


if __name__ == "__main__":
    sys.exit(main())
