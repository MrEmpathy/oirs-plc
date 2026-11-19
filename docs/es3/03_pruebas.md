# Plan, ejecución y validación de pruebas (Unidad 3)

Ejecución final: 18-11-2026 (pytest y E2E, tras DEF-15) · rama `main` · entorno Docker del [manual de instalación](01_instalacion.md)
(PostgreSQL 16, **MongoDB 7**, Redis 7, Nginx 1.27, WordPress 6.9) · ejecutado por: N. Beltrán (equipo local, Raspberry Pi 5).

Evidencias en `evidencias/es3/`: `junit_pytest.xml`, `pytest_ejecucion_final.txt` (con cobertura),
`junit_e2e.xml`, `e2e_ejecucion_final.txt`, `pi12_php.txt`, `bandit.txt`, `pip_audit.txt`,
`django_check_deploy.txt`, `bd_evidencias.txt`, `encuesta_nginx.txt` y `capturas/` (recorridos E2E y capturas
INF-01 a INF-05 del informe).

## 1. Alcance y cobertura

Se retoma el plan del Informe N.º 2 (sección 8): sus 52 casos se conservan con los mismos identificadores y se
agregan los casos de las funciones construidas en esta etapa (front administrativo, administración, procesos de
datos) más los recorridos de extremo a extremo.

| Tipo | Identificadores | Casos | Ejecuciones | Herramienta |
|---|---|---|---|---|
| Unitarias | PU-01..PU-24 | 24 | 69 | pytest |
| Integración | PI-01..PI-30 (PI-12 en PHP) | 30 | 33 | pytest + PHP CLI |
| Seguridad | PS-01..PS-32 | 32 | 35 | pytest |
| Extremo a extremo (navegador) | E2E-01..E2E-10 (E2E-10: 15 comprobaciones, destructiva) | 10 | 10 | Playwright (Chromium) |
| Manual | CP-M01 | 1 | 1 | WP-CLI / revisión |
| **Total** | | **97** | **148** | |

### 1.1 Cobertura de casos de uso (base de cálculo explícita)

Denominador: los 12 casos de uso del Informe N.º 2 (Tabla 9). Los 12 están implementados en esta versión.
Un CU se considera cubierto cuando tiene al menos un escenario normal ejecutado y aprobado; la tabla separa los
escenarios normales (N), alternativos o de error (A) y de borde o seguridad (B).

| CU | Caso de uso | HU | N | A | B |
|---|---|---|---|---|---|
| CU01 | Ingresar requerimiento (web) | HU01 | PI-01, E2E-01 | PU-18, PI-16, E2E-02, PS-16, PS-17 | PI-11 (40 concurrentes), PU-01..08, E2E-08 |
| CU02 | Responder encuesta anónima | HU02 | PI-07, E2E-03, E2E-09 | PI-08, PI-09, PI-10, E2E-09 (validación) | PI-23 (caché) |
| CU03 | Ingresar requerimiento presencial | HU01, HU03 | PI-15 | PI-16 | PS-24 (Dirección sin acceso) |
| CU04 | Clasificar y derivar | HU03 | PI-02, PI-14, E2E-01 | PI-04, PU-23 | PS-25, PS-26 |
| CU05 | Registrar respuesta y cerrar | HU04 | PI-02, PI-14, E2E-01 | PI-03 (fuera de plazo), PU-10 | PS-19, PS-20 |
| CU06 | Supervisar plazos de la red | HU05 | PI-17, E2E-04 | PI-18 (vencidos) | PU-06, PU-07 (umbrales 0, 5, 6) |
| CU07 | Consultar casos del establecimiento | HU06 | PI-13, E2E-05 | PS-09 | PS-08, PS-25 (IDOR → 404) |
| CU08 | Generar reportes e indicadores | HU08 | PI-06, PI-19, E2E-03 | PU-24 (período inválido) | PS-11 |
| CU09 | Exportar reporte | HU08 | E2E-04 | PS-12 (solo OIRS DSM) | PU-13 (fórmulas CSV) |
| CU10 | Administrar usuarios y perfiles | HU07 | PS-29, PI-26 | PI-25 | PU-21, PS-29 (sin establecimiento) |
| CU11 | Iniciar sesión (MFA según perfil) | HU07 | PS-22, PS-23 | PS-02, PS-03, PS-21 | PS-28, PS-30, E2E-07 (429) |
| CU12 | Actualizar contenidos del sitio | — | CP-M01 | CP-M01 (sin permisos de plugins) | — |

