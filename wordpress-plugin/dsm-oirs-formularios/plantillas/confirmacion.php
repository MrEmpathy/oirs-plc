<?php
/** Confirmación de un requerimiento registrado. Variable: $resultado (folio, vencimiento, tipo). */
defined( 'ABSPATH' ) || exit;
$tipo = DSM_OIRS_TIPOS[ $resultado['tipo'] ] ?? 'Solicitud';
?>
<div class="oirs" id="oirs-resultado">
	<div class="oirs-confirmacion" role="status" tabindex="-1">
		<h2 class="oirs-confirmacion__titulo"><?php echo esc_html( $tipo ); ?> recibida</h2>
		<p>Su número de folio es</p>
		<p class="oirs-folio"><?php echo esc_html( $resultado['folio'] ); ?></p>
		<p>Guárdelo: lo necesitará para cualquier consulta en la OIRS.</p>
		<?php if ( in_array( $resultado['tipo'], DSM_OIRS_TIPOS_CON_CONTACTO, true ) ) : ?>
			<p>Recibirá una respuesta a más tardar el <strong><?php echo esc_html( dsm_oirs_fecha_larga( $resultado['vencimiento'] ) ); ?></strong>
				(15 días hábiles, Ley N.° 20.584).</p>
		<?php endif; ?>
		<p class="oirs-acciones">
			<button type="button" class="oirs-boton oirs-boton--secundario" data-oirs-imprimir>Imprimir comprobante</button>
			<a class="oirs-enlace" href="<?php echo esc_url( get_permalink() ); ?>">Enviar otra solicitud</a>
		</p>
	</div>
</div>
