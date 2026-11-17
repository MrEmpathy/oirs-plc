# Registro de defectos — Implementación (Unidad 3)

Formato según la Guía ES3 (indicadores 3.1.5.11 y 3.1.6.12): cada defecto conserva el resultado original
fallido, su causa y la nueva ejecución tras la corrección. Las incidencias INC-01 a INC-05 corresponden a la
prueba de concepto (Informe N.º 2).

| ID | Fecha | Detectado por | Esperado | Obtenido | Causa (comprobada) | Severidad | Corrección | Nueva verificación |
|---|---|---|---|---|---|---|---|---|
| DEF-01 | 17-11-2026 | Revisión de `nginx.conf` al montar el entorno Docker | Nginx arranca como proxy de la aplicación | La configuración de referencia incluía `include proxy_params;`, archivo que existe en Nginx de Debian/Ubuntu pero no en la imagen `nginx:1.27-alpine` usada en `docker-compose` → Nginx no habría iniciado | Dependencia de un archivo propio de la distribución | Alta (bloquea el despliegue) | Cabeceras `Host`, `X-Real-IP`, `X-Forwarded-For` y `X-Forwarded-Proto` declaradas explícitamente en `despliegue/nginx/oirs.conf.template` | `curl https://localhost:8443/api/v1/salud` → 200 `{"estado":"ok"}` |
| DEF-02 | 17-11-2026 | PS-19 (primera ejecución en Docker: 80/81 aprobadas) | `DELETE` como `oirs_app` rechazado por falta de privilegio | `OperationalError: connection to 127.0.0.1:5432 refused` (la prueba no llegó a evaluar el privilegio) | La prueba tenía el host y la contraseña de `oirs_app` escritos en el código (válidos solo en el equipo de la PoC) | Media (prueba no portable; además, secreto en el código: contradice SC-05) | Host desde la configuración de Django y contraseña desde la variable `PG_APP_PASSWORD` | Batería completa en Docker: 81/81 aprobadas |