**Cobertura: 12 de 12 CU implementados cubiertos = 100 %**, con escenarios normales, alternativos y de borde en
11 de 12. CU12 tiene una verificación manual sin escenario de borde automatizado.

Disponibilidad y recuperación ante la caída de una base: E2E-10 y PI-27..PI-30 (sección 2.2).

Requisitos no funcionales: RNF01–RNF03 y las 15 amenazas de la Tabla 20 del Informe N.º 2 (PS-01..PS-32, bandit,
pip-audit). RNF05/RNF06 de forma automatizada (E2E-06: 390/820/1280 px, tema claro y oscuro, sin desplazamiento
horizontal). RNF07 con PS-19 y PS-20.

**Cobertura de código** (pytest-cov, 17-11-2026): **92 % total** (1789 instrucciones, 147 sin ejecutar). Servicios:
`requerimientos/servicios.py` 94 %, `cuentas/servicios.py` 95 %, `catalogos/servicios.py` 91 %. Cumple la
Definición de Terminado (≥ 80 % en servicios).

### 1.2 Fuera de alcance o no ejecutado (con su riesgo)

| Prueba planificada (Informe N.º 2) | Estado | Motivo | Riesgo y acción |
|---|---|---|---|
| Usabilidad SUS con funcionarios (T21) | **No ejecutada** | Requiere sesiones con funcionarios del DSM | Usabilidad no validada con usuarios reales. Agendar con la contraparte antes del piloto |
| Escaneo dinámico OWASP ZAP (T22) | **No ejecutada** | Requiere un ambiente de staging; en el equipo de desarrollo no había espacio en disco para la imagen de ZAP | Las amenazas están cubiertas por pruebas automatizadas, pero sin escaneo dinámico. Ejecutar en staging |
| Carga PR-01/PR-02 repetida con MongoDB 7 en staging | **No ejecutada** en esta etapa | Mismo motivo (staging); resultados vigentes de la PoC: p95 de 550 ms con 30 usuarios | Riesgo bajo: no se modificaron las consultas críticas. Repetir en staging (T22) |
| Aceptación con el Product Owner (T25) | **No ejecutada** | Depende de la contraparte | Pendiente: acta de aceptación |
| Instalación en el WordPress municipal | **Bloqueada** | Sin acceso al sitio del DSM | Se probó en un WordPress de demostración con la misma versión mayor |

## 2. Protocolo y fichas de ejecución

Todas las pruebas automatizadas siguen el mismo protocolo:
1. Precondición: entorno Docker en marcha y base de pruebas creada desde cero por pytest-django, con catálogos de
   prueba (2 CESFAM, unidades, categorías, feriados 2026–2027) y un usuario por perfil.
2. Ejecución:
   - `docker compose --profile herramientas run --rm pruebas pytest -q --cov=apps --junitxml=…`
   - E2E: `.venv/bin/pytest -c tests/e2e/pytest.ini tests/e2e`
3. Registro: JUnit (resultado y tiempo por ejecución) y salida de consola en `evidencias/es3/`.

El **resultado obtenido** de cada caso es el que verifican sus aserciones en esa ejecución, no una copia del
esperado. Cuando una aserción falla, pytest registra el valor real, y esos valores se conservan en el registro de
defectos.

