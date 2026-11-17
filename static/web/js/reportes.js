/* Gráficos de reportes con Chart.js 4. Los datos llegan con json_script (sin código en línea).
   Colores: primario institucional para cantidades; cada gráfico tiene su tabla de datos accesible. */
(function () {
  'use strict';
  var nodo = document.getElementById('datos-graficos');
  if (!nodo || !window.Chart) { return; }
  var datos = JSON.parse(nodo.textContent);
  var estilo = getComputedStyle(document.documentElement);
  var primario = estilo.getPropertyValue('--oirs-primario').trim() || '#046bd2';
  var texto = estilo.getPropertyValue('--oirs-texto').trim() || '#334155';
  var borde = estilo.getPropertyValue('--oirs-borde').trim() || '#d1d5db';
  var reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  Chart.defaults.color = texto;
  Chart.defaults.borderColor = borde;
  Chart.defaults.font.family = estilo.getPropertyValue('--bs-body-font-family');
  if (reducido) { Chart.defaults.animation = false; }

  function barras(id, serie, opciones) {
    var lienzo = document.getElementById(id);
    if (!lienzo || !serie || !serie.valores.length) { return; }
    new Chart(lienzo, {
      type: 'bar',
      data: { labels: serie.etiquetas, datasets: [{ data: serie.valores, backgroundColor: primario, borderRadius: 4, maxBarThickness: 36 }] },
      options: Object.assign({ maintainAspectRatio: false, plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }, opciones || {})
    });
  }
  barras('g-tipo', datos.por_tipo);
  barras('g-estado', datos.por_estado);
  barras('g-categoria', datos.por_categoria, { indexAxis: 'y', scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } });
  barras('g-satisfaccion', datos.satisfaccion, { scales: { y: { min: 1, max: 7 } } });
}());
