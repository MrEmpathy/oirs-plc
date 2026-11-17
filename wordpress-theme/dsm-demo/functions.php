<?php
/** Tema esqueleto para la demostración: registra el menú y la hoja de estilos. */
defined( 'ABSPATH' ) || exit;

add_action( 'after_setup_theme', function () {
	add_theme_support( 'title-tag' );
	register_nav_menus( array( 'principal' => 'Menú principal' ) );
} );

add_action( 'wp_enqueue_scripts', function () {
	wp_enqueue_style( 'dsm-demo', get_stylesheet_uri(), array(), '1.0.0' );
} );