### 2.1 Fichas detalladas (selección representativa)

| ID | HU / CU | Objetivo | Precondición | Procedimiento y datos | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|---|---|
| E2E-01 | HU01, HU03, HU04 / CU01, CU04, CU05 | Recorrido completo del reclamo, del sitio web al cierre | Entorno Docker; usuario E2E OIRS_EST del CESFAM PLC | En WordPress: Reclamo, CESFAM PLC, descripción con marca `E2E-<hora>`, María Pérez (ficticia), correo autorizado → Enviar. Recargar la confirmación. En el sistema: buscar el folio → derivar a SOME (Tiempos de espera) → responder por correo → cerrar | Folio con formato `PLC-AAAA-NNNNNN` y fecha límite; recargar no duplica; historial INGRESADO → EN_PROCESO → RESPONDIDO → CERRADO | Folio **PLC-2026-000009** con vencimiento 10-12-2026 y título «Reclamo recibido»; el folio se mantiene tras recargar; mensajes «Caso derivado a SOME», «dentro del plazo legal» y «Caso PLC-2026-000009 cerrado»; historial con los 4 estados (capturas E2E-01a..f) | Aprobado |
| E2E-02 | HU01 / CU01 (alternativo) | Validación del formulario ciudadano | Página `/oirs/` | Reclamo sin nombre ni contacto | Resumen de errores, error junto al campo, lo escrito se conserva, ningún caso creado | Resumen visible; «Indique su nombre…» en `#oirs-err-nombre`; `aria-invalid="true"`; la descripción se conserva; sin folio (captura E2E-02) | Aprobado |
| E2E-03 | HU02, HU08 / CU02, CU08 | La encuesta por QR llega al reporte del DSM | Usuario E2E OIRS_DSM con TOTP | `?est=CESFAM-PLC` en móvil (390 px); notas 6, 5, 7, 6, 6; Dental | Establecimiento preseleccionado; agradecimiento; el reporte suma una respuesta | **1.ª ejecución: Fallido** (`assert 1 == 2`: el reporte no cambió, DEF-06). **2.ª ejecución tras la corrección:** preselección correcta, «¡Gracias por su opinión!» y n = n_antes + 1 (capturas E2E-03a/b) | Aprobado (2.ª) |
| E2E-07 | HU07 / CU11 (borde) | Límite de tasa del inicio de sesión en Nginx | Ninguna | 8 POST seguidos a `/api/v1/sesion/iniciar` desde la misma IP | Algún 429 a partir del 6.º intento | Nginx respondió 429 dentro de los primeros 6 intentos | Aprobado |
| E2E-09 | HU02 / CU02 | Encuesta servida por Nginx sin WordPress (firma HMAC en njs) | Servicio `encuesta`; `.env` con `WP_HMAC_SECRET` | `?est=CESFAM-PUL`; enviar vacío; luego notas 6 en las 5 escalas, Dental y comentario; revisar `/`, `/encuesta.js` y `/api/*`; repetir en 390 px | Preselección; resumen de errores y `aria-invalid` en las 5 escalas; 201 y agradecimiento; el secreto no aparece en ninguna respuesta; sin desplazamiento horizontal | Igual al esperado (capturas E2E-09a..d). Casos de rechazo, límite de envíos y documento guardado en `encuesta_nginx.txt` | Aprobado |
| E2E-08 | — / CU01 (amenaza «spam y bots») | Límite de 10 envíos por hora del plugin | Contadores de WordPress limpios | 11 envíos incompletos de sugerencia (no crean casos) | Envíos 1–10: «Revise los campos marcados»; envío 11: rechazo genérico | Igual al esperado (captura E2E-08) | Aprobado |
| PI-12 | HU01 / CU01 | Firma del plugin PHP aceptada por la API Python a través de Nginx/TLS | API en marcha; secreto de `.env` | `php tests/integration/test_firma_php.php` dentro del contenedor de WordPress | 201 con la firma correcta; 401 con un secreto incorrecto | `HTTP 201 {"folio": "PLC-2026-000005", …}` / `HTTP 401 {"error": "Firma inválida"}` (`pi12_php.txt`) | Aprobado |
| PI-14 | HU03, HU04 / CU04, CU05 | Ciclo completo desde los formularios del front | Sesión OIRS_EST PLC | POST derivar → responder (EMAIL, hoy) → cerrar | Estado CERRADO, 4 estados en el historial y eventos en la bitácora | **1.ª ejecución: Fallido** (5 eventos en lugar de 4: defecto de la prueba, DEF-07). **2.ª:** estados y acciones de bitácora correctos | Aprobado (2.ª) |
| PS-22 | HU07 / CU11 | Segundo factor obligatorio en el front | Usuario OIRS_DSM con secreto TOTP | Contraseña correcta → código 000000 → código válido | Sin sesión hasta el código; el código erróneo cuenta como intento; se registra MFA_FALLIDO | Redirección a `/ingresar/verificar`; `/plazos` → 302 antes del código; `intentos_fallidos = 1`; 1 evento MFA_FALLIDO; con el código válido `/plazos` → 200 | Aprobado |
| PS-26 | HU06 / CU07 | La Dirección no puede derivar aunque envíe el formulario a mano | Sesión de Dirección PLC | POST directo a `/casos/<folio>/derivar` | 403 y el caso sigue INGRESADO (el botón tampoco se muestra) | Botón ausente; HTTP 403; estado INGRESADO | Aprobado |
| PS-31 | RNF01 | CSP y ausencia de JavaScript en línea | Sesión OIRS_EST | GET `/bandeja` y revisión de las 26 plantillas HTML | `script-src 'self'`; ningún `<script>` sin `src` ni `onclick=` | Cabeceras CSP y X-Frame-Options presentes; 0 coincidencias | Aprobado |
| PI-20 | — / retención (sección 6.1) | Anonimización por plazo de retención | 3 casos: cerrado antiguo, cerrado reciente, abierto antiguo | `anonimizar_solicitantes --dias 1825` | Solo se anonimiza el cerrado antiguo; el caso conserva su tipo y su establecimiento | Igual al esperado | Aprobado |
| CP-M01 | — / CU12 | El Editor de Comunicaciones administra contenidos, pero no plugins | WordPress instalado | `wp user list-caps comunicaciones`; crear una página como `comunicaciones` | Tiene `edit_pages`/`publish_pages`; no tiene `activate_plugins`/`install_plugins`/`manage_options` | 3 de 3 permisos de contenido; 0 de 3 de administración; página creada (id 14) y eliminada | Aprobado |

