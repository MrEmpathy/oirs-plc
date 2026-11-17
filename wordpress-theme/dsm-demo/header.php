<?php defined( 'ABSPATH' ) || exit; ?>
<!doctype html>
<html <?php language_attributes(); ?>>
<head>
	<meta charset="<?php bloginfo( 'charset' ); ?>">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<p class="demo-aviso">Sitio de demostración académica: representa al sitio del DSM para probar la integración del Sistema de Gestión OIRS. Datos ficticios.</p>
<header class="cabecera">
	<div class="contenedor">
		<a class="marca" href="<?php echo esc_url( home_url( '/' ) ); ?>">
			<img src="<?php echo esc_url( get_template_directory_uri() . '/logo.svg' ); ?>" alt="" width="48" height="48">
			<span><strong>Departamento de Salud Municipal</strong><span>Padre Las Casas</span></span>
		</a>
		<nav aria-label="Menú principal">
			<?php
			wp_nav_menu( array(
				'theme_location' => 'principal',
				'container'      => false,
				'menu_class'     => 'menu',
				'fallback_cb'    => false,
				'depth'          => 1,
			) );
			?>
		</nav>
	</div>
</header>
<main id="contenido">
