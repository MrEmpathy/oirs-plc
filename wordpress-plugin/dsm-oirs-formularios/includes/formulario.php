<?php
/**
 * Formulario OIRS: reclamo, sugerencia, consulta, solicitud y felicitación (HU01 / CU01).
 *
 * Flujo: el envío se procesa en `template_redirect` (antes de imprimir la página) y, si la API lo acepta,
 * se redirige con el patrón POST-redirección-GET: recargar la página de confirmación no crea un segundo caso.
 */
defined( 'ABSPATH' ) || exit;

/** Estado del envío en curso (errores y valores escritos) para volver a dibujar el formulario sin perder datos. */
$GLOBALS['dsm_oirs_req_estado'] = null;

/** Lee y sanitiza los campos del formulario (sanitize_* al recibir, esc_* al mostrar: SC-08). */
function dsm_oirs_campos_requerimiento(): array {
	$tipo = strtoupper( sanitize_key( dsm_oirs_post( 'tipo' ) ) );
	$sexo = strtoupper( sanitize_key( dsm_oirs_post( 'sexo' ) ) );
	$edad = dsm_oirs_post( 'edad' );
	$fat  = sanitize_text_field( dsm_oirs_post( 'fecha_atencion' ) );
	return array(
		'tipo'                     => isset( DSM_OIRS_TIPOS[ $tipo ] ) ? $tipo : '',
		'establecimiento'          => sanitize_text_field( dsm_oirs_post( 'establecimiento' ) ),
		'fecha_atencion'           => preg_match( '/^\d{4}-\d{2}-\d{2}$/', $fat ) ? $fat : '',
		'descripcion'              => sanitize_textarea_field( dsm_oirs_post( 'descripcion' ) ),
		'peticion_concreta'        => sanitize_textarea_field( dsm_oirs_post( 'peticion_concreta' ) ),
		'nombre'                   => sanitize_text_field( dsm_oirs_post( 'nombre' ) ),
		'apellidos'                => sanitize_text_field( dsm_oirs_post( 'apellidos' ) ),
		'email'                    => sanitize_email( dsm_oirs_post( 'email' ) ),
		'telefono'                 => sanitize_text_field( dsm_oirs_post( 'telefono' ) ),
		'edad'                     => ctype_digit( $edad ) ? (int) $edad : '',
		'sexo'                     => in_array( $sexo, array( 'F', 'M', 'O' ), true ) ? $sexo : '',
		'autoriza_respuesta_email' => '' !== dsm_oirs_post( 'autoriza_respuesta_email' ),
		'acepta_tratamiento_datos' => '' !== dsm_oirs_post( 'acepta_tratamiento_datos' ),
	);
}

/** Validaciones mínimas antes de llamar a la API (la validación definitiva la hace siempre el servidor: SC-01). */
function dsm_oirs_prevalidar( array $v ): array {
	$e = array();
	if ( '' === $v['tipo'] ) {
		$e['tipo'] = 'Seleccione el tipo de solicitud.';
	}
	if ( '' === $v['establecimiento'] ) {
		$e['establecimiento'] = 'Seleccione el establecimiento donde se atendió.';
	}
	if ( mb_strlen( $v['descripcion'] ) < 10 ) {
		$e['descripcion'] = 'Describa la situación con al menos 10 caracteres.';
	}
	if ( in_array( $v['tipo'], DSM_OIRS_TIPOS_CON_CONTACTO, true ) ) {
		if ( '' === $v['nombre'] ) {
			$e['nombre'] = 'Indique su nombre para que podamos responderle.';
		}
		if ( '' === $v['email'] && '' === $v['telefono'] ) {
			$e['email'] = 'Indique un correo o un teléfono para que podamos responderle.';
		}
	}
	if ( '' !== dsm_oirs_post( 'email' ) && '' === $v['email'] ) {
		$e['email'] = 'El correo no tiene un formato válido (ejemplo: nombre@correo.cl).';
	}
	if ( ! $v['acepta_tratamiento_datos'] ) {
		$e['acepta_tratamiento_datos'] = 'Debe aceptar el uso de sus datos para gestionar la solicitud.';
	}
	return $e;
}

