"""Privilegios por defecto: las tablas que creen migraciones futuras quedan con los mismos permisos mínimos
para oirs_app (sin DELETE), sin depender de repetir GRANT en cada migración."""
from django.db import migrations

SQL = """
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO oirs_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO oirs_app;
"""
REVERSA = """
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE ON TABLES FROM oirs_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM oirs_app;
"""


class Migration(migrations.Migration):
    dependencies = [("requerimientos", "0002_seguridad_bd")]
    operations = [migrations.RunSQL(SQL, REVERSA)]
