<?php
/**
 * Firma HMAC-SHA256 de las peticiones WordPress -> API OIRS (compatible con apps/integracion/hmac_firma.py).
 */
if ( ! function_exists( 'dsm_oirs_firmar' ) ) {
	function dsm_oirs_firmar( string $cuerpo, int $ts, string $secreto ): string {
		return hash_hmac( 'sha256', $ts . '.' . $cuerpo, $secreto );
	}
}
