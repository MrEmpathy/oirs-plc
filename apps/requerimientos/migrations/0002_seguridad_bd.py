"""Endurecimiento a nivel de base de datos: mínimo privilegio para el usuario de la aplicación
y bitácora de estados inmutable (append-only) mediante trigger."""
from django.db import migrations

SQL = r"""
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO oirs_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO oirs_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO oirs_app;
GRANT DELETE ON django_session TO oirs_app;
REVOKE UPDATE, DELETE ON historial_estado FROM oirs_app;

CREATE OR REPLACE FUNCTION fn_historial_inmutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'historial_estado es de solo inserción (RNF07)';
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER tg_historial_inmutable BEFORE UPDATE OR DELETE ON historial_estado
  FOR EACH ROW EXECUTE FUNCTION fn_historial_inmutable();
"""
REVERSA = "DROP TRIGGER IF EXISTS tg_historial_inmutable ON historial_estado; DROP FUNCTION IF EXISTS fn_historial_inmutable();"


class Migration(migrations.Migration):
    dependencies = [("requerimientos", "0001_initial"), ("sessions", "0001_initial"),
                    ("encuestas", "0001_initial"), ("catalogos", "0002_initial"), ("cuentas", "0001_initial")]
    operations = [migrations.RunSQL(SQL, REVERSA)]
