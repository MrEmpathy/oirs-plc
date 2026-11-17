<?php
/**
 * Encuesta de satisfacción. Variables: $def (preguntas), $estado, $establecimientos, $est_actual.
 * Cada pregunta de escala es un grupo de botones de opción 1–7 dentro de un fieldset con su leyenda.
 */
defined( 'ABSPATH' ) || exit;
$errores    = $estado['errores'];
$respuestas = $estado['valores']['respuestas'] ?? array();
?>
<div class="oirs" id="oirs-encuesta">
	<?php if ( $estado['general'] ) : ?>
		<div class="oirs-aviso oirs-aviso--error" role="alert" tabindex="-1" id="oirs-resumen">
			<p><strong><?php echo esc_html( $estado['general'] ); ?></strong></p>
			<?php if ( isset( $errores['__general'] ) ) : ?><p><?php echo esc_html( $errores['__general'] ); ?></p><?php endif; ?>
		</div>
	<?php endif; ?>
	<p class="oirs-nota">Encuesta anónima: no le pediremos su nombre ni datos de contacto. Escala de 1 (muy malo) a 7 (muy bueno).</p>
	<form method="post" class="oirs-form" novalidate data-oirs-form="encuesta">
		<?php wp_nonce_field( 'oirs_encuesta', 'oirs_nonce' ); ?>
		<input type="hidden" name="oirs_accion" value="encuesta">
		<p class="oirs-hp" aria-hidden="true"><label>No completar <input type="text" name="oirs_web" tabindex="-1" autocomplete="off"></label></p>

		<div class="oirs-campo">
			<label for="oirs-establecimiento">Establecimiento donde se atendió <span class="oirs-req" aria-hidden="true">*</span></label>
			<select id="oirs-establecimiento" name="establecimiento" required
				<?php echo isset( $errores['establecimiento'] ) ? 'aria-invalid="true" aria-describedby="oirs-err-establecimiento"' : ''; ?>>
				<option value="">Seleccione…</option>
				<?php foreach ( $establecimientos as $codigo => $nombre ) : ?>
					<option value="<?php echo esc_attr( $codigo ); ?>" <?php selected( $est_actual, $codigo ); ?>><?php echo esc_html( $nombre ); ?></option>
				<?php endforeach; ?>
			</select>
			<?php if ( isset( $errores['establecimiento'] ) ) : ?>
				<p class="oirs-campo__error" id="oirs-err-establecimiento"><?php echo esc_html( $errores['establecimiento'] ); ?></p>
			<?php endif; ?>
		</div>

		<?php foreach ( $def['preguntas'] as $i => $p ) : ?>
			<?php
			$id       = (string) $p['id'];
			$actual   = isset( $respuestas[ $id ] ) ? (string) $respuestas[ $id ] : '';
			$tiene_er = isset( $errores[ $id ] );
			?>
			<?php if ( 'escala' === $p['tipo'] ) : ?>
				<fieldset class="oirs-escala" id="oirs-<?php echo esc_attr( $id ); ?>"
					<?php echo $tiene_er ? 'aria-invalid="true" aria-describedby="oirs-err-' . esc_attr( $id ) . '"' : ''; ?>>
					<legend><?php echo esc_html( ( $i + 1 ) . '. ' . $p['texto'] ); ?>
						<?php if ( ! empty( $p['obligatoria'] ) ) : ?><span class="oirs-req" aria-hidden="true">*</span><?php endif; ?></legend>
					<div class="oirs-escala__opciones">
						<?php for ( $n = (int) $p['min']; $n <= (int) $p['max']; $n++ ) : ?>
							<label class="oirs-escala__opcion">
								<input type="radio" name="p_<?php echo esc_attr( $id ); ?>" value="<?php echo esc_attr( (string) $n ); ?>" <?php checked( $actual, (string) $n ); ?>>
								<span><?php echo esc_html( (string) $n ); ?></span>
							</label>
						<?php endfor; ?>
					</div>
					<p class="oirs-escala__extremos" aria-hidden="true"><span>Muy malo</span><span>Muy bueno</span></p>
					<?php if ( $tiene_er ) : ?><p class="oirs-campo__error" id="oirs-err-<?php echo esc_attr( $id ); ?>"><?php echo esc_html( $errores[ $id ] ); ?></p><?php endif; ?>
				</fieldset>
			<?php elseif ( 'opcion' === $p['tipo'] ) : ?>
				<div class="oirs-campo">
					<label for="oirs-<?php echo esc_attr( $id ); ?>"><?php echo esc_html( ( $i + 1 ) . '. ' . $p['texto'] ); ?></label>
					<select id="oirs-<?php echo esc_attr( $id ); ?>" name="p_<?php echo esc_attr( $id ); ?>">
						<option value="">Seleccione…</option>
						<?php foreach ( (array) $p['opciones'] as $op ) : ?>
							<option value="<?php echo esc_attr( (string) $op ); ?>" <?php selected( $actual, (string) $op ); ?>><?php echo esc_html( (string) $op ); ?></option>
						<?php endforeach; ?>
					</select>
				</div>
			<?php endif; ?>
		<?php endforeach; ?>

		<div class="oirs-campo">
			<label for="oirs-comentario">Comentario (opcional)</label>
			<p class="oirs-campo__ayuda" id="oirs-ayuda-comentario">No escriba su nombre, RUT ni datos de contacto: la encuesta es anónima.</p>
			<textarea id="oirs-comentario" name="comentario" rows="3" maxlength="1000" aria-describedby="oirs-ayuda-comentario"><?php echo esc_textarea( (string) ( $estado['valores']['comentario'] ?? '' ) ); ?></textarea>
		</div>
		<button type="submit" class="oirs-boton">Enviar respuesta</button>
	</form>
</div>
