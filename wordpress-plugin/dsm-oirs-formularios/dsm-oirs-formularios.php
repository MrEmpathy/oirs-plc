<?php
/**
 * Plugin Name: DSM OIRS – Formularios ciudadanos
 * Description: Formularios de reclamos, sugerencias, consultas, solicitudes, felicitaciones y encuesta de satisfacción
 *              del Departamento de Salud Municipal de Padre Las Casas. No guarda datos en WordPress: los envía
 *              firmados (HMAC-SHA256) al Sistema de Gestión OIRS.
 * Version: 1.0.0
 * Requires at least: 6.4
 * Requires PHP: 8.1
 * Author: Equipo Proyecto Integrado (N. Beltrán, M. Brellenthin)
 * License: GPL-2.0-or-later
 * Text Domain: dsm-oirs
 *
 * Uso:   [oirs_formulario]                 Formulario OIRS con selección de tipo.
 *        [oirs_formulario tipo="reclamo"]  Formulario fijo para un tipo.
 *        [oirs_encuesta]                   Encuesta de satisfacción anónima (?est=CODIGO preselecciona el establecimiento).
 *
 * Configuración (wp-config.php, nunca en la base de datos — SC-08):
 *        define( 'OIRS_API_URL', 'https://oirs.salud.padrelascasas.cl/' );
 *        define( 'OIRS_HMAC_SECRET', '...' );
 *        define( 'OIRS_API_CA', '/ruta/ca.crt' );            // opcional: CA propia (entorno de demostración)
 *        define( 'OIRS_URL_FUNCIONARIOS', 'https://...' );   // opcional: enlace «Acceso funcionarios»
 */
defined( 'ABSPATH' ) || exit; // SC-08: impide la ejecución directa del archivo.

const DSM_OIRS_VERSION = '1.0.0';
const DSM_OIRS_TIPOS   = array(
	'RECLAMO'      => 'Reclamo',
	'SUGERENCIA'   => 'Sugerencia',
	'CONSULTA'     => 'Consulta',
	'SOLICITUD'    => 'Solicitud',
	'FELICITACION' => 'Felicitación',
);
// Tipos que exigen identificación para poder responder (misma regla que la API: RequerimientoPublicoForm).
const DSM_OIRS_TIPOS_CON_CONTACTO = array( 'RECLAMO', 'CONSULTA', 'SOLICITUD' );
const DSM_OIRS_ENCUESTA           = 'satisfaccion-usuaria';
const DSM_OIRS_LIMITE_HORA        = 10;

require_once __DIR__ . '/includes/firma.php';
require_once __DIR__ . '/includes/api.php';
require_once __DIR__ . '/includes/formulario.php';
require_once __DIR__ . '/includes/encuesta.php';

if ( is_admin() ) {
	require_once __DIR__ . '/includes/ajustes.php';
}

add_action( 'wp_enqueue_scripts', function () {
	wp_register_style( 'dsm-oirs', plugins_url( 'assets/oirs.css', __FILE__ ), array(), DSM_OIRS_VERSION );
	wp_register_script( 'dsm-oirs', plugins_url( 'assets/oirs.js', __FILE__ ), array(), DSM_OIRS_VERSION, array( 'in_footer' => true ) );
} );

/** Encola los recursos solo en las páginas que usan un shortcode del plugin. */
function dsm_oirs_encolar(): void {
	wp_enqueue_style( 'dsm-oirs' );
	wp_enqueue_script( 'dsm-oirs' );
}

/** Limita envíos por IP (10 por hora) para mitigar spam y abuso del formulario público. */
function dsm_oirs_limite_superado(): bool {
	$ip    = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '0';
	$clave = 'oirs_rl_' . md5( $ip );
	$n     = (int) get_transient( $clave );
	if ( $n >= DSM_OIRS_LIMITE_HORA ) {
		return true;
	}
	set_transient( $clave, $n + 1, HOUR_IN_SECONDS );
	return false;
}

/** Valor enviado por el formulario, sin barras de escape (se sanitiza en cada uso). */
function dsm_oirs_post( string $campo ): string {
	return isset( $_POST[ $campo ] ) && is_string( $_POST[ $campo ] ) ? wp_unslash( $_POST[ $campo ] ) : ''; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput
}
