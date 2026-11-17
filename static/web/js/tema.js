/* Tema oscuro automático según la preferencia del sistema (sección 5.4). Se carga en <head> para evitar parpadeo. */
(function () {
  var oscuro = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
  function aplicar() { document.documentElement.setAttribute('data-bs-theme', oscuro && oscuro.matches ? 'dark' : 'light'); }
  aplicar();
  if (oscuro && oscuro.addEventListener) { oscuro.addEventListener('change', aplicar); }
}());
