<?php
/** Portada: tres accesos destacados (OIRS, encuesta, establecimientos), como en el prototipo v2 (sección 5.2). */
defined( 'ABSPATH' ) || exit;
get_header();
$url = fn( string $slug ) => esc_url( home_url( '/' . $slug . '/' ) );
?>
<section class="portada">
	<div class="contenedor">
		<h1>Salud para toda la comuna</h1>
		<p>Red de atención primaria de Padre Las Casas: CESFAM, CECOSF, postas rurales y SAPU.</p>
		<div class="accesos">
			<a class="acceso" href="<?php echo $url( 'oirs' ); // phpcs:ignore ?>"><strong>OIRS en línea</strong>Reclamos, sugerencias, consultas, solicitudes y felicitaciones.</a>
			<a class="acceso" href="<?php echo $url( 'encuesta-de-satisfaccion' ); // phpcs:ignore ?>"><strong>Evalúe su atención</strong>Encuesta de satisfacción anónima, en menos de 2 minutos.</a>
			<a class="acceso" href="<?php echo $url( 'establecimientos' ); // phpcs:ignore ?>"><strong>Establecimientos</strong>Direcciones y horarios de la red de salud.</a>
		</div>
	</div>
</section>
<section class="contenido">
	<div class="contenedor">
		<h2>Noticias</h2>
		<div class="noticias">
			<?php
			$q = new WP_Query( array( 'posts_per_page' => 3 ) );
			while ( $q->have_posts() ) :
				$q->the_post();
				?>
				<article class="noticia"><h3><?php the_title(); ?></h3><?php the_excerpt(); ?></article>
				<?php
			endwhile;
			wp_reset_postdata();
			?>
		</div>
	</div>
</section>
<?php
get_footer();