add_action( 'template_redirect', function () {
	if ( 'POST' !== ( $_SERVER['REQUEST_METHOD'] ?? '' ) || 'requerimiento' !== dsm_oirs_post( 'oirs_accion' ) ) {
		return;
	}
	$valores = dsm_oirs_campos_requerimiento();
	$estado  = array( 'valores' => $valores, 'errores' => array(), 'general' => '' );

	if ( ! wp_verify_nonce( sanitize_text_field( dsm_oirs_post( 'oirs_nonce' ) ), 'oirs_requerimiento' ) ) {
		$estado['general'] = 'El formulario expiró. Revise sus datos y vuelva a enviarlo.';
	} elseif ( '' !== dsm_oirs_post( 'oirs_web' ) || dsm_oirs_limite_superado() ) { // honeypot + 10 envíos/hora
		$estado['general'] = 'No fue posible procesar su solicitud. Intente más tarde.';
	} else {
		$estado['errores'] = dsm_oirs_prevalidar( $valores );
		if ( ! $estado['errores'] ) {
			$datos = array_filter( $valores, fn( $x ) => '' !== $x && null !== $x );
			$r     = dsm_oirs_api( 'POST', 'api/v1/publico/requerimientos', $datos );
			if ( ! is_wp_error( $r ) && 201 === $r['codigo'] ) {
				$token = wp_generate_password( 20, false );
				set_transient( 'oirs_ok_' . $token, array(
					'folio'      => (string) ( $r['datos']['folio'] ?? '' ),
					'vencimiento' => (string) ( $r['datos']['fecha_vencimiento'] ?? '' ),
					'tipo'       => $valores['tipo'],
				), 30 * MINUTE_IN_SECONDS );
				wp_safe_redirect( add_query_arg( 'oirs_ok', $token, get_permalink( get_queried_object_id() ) ) . '#oirs-resultado' );
				exit;
			}
			$estado['errores'] = is_wp_error( $r ) ? array() : dsm_oirs_errores_api( $r['datos'] );
			$estado['general'] = dsm_oirs_mensaje_error( $r );
		}
	}
	if ( $estado['errores'] && '' === $estado['general'] ) {
		$estado['general'] = 'Revise los campos marcados.';
	}
	$GLOBALS['dsm_oirs_req_estado'] = $estado;
} );

/** Fecha ISO (AAAA-MM-DD) en formato legible en español: «9 de diciembre de 2026». */
function dsm_oirs_fecha_larga( string $iso ): string {
	$meses = array( '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre' );
	if ( ! preg_match( '/^(\d{4})-(\d{2})-(\d{2})$/', $iso, $m ) ) {
		return $iso;
	}
	return (int) $m[3] . ' de ' . $meses[ (int) $m[2] ] . ' de ' . $m[1];
}

/** Shortcode: [oirs_formulario] o [oirs_formulario tipo="reclamo"] */
add_shortcode( 'oirs_formulario', function ( $atts ) {
	dsm_oirs_encolar();
	$atts      = shortcode_atts( array( 'tipo' => '' ), $atts, 'oirs_formulario' );
	$tipo_fijo = strtoupper( sanitize_key( $atts['tipo'] ) );
	$tipo_fijo = isset( DSM_OIRS_TIPOS[ $tipo_fijo ] ) ? $tipo_fijo : '';

	$token = isset( $_GET['oirs_ok'] ) ? sanitize_key( wp_unslash( $_GET['oirs_ok'] ) ) : '';
	if ( '' !== $token ) {
		$resultado = get_transient( 'oirs_ok_' . $token );
		if ( is_array( $resultado ) ) {
			ob_start();
			include __DIR__ . '/../plantillas/confirmacion.php';
			return ob_get_clean();
		}
	}

	$estado          = $GLOBALS['dsm_oirs_req_estado'] ?? array( 'valores' => array(), 'errores' => array(), 'general' => '' );
	$valores         = $estado['valores'];
	$errores         = $estado['errores'];
	$general         = $estado['general'];
	$establecimientos = dsm_oirs_establecimientos();
	$tipo_actual     = $tipo_fijo ?: ( $valores['tipo'] ?? '' );
	ob_start();
	include __DIR__ . '/../plantillas/formulario-requerimiento.php'; // escapa toda salida con esc_html/esc_attr
	return ob_get_clean();
} );
