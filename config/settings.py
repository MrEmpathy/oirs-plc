"""
Configuración del Sistema de Gestión OIRS - DSM Padre Las Casas.

Regla de codificación segura SC-05: ningún secreto se escribe en el código.
Todos los valores sensibles se leen desde variables de entorno (ver .env.example).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(nombre, defecto=None, obligatorio=False):
    valor = os.environ.get(nombre, defecto)
    if obligatorio and not valor:
        raise RuntimeError(f"Variable de entorno obligatoria no definida: {nombre}")
    return valor


DEBUG = env("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = env("DJANGO_SECRET_KEY", obligatorio=True)
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.cuentas",
    "apps.catalogos",
    "apps.requerimientos",
    "apps.encuestas",
    "apps.auditoria",
    "apps.reportes",
    "apps.integracion",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.cuentas.middleware.CabecerasSeguridadMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ]},
    }
]

# --- Base de datos estructurada (PostgreSQL) -------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("PG_DB", "oirs_plc"),
        "USER": env("PG_USER", "oirs_app"),
        "PASSWORD": env("PG_PASSWORD", obligatorio=True),
        "HOST": env("PG_HOST", "127.0.0.1"),
        "PORT": env("PG_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"sslmode": env("PG_SSLMODE", "prefer")},
    }
}

# --- Base de datos no estructurada / documental (MongoDB) -------------------
MONGO_URI = env("MONGO_URI", "mongodb://127.0.0.1:27017/")
MONGO_DB = env("MONGO_DB", "oirs_plc_docs")

# --- Integración WordPress -> sistema administrativo -----------------------
WP_HMAC_SECRET = env("WP_HMAC_SECRET", obligatorio=True)
WP_HMAC_TOLERANCIA_SEG = 300  # ventana anti-replay

# --- Autenticación ----------------------------------------------------------
AUTH_USER_MODEL = "cuentas.Usuario"
PASSWORD_HASHERS = [
    "apps.cuentas.hashers.Argon2idOWASP",  # Argon2id (OWASP)
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.cuentas.validators.ComplejidadValidator"},
]
LOGIN_MAX_INTENTOS = 5
LOGIN_BLOQUEO_MINUTOS = 15
ROLES_CON_MFA = ("ADMIN", "OIRS_DSM")

# --- Sesión y cookies -------------------------------------------------------
SESSION_COOKIE_AGE = 30 * 60           # 30 min de inactividad
SESSION_SAVE_EVERY_REQUEST = True       # expiración deslizante
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
SECURE_FLAGS = env("DJANGO_SECURE", "1") == "1"
SESSION_COOKIE_SECURE = SECURE_FLAGS
CSRF_COOKIE_SECURE = SECURE_FLAGS
SECURE_SSL_REDIRECT = SECURE_FLAGS
SECURE_HSTS_SECONDS = 31536000 if SECURE_FLAGS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_FLAGS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 256 * 1024  # 256 KB por petición

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Registro de errores: nunca se exponen trazas al usuario ---------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"oirs": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")}},
}

# --- Caché (producción: Redis; desarrollo: memoria local) --------------------
CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": env("REDIS_URL")}
          if env("REDIS_URL") else {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CACHE_TTL_REPORTES = 300

# --- Reglas de negocio -----------------------------------------------------
PLAZO_DIAS_HABILES = 15  # Ley N.° 20.584
