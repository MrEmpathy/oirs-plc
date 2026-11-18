# Alcance de la implementación y cambios respecto del diseño

Base: Informe N.º 2 (diseño y PoC, 18-10-2026). Versión evaluada: rama `es3/implementacion`, 17-11-2026.

## 1. Funcionalidades

| HU / requisito | Funcionalidad | Estado | Dónde |
|---|---|---|---|
| HU01 · RF01, RF03, RF08, RF11 | Ingreso web con folio y plazo legal | **Terminada** | Plugin `[oirs_formulario]`, `apps/integracion`, `apps/requerimientos/servicios.py` |
| HU01 · CU03 | Ingreso presencial con comprobante | **Terminada** | `/casos/nuevo` |
| HU02 · RF02, RNF03 | Encuesta anónima (QR con establecimiento preseleccionado) | **Terminada** | Plugin `[oirs_encuesta]`, `apps/encuestas` |
| HU03 · RF04, RF05 | Clasificar y derivar | **Terminada** | Detalle del caso |
| HU04 · RF06, RF07 | Responder y cerrar, con historial inmutable | **Terminada** | Detalle del caso; trigger en PostgreSQL |
| HU05 · RF08 | Panel de plazos de la red | **Terminada** | `/plazos` |
| HU06 · RNF02 | Vista de solo lectura para la Dirección | **Terminada** | Matriz de permisos |
| HU07 · RF10, RNF01 | Usuarios y perfiles, MFA, bloqueo, contraseña temporal y recuperación | **Terminada** | `/usuarios`, `/ingresar` |
| HU08 · RF09 | Reportes con gráficos y exportación CSV | **Terminada** | `/reportes` |
| RF12 · RNF10 | Contenidos administrables por Comunicaciones | **Terminada en la demostración** | Rol Editor de WordPress |
| Sección 4.5 | Respaldos cifrados y prueba de restauración | **Terminada** | `scripts/respaldo.sh`, `restaurar.sh` |
| Sección 6.1 / 6.5 | Anonimización por retención y verificación de referencias entre bases | **Terminada** (plazos provisorios) | Comandos `anonimizar_solicitantes`, `verificar_referencias` |
| DoD | Integración continua | **Parcial**: el flujo está definido, pero no se ha ejecutado en GitHub porque la rama aún no se publica | `.github/workflows/ci.yml` |
| Sección 4.5 | Publicación en el servidor municipal / VPS con Let's Encrypt | **Pendiente** (T23) | — |
| T21, T22, T25 | SUS, OWASP ZAP, carga en staging, aceptación | **Pendiente** | Ver [pruebas](03_pruebas.md), sección 1.2 |
| — | Tótem de autoservicio (Could) e integración con Rayen (Won't) | **Excluida**, como en el diseño | — |

Perfiles cubiertos: los 4 del sistema administrativo (Administrador, OIRS DSM, OIRS de establecimiento y Dirección), más el usuario de la red (sin cuenta) y la Unidad de
Comunicaciones (WordPress).

## 2. Restricciones de esta etapa

- **Sin acceso al WordPress municipal.** Se usa un WordPress 6.9 de demostración en Docker con un tema esqueleto
  (`wordpress-theme/dsm-demo`) que solo representa la estructura del sitio real: cabecera, menú, tres accesos y
  pie. No reproduce sus contenidos ni su marca: usa un ícono genérico y un aviso de «sitio de demostración».
  El plugin es el mismo que se instalaría en el sitio real (en el sitio del DSM: subir el plugin y agregar dos
  constantes en `wp-config.php`).
- **Encuesta sin WordPress, solo para demostración** (servicio `encuesta`, puerto 8082): página estática en
  Nginx que firma las llamadas con njs. No reemplaza al plugin: permite mostrar la encuesta sin levantar el
  sitio de demostración. La validación en el navegador requiere JavaScript; el plugin funciona sin él.
- **Datos ficticios** en todo el entorno, incluidos los usuarios `@dsm.test`, solicitantes de ejemplo y
  establecimientos (con una posta marcada como «dato de prueba»).
- Los correos de recuperación se escriben en el log; no hay servidor SMTP institucional.

## 3. Cambios respecto del diseño (Informe N.º 2) y su justificación

| # | Cambio | Justificación |
|---|---|---|
| C1 | **Paleta del sitio institucional** (azul `#046bd2` y grises del tema Astra de salud.padrelascasas.cl) en el plugin y en el sistema administrativo, en lugar del verde azulado del prototipo v2 | Continuidad visual entre el canal público y el sistema. Se conservan Atkinson Hyperlegible (RNF05), el semáforo, el tema oscuro y contrastes ≥ 4,5:1 |
| C2 | Front con **plantillas Django y formularios del servidor** (no una SPA sobre la API JSON) | Como estaba previsto en la Tabla 10: menor superficie de ataque y CSRF nativo. La API JSON se mantiene para WordPress y las pruebas |
| C3 | Nuevo endpoint firmado `GET /api/v1/publico/encuestas/<codigo>`: el plugin lee las preguntas de la API | Cambiar la encuesta no exige modificar WordPress (objetivo de la sección 6.4) |
| C4 | Inicio de sesión **en dos pasos** (contraseña → código), y un código TOTP erróneo **cuenta para el bloqueo** | En la PoC, el TOTP se enviaba junto con la contraseña y sus errores no se contaban: permitía probar códigos sin límite |
| C5 | Enrolamiento del segundo factor con QR generado en el servidor (`segno`) | El diseño exigía MFA, pero no definía cómo registrarlo. Sin servicios externos (CSP) |
| C6 | **MongoDB 7 real** en lugar de FerretDB | Pendiente (4) de las conclusiones del Informe N.º 2. Permite el índice TTL de la bitácora |
| C7 | `docker-compose.yml` en la raíz, ejecutable de punta a punta, con redes internas `datos` y `wp` | El compose de referencia de la PoC no tenía Dockerfile ni script de respaldo y no habría iniciado (DEF-01) |
| C8 | Respaldo como script del anfitrión (cron) en lugar de un contenedor `respaldo` | El contenedor de referencia necesitaba `pg_dump` y `mongodump` en una sola imagen. El script usa las herramientas de cada contenedor y se probó una restauración real |
| C9 | Caché del resumen de satisfacción con invalidación por generación | DEF-06: la caché de INC-04 ocultaba respuestas nuevas |
| C10 | Django 5.2.19 (antes 5.2.18), gunicorn 27, redis 8.1 | Parches de seguridad vigentes (pip-audit 0) y dependencia faltante (DEF-05) |
| C11 | Canal alternativo de demostración para la encuesta: Nginx + njs, sin WordPress | Presentar la encuesta sin el sitio WordPress. Reutiliza `oirs.css`, el endpoint de definición (C3) y el mismo esquema HMAC, por lo que no exige cambios en la API |
| C12 | Instalador de un solo comando (`scripts/instalar.sh`) con la encuesta en Nginx como servicio opcional (perfil de Compose) | Facilita instalar el sistema en otro equipo Linux y revisa antes los requisitos que hacían fallar la instalación a mitad de camino: procesador compatible con MongoDB 7, puertos y disco |

## 4. Trabajo colaborativo y control de versiones

Rama `es3/implementacion` con commits por etapa (entorno → WordPress → front → operación → pruebas →
documentación). Cada mensaje describe el cambio y los defectos que corrige.

| Integrante | Responsabilidad en el diseño (Tabla 3) | Producto en esta etapa | Evidencia |
|---|---|---|---|
| Nicolás Beltrán | Back-end, datos, seguridad e infraestructura | Entorno Docker, servicios, front administrativo, pruebas y documentación | Commits de la rama `es3/implementacion` |
| Martín Brellenthin | Plugin y tema WordPress, front, usabilidad, aceptación | **Por completar por el equipo**, por ejemplo: revisión del PR del plugin y del front, prueba SUS (T21), manual de Comunicaciones | Revisión y aprobación en el PR, issues del tablero |

> Nota para el equipo: la guía ES3 (indicador 3.1.3.6) pide relacionar un producto verificable de cada integrante
> con el repositorio. Hasta ahora todo el historial está a nombre de un integrante. Antes de la entrega conviene
> abrir el pull request de `es3/implementacion` y que Martín registre su revisión y sus cambios (por ejemplo, en el
> plugin o en los textos), y documentar ahí cómo se coordinaron.
