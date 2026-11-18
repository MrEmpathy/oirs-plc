#!/bin/sh
# Instalación completa en un equipo Linux con un solo comando: revisa requisitos, prepara el .env y los
# certificados, construye y levanta los servicios, espera a que la API esté sana, instala el WordPress de
# demostración y, si se pide, habilita el acceso desde la red. Puede ejecutarse de nuevo sin perder datos.
#
# Uso:  ./scripts/instalar.sh [opciones]
#   --sin-encuesta        No levantar la encuesta de demostración servida por Nginx (puerto 8082)
#   --con-encuesta        Levantarla (valor por defecto en una instalación nueva)
#   --nombre NOMBRE       Nombre con que otros equipos de la red llegarán al servidor (ej.: ls.local)
#   --ip IP               IP adicional aceptada (puede repetirse); requiere --nombre
#   --red                 Igual que --nombre "$(hostname).local" --ip <IP principal del equipo>
#   --instalar-docker     Si falta Docker, instalarlo desde el repositorio oficial (Debian, Ubuntu, Raspberry Pi OS)
#   --ayuda               Muestra esta ayuda
# Puertos (solo en la primera instalación): OIRS_HTTPS_PUERTO_PUBLICO=9443 WP_PUERTO_PUBLICO=9080 … ./scripts/instalar.sh
set -eu
cd "$(dirname "$0")/.."
RAIZ=$(pwd)
LOG="$RAIZ/instalacion.log"

ENCUESTA=""            # "", "si" o "no" ("" = conservar lo que diga el .env)
NOMBRE=""
IPS=""
RED=0
INSTALAR_DOCKER=0

ayuda() { sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; }
paso() { printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
ok() { printf '  ✓ %s\n' "$*"; }
aviso() { printf '  ! %s\n' "$*"; }
fallar() { printf '\n  ✗ %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --sin-encuesta) ENCUESTA=no ;;
    --con-encuesta) ENCUESTA=si ;;
    --nombre) [ $# -ge 2 ] || fallar "--nombre necesita un valor"; NOMBRE=$2; shift ;;
    --ip) [ $# -ge 2 ] || fallar "--ip necesita un valor"; IPS="$IPS $2"; shift ;;
    --red) RED=1 ;;
    --instalar-docker) INSTALAR_DOCKER=1 ;;
    -h|--ayuda|--help) ayuda; exit 0 ;;
    *) fallar "Opción desconocida: $1 (use --ayuda)" ;;
  esac
  shift
done
if [ "$RED" = 1 ]; then
  [ -n "$NOMBRE" ] || NOMBRE="$(hostname).local"
  ip_principal=$(hostname -I 2>/dev/null | awk '{print $1}')
  [ -n "$ip_principal" ] && IPS="$IPS $ip_principal"
fi
[ -n "$IPS" ] && [ -z "$NOMBRE" ] && fallar "--ip requiere --nombre (o use --red)"

# Si algo falla, se muestran las últimas líneas del registro detallado.
: > "$LOG"
terminar() {
  codigo=$?
  if [ "$codigo" -ne 0 ]; then
    printf '\nLa instalación se detuvo. Últimas líneas de %s:\n' "$LOG" >&2
    tail -n 25 "$LOG" >&2 || true
  fi
}
trap terminar EXIT
registrar() { "$@" >>"$LOG" 2>&1; }   # ejecuta un comando y guarda su salida en el registro

# ------------------------------------------------------------------------------------------------------
paso "1/6 Requisitos del equipo"
[ "$(uname -s)" = Linux ] || fallar "Este instalador es para Linux."
for c in openssl curl awk sed grep; do
  command -v "$c" >/dev/null 2>&1 || fallar "Falta «$c». En Debian/Ubuntu: sudo apt install $c"
done
ok "Herramientas básicas: openssl, curl"

instalar_docker() {
  [ -r /etc/os-release ] || fallar "No se reconoce la distribución: instale Docker manualmente (docs.docker.com/engine/install)."
  . /etc/os-release
  case "${ID:-}" in
    debian|ubuntu|raspbian) ;;
    *) fallar "Instalación automática solo en Debian, Ubuntu o Raspberry Pi OS (este equipo: ${ID:-?}). Vea docs.docker.com/engine/install" ;;
  esac
  command -v sudo >/dev/null 2>&1 || fallar "Se necesita sudo para instalar Docker."
  echo "  Instalando Docker Engine y Compose v2 desde download.docker.com (puede pedir su contraseña)…"
  sudo apt-get update -qq >>"$LOG" 2>&1
  sudo apt-get install -y -qq ca-certificates curl >>"$LOG" 2>&1
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$ID ${VERSION_CODENAME:?} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -qq >>"$LOG" 2>&1
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >>"$LOG" 2>&1
  sudo usermod -aG docker "$(id -un)"
  ok "Docker instalado; el usuario $(id -un) se agregó al grupo docker"
}

