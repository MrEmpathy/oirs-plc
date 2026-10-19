# Sistema de Gestión OIRS — Prueba de concepto (Proyecto Integrado, Informe N.º 2)

Requisitos: Python 3.12+, PostgreSQL 16, MongoDB 7 (o motor compatible), PHP 8.x (prueba PI-12).

```bash
pip install -r requirements.txt pytest pytest-django pytest-cov locust bandit pip-audit pyotp holidays
# Roles de BD: oirs_owner (migraciones, CREATEDB) y oirs_app (aplicación)
export DJANGO_SECRET_KEY=... DJANGO_SECURE=0 PG_HOST=127.0.0.1 WP_HMAC_SECRET=dev-hmac-secret-solo-pruebas
PG_USER=oirs_owner PG_PASSWORD=... python manage.py migrate
PG_USER=oirs_app PG_PASSWORD=... python manage.py sembrar_datos
PG_USER=oirs_owner PG_PASSWORD=... pytest -v --cov=apps          # 81 pruebas
php tests/integration/test_firma_php.php                          # requiere la API en ejecución (gunicorn)
locust -f tests/performance/locustfile.py --headless -u 30 -r 5 -t 120s --host http://127.0.0.1:8000
```

`evidencias/` contiene las salidas de la ejecución del 18-10-2026. `prototipo.html` es el prototipo v2.