### 2.2 Caída de las bases de datos durante una sesión (E2E-10)

Pregunta de la evaluación: ¿qué pasa si la base de datos cae en mitad de una sesión? `tests/e2e/caida_bases.py`
deja una sesión abierta del encargado OIRS, un ingreso presencial a medio enviar y un ciudadano con el formulario
listo; detiene uno a uno PostgreSQL, MongoDB, Redis y MariaDB (`docker compose stop`), registra lo que ve cada
usuario, vuelve a levantarlos y comprueba la sesión, la integridad y la recuperación. Es destructiva (interrumpe
el servicio unos segundos), por eso no forma parte de la batería automática:
`.venv/bin/python tests/e2e/caida_bases.py <etapa>`. Las correcciones quedaron además cubiertas por pruebas
automatizadas que simulan cada caída (PI-27 a PI-30, `tests/integration/test_resiliencia.py`).

**Resultado: antes de corregir, 6 de 15 comprobaciones cumplían; después, 15 de 15** (evidencias
`caida_bases_antes.txt` y `caida_bases_despues.txt`, capturas `E2E-10a..c`). Lo que se mantuvo correcto desde el
inicio: ningún caso quedó a medias (transacciones), la sesión sobrevivió a la caída, no hubo referencias huérfanas
entre bases y el sistema de funcionarios siguió operando sin WordPress. Defectos encontrados: DEF-16 a DEF-19.

