# Manual de instalación y puesta en marcha

Versión: rama `es3/implementacion` · Fecha de verificación: 17-11-2026.

## 1. Entorno y dependencias

| Elemento | Versión probada | Notas |
|---|---|---|
| Sistema operativo del anfitrión | Raspberry Pi OS (Debian 12, Linux 6.12, arm64) | También funciona en x86-64 (todas las imágenes son multiarquitectura) |
| Docker Engine / Compose | 29.9 / v5.6 | Mínimo: Docker 24 y Compose v2 |
| `openssl` | 3.0 | Genera secretos y certificados |
| Python (dentro de la imagen) | 3.13 (python:3.13-slim) | Django 5.2.19 LTS, gunicorn 27, psycopg 3.3, pymongo 4.19, redis 8.1 |
| PostgreSQL | 16 (postgres:16-alpine) | Base estructurada |
| MongoDB | 7 (mongo:7) | Base documental (en la PoC se usó FerretDB; ahora MongoDB real) |
| Redis | 7 (redis:7-alpine) | Caché de indicadores |
| Nginx | 1.27 (nginx:1.27-alpine) | TLS 1.2/1.3, HSTS, límite de tasa del inicio de sesión |
| WordPress / PHP / MariaDB | 6.9 / 8.3 / 11.4 | Sitio de demostración (reemplaza al WordPress municipal) |
| Recursos | 4 GB de RAM, 6 GB de disco | Medido el 17-11-2026: ~1,2 GB de RAM con los 7 servicios en marcha (suma de memoria residente de sus procesos; WordPress ocupa 511 MB) |

Dependencias Python fijadas en `requirements.txt` (ejecución) y `requirements-dev.txt` (pruebas y análisis).

### Variables de configuración

Se definen en `.env`, que **no se versiona**. `scripts/preparar_entorno.sh` lo crea con valores aleatorios;
`.env.example` documenta cada variable sin valores reales.

| Variable | Uso |
|---|---|
| `DJANGO_SECRET_KEY` | Firma de sesiones y tokens (obligatoria; la aplicación no arranca sin ella) |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | Nombres y orígenes aceptados |
| `PG_SUPERUSER_PASSWORD`, `PG_OWNER_PASSWORD`, `PG_PASSWORD` | Roles `postgres`, `oirs_owner` (migraciones) y `oirs_app` (aplicación) |
| `MONGO_ROOT_PASSWORD`, `MONGO_APP_PASSWORD`, `MONGO_URI` | Administrador y usuario de la aplicación en MongoDB |
| `REDIS_URL` | Caché |
| `WP_HMAC_SECRET` | Secreto compartido WordPress ↔ API (firma HMAC-SHA256) |
| `WP_DB_PASSWORD`, `WP_ADMIN_CLAVE` | Base de datos y administrador del WordPress de demostración |
| `CLAVE_DEMO` | Contraseña inicial de los usuarios de demostración |
| `RESPALDO_CLAVE` | Clave de cifrado de los respaldos (se crea en el primer respaldo) |
| `OIRS_HTTPS_PUERTO_PUBLICO`, `OIRS_HTTP_PUERTO_PUBLICO`, `WP_PUERTO_PUBLICO` | Puertos publicados (8443, 8081, 8080) |
| `RETENCION_DATOS_PERSONALES_DIAS`, `RETENCION_BITACORA_DIAS` | Plazos de retención (por defecto 5 y 2 años; pendientes de confirmar con el DSM) |

## 2. Procedimiento reproducible

```bash
git clone https://github.com/MrEmpathy/oirs-plc.git && cd oirs-plc
git checkout es3/implementacion
./scripts/preparar_entorno.sh
docker compose up -d --build
./scripts/instalar_wordpress.sh
```

Qué hace cada paso:

1. **`preparar_entorno.sh`**: crea `.env` (permisos 600) con secretos aleatorios y una CA local de desarrollo con
   el certificado del servidor (`despliegue/certs/`). Para usar otros puertos:
   `OIRS_HTTPS_PUERTO_PUBLICO=9443 WP_PUERTO_PUBLICO=9080 ./scripts/preparar_entorno.sh`.
2. **`docker compose up -d --build`**: construye la imagen de la aplicación y levanta los servicios en orden.
   - Al crear los volúmenes, `despliegue/postgres/01-roles.sh` crea los roles `oirs_owner` y `oirs_app` y la base
     `oirs_plc`; `despliegue/mongo/01-usuario.js` crea el usuario de la aplicación en MongoDB.
   - El servicio `migrar` aplica las migraciones con `oirs_owner` (tablas, restricciones, índices, trigger de
     historial inmutable y privilegios mínimos de `oirs_app`) y carga los datos iniciales (`sembrar_datos`):
     6 establecimientos, 35 unidades, 8 categorías, feriados 2025–2027, 5 usuarios y la encuesta.
   - Después arrancan `app` (gunicorn 3×4) y `nginx`.
3. **`instalar_wordpress.sh`**: con WP-CLI instala WordPress, activa el tema `dsm-demo` y el plugin, crea las
   páginas «OIRS en línea» (`[oirs_formulario]`), «Encuesta de satisfacción» (`[oirs_encuesta]`) y
   «Establecimientos», el menú, tres noticias y el usuario Editor `comunicaciones`.

