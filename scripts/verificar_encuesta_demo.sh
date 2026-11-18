#!/bin/sh
# Verifica la encuesta servida por Nginx sin WordPress (despliegue/encuesta-demo) y deja la evidencia en
# evidencias/es3/encuesta_nginx.txt. Envía una respuesta real de prueba. Al terminar reinicia el contenedor
# para limpiar el contador del límite de envíos.
# Uso: ./scripts/verificar_encuesta_demo.sh
set -eu
cd "$(dirname "$0")/.."
. ./.env
U="http://localhost:${ENCUESTA_PUERTO_PUBLICO:-8082}"
case ",${COMPOSE_PROFILES:-}," in
  *,encuesta,*) ;;
  *) echo "La encuesta de demostración no está activada (COMPOSE_PROFILES sin «encuesta»). Use ./scripts/instalar.sh --con-encuesta"; exit 1 ;;
esac
J='Content-Type: application/json'
O=evidencias/es3/encuesta_nginx.txt
c() { printf '%-42s' "$1"; shift; curl -s -w '  → HTTP %{http_code}\n' "$@"; }
mongo() {
  docker compose exec -T mongo sh -c "mongosh -u root -p \"\$MONGO_INITDB_ROOT_PASSWORD\" --quiet --eval '$1'"
}

docker compose restart encuesta >/dev/null 2>&1 && sleep 2
{
echo "# Encuesta servida por Nginx sin WordPress (despliegue/encuesta-demo) — verificación $(date '+%Y-%m-%d %H:%M %Z')"
echo "# $(docker compose exec -T encuesta nginx -v 2>&1) · njs $(docker compose exec -T encuesta njs -v)"
echo; echo "## 1. Cabeceras de seguridad de la página"
curl -s -D - -o /dev/null "$U/" | grep -iE "^(HTTP|content-security|x-frame|x-content|referrer|permissions|server)"
echo; echo "## 2. Preguntas de la versión activa (GET /api/encuesta, firmado por njs)"
curl -s "$U/api/encuesta" | head -c 300; echo " …"
echo; echo "## 3. Establecimientos (GET /api/catalogos: solo código y nombre, sin el DSM)"
curl -s "$U/api/catalogos"; echo

echo; echo "## 4. Casos de envío (POST /api/respuestas)"
antes=$(mongo 'db.getSiblingDB("oirs_plc_docs").respuestas_encuesta.countDocuments()')
c "Respuesta válida" -H "$J" -d '{"establecimiento":"CESFAM-PLC","respuestas":{"p1":6,"p2":6,"p3":7,"p4":6,"p5":7,"p6":"Médica"}}' "$U/api/respuestas"
c "Trampa para bots (honeypot) completada" -H "$J" -d '{"establecimiento":"CESFAM-PLC","respuestas":{"p1":6},"web":"x"}' "$U/api/respuestas"
c "Establecimiento inexistente" -H "$J" -d '{"establecimiento":"NOEXISTE","respuestas":{"p1":6,"p2":6,"p3":7,"p4":6,"p5":7}}' "$U/api/respuestas"
c "Datos personales en las respuestas" -H "$J" -d '{"establecimiento":"CESFAM-PLC","respuestas":{"p1":6,"p2":6,"p3":7,"p4":6,"p5":7,"rut":"1-9"}}' "$U/api/respuestas"
c "JSON mal formado" -H "$J" -d 'xx' "$U/api/respuestas"
c "Envío desde otro sitio (Sec-Fetch-Site)" -H "$J" -H 'Sec-Fetch-Site: cross-site' -d '{}' "$U/api/respuestas"
c "Método GET" "$U/api/respuestas"
c "Ruta de la API no expuesta" -o /dev/null "$U/api/requerimientos"
c "Cuerpo mayor a 8 KB" -o /dev/null -H "$J" --data-binary "{\"comentario\":\"$(head -c 9000 /dev/zero | tr '\0' a)\"}" "$U/api/respuestas"
despues=$(mongo 'db.getSiblingDB("oirs_plc_docs").respuestas_encuesta.countDocuments()')
echo "Respuestas en MongoDB: antes $antes, después $despues (solo se guardó la válida)"

echo; echo "## 5. El secreto HMAC no llega al navegador (apariciones en cada respuesta)"
for f in / /encuesta.js /api/encuesta /api/catalogos; do echo "$f: $(curl -s "$U$f" | grep -c "$WP_HMAC_SECRET" || true)"; done

echo; echo "## 6. Límite de envíos por IP (ráfaga de 10 y luego 1 por minuto): 14 envíos seguidos tras reiniciar"
docker compose restart encuesta >/dev/null 2>&1 && sleep 2
for i in $(seq 1 14); do
  curl -s -o /dev/null -w '%{http_code} ' -H "$J" -d '{"establecimiento":"NOEXISTE","respuestas":{}}' "$U/api/respuestas"
done; echo
curl -s -H "$J" -d '{}' "$U/api/respuestas"; echo

echo; echo "## 7. Registro de accesos sin IP (anonimato). El de errores solo la anota al rechazar un cuerpo excesivo (abuso)"
docker compose logs --no-log-prefix encuesta 2>&1 | grep '"POST /api/respuestas' | tail -3

echo; echo "## 8. Última respuesta guardada en MongoDB (sin IP, sin hora, sin datos personales)"
mongo 'printjson(db.getSiblingDB("oirs_plc_docs").respuestas_encuesta.find({}, {_id: 0}).sort({_id: -1}).limit(1).toArray())'
} > "$O" 2>&1
docker compose restart encuesta >/dev/null 2>&1
cat "$O"