| ID | Escenario | Esperado | Antes de corregir | Después de corregir |
|---|---|---|---|---|
| E2E-10.1 | PostgreSQL caído: el funcionario navega a la bandeja | Página «Servicio no disponible» (503) sin detalles técnicos | HTTP 500 · «Internal Server Error» · error sin formato (**NO**) | HTTP 503 · «Servicio no disponible · DSM Padre Las Casas» (**Sí**) |
| E2E-10.2 | PostgreSQL caído: el funcionario envía un ingreso presencial | «Servicio no disponible» (503) en menos de 5 s; el caso no se crea a medias | HTTP 500 en 0.1 s · «Internal Server Error» · error sin formato (**NO**) | HTTP 503 en 0.2 s · «Servicio no disponible · DSM Padre Las Casas» (**Sí**) |
| E2E-10.3 | PostgreSQL caído: el ciudadano envía el formulario OIRS | Aviso de servicio no disponible y el texto escrito se conserva | «No fue posible registrar su solicitud. Revise los campos marcados.» · texto conservado: sí (**NO**) | «El servicio no está disponible en este momento. Sus datos se conservan: intente enviarlos de nuevo en unos minutos.» · texto conservado: sí (**Sí**) |
| E2E-10.4 | PostgreSQL de vuelta: 12 peticiones seguidas con la misma sesión | Todas 200, sin volver a iniciar sesión | 11/12 con 200; la sesión siguió activa (**NO**) | 12/12 con 200; la sesión siguió activa (**Sí**) |
| E2E-10.5 | Integridad tras la caída | Ningún caso nuevo ni caso sin historial | casos antes 14, después 14; casos sin historial: 0 (**Sí**) | casos antes 13, después 13; casos sin historial: 0 (**Sí**) |
| E2E-10.6 | Reintento del ciudadano con la base de vuelta | Folio asignado, una sola vez | folio PLC-2026-000015 (**Sí**) | folio PLC-2026-000014 (**Sí**) |
| E2E-10.7 | MongoDB caído: la Dirección inicia sesión | Ingresa sin demora perceptible (< 2 s) | ingresó en 3.7 s (**NO**) | ingresó en 1.1 s (**Sí**) |
| E2E-10.8 | MongoDB caído: el encargado sigue trabajando con los casos | Bandeja disponible (200) sin demora | HTTP 200 en 0.1 s (**Sí**) | HTTP 200 en 0.1 s (**Sí**) |
| E2E-10.9 | MongoDB caído: el ciudadano envía la encuesta | Aviso de servicio no disponible | error: No fue posible registrar su solicitud. Revise los campos marcados. (**NO**) | error: El servicio no está disponible en este momento. Sus datos se conservan: intente enviarlos de nuevo en unos minutos. (**Sí**) |
| E2E-10.10 | Bitácora durante la caída de MongoDB | Los eventos quedan completos en el registro de la aplicación (no se pierden) | 0 evento(s) completos en el registro (**NO**) | 2 evento(s) completos en el registro (**Sí**) |
| E2E-10.11 | Redis caído: el encargado abre los reportes | Reportes disponibles (200), calculados sin caché | HTTP 500 · «Error interno · DSM Padre Las Casas» (**NO**) | HTTP 200 · «Reportes e indicadores · DSM Padre Las Casas» (**Sí**) |
| E2E-10.12 | Redis caído: el ciudadano envía la encuesta | Confirmación y exactamente una respuesta guardada | error: No fue posible registrar su solicitud. Revise los campos marcados.; respuestas guardadas: 1 (**NO**) | confirmación «¡Gracias por su opinión!»; respuestas guardadas: 1 (**Sí**) |
| E2E-10.13 | MariaDB caído: sitio público y sistema | El sitio WordPress cae; el sistema de funcionarios sigue disponible | sitio HTTP 500; sistema HTTP 200 (**Sí**) | sitio HTTP 500; sistema HTTP 200 (**Sí**) |
| E2E-10.14 | MariaDB de vuelta | El sitio vuelve sin intervención | HTTP 200 (**Sí**) | HTTP 200 (**Sí**) |
| E2E-10.15 | Consistencia entre bases al final | Sin referencias huérfanas | sin referencias huérfanas (**Sí**) | sin referencias huérfanas (**Sí**) |

