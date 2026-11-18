#!/bin/sh
# Evidencias de base de datos para el Informe 3 (criterio 3.1.2): estructura real, escritura y lectura de un caso,
# reglas de integridad probadas con datos inválidos, plan de la consulta de la bandeja y base documental.
# Las pruebas de integridad usan el rol de la aplicación (oirs_app) dentro de transacciones que se revierten:
# no modifican datos. Resultado: evidencias/es3/bd_evidencias.txt
# Uso: ./scripts/evidencias_bd.sh [FOLIO]     (por defecto, el último caso creado desde el sitio web)
set -eu
cd "$(dirname "$0")/.."
. ./.env
O=evidencias/es3/bd_evidencias.txt
sql() { docker compose exec -T postgres psql -U postgres -d oirs_plc "$@"; }
FOLIO=${1:-$(sql -Atc "select folio from requerimiento where canal='WEB' order by id desc limit 1;")}
EST="(select id from establecimiento where codigo='CESFAM-PLC')"
COLS="folio,tipo,canal,establecimiento_id,descripcion,peticion_concreta,fecha_ingreso,fecha_vencimiento,estado"

# Intento inválido como oirs_app: las FK de Django son diferidas (se revisan al confirmar), por eso se fuerzan
# inmediatas. ON_ERROR_STOP detiene en el primer error; si el intento se aceptara, se imprime «ACEPTADO».
intento() {
  printf '%s\n' "$1"
  docker compose exec -T -e PGPASSWORD="$PG_PASSWORD" postgres psql -q -U oirs_app -h 127.0.0.1 -d oirs_plc \
    -v ON_ERROR_STOP=1 -c "begin; set constraints all immediate; $2; select 'ACEPTADO (no debía aceptarse)' as resultado; rollback;" \
    2>&1 | grep -E "ERROR|DETAIL|ACEPTADO" | sed 's/^/   /' || true
}
mongo() { docker compose exec -T mongo sh -c "mongosh -u root -p \"\$MONGO_INITDB_ROOT_PASSWORD\" --quiet --eval '$1'"; }