Tiempo medido en una copia limpia con las imágenes ya descargadas: 32 s para `docker compose up -d --build`,
más la instalación de WordPress (menos de un minuto). La primera vez se descargan unos 2,5 GB de imágenes.

**Certificado:** el navegador mostrará una advertencia porque la CA es local. Puede aceptarse o importarse
`despliegue/certs/ca.crt` como autoridad de confianza en el navegador.

## 3. Verificación de funcionamiento

```bash
docker compose ps                                                   # todos los servicios «Up» / «healthy»
curl --cacert despliegue/certs/ca.crt https://localhost:8443/api/v1/salud
# {"estado": "ok", "postgresql": "ok", "documental": "ok"}
```

Operación básica de punta a punta (la misma que ejecuta automáticamente la prueba E2E-01):

1. Abrir http://localhost:8080 → «OIRS en línea» → elegir «Reclamo», el CESFAM Padre Las Casas, escribir
   «Prueba DEMO-01», nombre y correo, aceptar el tratamiento de datos y enviar. Se muestra un folio
   `PLC-AAAA-NNNNNN` y la fecha límite.
2. Comprobar que se guardó:
   `docker compose exec postgres psql -U postgres -d oirs_plc -c "select folio, canal, estado from requerimiento order by id desc limit 1;"`
3. Ingresar en https://localhost:8443 como `oirs.plc@dsm.test` (contraseña `CLAVE_DEMO`), definir una contraseña
   propia y buscar el folio en la bandeja.

En WordPress: `Ajustes → DSM OIRS → Probar conexión` verifica TLS, firma y catálogos en un solo paso.

### Verificación realizada desde una copia limpia (17-11-2026)

Clonado del repositorio en un directorio vacío, con puertos 9443/9081/9080 para convivir con otra instalación:
`preparar_entorno.sh` → `docker compose up -d --build` → `instalar_wordpress.sh`. Resultado: `/api/v1/salud` en
`ok`, formulario con 5 establecimientos, envío real con folio `PLC-2026-000001` guardado en PostgreSQL e ingreso
de `oirs.plc@dsm.test` redirigido al cambio obligatorio de contraseña. Esta verificación detectó DEF-10 (puerto
fijo en `CSRF_TRUSTED_ORIGINS`), corregido antes de repetirla.

## 4. Operación

| Tarea | Comando | Frecuencia sugerida |
|---|---|---|
| Respaldo cifrado (PostgreSQL + MongoDB) | `./scripts/respaldo.sh` | Diaria, 02:00 (cron: `0 2 * * * cd /ruta && ./scripts/respaldo.sh`) |
| Verificar un respaldo | `./scripts/restaurar.sh respaldos/AAAAMMDD-HHMMSS` | Mensual |
| Restaurar | `./scripts/restaurar.sh respaldos/AAAAMMDD-HHMMSS --confirmar` | Ante incidentes |
| Anonimizar datos personales vencidos | `docker compose exec app python manage.py anonimizar_solicitantes` (`--simular` para revisar) | Diaria |
| Consistencia entre bases | `docker compose exec app python manage.py verificar_referencias` | Diaria (nocturna) |
| Registro de la aplicación | `docker compose logs -f app` | Ante incidentes |

Los respaldos quedan en `respaldos/` (retención local de 30 días). La regla 3-2-1 exige además copiarlos fuera del
servidor; sin `RESPALDO_CLAVE` no pueden descifrarse, por lo que esa clave debe guardarse también aparte.

## 5. Problemas conocidos

| Síntoma | Causa | Solución |
|---|---|---|
| Advertencia de certificado en el navegador | CA local de desarrollo | Aceptar o importar `despliegue/certs/ca.crt`; en producción usar Let's Encrypt |
| El formulario de WordPress dice «no está disponible» | La API no responde o el certificado no es legible | `Ajustes → DSM OIRS → Probar conexión`; revisar `docker compose ps` |
| «No fue posible procesar su solicitud» tras muchos envíos | Límite anti-spam: 10 envíos por hora por IP | Esperar una hora o, en pruebas, `docker compose --profile herramientas run --rm wpcli wp transient delete --all` |
| HTTP 429 al iniciar sesión | Límite de Nginx: 5 intentos por minuto por IP | Esperar un minuto |
| El correo de recuperación no llega | En desarrollo los correos se escriben en el log | `docker compose logs app` y buscar «Recuperación de contraseña» |
| Puertos 8080/8081/8443 ocupados | Otro servicio en el equipo | Cambiar los puertos al ejecutar `preparar_entorno.sh` (ver paso 1) |

## 6. Ubicación del código, datos y configuración

- Código: `apps/` (Django), `wordpress-plugin/`, `wordpress-theme/`; configuración en `config/settings.py`
  (lee todo secreto desde variables de entorno) y `despliegue/`.
- Datos: volúmenes Docker `pgdata` (PostgreSQL), `mongodata` (MongoDB), `wpdb` y `wpdata` (WordPress).
- Secretos: solo en `.env` y `despliegue/certs/`, ambos excluidos de Git (`.gitignore`) y de la imagen Docker (`.dockerignore`).