La primera ejecución de la línea base (`caida_bases_antes_1.txt`) tuvo además defectos **de la prueba**: la encuesta
se abría con MongoDB ya detenido y Chromium abortaba peticiones al cambiar las interfaces de red de Docker
(`ERR_NETWORK_CHANGED`), lo que hizo fallar 10.6 sin que fuera un problema del sistema. Se corrigió la prueba (la
página se abre antes de la caída, pausas tras detener o levantar y reintento de navegación) y la línea base se repitió
sobre el código original sin las correcciones: 10.6 cumple también allí, y las demás fallas se confirmaron.

### 2.3 Registro completo

El listado de las 132 ejecuciones automatizadas (ID, módulo, función, tiempo y estado) está en
`evidencias/es3/junit_pytest.xml`; el de las 9 E2E, en `junit_e2e.xml`. Resumen por caso:

| ID | Escenario | Ejec. | Estado |
|---|---|---|---|
| PU-01..PU-08 | Plazos en días hábiles y semáforo (incluye umbrales 0/5/6 y 28 fechas) | 15 | Aprobado |
| PU-09..PU-16 | Máquina de estados, contraseñas, CSV, HMAC, IP /24, bitácora sin datos personales | 23 | Aprobado |
| PU-17..PU-20 | Validación del formulario público con listas blancas | 9 | Aprobado |
| PU-21..PU-24 | Contraseña temporal (20 muestras), filtros, unidades por establecimiento, período de reportes | 25 | Aprobado |
| PI-01..PI-11 | Flujo API, encuestas, concurrencia (40 ingresos) | 14 | Aprobado |
| PI-12 | Firma PHP → API real | 1 | Aprobado |
| PI-13..PI-19 | Front: bandeja, ciclo completo, presencial, panel, filtros, reportes | 7 | Aprobado |
| PI-20..PI-23 | Anonimización, referencias huérfanas, TTL de la bitácora, caché de encuestas | 4 | Aprobado |
| PI-24..PI-26 | Administración de catálogos y cuentas | 3 | Aprobado |
| PS-01..PS-20 | Autenticación, autorización, inyección, XSS, CSRF, canal HMAC, mínimo privilegio | 23 | Aprobado |
| PS-21..PS-32 | Front: contraseña temporal, MFA, enrolamiento, matriz, IDOR, CSRF, redirección abierta, administración, recuperación, CSP, errores | 12 | Aprobado |
| E2E-01..E2E-09 | Recorridos en el navegador (E2E-09: encuesta sin WordPress) | 9 | Aprobado |
| CP-M01 | Rol Editor en WordPress | 1 | Aprobado |

## 3. Validación de resultados

| | Aprobado | Fallido | Bloqueado | No ejecutado |
|---|---|---|---|---|
| Ejecución final (18-11-2026) | 97 casos / 148 ejecuciones | 0 | 1 (instalación en el WordPress municipal) | 4 (SUS, ZAP, carga en staging, aceptación) |

Ejecuciones fallidas **durante** la etapa (conservadas, sin borrar): primera corrida en Docker 80/81 (DEF-02);
E2E-03 (DEF-06); PI-14 y PI-24 (DEF-07); E2E-01..03 por el límite anti-spam (DEF-08). Todas se repitieron tras la
corrección o el ajuste y quedaron aprobadas. Detalle en el [registro de defectos](registro_defectos.md).