{
echo "# Evidencias de base de datos — $(date '+%Y-%m-%d %H:%M %Z') — entorno Docker (PostgreSQL 16, MongoDB 7)"
echo; echo "## 1. Tablas de la base estructurada y cantidad de filas (datos ficticios)"
sql -c "select relname as tabla, n_live_tup as filas from pg_stat_user_tables where relname not like 'django_%' and relname not like 'auth_%' order by relname;"
echo "## 2. Restricciones declaradas (PK, FK, UNIQUE, CHECK)"
sql -c "select conrelid::regclass as tabla, conname as restriccion, case contype when 'p' then 'PK' when 'f' then 'FK' when 'u' then 'UNIQUE' when 'c' then 'CHECK' end as tipo, case when contype='f' then (case when condeferrable then 'diferible' else 'inmediata' end) else '' end as verificacion from pg_constraint where conrelid::regclass::text in ('requerimiento','solicitante','usuario','historial_estado','respuesta','derivacion','unidad','encuesta','categoria') order by 1,3,2;"
echo "## 3. Índices de requerimiento"
sql -c "select indexname as indice, indexdef as definicion from pg_indexes where tablename='requerimiento' order by 1;"
echo "## 4. Escritura y lectura: caso $FOLIO, creado desde el sitio web, recuperado con sus relaciones"
sql -c "select r.folio, r.tipo, r.canal, e.nombre as establecimiento, r.estado, r.fecha_vencimiento, s.nombre as solicitante, u.nombre as unidad from requerimiento r join establecimiento e on e.id=r.establecimiento_id left join solicitante s on s.id=r.solicitante_id left join unidad u on u.id=r.unidad_derivada_id where r.folio='$FOLIO';"
sql -c "select h.estado_anterior, h.estado_nuevo, h.accion, to_char(h.fecha,'DD-MM-YYYY HH24:MI') as fecha from historial_estado h join requerimiento r on r.id=h.requerimiento_id where r.folio='$FOLIO' order by h.id;"
sql -c "select r.folio, p.medio, p.fecha_emision, p.dentro_plazo from respuesta p join requerimiento r on r.id=p.requerimiento_id where r.folio='$FOLIO';"

echo "## 5. Reglas de integridad: intentos inválidos con el rol de la aplicación (oirs_app), transacciones revertidas"
intento "a) Fecha de vencimiento anterior al ingreso (CHECK ck_req_vencimiento_posterior):" \
  "insert into requerimiento($COLS) values ('PLC-2026-999991','RECLAMO','WEB',$EST,'Prueba de integridad DEMO-BD','',now(),current_date-1,'INGRESADO')"
intento "b) Establecimiento inexistente (FOREIGN KEY):" \
  "insert into requerimiento($COLS) values ('PLC-2026-999992','RECLAMO','WEB',999999,'Prueba de integridad DEMO-BD','',now(),current_date+20,'INGRESADO')"
intento "c) Folio duplicado (UNIQUE):" \
  "insert into requerimiento($COLS) values ('$FOLIO','RECLAMO','WEB',$EST,'Prueba de integridad DEMO-BD','',now(),current_date+20,'INGRESADO')"
intento "d) Descripción nula (NOT NULL):" \
  "insert into requerimiento($COLS) values ('PLC-2026-999993','RECLAMO','WEB',$EST,null,'',now(),current_date+20,'INGRESADO')"
intento "e) Respuesta por correo autorizada sin correo ni teléfono (CHECK ck_solicitante_contacto):" \
  "insert into solicitante(nombre,apellidos,email,telefono,sexo,autoriza_respuesta_email,anonimizado) values ('DEMO-BD','','','','',true,false)"
intento "f) Modificar el historial de estados (privilegio UPDATE revocado):" \
  "update historial_estado set comentario='alterado' where id=(select min(id) from historial_estado)"
intento "g) Eliminar un caso (oirs_app no tiene DELETE):" \
  "delete from requerimiento where folio='$FOLIO'"
echo "h) Borrar el historial como superusuario (trigger tg_historial_inmutable):"
sql -q -v ON_ERROR_STOP=1 -c "begin; delete from historial_estado where id=(select min(id) from historial_estado); rollback;" 2>&1 \
  | grep -E "ERROR" | sed 's/^/   /' || true
echo "i) Intento válido de control (debe aceptarse y luego revertirse):"
docker compose exec -T -e PGPASSWORD="$PG_PASSWORD" postgres psql -q -U oirs_app -h 127.0.0.1 -d oirs_plc -v ON_ERROR_STOP=1 \
  -c "begin; set constraints all immediate; insert into requerimiento($COLS) values ('PLC-2026-999994','RECLAMO','WEB',$EST,'Prueba de integridad DEMO-BD','',now(),current_date+20,'INGRESADO'); select 'aceptado: ' || folio as resultado from requerimiento where folio='PLC-2026-999994'; rollback;" \
  2>&1 | grep -E "aceptado|ERROR" | sed 's/^/   /'
echo "Comprobación posterior: casos PLC-2026-99999x = $(sql -Atc "select count(*) from requerimiento where folio like 'PLC-2026-99999%';"); solicitantes DEMO-BD = $(sql -Atc "select count(*) from solicitante where nombre='DEMO-BD';")"

echo; echo "## 6. Consulta frecuente de la bandeja (casos abiertos de un establecimiento): plan de ejecución"
sql -c "set enable_seqscan=off; explain select folio, estado, fecha_vencimiento from requerimiento where establecimiento_id=$EST and estado in ('INGRESADO','EN_PROCESO') order by fecha_vencimiento;"
echo "(Con pocas filas PostgreSQL prefiere recorrer la tabla; enable_seqscan=off muestra el índice que usa con volumen real.)"

echo; echo "## 7. Base documental (MongoDB): colecciones, índices y documentos de ejemplo"
mongo 'const d=db.getSiblingDB("oirs_plc_docs"); d.getCollectionNames().sort().forEach(c=>{print(c+": "+d[c].countDocuments()+" documentos"); d[c].getIndexes().forEach(i=>print("   índice "+i.name+" "+JSON.stringify(i.key)+(i.expireAfterSeconds?" (TTL "+i.expireAfterSeconds/86400+" días)":"")+(i.unique?" (único)":"")))})'
echo "Respuesta de encuesta (sin IP, sin hora, sin datos personales):"
mongo 'printjson(db.getSiblingDB("oirs_plc_docs").respuestas_encuesta.find({},{_id:0}).sort({_id:-1}).limit(1).toArray()[0])'
echo "Eventos de bitácora del caso $FOLIO (referencia por folio a PostgreSQL):"
mongo "printjson(db.getSiblingDB(\"oirs_plc_docs\").bitacora_auditoria.find({folio:\"$FOLIO\"},{_id:0}).sort({ts:1}).limit(2).toArray())"

echo; echo "## 8. Consistencia entre bases (referencias de MongoDB a PostgreSQL)"
docker compose exec -T app python manage.py verificar_referencias 2>&1 | grep -v "objects imported"
} > "$O" 2>&1
echo "Evidencia guardada en $O"
