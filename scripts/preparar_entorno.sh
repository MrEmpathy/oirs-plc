#!/bin/sh
# Prepara un entorno local reproducible: archivo .env con secretos aleatorios y certificados TLS de desarrollo.
# Es idempotente: no sobrescribe un .env ni certificados existentes.
# Uso: ./scripts/preparar_entorno.sh
set -eu
cd "$(dirname "$0")/.."

aleatorio() { openssl rand -hex "${1:-24}"; }

if [ -f .env ]; then
  echo "· .env ya existe: se conserva."
else
  umask 077
  cat > .env <<EOF
# Generado por scripts/preparar_entorno.sh el $(date +%F). NO versionar (está en .gitignore).
DJANGO_SECRET_KEY=$(aleatorio 32)
DJANGO_DEBUG=0
DJANGO_SECURE=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,nginx
DJANGO_CSRF_TRUSTED_ORIGINS=https://localhost:8443,https://127.0.0.1:8443
DJANGO_CONFIAR_PROXY=1

PG_SUPERUSER_PASSWORD=$(aleatorio)
PG_OWNER_PASSWORD=$(aleatorio)
PG_DB=oirs_plc
PG_USER=oirs_app
PG_PASSWORD=$(aleatorio)
PG_HOST=postgres
PG_SSLMODE=disable

MONGO_ROOT_PASSWORD=$(aleatorio)
MONGO_APP_PASSWORD=__MONGO_APP__
MONGO_URI=mongodb://oirs_app:__MONGO_APP__@mongo:27017/?authSource=admin
MONGO_DB=oirs_plc_docs

REDIS_URL=redis://redis:6379/0
WP_HMAC_SECRET=$(aleatorio 32)
WP_DB_PASSWORD=$(aleatorio)

# Contraseña inicial de los usuarios de demostración (deben cambiarla en el primer ingreso).
CLAVE_DEMO=Demo#Oirs$(aleatorio 3)!
EOF
  mongo_app=$(aleatorio)
  sed -i "s/__MONGO_APP__/${mongo_app}/g" .env
  echo "· .env creado con secretos aleatorios."
fi

CERTS=despliegue/certs
mkdir -p "$CERTS"
if [ -f "$CERTS/servidor.crt" ]; then
  echo "· Certificados ya existen: se conservan."
else
  # CA local de desarrollo: puede importarse en el navegador para evitar la advertencia de certificado.
  openssl req -x509 -newkey rsa:2048 -nodes -days 825 -subj "/CN=CA local OIRS PLC (desarrollo)" \
          -keyout "$CERTS/ca.key" -out "$CERTS/ca.crt" 2>/dev/null
  openssl req -newkey rsa:2048 -nodes -subj "/CN=localhost" \
          -keyout "$CERTS/servidor.key" -out "$CERTS/servidor.csr" 2>/dev/null
  printf "subjectAltName=DNS:localhost,DNS:nginx,IP:127.0.0.1\nextendedKeyUsage=serverAuth\n" > "$CERTS/ext.cnf"
  openssl x509 -req -in "$CERTS/servidor.csr" -CA "$CERTS/ca.crt" -CAkey "$CERTS/ca.key" -CAcreateserial \
          -days 825 -extfile "$CERTS/ext.cnf" -out "$CERTS/servidor.crt" 2>/dev/null
  rm -f "$CERTS/servidor.csr" "$CERTS/ext.cnf"
  chmod 600 "$CERTS/ca.key" "$CERTS/servidor.key"
  echo "· Certificados de desarrollo creados en $CERTS (CA: $CERTS/ca.crt)."
fi

echo "Listo. Siguiente paso: docker compose up -d --build && ./scripts/instalar_wordpress.sh"
