/* DSM OIRS – mejora progresiva: el formulario funciona sin JavaScript (el servidor valida siempre). */
( function () {
	'use strict';
	// Enfoca el resumen de errores o la confirmación para que los lectores de pantalla los anuncien.
	var foco = document.getElementById( 'oirs-resumen' ) || document.querySelector( '.oirs-confirmacion' );
	if ( foco ) { foco.focus(); }

	// Adapta la sección de contacto al tipo elegido (obligatoria para reclamo, consulta y solicitud).
	var form = document.querySelector( '[data-oirs-form="requerimiento"]' );
	if ( form ) {
		var actualizar = function () {
			var elegido = form.querySelector( 'input[name="tipo"]:checked' );
			if ( ! elegido ) { return; }
			var obligatorio = elegido.getAttribute( 'data-contacto' ) === '1';
			form.querySelectorAll( '[data-si-contacto],[data-req-contacto]' ).forEach( function ( el ) { el.hidden = ! obligatorio; } );
			form.querySelectorAll( '[data-no-contacto]' ).forEach( function ( el ) {
				el.hidden = obligatorio;
				el.textContent = 'Opcionales: puede enviar su ' + elegido.parentNode.querySelector( '.oirs-tipo__nombre' ).textContent.toLowerCase() + ' sin identificarse.';
			} );
		};
		form.addEventListener( 'change', function ( e ) { if ( e.target.name === 'tipo' ) { actualizar(); } } );
		actualizar();
	}

	document.querySelectorAll( '[data-oirs-imprimir]' ).forEach( function ( b ) {
		b.addEventListener( 'click', function () { window.print(); } );
	} );
}() );
