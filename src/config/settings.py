import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


def env_any(*names, default=None):
    for name in names:
        value = os.environ.get(name)
        if value not in (None, ''):
            return value
    return default


def db_env(name, default=None):
    alias_map = {
        'DB_NAME': 'POSTGRES_DB',
        'DB_USER': 'POSTGRES_USER',
        'DB_PASSWORD': 'POSTGRES_PASSWORD',
        'DB_HOST': 'POSTGRES_HOST',
        'DB_PORT': 'POSTGRES_PORT',
    }
    legacy_name = alias_map.get(name, name.replace('DB_', 'POSTGRES_'))
    return env_any(name, legacy_name, default=default)


# SECURITY
SECRET_KEY = env('SECRET_KEY', 'django-insecure-dev-key-change-me')
DEBUG = env('DEBUG', '1') == '1'
ALLOWED_HOSTS = [
    host.strip()
    for host in env('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
    if host.strip()
]


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
    'admision.apps.AdmisionConfig',
    'triage.apps.TriageConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
AUTH_USER_MODEL = 'core.User'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database selection: prefer explicit DB_ENGINE, otherwise detect DB envs for Postgres
db_engine = env('DB_ENGINE')
if not db_engine:
    db_engine = 'django.db.backends.postgresql' if any(
        os.environ.get(name)
        for name in (
            'DB_NAME',
            'POSTGRES_DB',
            'DB_USER',
            'POSTGRES_USER',
            'DB_PASSWORD',
            'POSTGRES_PASSWORD',
            'DB_HOST',
            'POSTGRES_HOST',
        )
    ) else 'django.db.backends.sqlite3'

if db_engine == 'django.db.backends.postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_env('DB_NAME', 'app_lis'),
            'USER': db_env('DB_USER', 'app_lis'),
            'PASSWORD': db_env('DB_PASSWORD', 'app_lis'),
            'HOST': db_env('DB_HOST', 'db'),
            'PORT': db_env('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'landing'
