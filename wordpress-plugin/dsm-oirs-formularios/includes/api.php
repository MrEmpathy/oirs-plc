<?php
/**
 * Cliente de la API pública del Sistema de Gestión OIRS (servidor a servidor, firmado con HMAC-SHA256).
 * El navegador del ciudadano nunca se comunica con la API: solo el servidor de WordPress conoce el secreto.
 */
defined( 'ABSPATH' ) || exit;

/** La URL de la API y el secreto se definen en wp-config.php (nunca en la base de datos ni en el código). */
function dsm_oirs_config(): array {
	return array(
		'api'     => defined( 'OIRS_API_URL' ) ? (string) OIRS_API_URL : '',
		'secreto' => defined( 'OIRS_HMAC_SECRET' ) ? (string) OIRS_HMAC_SECRET : '',
		'ca'      => defined( 'OIRS_API_CA' ) ? (string) OIRS_API_CA : '',
	);
}

/**
 * Petición firmada a la API. Devuelve array( 'codigo' => int, 'datos' => array ) o WP_Error.
 * Firma: HMAC-SHA256( secreto, "<timestamp>.<cuerpo>" ) en X-OIRS-Firma (la API rechaza más de 300 s de desfase).
 */
function dsm_oirs_api( string $metodo, string $ruta, ?array $datos = null ) {
	$cfg = dsm_oirs_config();
	if ( '' === $cfg['api'] || '' === $cfg['secreto'] ) {
		return new WP_Error( 'oirs_config', 'Servicio no configurado.' );
	}
	$cuerpo = null === $datos ? '' : wp_json_encode( $datos );
	$ts     = time();
	$args   = array(
		'method'    => $metodo,
		'timeout'   => 10,
		'sslverify' => true, // nunca se desactiva la verificación TLS
		'headers'   => array(
			'Accept'           => 'application/json',
			'X-OIRS-Timestamp' => (string) $ts,
			'X-OIRS-Firma'     => dsm_oirs_firmar( $cuerpo, $ts, $cfg['secreto'] ),
		),
	);
	if ( '' !== $cfg['ca'] ) {
		$args['sslcertificates'] = $cfg['ca']; // CA del entorno de demostración (certificado autofirmado)
	}
	if ( 'POST' === $metodo ) {
		$args['headers']['Content-Type'] = 'application/json';
		$args['body']                    = $cuerpo;
	}
	$resp = wp_remote_request( trailingslashit( $cfg['api'] ) . ltrim( $ruta, '/' ), $args );
	if ( is_wp_error( $resp ) ) {
		return $resp;
	}
	$json = json_decode( wp_remote_retrieve_body( $resp ), true );
	return array(
		'codigo' => (int) wp_remote_retrieve_response_code( $resp ),
		'datos'  => is_array( $json ) ? $json : array(),
	);
}

/** Catálogos públicos (establecimientos activos). Caché de 10 minutos para no consultar la API en cada visita. */
function dsm_oirs_establecimientos(): array {
	$cache = get_transient( 'oirs_catalogos' );
	if ( is_array( $cache ) ) {
		return $cache;
	}
	$r = dsm_oirs_api( 'GET', 'api/v1/publico/catalogos' );
	if ( is_wp_error( $r ) || 200 !== $r['codigo'] ) {
		return array();
	}
	$lista = array();
	foreach ( (array) ( $r['datos']['establecimientos'] ?? array() ) as $e ) {
		if ( isset( $e['codigo'], $e['nombre'] ) && 'DSM' !== $e['codigo'] ) {
			$lista[ (string) $e['codigo'] ] = (string) $e['nombre'];
		}
	}
	set_transient( 'oirs_catalogos', $lista, 10 * MINUTE_IN_SECONDS );
	return $lista;
}

/**
 * Traduce los errores de validación de la API ("campo: mensaje") a errores por campo para mostrarlos
 * junto al control correspondiente. Los mensajes sin campo se muestran como error general.
 */
function dsm_oirs_errores_api( array $datos ): array {
	$errores = array();
	foreach ( (array) ( $datos['detalle'] ?? array() ) as $msg ) {
		$msg = (string) $msg;
		if ( preg_match( '/^([a-z_]+): (.+)$/', $msg, $m ) ) {
			$errores[ $m[1] ] = $m[2];
		} else {
			$errores['__general'] = $msg;
		}
	}
	return $errores;
}

/** Mensaje traducido para los errores más frecuentes de la API (Django entrega mensajes en español). */
function dsm_oirs_mensaje_error( WP_Error|array $r ): string {
	if ( is_wp_error( $r ) ) {
		return 'El servicio no está disponible en este momento. Intente más tarde o acuda a la OIRS de su establecimiento.';
	}
	if ( 401 === $r['codigo'] ) {
		return 'No fue posible verificar el origen de la solicitud. Avise al administrador del sitio.';
	}
	if ( $r['codigo'] >= 500 ) { // 503: una base del sistema está caída; los datos del formulario se conservan (DEF-16)
		return 'El servicio no está disponible en este momento. Sus datos se conservan: intente enviarlos de nuevo en unos minutos.';
	}
	return 'No fue posible registrar su solicitud. Revise los campos marcados.';
}
