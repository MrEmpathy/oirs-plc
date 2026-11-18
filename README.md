# Sistema de Gestión OIRS — DSM Padre Las Casas

Proyecto Integrado (Ingeniería en Informática, IEI-N4-C3). Implementación (Unidad 3) del sistema diseñado en el
Informe N.º 2: gestión de reclamos, sugerencias, consultas, solicitudes y felicitaciones con folio, plazo legal de
15 días hábiles (Ley N.º 20.584), trazabilidad inmutable y encuesta de satisfacción anónima, integrado al sitio
WordPress del Departamento de Salud Municipal mediante un plugin.

```
Ciudadano ──► WordPress + plugin DSM OIRS ──HTTPS + HMAC──► Nginx ──► Django (gunicorn) ──► PostgreSQL 16
                                                               ▲                       └──► MongoDB 7 (encuestas, bitácora)
Funcionarios ──────────────── HTTPS (sesión + 2FA) ────────────┘                       └──► Redis 7 (caché)
```

## Puesta en marcha rápida

Requisitos: Linux (x86-64 con AVX o arm64 ARMv8.2, p. ej. Raspberry Pi 5), `openssl`, `curl`, 4 GB de RAM y 6 GB
de disco libres. Docker 24+ con Compose v2: si falta, `./scripts/instalar.sh --instalar-docker` lo instala.

```bash
./scripts/instalar.sh                  # todo en un paso: requisitos, .env, certificados, servicios, WordPress
./scripts/instalar.sh --red            # además, acceso desde otros equipos (nombre .local e IP del servidor)
./scripts/instalar.sh --sin-encuesta   # sin la encuesta de demostración servida por Nginx
```

Paso a paso (lo mismo que hace el instalador):

```bash
./scripts/preparar_entorno.sh          # .env con secretos aleatorios + certificados TLS de desarrollo
docker compose up -d --build           # PostgreSQL, MongoDB, Redis, app, Nginx, encuesta, WordPress, MariaDB
./scripts/instalar_wordpress.sh        # WordPress de demostración con el plugin y sus páginas
```

| Dirección | Qué es | Quién la usa |
|---|---|---|
| https://localhost:8443 | Sistema de Gestión OIRS (Nginx → Django) | Funcionarios |
| http://localhost:8080 | Sitio WordPress de demostración con el plugin | Ciudadanos |
| http://localhost:8082 | Encuesta de satisfacción servida por Nginx, sin WordPress (solo demostración; opcional) | Ciudadanos |

Usuarios de demostración: `admin@dsm.test`, `oirs.dsm@dsm.test`, `oirs.plc@dsm.test`, `oirs.pul@dsm.test`,
`dir.plc@dsm.test`. Contraseña inicial: valor `CLAVE_DEMO` del `.env` (se pide cambiarla en el primer ingreso).

El detalle está en el [manual de instalación](docs/es3/01_instalacion.md) y en el [manual de usuario](docs/es3/02_manual_usuario.md).

## Pruebas

```bash
docker compose --profile herramientas run --rm pruebas pytest -q --cov=apps     # 132 pruebas (unitarias, integración, seguridad, front)
.venv/bin/pytest -c tests/e2e/pytest.ini tests/e2e                                # 9 recorridos E2E con Playwright
```

Resultados, cobertura y trazabilidad: [plan y ejecución de pruebas](docs/es3/03_pruebas.md) ·
[registro de defectos](docs/es3/registro_defectos.md) · evidencias en `evidencias/es3/`.

## Estructura

```
apps/
  core/            acceso documental, manejo centralizado de errores, JSON seguro
  cuentas/         usuario, autenticación (Argon2id, bloqueo, TOTP), RBAC, administración de cuentas
  catalogos/       establecimientos, unidades, categorías, feriados (+ administración)
  requerimientos/  modelos, servicios, plazos, selectores, API, procesos de retención y consistencia
  encuestas/       metadatos (PostgreSQL) + respuestas anónimas (MongoDB)
  reportes/        indicadores que integran ambas bases y exportación CSV segura
  auditoria/       bitácora de eventos de seguridad (MongoDB, índice TTL)
  integracion/     API pública para WordPress (HMAC), validación de formularios
  web/             front administrativo: vistas, formularios y plantillas (Bootstrap 5.3)
config/            settings (secretos desde variables de entorno), urls
static/            CSS/JS propios y librerías servidas localmente (CSP sin CDN)
tests/             unit/ integration/ security/ web/ e2e/ performance/
wordpress-plugin/  dsm-oirs-formularios (PHP)
wordpress-theme/   dsm-demo: esqueleto del sitio para la demostración
despliegue/        nginx, inicialización de PostgreSQL/MongoDB, entrypoint
scripts/           preparar_entorno, instalar_wordpress, respaldo, restaurar
docs/es3/          manuales, pruebas, alcance y defectos (Informe N.º 3)
evidencias/        es3/: ejecución de la implementación · raíz: PoC del Informe N.º 2
```

`evidencias/` (raíz) y `prototipo*.html` corresponden a la prueba de concepto del Informe N.º 2 y se conservan sin cambios.
