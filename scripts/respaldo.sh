#!/bin/sh
# Respaldo diario cifrado de PostgreSQL y de la base documental (sección 4.5, regla 3-2-1).
#   - pg_dump (formato custom) y mongodump (archivo comprimido), cifrados con AES-256 (openssl, PBKDF2).
#   - Retención local de 30 días; la copia fuera del servidor se sincroniza aparte (rclone/rsync a otro equipo).
# Uso: ./scripts/respaldo.sh            Cron sugerido:  0 2 * * *  cd /ruta/oirs-plc && ./scripts/respaldo.sh
# Requiere RESPALDO_CLAVE en .env (se genera si no existe). Restaurar: ./scripts/restaurar.sh <carpeta>
set -eu
cd "$(dirname "$0")/.."
if ! grep -q '^RESPALDO_CLAVE=' .env; then
  echo "RESPALDO_CLAVE=$(openssl rand -hex 32)" >> .env
  echo "· Se generó RESPALDO_CLAVE en .env: guárdela también fuera del servidor (sin ella no se puede restaurar)."
fi
RESPALDO_CLAVE=$(grep '^RESPALDO_CLAVE=' .env | cut -d= -f2-)
export RESPALDO_CLAVE
DESTINO="respaldos/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DESTINO"
umask 077
cifrar() { openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass env:RESPALDO_CLAVE -out "$1"; }

docker compose exec -T postgres pg_dump -U postgres -Fc oirs_plc | cifrar "$DESTINO/postgres_oirs_plc.dump.enc"
docker compose exec -T mongo sh -c 'mongodump --quiet --username root --password "$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase admin --db oirs_plc_docs --archive --gzip' | cifrar "$DESTINO/mongo_oirs_plc_docs.archive.gz.enc"

( cd "$DESTINO" && sha256sum ./*.enc > SHA256SUMS )
find respaldos -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +   # retención local: 30 días
echo "Respaldo creado en $DESTINO:"; ls -l "$DESTINO"
