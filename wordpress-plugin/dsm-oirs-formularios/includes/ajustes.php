<?php
/**
 * Página «Ajustes → DSM OIRS»: muestra si la integración está configurada y permite probar la conexión.
 * Nunca muestra el secreto: solo indica si está definido (SC-05 / SC-08).
 */
defined( 'ABSPATH' ) || exit;

add_action( 'admin_menu', function () {
	add_options_page( 'DSM OIRS', 'DSM OIRS', 'manage_options', 'dsm-oirs', 'dsm_oirs_pagina_ajustes' );
} );

function dsm_oirs_pagina_ajustes(): void {
	if ( ! current_user_can( 'manage_options' ) ) {
		wp_die( esc_html__( 'No autorizado.' ) );
	}
	$cfg       = dsm_oirs_config();
	$resultado = null;
	if ( isset( $_POST['oirs_probar'] ) ) {
		check_admin_referer( 'oirs_probar' );
		delete_transient( 'oirs_catalogos' );
		delete_transient( 'oirs_encuesta_def' );
		$r = dsm_oirs_api( 'GET', 'api/v1/publico/catalogos' ); // prueba conexión, TLS y firma a la vez
		if ( is_wp_error( $r ) ) {
			$resultado = array( 'ok' => false, 'msg' => 'Sin conexión: ' . $r->get_error_message() );
		} elseif ( 200 === $r['codigo'] ) {
			$n         = count( (array) ( $r['datos']['establecimientos'] ?? array() ) );
			$resultado = array( 'ok' => true, 'msg' => "Conexión correcta: firma aceptada, {$n} establecimientos disponibles." );
		} elseif ( 401 === $r['codigo'] ) {
			$resultado = array( 'ok' => false, 'msg' => 'La API rechazó la firma (401): revise OIRS_HMAC_SECRET o la hora del servidor.' );
		} else {
			$resultado = array( 'ok' => false, 'msg' => 'Respuesta inesperada de la API: HTTP ' . $r['codigo'] );
		}
	}
	?>
	<div class="wrap">
		<h1>DSM OIRS – Formularios ciudadanos</h1>
		<p>La configuración se define en <code>wp-config.php</code> y no puede modificarse desde este panel.</p>
		<table class="widefat striped" style="max-width:720px">
			<tbody>
				<tr><th>URL de la API (<code>OIRS_API_URL</code>)</th><td><?php echo $cfg['api'] ? esc_html( $cfg['api'] ) : '<strong>No definida</strong>'; ?></td></tr>
				<tr><th>Secreto HMAC (<code>OIRS_HMAC_SECRET</code>)</th><td><?php echo $cfg['secreto'] ? 'Definido (oculto)' : '<strong>No definido</strong>'; ?></td></tr>
				<tr><th>CA propia (<code>OIRS_API_CA</code>)</th><td><?php echo $cfg['ca'] ? esc_html( $cfg['ca'] ) : 'No (se usa el almacén de certificados del sistema)'; ?></td></tr>
				<tr><th>Shortcodes</th><td><code>[oirs_formulario]</code>, <code>[oirs_formulario tipo="reclamo"]</code>, <code>[oirs_encuesta]</code></td></tr>
			</tbody>
		</table>
		<?php if ( $resultado ) : ?>
			<div class="notice <?php echo $resultado['ok'] ? 'notice-success' : 'notice-error'; ?>"><p><?php echo esc_html( $resultado['msg'] ); ?></p></div>
		<?php endif; ?>
		<form method="post">
			<?php wp_nonce_field( 'oirs_probar' ); ?>
			<p><button type="submit" name="oirs_probar" value="1" class="button button-primary">Probar conexión</button></p>
		</form>
	</div>
	<?php
}
