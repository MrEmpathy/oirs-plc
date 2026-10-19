"""PR-01..PR-03: carga concurrente sobre la API (gunicorn + PostgreSQL + base documental).
Ejecución: locust -f tests/performance/locustfile.py --headless -u 50 -r 10 -t 2m --host http://127.0.0.1:8000"""
import json
import random
import time

from locust import HttpUser, between, task

from apps.integracion.hmac_firma import firmar

SECRETO = "dev-hmac-secret-solo-pruebas"
CLAVE = "Demo#Oirs2026!"


class SitioWordPress(HttpUser):
    """Simula el plugin de WordPress enviando formularios ciudadanos (servidor a servidor)."""
    weight = 2
    wait_time = between(1, 3)

    def _post(self, url, datos, nombre):
        cuerpo = json.dumps(datos).encode()
        ts = int(time.time())
        self.client.post(url, data=cuerpo, name=nombre, headers={"Content-Type": "application/json",
                         "X-OIRS-Timestamp": str(ts), "X-OIRS-Firma": firmar(cuerpo, ts, SECRETO)})

    @task(3)
    def reclamo(self):
        self._post("/api/v1/publico/requerimientos", {
            "tipo": random.choice(["RECLAMO", "CONSULTA", "SUGERENCIA"]),
            "establecimiento": random.choice(["CESFAM-PLC", "CESFAM-PUL", "CESFAM-CON"]),
            "descripcion": "Prueba de carga: demora en la atención de SOME.", "nombre": "Carga",
            "email": "carga@example.com", "acepta_tratamiento_datos": True}, "POST requerimiento (WP)")

    @task(2)
    def encuesta(self):
        self._post("/api/v1/publico/encuestas/satisfaccion-usuaria/respuestas", {
            "establecimiento": "CESFAM-PLC", "respuestas": {f"p{i}": random.randint(1, 7) for i in range(1, 6)}},
            "POST encuesta (WP)")


class Funcionario(HttpUser):
    """Encargado OIRS / dirección operando la bandeja y los reportes."""
    weight = 3
    wait_time = between(2, 5)

    def on_start(self):
        email = random.choice(["oirs.plc@dsm.test", "oirs.pul@dsm.test", "dir.plc@dsm.test"])
        self.client.get("/api/v1/sesion/csrf", name="GET csrf")
        r = self.client.post("/api/v1/sesion/iniciar", json={"email": email, "password": CLAVE},
                             headers={"X-CSRFToken": self.client.cookies.get("csrftoken", "")}, name="POST login")
        r.raise_for_status()
        self.csrf = self.client.cookies.get("csrftoken", "")

    @task(5)
    def bandeja(self):
        self.client.get("/api/v1/requerimientos?estado=EN_PROCESO", name="GET bandeja")

    @task(2)
    def busqueda(self):
        self.client.get("/api/v1/requerimientos?q=SOME", name="GET búsqueda")

    @task(1)
    def indicadores(self):
        self.client.get("/api/v1/reportes/indicadores?desde=2026-01-01&hasta=2026-10-31", name="GET indicadores")
