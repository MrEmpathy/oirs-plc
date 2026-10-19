<?php
/**
 * Plugin Name: DSM OIRS – Formularios ciudadanos
 * Description: Formularios de reclamos, sugerencias, consultas, solicitudes, felicitaciones y encuesta de satisfacción
 *              del Departamento de Salud Municipal de Padre Las Casas. Envía los datos al Sistema de Gestión OIRS.
 * Version: 0.1.0
 * Requires PHP: 8.1
 */
defined( 'ABSPATH' ) || exit; // SC-08: impide la ejecución directa del archivo.

require_once __DIR__ . '/includes/firma.php';

const DSM_OIRS_TIPOS = array( 'RECLAMO', 'SUGERENCIA', 'CONSULTA', 'SOLICITUD', 'FELICITACION' );

/** La URL de la API y el secreto se definen en wp-config.php (nunca en la base de datos ni en el código). */
function dsm_oirs_config(): array {
	return array(
		'api'     => defined( 'OIRS_API_URL' ) ? OIRS_API_URL : '',
		'secreto' => defined( 'OIRS_HMAC_SECRET' ) ? OIRS_HMAC_SECRET : '',
	);
}

function dsm_oirs_enviar( string $ruta, array $datos ) {
	$cfg = dsm_oirs_config();
	if ( empty( $cfg['api'] ) || empty( $cfg['secreto'] ) ) {
		return new WP_Error( 'oirs_config', 'Servicio no configurado.' );
	}
	$cuerpo = wp_json_encode( $datos );
	$ts     = time();
	return wp_remote_post( trailingslashit( $cfg['api'] ) . ltrim( $ruta, '/' ), array(
		'timeout'   => 10,
		'sslverify' => true,
		'headers'   => array(
			'Content-Type'     => 'application/json',
			'X-OIRS-Timestamp' => (string) $ts,
			'X-OIRS-Firma'     => dsm_oirs_firmar( $cuerpo, $ts, $cfg['secreto'] ),
		),
		'body'      => $cuerpo,
	) );
}

/** Limita envíos por IP (10 por hora) para mitigar spam y abuso del formulario público. */
function dsm_oirs_limite_superado(): bool {
	$ip    = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '0';
	$clave = 'oirs_rl_' . md5( $ip );
	$n     = (int) get_transient( $clave );
	if ( $n >= 10 ) {
		return true;
	}
	set_transient( $clave, $n + 1, HOUR_IN_SECONDS );
	return false;
}

function dsm_oirs_procesar_requerimiento(): string {
	if ( ! isset( $_POST['oirs_nonce'] ) || ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['oirs_nonce'] ) ), 'oirs_requerimiento' ) ) {
		return '<p class="oirs-error" role="alert">La sesión del formulario expiró. Recargue la página.</p>';
	}
	if ( ! empty( $_POST['oirs_web'] ) || dsm_oirs_limite_superado() ) { // honeypot + límite
		return '<p class="oirs-error" role="alert">No fue posible procesar su solicitud. Intente más tarde.</p>';
	}
	$tipo = strtoupper( sanitize_key( wp_unslash( $_POST['tipo'] ?? '' ) ) );
	if ( ! in_array( $tipo, DSM_OIRS_TIPOS, true ) ) {
		return '<p class="oirs-error" role="alert">Tipo de solicitud no válido.</p>';
	}
	$datos = array(
		'tipo'                      => $tipo,
		'establecimiento'           => sanitize_text_field( wp_unslash( $_POST['establecimiento'] ?? '' ) ),
		'descripcion'               => sanitize_textarea_field( wp_unslash( $_POST['descripcion'] ?? '' ) ),
		'peticion_concreta'         => sanitize_textarea_field( wp_unslash( $_POST['peticion_concreta'] ?? '' ) ),
		'fecha_atencion'            => sanitize_text_field( wp_unslash( $_POST['fecha_atencion'] ?? '' ) ),
		'nombre'                    => sanitize_text_field( wp_unslash( $_POST['nombre'] ?? '' ) ),
		'apellidos'                 => sanitize_text_field( wp_unslash( $_POST['apellidos'] ?? '' ) ),
		'email'                     => sanitize_email( wp_unslash( $_POST['email'] ?? '' ) ),
		'telefono'                  => sanitize_text_field( wp_unslash( $_POST['telefono'] ?? '' ) ),
		'autoriza_respuesta_email'  => ! empty( $_POST['autoriza_respuesta_email'] ),
		'acepta_tratamiento_datos'  => ! empty( $_POST['acepta_tratamiento_datos'] ),
	);
	$resp = dsm_oirs_enviar( 'api/v1/publico/requerimientos', array_filter( $datos, fn( $v ) => '' !== $v ) );
	if ( is_wp_error( $resp ) || 201 !== wp_remote_retrieve_response_code( $resp ) ) {
		return '<p class="oirs-error" role="alert">No fue posible registrar su solicitud. Revise los datos e intente nuevamente.</p>';
	}
	$json = json_decode( wp_remote_retrieve_body( $resp ), true );
	return sprintf(
		'<div class="oirs-ok" role="status"><h3>Solicitud recibida</h3><p>Su número de folio es <strong>%s</strong>. Guárdelo para cualquier consulta. Plazo de respuesta: %s.</p></div>',
		esc_html( $json['folio'] ?? '' ),
		esc_html( $json['fecha_vencimiento'] ?? '' )
	);
}

/** Shortcode: [oirs_formulario tipo="reclamo"] */
add_shortcode( 'oirs_formulario', function ( $atts ) {
	$atts = shortcode_atts( array( 'tipo' => 'reclamo' ), $atts );
	$html = '';
	if ( 'POST' === ( $_SERVER['REQUEST_METHOD'] ?? '' ) && isset( $_POST['oirs_enviar'] ) ) {
		$html .= dsm_oirs_procesar_requerimiento();
	}
	ob_start();
	include __DIR__ . '/plantillas/formulario-requerimiento.php'; // escapa toda salida con esc_html/esc_attr
	return $html . ob_get_clean();
} );
