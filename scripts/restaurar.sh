#!/bin/sh
# Restaura un respaldo creado por respaldo.sh (prueba mensual de restauración, sección 4.5).
# Uso: ./scripts/restaurar.sh respaldos/AAAAMMDD-HHMMSS [--confirmar]
#  Sin --confirmar solo verifica integridad (SHA-256) y que el archivo se pueda descifrar y leer.
#  Con --confirmar REEMPLAZA los datos actuales de PostgreSQL y de la base documental.
set -eu
cd "$(dirname "$0")/.."
ORIGEN=${1:?Indique la carpeta del respaldo}
RESPALDO_CLAVE=$(grep '^RESPALDO_CLAVE=' .env | cut -d= -f2-)
export RESPALDO_CLAVE
descifrar() { openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:RESPALDO_CLAVE -in "$1"; }

( cd "$ORIGEN" && sha256sum -c SHA256SUMS )
descifrar "$ORIGEN/postgres_oirs_plc.dump.enc" | docker compose exec -T postgres pg_restore --list >/dev/null
echo "· PostgreSQL: respaldo legible ($(descifrar "$ORIGEN/postgres_oirs_plc.dump.enc" | docker compose exec -T postgres pg_restore --list | grep -c 'TABLE DATA') tablas con datos)."
descifrar "$ORIGEN/mongo_oirs_plc_docs.archive.gz.enc" | gzip -t && echo "· Base documental: archivo íntegro."

if [ "${2:-}" != "--confirmar" ]; then
  echo "Verificación completada. Para restaurar de verdad agregue --confirmar."
  exit 0
fi
docker compose stop app
descifrar "$ORIGEN/postgres_oirs_plc.dump.enc" | docker compose exec -T postgres pg_restore -U postgres -d oirs_plc --clean --if-exists
descifrar "$ORIGEN/mongo_oirs_plc_docs.archive.gz.enc" | docker compose exec -T mongo sh -c 'mongorestore --quiet --username root \
  --password "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --nsInclude "oirs_plc_docs.*" --drop --archive --gzip'
docker compose start app
echo "Restauración completada desde $ORIGEN."
