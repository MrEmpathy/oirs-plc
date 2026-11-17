/* Comportamientos comunes. Sin JavaScript en línea: compatible con la CSP script-src 'self'. */
(function () {
  'use strict';
  // Anuncia y enfoca el primer resumen de errores para lectores de pantalla.
  var foco = document.querySelector('[data-enfocar]');
  if (foco) { foco.focus(); }
  // Reabre el diálogo cuyo formulario volvió con errores de validación.
  document.querySelectorAll('.modal[data-abrir]').forEach(function (m) { bootstrap.Modal.getOrCreateInstance(m).show(); });
  // Lleva el foco al primer campo al abrir un diálogo.
  document.querySelectorAll('.modal').forEach(function (m) {
    m.addEventListener('shown.bs.modal', function () {
      var campo = m.querySelector('.is-invalid, input:not([type=hidden]), select, textarea');
      if (campo) { campo.focus(); }
    });
  });
  document.querySelectorAll('[data-imprimir]').forEach(function (b) { b.addEventListener('click', function () { window.print(); }); });
}());
