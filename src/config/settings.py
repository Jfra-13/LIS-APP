import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def env_any(*names, default=None):
    for name in names:
        value = os.environ.get(name)
        if value not in (None, ""):
            return value
    return default


def db_env(name, default=None):
    alias_map = {
        "DB_NAME": "POSTGRES_DB",
        "DB_USER": "POSTGRES_USER",
        "DB_PASSWORD": "POSTGRES_PASSWORD",
        "DB_HOST": "POSTGRES_HOST",
        "DB_PORT": "POSTGRES_PORT",
    }
    legacy_name = alias_map.get(name, name.replace("DB_", "POSTGRES_"))
    return env_any(name, legacy_name, default=default)


# SECURITY
INSECURE_SECRET_KEY = "django-insecure-dev-key-change-me"
SECRET_KEY = env("SECRET_KEY", INSECURE_SECRET_KEY)
DEBUG = env("DEBUG", "1") == "1"

# Fail fast: never boot a deployment with the insecure development key.
if not DEBUG and SECRET_KEY == INSECURE_SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY must be set to a strong, unique value when DEBUG is off."
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in env("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    host.strip()
    for host in env("CSRF_TRUSTED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    if host.strip()
]

# Production security hardening. Secure-by-default when DEBUG is off; each flag
# can still be overridden by env (e.g. a plain-HTTP staging may turn the SSL
# redirect off). When DEBUG is on, everything stays relaxed for local work.
_tls_default = not DEBUG
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", _tls_default)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", _tls_default)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", _tls_default)
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "31536000" if _tls_default else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", _tls_default)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", _tls_default)
SECURE_CONTENT_TYPE_NOSNIFF = True
# Honor the X-Forwarded-Proto header set by the reverse proxy / load balancer.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
    "admision.apps.AdmisionConfig",
    "triage.apps.TriageConfig",
    "medico.apps.MedicoConfig",
    "consulta.apps.ConsultaConfig",
    "portal_paciente.apps.PortalPacienteConfig",
    "autenticacion_paciente.apps.AutenticacionPacienteConfig",
    "simple_history",
    "django_htmx",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves the collected static files in production without a separate server.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "config.urls"
AUTH_USER_MODEL = "core.User"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database selection: prefer explicit DB_ENGINE, otherwise detect DB envs for Postgres
db_engine = env("DB_ENGINE")
if not db_engine:
    db_engine = (
        "django.db.backends.postgresql"
        if any(
            os.environ.get(name)
            for name in (
                "DB_NAME",
                "POSTGRES_DB",
                "DB_USER",
                "POSTGRES_USER",
                "DB_PASSWORD",
                "POSTGRES_PASSWORD",
                "DB_HOST",
                "POSTGRES_HOST",
            )
        )
        else "django.db.backends.sqlite3"
    )

if db_engine == "django.db.backends.postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": db_env("DB_NAME", "app_lis"),
            "USER": db_env("DB_USER", "app_lis"),
            "PASSWORD": db_env("DB_PASSWORD", "app_lis"),
            "HOST": db_env("DB_HOST", "db"),
            "PORT": db_env("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "es"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # WhiteNoise: compress + hash static files for long-lived caching.
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "landing"

# Celery configuration
# Broker URL: read from environment or default to the rabbitmq service in docker-compose
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")
# Optionally set a result backend (empty by default). Use RPC or a dedicated backend if required.
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "")

# Serialization settings to avoid Decimal/UUID issues
CELERY_TASK_SERIALIZER = env("CELERY_TASK_SERIALIZER", "json")
CELERY_RESULT_SERIALIZER = env("CELERY_RESULT_SERIALIZER", "json")
CELERY_ACCEPT_CONTENT = ["json"]

# For local testing you can enable eager mode by setting CELERY_TASK_ALWAYS_EAGER=1 in env
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER", "0") == "1"

# Email Configuration
# In DEBUG, write emails to the console so magic links work without SMTP credentials.
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT", 587)
EMAIL_USE_TLS = env("EMAIL_USE_TLS", "1") == "1"
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "noreply@applis.com")


# Logging: single console stream (captured by Docker / the platform's log driver).
# Application loggers (medico/triage/consulta) already attach structured context
# via `logger.info(..., extra={...})`; the worker logs through the celery logger.
LOG_LEVEL = env("LOG_LEVEL", "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "medico": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "triage": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "consulta": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
