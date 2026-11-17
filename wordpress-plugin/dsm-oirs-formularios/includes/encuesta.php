<?php
/**
 * Encuesta de satisfacción anónima (HU02 / CU02). Las preguntas se leen desde la API (versión activa),
 * por lo que una nueva versión de la encuesta no requiere modificar el plugin.
 * Anonimato: no se envían IP, nombre, correo ni hora; solo el establecimiento y las respuestas.
 */
defined( 'ABSPATH' ) || exit;

$GLOBALS['dsm_oirs_enc_estado'] = null;

function dsm_oirs_definicion_encuesta(): ?array {
	$cache = get_transient( 'oirs_encuesta_def' );
	if ( is_array( $cache ) ) {
		return $cache;
	}
	$r = dsm_oirs_api( 'GET', 'api/v1/publico/encuestas/' . DSM_OIRS_ENCUESTA );
	if ( is_wp_error( $r ) || 200 !== $r['codigo'] || empty( $r['datos']['preguntas'] ) ) {
		return null;
	}
	set_transient( 'oirs_encuesta_def', $r['datos'], 10 * MINUTE_IN_SECONDS );
	return $r['datos'];
}

add_action( 'template_redirect', function () {
	if ( 'POST' !== ( $_SERVER['REQUEST_METHOD'] ?? '' ) || 'encuesta' !== dsm_oirs_post( 'oirs_accion' ) ) {
		return;
	}
	$def     = dsm_oirs_definicion_encuesta();
	$estab   = sanitize_text_field( dsm_oirs_post( 'establecimiento' ) );
	$resp    = array();
	$errores = array();
	foreach ( (array) ( $def['preguntas'] ?? array() ) as $p ) {
		$id  = (string) $p['id'];
		$raw = sanitize_text_field( dsm_oirs_post( 'p_' . $id ) );
		if ( '' === $raw ) {
			if ( ! empty( $p['obligatoria'] ) ) {
				$errores[ $id ] = 'Responda esta pregunta.';
			}
			continue;
		}
		$resp[ $id ] = 'escala' === $p['tipo'] ? (int) $raw : $raw;
	}
	if ( '' === $estab ) {
		$errores['establecimiento'] = 'Seleccione el establecimiento donde se atendió.';
	}
	$estado = array(
		'valores' => array( 'establecimiento' => $estab, 'respuestas' => $resp, 'comentario' => sanitize_textarea_field( dsm_oirs_post( 'comentario' ) ) ),
		'errores' => $errores,
		'general' => '',
	);
	if ( ! wp_verify_nonce( sanitize_text_field( dsm_oirs_post( 'oirs_nonce' ) ), 'oirs_encuesta' ) ) {
		$estado['general'] = 'El formulario expiró. Vuelva a enviarlo.';
	} elseif ( '' !== dsm_oirs_post( 'oirs_web' ) || dsm_oirs_limite_superado() ) {
		$estado['general'] = 'No fue posible registrar su respuesta. Intente más tarde.';
	} elseif ( ! $errores ) {
		$r = dsm_oirs_api( 'POST', 'api/v1/publico/encuestas/' . DSM_OIRS_ENCUESTA . '/respuestas', array(
			'establecimiento' => $estab,
			'respuestas'      => (object) $resp,
			'comentario'      => $estado['valores']['comentario'],
		) );
		if ( ! is_wp_error( $r ) && 201 === $r['codigo'] ) {
			wp_safe_redirect( add_query_arg( 'oirs_gracias', '1', get_permalink( get_queried_object_id() ) ) . '#oirs-resultado' );
			exit;
		}
		$estado['general'] = dsm_oirs_mensaje_error( $r );
		if ( ! is_wp_error( $r ) && ! empty( $r['datos']['detalle'] ) ) {
			$estado['errores']['__general'] = implode( ' ', array_map( 'strval', (array) $r['datos']['detalle'] ) );
		}
	} else {
		$estado['general'] = 'Faltan respuestas obligatorias.';
	}
	$GLOBALS['dsm_oirs_enc_estado'] = $estado;
} );

/** Shortcode: [oirs_encuesta]. El parámetro ?est=CODIGO (código QR del establecimiento) lo preselecciona. */
add_shortcode( 'oirs_encuesta', function () {
	dsm_oirs_encolar();
	if ( isset( $_GET['oirs_gracias'] ) ) {
		return '<div class="oirs" id="oirs-resultado"><div class="oirs-confirmacion" role="status" tabindex="-1">'
			. '<h2 class="oirs-confirmacion__titulo">¡Gracias por su opinión!</h2>'
			. '<p>Su respuesta es anónima y nos ayuda a mejorar la atención en la red de salud comunal.</p></div></div>';
	}
	$def = dsm_oirs_definicion_encuesta();
	if ( ! $def ) {
		return '<div class="oirs"><div class="oirs-aviso oirs-aviso--error" role="alert"><p>La encuesta no está disponible en este momento.</p></div></div>';
	}
	$estado           = $GLOBALS['dsm_oirs_enc_estado'] ?? array( 'valores' => array(), 'errores' => array(), 'general' => '' );
	$establecimientos = dsm_oirs_establecimientos();
	$est_qr           = isset( $_GET['est'] ) ? sanitize_text_field( wp_unslash( $_GET['est'] ) ) : '';
	$est_actual       = $estado['valores']['establecimiento'] ?? ( isset( $establecimientos[ $est_qr ] ) ? $est_qr : '' );
	ob_start();
	include __DIR__ . '/../plantillas/encuesta.php';
	return ob_get_clean();
} );
