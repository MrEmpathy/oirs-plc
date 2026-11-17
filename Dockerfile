# Imagen de la aplicación Django del Sistema de Gestión OIRS (gunicorn gthread detrás de Nginx).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
ARG INSTALAR_DEV=0
RUN pip install -r requirements.txt \
 && if [ "$INSTALAR_DEV" = "1" ]; then pip install -r requirements-dev.txt; fi

COPY . .

# La aplicación nunca se ejecuta como root dentro del contenedor.
RUN useradd --system --uid 10001 --home /app oirs \
 && mkdir -p /app/staticfiles \
 && chown -R oirs /app/staticfiles
USER oirs

EXPOSE 8000
CMD ["sh", "despliegue/entrypoint.sh"]
