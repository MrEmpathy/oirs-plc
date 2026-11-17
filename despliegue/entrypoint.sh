#!/bin/sh
# Arranque del contenedor de la aplicación: archivos estáticos + gunicorn (3 procesos x 4 hilos, sección 4.4).
set -e
python manage.py collectstatic --noinput --verbosity 0
exec gunicorn config.wsgi:application -k gthread -w "${GUNICORN_WORKERS:-3}" --threads "${GUNICORN_THREADS:-4}" \
     --timeout 60 -b 0.0.0.0:8000 --access-logfile - --forwarded-allow-ips="*" --no-control-socket
