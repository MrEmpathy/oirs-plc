#!/bin/sh
# Instala y configura el WordPress de demostración con WP-CLI (idempotente).
# Reproduce lo que haría la Municipalidad en su sitio: activar el plugin y publicar las páginas con los shortcodes.
# Uso: ./scripts/instalar_wordpress.sh        (requiere: docker compose up -d)
set -eu
cd "$(dirname "$0")/.."
. ./.env

WP_URL="http://${OIRS_NOMBRE_PUBLICO:-localhost}:${WP_PUERTO_PUBLICO:-8080}"
wp() { docker compose --profile herramientas run --rm -T wpcli wp "$@"; }

echo "· Esperando a WordPress…"
i=0
until wp core is-installed >/dev/null 2>&1 || wp db check >/dev/null 2>&1; do
  i=$((i + 1)); [ "$i" -gt 30 ] && { echo "WordPress no responde"; exit 1; }; sleep 3
done

if ! wp core is-installed >/dev/null 2>&1; then
  WP_ADMIN_CLAVE=$(openssl rand -base64 18)
  wp core install --url="$WP_URL" --title="Departamento de Salud Municipal – Padre Las Casas (demo)" \
     --admin_user=admin_wp --admin_password="$WP_ADMIN_CLAVE" --admin_email=admin@dsm.test --skip-email
  echo "WP_ADMIN_CLAVE=$WP_ADMIN_CLAVE" >> .env
  echo "· WordPress instalado. Usuario admin_wp (contraseña guardada en .env como WP_ADMIN_CLAVE)."
fi

wp option update blogdescription "Sitio de demostración" >/dev/null
wp option update timezone_string "America/Santiago" >/dev/null
wp option update date_format "d-m-Y" >/dev/null
wp language core install es_CL --activate >/dev/null 2>&1 || echo "  (sin paquete de idioma es_CL: se mantiene el idioma base)"
wp rewrite structure '/%postname%/' --hard >/dev/null
wp theme activate dsm-demo >/dev/null
wp plugin activate dsm-oirs-formularios >/dev/null
echo "· Tema dsm-demo y plugin DSM OIRS activos."

pagina() { # slug, título, contenido
  id=$(wp post list --post_type=page --name="$1" --field=ID)
  if [ -z "$id" ]; then
    id=$(wp post create --post_type=page --post_status=publish --post_name="$1" --post_title="$2" --post_content="$3" --porcelain)
  fi
  echo "$id"
}

P_OIRS=$(pagina oirs "OIRS en línea" '<!-- wp:paragraph --><p>La Oficina de Informaciones, Reclamos y Sugerencias recibe sus reclamos, sugerencias, consultas, solicitudes y felicitaciones sobre la atención en la red de salud comunal.</p><!-- /wp:paragraph --><!-- wp:shortcode -->[oirs_formulario]<!-- /wp:shortcode -->')
P_ENC=$(pagina encuesta-de-satisfaccion "Encuesta de satisfacción" '<!-- wp:paragraph --><p>Cuéntenos cómo fue su atención. Sus respuestas son anónimas.</p><!-- /wp:paragraph --><!-- wp:shortcode -->[oirs_encuesta]<!-- /wp:shortcode -->')
P_EST=$(pagina establecimientos "Establecimientos" '<!-- wp:list --><ul><li>CESFAM Padre Las Casas</li><li>CESFAM Pulmahue</li><li>CESFAM Conunhuenu</li><li>SAPU Padre Las Casas</li><li>Postas de salud rural</li></ul><!-- /wp:list --><!-- wp:paragraph --><p>Contenido de ejemplo administrado por la Unidad de Comunicaciones.</p><!-- /wp:paragraph -->')
echo "· Páginas: OIRS ($P_OIRS), Encuesta ($P_ENC), Establecimientos ($P_EST)."

if ! wp menu list --fields=name --format=csv | grep -q "^Principal$"; then
  wp menu create "Principal" >/dev/null
  wp menu item add-custom Principal "Inicio" "$WP_URL/" >/dev/null
  wp menu item add-post Principal "$P_OIRS" >/dev/null
  wp menu item add-post Principal "$P_ENC" >/dev/null
  wp menu item add-post Principal "$P_EST" >/dev/null
  wp menu location assign Principal principal >/dev/null
fi

if [ "$(wp post list --post_type=post --format=count)" -lt 3 ]; then
  wp post delete 1 --force >/dev/null 2>&1 || true
  for t in "Campaña de vacunación de invierno" "Nuevo horario de extensión en CESFAM Pulmahue" "Operativo de salud rural"; do
    wp post create --post_status=publish --post_title="$t" --post_content="Noticia de ejemplo para la demostración." >/dev/null
  done
fi

# Rol «Editor» para la Unidad de Comunicaciones (RF12): publica contenidos, no instala plugins (sección 7.1).
if ! wp user get comunicaciones >/dev/null 2>&1; then
  wp user create comunicaciones comunicaciones@dsm.test --role=editor --user_pass="$(openssl rand -base64 18)" >/dev/null
  echo "· Usuario «comunicaciones» (Editor) creado."
fi

echo "Listo: $WP_URL  ·  Administración: $WP_URL/wp-admin  ·  Ajustes → DSM OIRS → Probar conexión"
