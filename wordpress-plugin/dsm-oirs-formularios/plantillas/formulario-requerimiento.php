<?php defined( 'ABSPATH' ) || exit; ?>
<form method="post" class="oirs-form" novalidate>
	<?php wp_nonce_field( 'oirs_requerimiento', 'oirs_nonce' ); ?>
	<input type="hidden" name="tipo" value="<?php echo esc_attr( strtoupper( $atts['tipo'] ) ); ?>">
	<p class="oirs-hp" aria-hidden="true"><label>Web <input type="text" name="oirs_web" tabindex="-1" autocomplete="off"></label></p>
	<label for="oirs-est">Establecimiento donde se atendió *</label>
	<select id="oirs-est" name="establecimiento" required></select>
	<label for="oirs-desc">Describa la situación *</label>
	<textarea id="oirs-desc" name="descripcion" minlength="10" maxlength="4000" required></textarea>
	<label><input type="checkbox" name="acepta_tratamiento_datos" required> Acepto el uso de mis datos solo para gestionar esta solicitud (Ley N.° 19.628).</label>
	<button type="submit" name="oirs_enviar" value="1">Enviar</button>
</form>
