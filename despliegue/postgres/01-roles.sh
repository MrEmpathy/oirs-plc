#!/bin/sh
# Se ejecuta una sola vez al crear el volumen de PostgreSQL.
# Roles (sección 6.3): oirs_owner = propietario, solo migraciones (CREATEDB para la BD de pruebas);
#                      oirs_app   = aplicación, privilegios mínimos (los otorga la migración 0002).
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<SQL
CREATE ROLE oirs_owner LOGIN CREATEDB PASSWORD '${PG_OWNER_PASSWORD}';
CREATE ROLE oirs_app LOGIN PASSWORD '${PG_APP_PASSWORD}';
CREATE DATABASE oirs_plc OWNER oirs_owner;
REVOKE ALL ON DATABASE oirs_plc FROM PUBLIC;
GRANT CONNECT ON DATABASE oirs_plc TO oirs_app;
SQL
