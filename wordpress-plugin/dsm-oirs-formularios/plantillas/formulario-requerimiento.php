<?php
/**
 * Formulario OIRS. Variables: $tipo_fijo, $tipo_actual, $valores, $errores, $general, $establecimientos.
 * Accesibilidad (sección 5.4): etiquetas visibles, ayuda asociada con aria-describedby, resumen de errores
 * enlazado y anunciado (role=alert), campos inválidos con aria-invalid.
 */
defined( 'ABSPATH' ) || exit;

$v   = fn( string $c ) => esc_attr( (string) ( $valores[ $c ] ?? '' ) );
$err = function ( string $c ) use ( $errores ): string {
	return isset( $errores[ $c ] )
		? '<p class="oirs-campo__error" id="oirs-err-' . esc_attr( $c ) . '">' . esc_html( $errores[ $c ] ) . '</p>'
		: '';
};
$inv = fn( string $c ) => isset( $errores[ $c ] ) ? ' aria-invalid="true" aria-describedby="oirs-err-' . esc_attr( $c ) . '"' : '';
$con_contacto = in_array( $tipo_actual, DSM_OIRS_TIPOS_CON_CONTACTO, true );
?>
<div class="oirs" id="oirs-formulario">
	<?php if ( $general ) : ?>
		<div class="oirs-aviso oirs-aviso--error" role="alert" tabindex="-1" id="oirs-resumen">
			<p><strong><?php echo esc_html( $general ); ?></strong></p>
			<?php if ( $errores ) : ?>
				<ul>
					<?php foreach ( $errores as $campo => $mensaje ) : ?>
						<?php if ( '__general' === $campo ) : ?>
							<li><?php echo esc_html( $mensaje ); ?></li>
						<?php else : ?>
							<li><a href="#oirs-<?php echo esc_attr( $campo ); ?>"><?php echo esc_html( $mensaje ); ?></a></li>
						<?php endif; ?>
					<?php endforeach; ?>
				</ul>
			<?php endif; ?>
		</div>
	<?php endif; ?>

	<?php if ( ! $establecimientos ) : ?>
		<div class="oirs-aviso oirs-aviso--error" role="alert">
			<p>El formulario no está disponible en este momento. Puede presentar su solicitud en la OIRS de su establecimiento.</p>
		</div>
	<?php endif; ?>

	<form method="post" class="oirs-form" novalidate data-oirs-form="requerimiento">
		<?php wp_nonce_field( 'oirs_requerimiento', 'oirs_nonce' ); ?>
		<input type="hidden" name="oirs_accion" value="requerimiento">
		<p class="oirs-hp" aria-hidden="true"><label>No completar <input type="text" name="oirs_web" tabindex="-1" autocomplete="off"></label></p>

		<?php if ( $tipo_fijo ) : ?>
			<input type="hidden" name="tipo" value="<?php echo esc_attr( $tipo_fijo ); ?>">
		<?php else : ?>
			<fieldset class="oirs-tipos" id="oirs-tipo"<?php echo $inv( 'tipo' ); // phpcs:ignore ?>>
				<legend>¿Qué desea hacer? <span class="oirs-req" aria-hidden="true">*</span></legend>
				<?php
				$ayudas = array(
					'RECLAMO'      => 'Cuando un derecho no fue respetado o la atención no fue adecuada.',
					'SUGERENCIA'   => 'Una idea para mejorar la atención.',
					'CONSULTA'     => 'Una duda sobre trámites, horarios o prestaciones.',
					'SOLICITUD'    => 'Pedir un documento, certificado o gestión.',
					'FELICITACION' => 'Reconocer una buena atención.',
				);
				foreach ( DSM_OIRS_TIPOS as $codigo => $nombre ) :
					?>
					<label class="oirs-tipo">
						<input type="radio" name="tipo" value="<?php echo esc_attr( $codigo ); ?>" <?php checked( $tipo_actual, $codigo ); ?>
							data-contacto="<?php echo in_array( $codigo, DSM_OIRS_TIPOS_CON_CONTACTO, true ) ? '1' : '0'; ?>">
						<span class="oirs-tipo__nombre"><?php echo esc_html( $nombre ); ?></span>
						<span class="oirs-tipo__ayuda"><?php echo esc_html( $ayudas[ $codigo ] ); ?></span>
					</label>
				<?php endforeach; ?>
				<?php echo $err( 'tipo' ); // phpcs:ignore ?>
			</fieldset>
		<?php endif; ?>

		<fieldset class="oirs-grupo">
			<legend>Su atención</legend>
			<div class="oirs-campo">
				<label for="oirs-establecimiento">Establecimiento donde se atendió <span class="oirs-req" aria-hidden="true">*</span></label>
				<select id="oirs-establecimiento" name="establecimiento" required<?php echo $inv( 'establecimiento' ); // phpcs:ignore ?>>
					<option value="">Seleccione…</option>
					<?php foreach ( $establecimientos as $codigo => $nombre ) : ?>
						<option value="<?php echo esc_attr( $codigo ); ?>" <?php selected( $valores['establecimiento'] ?? '', $codigo ); ?>><?php echo esc_html( $nombre ); ?></option>
					<?php endforeach; ?>
				</select>
				<?php echo $err( 'establecimiento' ); // phpcs:ignore ?>
			</div>
			<div class="oirs-campo oirs-campo--corto">
				<label for="oirs-fecha_atencion">Fecha de la atención</label>
				<input type="date" id="oirs-fecha_atencion" name="fecha_atencion" value="<?php echo $v( 'fecha_atencion' ); // phpcs:ignore ?>"
					max="<?php echo esc_attr( wp_date( 'Y-m-d' ) ); ?>"<?php echo $inv( 'fecha_atencion' ); // phpcs:ignore ?>>
				<?php echo $err( 'fecha_atencion' ); // phpcs:ignore ?>
			</div>
			<div class="oirs-campo">
				<label for="oirs-descripcion">Describa la situación <span class="oirs-req" aria-hidden="true">*</span></label>
				<p class="oirs-campo__ayuda" id="oirs-ayuda-descripcion">Indique qué ocurrió, cuándo y dónde. No incluya diagnósticos ni datos de otras personas.</p>
				<textarea id="oirs-descripcion" name="descripcion" rows="6" minlength="10" maxlength="4000" required
					aria-describedby="oirs-ayuda-descripcion<?php echo isset( $errores['descripcion'] ) ? ' oirs-err-descripcion' : ''; ?>"
					<?php echo isset( $errores['descripcion'] ) ? 'aria-invalid="true"' : ''; ?>><?php echo esc_textarea( (string) ( $valores['descripcion'] ?? '' ) ); ?></textarea>
				<?php echo $err( 'descripcion' ); // phpcs:ignore ?>
			</div>
			<div class="oirs-campo">
				<label for="oirs-peticion_concreta">¿Qué solicita concretamente?</label>
				<textarea id="oirs-peticion_concreta" name="peticion_concreta" rows="3" maxlength="2000"<?php echo $inv( 'peticion_concreta' ); // phpcs:ignore ?>><?php echo esc_textarea( (string) ( $valores['peticion_concreta'] ?? '' ) ); ?></textarea>
				<?php echo $err( 'peticion_concreta' ); // phpcs:ignore ?>
			</div>
		</fieldset>

		<fieldset class="oirs-grupo" data-oirs-contacto>
			<legend>Sus datos de contacto</legend>
			<p class="oirs-campo__ayuda" data-oirs-contacto-ayuda>
				<span data-si-contacto <?php echo $con_contacto ? '' : 'hidden'; ?>>Son necesarios para responderle. Indique al menos un correo o un teléfono.</span>
				<span data-no-contacto <?php echo $con_contacto ? 'hidden' : ''; ?>>Opcionales: puede enviar su <?php echo esc_html( $tipo_actual ? mb_strtolower( DSM_OIRS_TIPOS[ $tipo_actual ] ) : 'solicitud' ); ?> sin identificarse.</span>
			</p>
			<div class="oirs-fila">
				<div class="oirs-campo">
					<label for="oirs-nombre">Nombre <span class="oirs-req" aria-hidden="true" data-req-contacto <?php echo $con_contacto ? '' : 'hidden'; ?>>*</span></label>
					<input type="text" id="oirs-nombre" name="nombre" maxlength="80" autocomplete="given-name" value="<?php echo $v( 'nombre' ); // phpcs:ignore ?>"<?php echo $inv( 'nombre' ); // phpcs:ignore ?>>
					<?php echo $err( 'nombre' ); // phpcs:ignore ?>
				</div>
				<div class="oirs-campo">
					<label for="oirs-apellidos">Apellidos</label>
					<input type="text" id="oirs-apellidos" name="apellidos" maxlength="80" autocomplete="family-name" value="<?php echo $v( 'apellidos' ); // phpcs:ignore ?>"<?php echo $inv( 'apellidos' ); // phpcs:ignore ?>>
					<?php echo $err( 'apellidos' ); // phpcs:ignore ?>
				</div>
			</div>
			<div class="oirs-fila">
				<div class="oirs-campo">
					<label for="oirs-email">Correo electrónico</label>
					<input type="email" id="oirs-email" name="email" maxlength="254" autocomplete="email" inputmode="email" value="<?php echo $v( 'email' ); // phpcs:ignore ?>"<?php echo $inv( 'email' ); // phpcs:ignore ?>>
					<?php echo $err( 'email' ); // phpcs:ignore ?>
				</div>
				<div class="oirs-campo">
					<label for="oirs-telefono">Teléfono</label>
					<input type="tel" id="oirs-telefono" name="telefono" maxlength="15" autocomplete="tel" inputmode="tel" placeholder="+56 9 1234 5678" value="<?php echo $v( 'telefono' ); // phpcs:ignore ?>"<?php echo $inv( 'telefono' ); // phpcs:ignore ?>>
					<?php echo $err( 'telefono' ); // phpcs:ignore ?>
				</div>
			</div>
			<div class="oirs-fila">
				<div class="oirs-campo oirs-campo--corto">
					<label for="oirs-edad">Edad (opcional)</label>
					<input type="number" id="oirs-edad" name="edad" min="0" max="120" inputmode="numeric" value="<?php echo $v( 'edad' ); // phpcs:ignore ?>"<?php echo $inv( 'edad' ); // phpcs:ignore ?>>
					<?php echo $err( 'edad' ); // phpcs:ignore ?>
				</div>
				<div class="oirs-campo oirs-campo--corto">
					<label for="oirs-sexo">Sexo (opcional)</label>
					<select id="oirs-sexo" name="sexo">
						<option value="">Prefiero no indicar</option>
						<?php foreach ( array( 'F' => 'Femenino', 'M' => 'Masculino', 'O' => 'Otro' ) as $c => $n ) : ?>
							<option value="<?php echo esc_attr( $c ); ?>" <?php selected( $valores['sexo'] ?? '', $c ); ?>><?php echo esc_html( $n ); ?></option>
						<?php endforeach; ?>
					</select>
				</div>
			</div>
			<label class="oirs-check">
				<input type="checkbox" name="autoriza_respuesta_email" value="1" <?php checked( ! empty( $valores['autoriza_respuesta_email'] ) ); ?>>
				Autorizo que me respondan por correo electrónico (si no, la respuesta se envía por carta certificada).
			</label>
		</fieldset>

		<div class="oirs-campo">
			<label class="oirs-check" id="oirs-acepta_tratamiento_datos">
				<input type="checkbox" name="acepta_tratamiento_datos" value="1" required <?php checked( ! empty( $valores['acepta_tratamiento_datos'] ) ); ?><?php echo $inv( 'acepta_tratamiento_datos' ); // phpcs:ignore ?>>
				Acepto que mis datos se usen solo para gestionar esta solicitud (Ley N.° 19.628). <span class="oirs-req" aria-hidden="true">*</span>
			</label>
			<?php echo $err( 'acepta_tratamiento_datos' ); // phpcs:ignore ?>
		</div>

		<p class="oirs-nota">Plazo legal de respuesta: 15 días hábiles (Ley N.° 20.584). Los campos con <span class="oirs-req">*</span> son obligatorios.</p>
		<button type="submit" class="oirs-boton">Enviar solicitud</button>
	</form>
</div>
