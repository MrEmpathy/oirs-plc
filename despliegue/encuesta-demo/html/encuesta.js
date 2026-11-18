/* Encuesta de demostración sin WordPress: dibuja las preguntas de la versión activa (leídas de la API a través
   de Nginx) con el mismo marcado y las mismas clases que plantillas/encuesta.php del plugin. Todo el texto
   se inserta con textContent (nunca innerHTML), por lo que los datos no se interpretan como HTML. */
( function () {
	'use strict';
	var raiz = document.getElementById( 'oirs-encuesta' );

	function el( etiqueta, atributos, texto ) {
		var nodo = document.createElement( etiqueta );
		Object.keys( atributos || {} ).forEach( function ( k ) { nodo.setAttribute( k, atributos[ k ] ); } );
		if ( texto !== undefined ) { nodo.textContent = texto; }
		return nodo;
	}

	function obtener( url ) {
		return fetch( url, { headers: { Accept: 'application/json' } } ).then( function ( r ) {
			return r.json().then( function ( d ) { if ( ! r.ok ) { throw new Error( d.error || 'Error' ); } return d; } );
		} );
	}

	function aviso( mensaje, detalle ) {
		var caja = el( 'div', { 'class': 'oirs-aviso oirs-aviso--error', role: 'alert', tabindex: '-1', id: 'oirs-resumen' } );
		var p = el( 'p' );
		p.appendChild( el( 'strong', {}, mensaje ) );
		caja.appendChild( p );
		( detalle || [] ).forEach( function ( d ) { caja.appendChild( el( 'p', {}, d ) ); } );
		return caja;
	}

	function error( campo, id, mensaje ) {
		campo.setAttribute( 'aria-invalid', 'true' );
		campo.setAttribute( 'aria-describedby', 'oirs-err-' + id );
		return el( 'p', { 'class': 'oirs-campo__error', id: 'oirs-err-' + id }, mensaje );
	}

	function limpiarErrores( form ) {
		form.querySelectorAll( '.oirs-campo__error' ).forEach( function ( n ) { n.remove(); } );
		form.querySelectorAll( '[aria-invalid]' ).forEach( function ( n ) {
			n.removeAttribute( 'aria-invalid' );
			n.removeAttribute( 'aria-describedby' );
		} );
	}

	function dibujar( def, establecimientos ) {
		var preseleccion = new URLSearchParams( location.search ).get( 'est' ) || '';  // código QR del establecimiento
		raiz.textContent = '';
		raiz.appendChild( el( 'p', { 'class': 'oirs-nota' },
			'Encuesta anónima: no le pediremos su nombre ni datos de contacto. Escala de 1 (muy malo) a 7 (muy bueno).' ) );

		var form = el( 'form', { 'class': 'oirs-form', novalidate: '', 'data-oirs-form': 'encuesta' } );
		var hp = el( 'p', { 'class': 'oirs-hp', 'aria-hidden': 'true' } );
		var hpl = el( 'label', {}, 'No completar ' );
		hpl.appendChild( el( 'input', { type: 'text', name: 'web', tabindex: '-1', autocomplete: 'off' } ) );
		hp.appendChild( hpl );
		form.appendChild( hp );

		var cEst = el( 'div', { 'class': 'oirs-campo', 'data-campo': 'establecimiento' } );
		var lEst = el( 'label', { 'for': 'oirs-establecimiento' }, 'Establecimiento donde se atendió ' );
		lEst.appendChild( el( 'span', { 'class': 'oirs-req', 'aria-hidden': 'true' }, '*' ) );
		var sEst = el( 'select', { id: 'oirs-establecimiento', name: 'establecimiento', required: '' } );
		sEst.appendChild( el( 'option', { value: '' }, 'Seleccione…' ) );
		establecimientos.forEach( function ( e ) {
			var o = el( 'option', { value: e.codigo }, e.nombre );
			if ( e.codigo === preseleccion ) { o.selected = true; }
			sEst.appendChild( o );
		} );
		cEst.appendChild( lEst );
		cEst.appendChild( sEst );
		form.appendChild( cEst );

		def.preguntas.forEach( function ( p, i ) {
			var id = String( p.id );
			var titulo = ( i + 1 ) + '. ' + p.texto;
			if ( p.tipo === 'escala' ) {
				var fs = el( 'fieldset', { 'class': 'oirs-escala', id: 'oirs-' + id, 'data-campo': id } );
				var lg = el( 'legend', {}, titulo + ' ' );
				if ( p.obligatoria ) { lg.appendChild( el( 'span', { 'class': 'oirs-req', 'aria-hidden': 'true' }, '*' ) ); }
				fs.appendChild( lg );
				var ops = el( 'div', { 'class': 'oirs-escala__opciones' } );
				for ( var n = Number( p.min ); n <= Number( p.max ); n++ ) {
					var op = el( 'label', { 'class': 'oirs-escala__opcion' } );
					op.appendChild( el( 'input', { type: 'radio', name: 'p_' + id, value: String( n ) } ) );
					op.appendChild( el( 'span', {}, String( n ) ) );
					ops.appendChild( op );
				}
				fs.appendChild( ops );
				var ext = el( 'p', { 'class': 'oirs-escala__extremos', 'aria-hidden': 'true' } );
				ext.appendChild( el( 'span', {}, 'Muy malo' ) );
				ext.appendChild( el( 'span', {}, 'Muy bueno' ) );
				fs.appendChild( ext );
				fs.dataset.obligatoria = p.obligatoria ? '1' : '';
				fs.dataset.tipo = 'escala';
				form.appendChild( fs );
			} else if ( p.tipo === 'opcion' ) {
				var c = el( 'div', { 'class': 'oirs-campo', 'data-campo': id } );
				c.appendChild( el( 'label', { 'for': 'oirs-' + id }, titulo ) );
				var s = el( 'select', { id: 'oirs-' + id, name: 'p_' + id } );
				s.appendChild( el( 'option', { value: '' }, 'Seleccione…' ) );
				( p.opciones || [] ).forEach( function ( v ) { s.appendChild( el( 'option', { value: String( v ) }, String( v ) ) ); } );
				c.appendChild( s );
				c.dataset.obligatoria = p.obligatoria ? '1' : '';
				form.appendChild( c );
			}
		} );

		var cCom = el( 'div', { 'class': 'oirs-campo' } );
		cCom.appendChild( el( 'label', { 'for': 'oirs-comentario' }, 'Comentario (opcional)' ) );
		cCom.appendChild( el( 'p', { 'class': 'oirs-campo__ayuda', id: 'oirs-ayuda-comentario' },
			'No escriba su nombre, RUT ni datos de contacto: la encuesta es anónima.' ) );
		cCom.appendChild( el( 'textarea', { id: 'oirs-comentario', name: 'comentario', rows: '3', maxlength: '1000',
			'aria-describedby': 'oirs-ayuda-comentario' } ) );
		form.appendChild( cCom );
		form.appendChild( el( 'button', { type: 'submit', 'class': 'oirs-boton' }, 'Enviar respuesta' ) );
		raiz.appendChild( form );

		form.addEventListener( 'submit', function ( ev ) {
			ev.preventDefault();
			enviar( form, def );
		} );
	}

	function enviar( form, def ) {
		var previo = document.getElementById( 'oirs-resumen' );
		if ( previo ) { previo.remove(); }
		limpiarErrores( form );

		var datos = { establecimiento: form.establecimiento.value, respuestas: {}, comentario: form.comentario.value.trim(),
			web: form.web.value };
		var faltan = [];
		if ( ! datos.establecimiento ) {
			form.querySelector( '[data-campo="establecimiento"]' ).appendChild(
				error( form.establecimiento, 'establecimiento', 'Seleccione el establecimiento donde se atendió.' ) );
			faltan.push( form.establecimiento );
		}
		def.preguntas.forEach( function ( p ) {
			var id = String( p.id );
			var marcado = form.querySelector( '[name="p_' + id + '"]:checked' ) || form.querySelector( 'select[name="p_' + id + '"]' );
			var valor = marcado ? marcado.value : '';
			if ( valor === '' ) {
				if ( p.obligatoria ) {
					var contenedor = form.querySelector( '[data-campo="' + id + '"]' );
					contenedor.appendChild( error( contenedor, id, 'Responda esta pregunta.' ) );
					faltan.push( contenedor );
				}
				return;
			}
			datos.respuestas[ id ] = p.tipo === 'escala' ? Number( valor ) : valor;
		} );
		if ( faltan.length ) {
			var a = aviso( 'Faltan respuestas obligatorias.' );
			raiz.insertBefore( a, raiz.firstChild );
			a.focus();
			return;
		}

		var boton = form.querySelector( 'button[type="submit"]' );
		boton.disabled = true;
		boton.textContent = 'Enviando…';
		fetch( '/api/respuestas', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
			body: JSON.stringify( datos ),
		} ).then( function ( r ) {
			return r.json().catch( function () { return {}; } ).then( function ( d ) { return { ok: r.status === 201, d: d }; } );
		} ).then( function ( res ) {
			if ( res.ok ) { return gracias(); }
			var a = aviso( res.d.error || 'No fue posible registrar su respuesta.', res.d.detalle );
			raiz.insertBefore( a, raiz.firstChild );
			a.focus();
			boton.disabled = false;
			boton.textContent = 'Enviar respuesta';
		} ).catch( function () {
			var a = aviso( 'El servicio no está disponible en este momento. Intente más tarde.' );
			raiz.insertBefore( a, raiz.firstChild );
			a.focus();
			boton.disabled = false;
			boton.textContent = 'Enviar respuesta';
		} );
	}

	function gracias() {
		raiz.textContent = '';
		var caja = el( 'div', { 'class': 'oirs-confirmacion', role: 'status', tabindex: '-1', id: 'oirs-resultado' } );
		caja.appendChild( el( 'h2', { 'class': 'oirs-confirmacion__titulo' }, '¡Gracias por su opinión!' ) );
		caja.appendChild( el( 'p', {}, 'Su respuesta es anónima y nos ayuda a mejorar la atención en la red de salud comunal.' ) );
		raiz.appendChild( caja );
		caja.focus();
	}

	Promise.all( [ obtener( '/api/encuesta' ), obtener( '/api/catalogos' ) ] ).then( function ( r ) {
		dibujar( r[ 0 ], r[ 1 ].establecimientos );
	} ).catch( function () {
		raiz.textContent = '';
		raiz.appendChild( aviso( 'La encuesta no está disponible en este momento.' ) );
	} );
}() );