**Conclusión:** el comportamiento funcional y de seguridad de los 12 casos de uso está validado en el entorno de
demostración, de forma automatizada y repetible. **No** está validada todavía la usabilidad con funcionarios reales
(SUS), la resistencia ante un escaneo dinámico (ZAP), el rendimiento en el servidor definitivo ni la aceptación del
DSM. Los análisis estático y de dependencias quedaron sin hallazgos: bandit 0 (3.072 líneas analizadas) y pip-audit 0.

## 4. Comparación, defectos y recomendaciones

### 4.1 Resultados esperados frente a obtenidos

| CP | Esperado | Obtenido (1.ª ejecución) | Discrepancia | Causa (comprobada) | Estado final |
|---|---|---|---|---|---|
| PS-19 | `DELETE` como `oirs_app` rechazado por falta de privilegio | Error de conexión a 127.0.0.1 | La prueba no llegó a evaluar el privilegio | Host y contraseña fijos en la prueba (DEF-02) | Aprobado |
| Prueba manual del formulario | Lista de establecimientos | Aviso «no disponible» | Canal ciudadano inutilizable | CA ilegible para `www-data` (DEF-03) | Aprobado |
| Exploración `/reportes` | Página de indicadores | HTTP 500 sin traza | Reportes caídos y sin diagnóstico | Faltaba el log de `django.request` y el paquete `redis` (DEF-04, DEF-05) | Aprobado |
| E2E-03 | n + 1 respuestas | n (sin cambio) | Indicador desactualizado hasta 5 min | Caché sin invalidación (DEF-06) | Aprobado |
| Revisión de la imagen | Imagen sin secretos | `.env`, `.git` y respaldos incluidos | Exposición de secretos | Faltaba `.dockerignore` (DEF-09) | Corregido y verificado |
| Instalación limpia en el puerto 9443 | Inicio de sesión funcional | (detectado antes de ejecutar) 403 CSRF previsible | Instalación no portable | Puerto fijo en el script (DEF-10) | Aprobado |

### 4.2 Recomendaciones derivadas de los resultados

| Hallazgo | Acción recomendada | Responsable / componente | Cómo verificar | Estado |
|---|---|---|---|---|
| DEF-05: una dependencia declarada en la arquitectura no estaba instalada y las pruebas no lo detectaron (usaban caché en memoria) | Ejecutar la batería también contra el entorno con Redis (no solo en memoria) | CI (`.github/workflows/ci.yml`): agregar el servicio Redis | El job de CI con `REDIS_URL` definido pasa | Pendiente |
| DEF-09: secretos dentro de la imagen | Revisar el contenido de la imagen en cada versión | DoD / revisión de PR | `docker run … ls -a /app` sin `.env` | Aplicado (`.dockerignore`); revisión periódica pendiente |
| DEF-06: la caché ocultaba datos nuevos | Toda caché nueva debe definir cómo se invalida | Estándar de código (agregar a SC-09/SC-10) | Prueba análoga a PI-23 por cada caché | Aplicado en encuestas |
| SUS, ZAP y carga no ejecutados | Ejecutarlos en staging antes del piloto (T21, T22) | Equipo + DSM | SUS ≥ 68; ZAP sin alertas altas; p95 ≤ 2 s con 30 usuarios | Pendiente |
| Retención de datos provisoria (5 y 2 años) | Confirmar los plazos con el DSM | Contraparte | Valores en `.env` acordados por escrito | Pendiente |
| E2E-08 / DEF-08: el límite por IP del plugin puede afectar a un CESFAM que comparte IP pública (NAT) | Evaluar con el DSM un límite por IP más alto o una verificación adicional | Plugin (`DSM_OIRS_LIMITE_HORA`) | Prueba con el volumen real de un CESFAM | Propuesta |