if ! command -v docker >/dev/null 2>&1; then
  if [ "$INSTALAR_DOCKER" = 0 ] && [ -t 0 ]; then
    printf '  Docker no está instalado. ¿Instalarlo ahora desde el repositorio oficial? [s/N] '
    read -r r; case "$r" in s|S|si|SI|sí) INSTALAR_DOCKER=1 ;; esac
  fi
  [ "$INSTALAR_DOCKER" = 1 ] || fallar "Docker no está instalado. Repita con --instalar-docker o vea docs.docker.com/engine/install"
  instalar_docker
fi

if ! docker info >/dev/null 2>&1; then
  if id -nG | tr ' ' '\n' | grep -qx docker || ! getent group docker | grep -q "[:,]$(id -un)\(,\|$\)"; then
    fallar "No se puede usar Docker: revise que el servicio esté activo (sudo systemctl start docker)."
  fi
  # Recién agregado al grupo docker: se continúa en una sesión con ese grupo, sin cerrar sesión.
  aviso "Continuando con el grupo docker recién asignado…"
  trap - EXIT
  exec sg docker -c "sh '$0' $*"
fi
v=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 0)
[ "${v%%.*}" -ge 24 ] 2>/dev/null || fallar "Se requiere Docker 24 o superior (instalado: $v)."
docker compose version >/dev/null 2>&1 || fallar "Falta Docker Compose v2 (paquete docker-compose-plugin)."
ok "Docker $v · Compose $(docker compose version --short)"

# MongoDB 7 exige instrucciones que algunos procesadores no tienen: se avisa antes de descargar nada.
case "$(uname -m)" in
  aarch64|arm64)
    grep -qw atomics /proc/cpuinfo || fallar "MongoDB 7 requiere ARMv8.2-A (p. ej. Raspberry Pi 5). Este procesador no lo soporta (Raspberry Pi 4 o anterior)." ;;
  x86_64|amd64)
    grep -qw avx /proc/cpuinfo || fallar "MongoDB 7 requiere un procesador con AVX." ;;
  *) fallar "Arquitectura no soportada: $(uname -m) (se requiere x86_64 o arm64)." ;;
esac
ok "Procesador $(uname -m) compatible con MongoDB 7"

mem_mb=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
disco_gb=$(df -Pk "$RAIZ" | awk 'NR==2 {print int($4/1048576)}')
[ "$mem_mb" -ge 3500 ] && ok "Memoria: $mem_mb MB" || aviso "Memoria: $mem_mb MB (se recomiendan 4 GB; puede funcionar lento)"
# Las imágenes ocupan unos 2,5 GB más la compilación: si ya están descargadas basta con 1 GB para los datos.
faltan=0
for img in $(awk '$1 == "image:" {print $2}' docker-compose.yml | grep -v '^oirs-plc/' | sort -u); do   # sin leer el .env
  docker image inspect "$img" >/dev/null 2>&1 || faltan=$((faltan + 1))
done
minimo=1; [ "$faltan" -gt 0 ] && minimo=6
[ "$disco_gb" -ge "$minimo" ] && ok "Disco libre: $disco_gb GB (imágenes por descargar: $faltan)" \
  || fallar "Disco libre: $disco_gb GB; se necesitan $minimo GB (imágenes por descargar: $faltan)."

# ------------------------------------------------------------------------------------------------------
paso "2/6 Configuración (.env) y certificados"
nuevo=0; [ -f .env ] || nuevo=1
registrar ./scripts/preparar_entorno.sh
. ./.env
fijar() { # variable valor: cambia o agrega una línea del .env
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
case "$ENCUESTA" in
  si) fijar COMPOSE_PROFILES encuesta ;;
  no) fijar COMPOSE_PROFILES "" ;;
  *) grep -q '^COMPOSE_PROFILES=' .env || fijar COMPOSE_PROFILES encuesta ;;   # .env anterior a la opción
esac
. ./.env
case ",${COMPOSE_PROFILES:-}," in *,encuesta,*) CON_ENCUESTA=1 ;; *) CON_ENCUESTA=0 ;; esac
P_HTTPS=${OIRS_HTTPS_PUERTO_PUBLICO:-8443}; P_HTTP=${OIRS_HTTP_PUERTO_PUBLICO:-8081}
P_WP=${WP_PUERTO_PUBLICO:-8080}; P_ENC=${ENCUESTA_PUERTO_PUBLICO:-8082}
[ "$nuevo" = 1 ] && ok ".env creado con secretos aleatorios" || ok ".env existente conservado"
[ "$CON_ENCUESTA" = 1 ] && ok "Encuesta de demostración en Nginx: incluida (puerto $P_ENC)" \
                        || ok "Encuesta de demostración en Nginx: no incluida"

