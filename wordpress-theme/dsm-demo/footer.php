<?php defined( 'ABSPATH' ) || exit; ?>
</main>
<footer class="pie">
	<div class="contenedor">
		<p><strong>Departamento de Salud Municipal de Padre Las Casas</strong><br>Sitio de demostración (no oficial).</p>
		<p>
			<?php if ( defined( 'OIRS_URL_FUNCIONARIOS' ) ) : ?>
				<a href="<?php echo esc_url( OIRS_URL_FUNCIONARIOS ); ?>">Acceso funcionarios (Sistema OIRS)</a>
			<?php endif; ?>
		</p>
	</div>
</footer>
<?php wp_footer(); ?>
</body>
</html>
