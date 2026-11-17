# Manual de usuario por perfil

El sistema tiene dos partes:

- **Sitio web del DSM (WordPress)**: lo usa la ciudadanía, sin cuenta.
- **Sistema de Gestión OIRS** (`https://…:8443`): lo usan los funcionarios con cuenta individual.

Cada perfil ve en el menú solo las opciones que tiene autorizadas. Si alguien intenta entrar por la dirección a una
opción que no le corresponde, el sistema responde «No autorizado» y registra el intento.

| Opción del menú | Administrador | Encargado OIRS DSM | Encargado OIRS establecimiento | Dirección |
|---|---|---|---|---|
| Bandeja de casos | Todos (lectura) | Todos (lectura) | Su establecimiento (gestión) | Su establecimiento (lectura) |
| Ingreso presencial | — | — | ✔ | — |
| Panel de plazos | ✔ | ✔ | — | — |
| Reportes | — | Toda la red + exportar CSV | Su establecimiento | Su establecimiento |
| Usuarios y Catálogos | ✔ | — | — | — |
| Verificación en dos pasos | Obligatoria | Obligatoria | Opcional | Opcional |

## 1. Usuario de la red de salud (sitio web)

**Enviar un reclamo, sugerencia, consulta, solicitud o felicitación**
1. En la portada, pulse «OIRS en línea».
2. Elija qué desea hacer. Para reclamos, consultas y solicitudes son obligatorios su nombre y un correo o teléfono,
   porque se le debe responder. Las sugerencias y felicitaciones pueden enviarse sin identificarse.
3. Elija el establecimiento, describa la situación y acepte el uso de sus datos.
4. Pulse «Enviar solicitud». Verá su **número de folio** y la fecha en que, a más tardar, recibirá la respuesta
   (15 días hábiles). Puede imprimir el comprobante.

Si falta algún dato, el formulario lo indica junto al campo y conserva lo que ya escribió.

**Responder la encuesta de satisfacción**: en «Encuesta de satisfacción» (o escaneando el código QR del
establecimiento, que lo deja preseleccionado), califique cinco aspectos de 1 a 7 y, si quiere, agregue un comentario
sin datos personales. La encuesta es anónima.

## 2. Ingreso al sistema (todos los funcionarios)

1. Ingrese con su correo institucional y su contraseña.
2. **Primer ingreso:** el sistema le pide cambiar la contraseña temporal. La nueva debe tener 12 caracteres o más,
   con mayúscula, minúscula, número y símbolo.
3. **Verificación en dos pasos** (Administrador y Encargado OIRS DSM): la primera vez se muestra un código QR.
   Escanéelo con una aplicación autenticadora (Google Authenticator, Microsoft Authenticator, FreeOTP) y escriba el
   código de 6 dígitos. En los ingresos siguientes solo se pide el código.
4. Tras 5 intentos fallidos (de contraseña o de código), la cuenta se bloquea 15 minutos.
5. **¿Olvidó su contraseña?** En la pantalla de ingreso pida un enlace; llega al correo y sirve una sola vez
   durante 30 minutos.
6. La sesión se cierra sola después de 30 minutos sin actividad. Use «Salir» al terminar.

## 3. Encargado OIRS de establecimiento

**Bandeja**: muestra los casos abiertos de su establecimiento, ordenados por fecha de vencimiento. Las cuatro
tarjetas superiores (Abiertos, Por vencer, Vencidos, Por cerrar) funcionan también como filtros. El semáforo indica
los días hábiles restantes: verde (más de 5), ámbar (5 o menos) y rojo (vencido).

**Gestionar un caso** (abra el folio):
1. **Clasificar y derivar**: elija el motivo y la unidad del establecimiento que debe resolverlo, y agregue
   instrucciones si lo necesita. El caso pasa a «En proceso». Puede reasignarlo mientras siga en proceso.
2. **Registrar respuesta**: escriba el texto, el medio (correo solo si el usuario lo autorizó; si no, carta
   certificada) y la fecha de emisión. El sistema indica si quedó dentro o fuera del plazo legal. El caso pasa a
   «Respondido».
3. **Cerrar caso**: una vez enviada la respuesta, confírmelo en el diálogo. Un caso cerrado no se puede modificar.

El historial del caso registra cada cambio con fecha y responsable, y no puede editarse.

**Ingreso presencial**: digitalice el formulario en papel. El sistema asigna el folio y el plazo, y muestra un
comprobante imprimible para entregar al usuario.

**Reportes**: indicadores de su establecimiento por período (sin exportación).

## 4. Dirección de establecimiento

Consulta la bandeja, el detalle y las respuestas de los casos de su establecimiento, además de sus reportes, en
**modo de solo lectura**: no ve botones de gestión y el servidor rechaza cualquier intento de modificar.

## 5. Encargado OIRS del Departamento (DSM)

- **Panel de plazos**: casos abiertos de toda la red por establecimiento (en plazo, por vencer, vencidos) y lista de
  casos críticos (vencidos o con 2 días hábiles o menos). Cada fila abre la bandeja filtrada.
- **Bandeja y detalle**: lectura de todos los casos. Los datos de contacto del solicitante no se muestran en este
  perfil (minimización).
- **Reportes**: total de casos, porcentaje respondido dentro de plazo, tiempo promedio, casos por tipo, estado,
  motivo y establecimiento, y satisfacción usuaria por pregunta. Cada gráfico tiene su tabla de datos.
- **Exportar CSV**: descarga los casos del período **sin datos personales**. Cada exportación queda registrada.

## 6. Administrador del sistema

- **Usuarios**: «Nuevo usuario» crea la cuenta con perfil y, si corresponde, establecimiento. Se muestra **una sola
  vez** una contraseña temporal para entregarla por un canal seguro. En la ficha del usuario puede:
  - desbloquear la cuenta;
  - emitir una nueva contraseña temporal;
  - restablecer la verificación en dos pasos (por ejemplo, si el funcionario perdió el teléfono);
  - desactivar o activar la cuenta.

  Las cuentas no se eliminan, para conservar la trazabilidad. El administrador nunca ve contraseñas ni secretos.
- **Catálogos**: establecimientos, unidades de derivación, motivos (solo puede existir un motivo «Otro») y
  feriados. Los registros se desactivan en lugar de eliminarse. Un feriado nuevo se aplica a los casos que ingresen
  desde ese momento.

## 7. Unidad de Participación y Comunicaciones (WordPress)

Con el usuario de rol **Editor**, edite páginas y noticias desde el panel de WordPress. Para mostrar los formularios
en una página, agregue un bloque «Shortcode» con `[oirs_formulario]` (o `[oirs_formulario tipo="reclamo"]`) o
`[oirs_encuesta]`. El rol Editor no puede instalar plugins ni cambiar la configuración de la integración, que se
define en `wp-config.php`.