# Puertos: solo se revisan si esta instalación aún no está en marcha (si lo está, los ocupa ella misma).
if [ -z "$(docker compose ps -q 2>/dev/null)" ] && command -v ss >/dev/null 2>&1; then
  puertos="$P_HTTPS $P_HTTP $P_WP"; [ "$CON_ENCUESTA" = 1 ] && puertos="$puertos $P_ENC"
  for p in $puertos; do
    ss -ltnH "sport = :$p" | grep -q . && fallar "El puerto $p está ocupado. Use otros, por ejemplo: OIRS_HTTPS_PUERTO_PUBLICO=9443 OIRS_HTTP_PUERTO_PUBLICO=9081 WP_PUERTO_PUBLICO=9080 ENCUESTA_PUERTO_PUBLICO=9082 $0 (solo en una instalación nueva: borre antes el .env)"
  done
  ok "Puertos libres: $puertos"
fi

# ------------------------------------------------------------------------------------------------------
paso "3/6 Construcción y arranque de los servicios (la primera vez puede tardar varios minutos)"
registrar docker compose up -d --build --remove-orphans
if [ "$CON_ENCUESTA" = 0 ]; then
  registrar docker compose --profile encuesta rm -sf encuesta || true   # por si quedó de una instalación anterior
fi
ok "Servicios en marcha: $(docker compose ps --services --status running | tr '\n' ' ')"

printf '  Esperando a la API'
i=0
until curl -fsS --cacert despliegue/certs/ca.crt "https://localhost:$P_HTTPS/api/v1/salud" 2>/dev/null | grep -q '"estado": *"ok"'; do
  i=$((i + 1)); [ "$i" -gt 60 ] && { echo; docker compose logs --tail 40 migrar app >>"$LOG" 2>&1; fallar "La API no respondió en 5 minutos."; }
  printf '.'; sleep 5
done
echo; ok "API sana: https://localhost:$P_HTTPS/api/v1/salud (PostgreSQL y MongoDB en «ok»)"

# ------------------------------------------------------------------------------------------------------
paso "4/6 WordPress de demostración con el plugin"
registrar ./scripts/instalar_wordpress.sh
ok "WordPress instalado; páginas «OIRS en línea», «Encuesta de satisfacción» y «Establecimientos»"

# ------------------------------------------------------------------------------------------------------
paso "5/6 Acceso desde la red"
if [ -n "$NOMBRE" ]; then
  # shellcheck disable=SC2086
  registrar ./scripts/configurar_acceso_red.sh "$NOMBRE" $IPS
  . ./.env
  ok "Acepta conexiones como: $NOMBRE$IPS"
elif [ -n "${OIRS_NOMBRE_PUBLICO:-}" ]; then
  ok "Se conserva el acceso ya configurado: $DJANGO_ALLOWED_HOSTS"
else
  ok "Solo localhost (para otros equipos: --nombre NOMBRE [--ip IP] o --red)"
fi
HOST=${OIRS_NOMBRE_PUBLICO:-localhost}

# ------------------------------------------------------------------------------------------------------
paso "6/6 Verificación final"
codigo=$(curl -s -o /dev/null -w '%{http_code}' --cacert despliegue/certs/ca.crt "https://localhost:$P_HTTPS/ingresar")
[ "$codigo" = 200 ] && ok "Página de ingreso de funcionarios: 200" || fallar "La página de ingreso respondió $codigo."
codigo=$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $HOST:$P_WP" "http://localhost:$P_WP/oirs/")
[ "$codigo" = 200 ] && ok "Formulario OIRS en WordPress: 200" || fallar "WordPress respondió $codigo."
if [ "$CON_ENCUESTA" = 1 ]; then
  i=0
  until curl -fsS "http://localhost:$P_ENC/api/encuesta" 2>/dev/null | grep -q '"preguntas"'; do
    i=$((i + 1)); [ "$i" -gt 12 ] && fallar "La encuesta de demostración no responde."
    sleep 5
  done
  ok "Encuesta en Nginx: preguntas firmadas y leídas desde la API"
fi

trap - EXIT
cat <<EOF

────────────────────────────────────────────────────────────────────────
 Instalación completa
────────────────────────────────────────────────────────────────────────
 Funcionarios (Sistema OIRS):   https://$HOST:$P_HTTPS
 Ciudadanos (WordPress demo):   http://$HOST:$P_WP
EOF
[ "$CON_ENCUESTA" = 1 ] && echo " Encuesta sin WordPress:        http://$HOST:$P_ENC/?est=CESFAM-PLC"
cat <<EOF

 Usuarios de demostración: admin@dsm.test, oirs.dsm@dsm.test, oirs.plc@dsm.test,
 oirs.pul@dsm.test y dir.plc@dsm.test. Contraseña inicial: $CLAVE_DEMO
 (se pide cambiarla en el primer ingreso; admin y oirs.dsm registran además el segundo factor).

 Certificado: el navegador mostrará una advertencia porque la CA es local. Para evitarla, importe
 $RAIZ/despliegue/certs/ca.crt como autoridad de confianza.

 Detener: docker compose stop · Ver registros: docker compose logs -f app · Detalle: $LOG
EOF
