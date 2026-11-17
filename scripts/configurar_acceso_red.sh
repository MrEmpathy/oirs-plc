#!/bin/sh
# Habilita el acceso desde otros equipos de la red con un nombre (y, opcionalmente, IPs) además de localhost.
# Actualiza el .env (hosts permitidos y orígenes CSRF), renueva el certificado del servidor con esos nombres
# (misma CA local, no hay que volver a importarla) y cambia la dirección pública de WordPress.
# Uso: ./scripts/configurar_acceso_red.sh ls.local 192.168.1.191
set -eu
cd "$(dirname "$0")/.."
NOMBRE=${1:?Indique el nombre público, por ejemplo: ls.local}
shift
EXTRAS="$*"
. ./.env
P_HTTPS=${OIRS_HTTPS_PUERTO_PUBLICO:-8443}
P_WP=${WP_PUERTO_PUBLICO:-8080}

# 1. Hosts permitidos y orígenes de confianza para CSRF
HOSTS="localhost,127.0.0.1,nginx,$NOMBRE"
ORIGENES="https://localhost:$P_HTTPS,https://127.0.0.1:$P_HTTPS,https://$NOMBRE:$P_HTTPS"
for x in $EXTRAS; do HOSTS="$HOSTS,$x"; ORIGENES="$ORIGENES,https://$x:$P_HTTPS"; done
fijar() { # variable valor
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
fijar DJANGO_ALLOWED_HOSTS "$HOSTS"
fijar DJANGO_CSRF_TRUSTED_ORIGINS "$ORIGENES"
fijar OIRS_NOMBRE_PUBLICO "$NOMBRE"
echo "· .env actualizado: $HOSTS"

# 2. Certificado del servidor con los nuevos nombres (firmado por la CA local existente)
CERTS=despliegue/certs
SAN="DNS:localhost,DNS:nginx,IP:127.0.0.1,DNS:$NOMBRE"
for x in $EXTRAS; do
  case "$x" in *[!0-9.]*) SAN="$SAN,DNS:$x" ;; *) SAN="$SAN,IP:$x" ;; esac
done
openssl req -newkey rsa:2048 -nodes -subj "/CN=$NOMBRE" -keyout "$CERTS/servidor.key" -out "$CERTS/servidor.csr" 2>/dev/null
printf "subjectAltName=%s\nextendedKeyUsage=serverAuth\n" "$SAN" > "$CERTS/ext.cnf"
openssl x509 -req -in "$CERTS/servidor.csr" -CA "$CERTS/ca.crt" -CAkey "$CERTS/ca.key" -CAcreateserial \
        -days 825 -extfile "$CERTS/ext.cnf" -out "$CERTS/servidor.crt" 2>/dev/null
rm -f "$CERTS/servidor.csr" "$CERTS/ext.cnf"
chmod 600 "$CERTS/servidor.key"; chmod 644 "$CERTS/servidor.crt"
echo "· Certificado renovado para: $SAN"

# 3. Servicios que leen esa configuración
docker compose up -d --force-recreate app nginx wordpress >/dev/null 2>&1
WP_URL="http://$NOMBRE:$P_WP"
docker compose --profile herramientas run --rm -T wpcli sh -c \
  "wp option update home '$WP_URL' && wp option update siteurl '$WP_URL' && wp menu item list Principal --fields=db_id,link --format=csv" \
  2>/dev/null | grep -E '^[0-9]+,http' | while IFS=, read -r id enlace; do
    case "$enlace" in http://localhost:*/|http://*:"$P_WP"/) \
      docker compose --profile herramientas run --rm -T wpcli wp menu item update "$id" --link="$WP_URL/" >/dev/null 2>&1 ;; esac
  done
echo "Listo:"
echo "  Ciudadanos:    $WP_URL"
echo "  Funcionarios:  https://$NOMBRE:$P_HTTPS   (importe $CERTS/ca.crt en el navegador para evitar la advertencia)"
