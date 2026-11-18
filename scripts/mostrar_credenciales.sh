#!/bin/sh
# Muestra las credenciales de demostración de ESTA instalación, leídas del .env local (que nunca se versiona).
# Indica además si cada usuario sigue con la contraseña inicial o ya la cambió (consulta a PostgreSQL).
# Uso: ./scripts/mostrar_credenciales.sh                         muestra usuarios y contraseñas
#      ./scripts/mostrar_credenciales.sh --restablecer-comunicaciones
#                                                               nueva contraseña para el Editor de WordPress
# Solo para el entorno de demostración: imprime secretos en la terminal.
set -eu
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "No hay .env: ejecute primero ./scripts/instalar.sh"; exit 1; }
. ./.env

fijar() { # variable valor: cambia o agrega una línea del .env
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}

if [ "${1:-}" = "--restablecer-comunicaciones" ]; then
  nueva="Com#$(openssl rand -hex 6)Aa1"
  docker compose --profile herramientas run --rm -T wpcli wp user update comunicaciones --user_pass="$nueva" \
    --skip-email >/dev/null 2>&1 || { echo "No se pudo actualizar (¿WordPress en marcha?)"; exit 1; }
  fijar WP_COMUNICACIONES_CLAVE "$nueva"
  WP_COMUNICACIONES_CLAVE=$nueva
  echo "Contraseña de «comunicaciones» restablecida y guardada en .env (WP_COMUNICACIONES_CLAVE)."
  echo
elif [ -n "${1:-}" ]; then
  sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
fi

HOST=${OIRS_NOMBRE_PUBLICO:-localhost}

# Estado de cada cuenta: debe_cambiar_clave = true significa que aún usa la contraseña inicial (CLAVE_DEMO).
estado() {
  docker compose exec -T postgres psql -U postgres -d oirs_plc -Atc \
    "select case when not is_active then 'desactivada'
                 when bloqueado_hasta > now() then 'bloqueada temporalmente'
                 when debe_cambiar_clave then 'contraseña inicial'
                 else 'ya la cambió (no se puede recuperar)' end
       || case when mfa_secreto = '' and rol in ('ADMIN','OIRS_DSM') then ' · registrará 2FA al ingresar' else '' end
     from usuario where email='$1';" 2>/dev/null || echo "(base no disponible)"
}

echo "Sistema de Gestión OIRS · https://$HOST:${OIRS_HTTPS_PUERTO_PUBLICO:-8443}"
echo "Contraseña inicial de los usuarios de demostración (CLAVE_DEMO): ${CLAVE_DEMO:-(no definida)}"
echo
printf '  %-20s %-38s %s\n' "Usuario" "Perfil" "Estado"
for fila in "admin@dsm.test|Administrador" "oirs.dsm@dsm.test|Encargado OIRS DSM" \
            "oirs.plc@dsm.test|Encargado OIRS CESFAM Padre Las Casas" "oirs.pul@dsm.test|Encargado OIRS CESFAM Pulmahue" \
            "dir.plc@dsm.test|Dirección CESFAM Padre Las Casas"; do
  correo=${fila%%|*}
  perfil=${fila#*|}
  printf '  %-20s %-38s %s\n' "$correo" "$perfil" "$(estado "$correo")"
done
echo
echo "  Si alguien olvidó la contraseña que eligió: el Administrador abre su ficha en «Usuarios» y usa"
echo "  «Emitir contraseña temporal», o el usuario pulsa «¿Olvidó su contraseña?» en el ingreso (en la demostración"
echo "  el enlace de recuperación queda en: docker compose logs app)."
echo
echo "WordPress de demostración · https://$HOST:${WP_PUERTO_PUBLICO:-8080}/wp-admin"
printf '  %-16s %-14s %s\n' "admin_wp" "Administrador" "${WP_ADMIN_CLAVE:-(no definida: ejecute instalar_wordpress.sh)}"
printf '  %-16s %-14s %s\n' "comunicaciones" "Editor" \
  "${WP_COMUNICACIONES_CLAVE:-(no guardada: use --restablecer-comunicaciones)}"
