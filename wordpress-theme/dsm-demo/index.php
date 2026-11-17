<?php
defined( 'ABSPATH' ) || exit;
get_header();
?>
<div class="contenido">
	<div class="contenedor">
		<?php while ( have_posts() ) : the_post(); ?>
			<article>
				<h1><?php the_title(); ?></h1>
				<?php the_content(); ?>
			</article>
		<?php endwhile; ?>
	</div>
</div>
<?php
get_footer();
