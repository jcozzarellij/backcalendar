import os
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_HOSTS = ["*"]

VERSION_CSS = '3.0'

# SESSION CONFIGURATION
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
# 30 días desde la última actividad, no 5 años. Con SESSION_SAVE_EVERY_REQUEST la sesión se
# renueva en cada request, así que a quien usa la plataforma no lo desloguea nunca; lo que se
# acota es la vida de una cookie robada y el crecimiento de django_session (que nadie purgaba).
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_SAVE_EVERY_REQUEST = True


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# CREDENCIALES
import json

with open(os.path.join(BASE_DIR, 'credenciales.json')) as json_file:
    data = json.load(json_file)
    # POSTGRES
    POSTGRES_USER = data.get('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = data['POSTGRES_PASSWORD']
    POSTGRES_HOST = data['POSTGRES_HOST']
    POSTGRES_PORT = data['POSTGRES_PORT']
    POSTGRES_DBNAME = data['POSTGRES_DBNAME']

    BASE_URL_PRODUCCION = data['BASE_URL_PRODUCCION']
    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = data['SECRET_KEY']
    # Correo saliente: un solo SMTP (Gmail con contraseña de aplicación, SendGrid con usuario
    # 'apikey' y la API key como contraseña, o cualquier otro). Lo usan send_html_mail y core.correos.
    EMAIL_HOST = str(data.get('EMAIL_HOST') or 'smtp.gmail.com').strip()
    EMAIL_PORT = int(data.get('EMAIL_PORT') or 587)
    EMAIL_USE_TLS = bool(data.get('EMAIL_USE_TLS', True))
    EMAIL_USE_SSL = not EMAIL_USE_TLS
    EMAIL_HOST_USER = str(data.get('EMAIL_HOST_USER') or '').strip()
    EMAIL_HOST_PASSWORD = str(data.get('EMAIL_HOST_PASSWORD') or '').replace(' ', '')
    DEFAULT_FROM_EMAIL = str(data.get('DEFAULT_FROM_EMAIL') or EMAIL_HOST_USER).strip()
    EMAIL_TIMEOUT = 30
    ERROR_NOTIFY_EMAILS = data.get('ERROR_NOTIFY_EMAILS', []) or []
    # SSL
    USE_SSL = data['USE_SSL']
    SECURE_SSL_REDIRECT = USE_SSL
    DEBUG = data["DEBUG"]
    DOMINIO_GENERAL = data["DOMINIO_GENERAL"]
    WINDOWS = data["WINDOWS"]
    URL_GENERAL = ("https://" if USE_SSL else "http://") + DOMINIO_GENERAL
    # Endurecimiento de despliegue (2026-07-10). Con DEBUG=False el Host header deja de
    # aceptar cualquier valor; con USE_SSL las cookies solo viajan por HTTPS y se activa
    # HSTS. SECURE_PROXY_SSL_HEADER: detrás de nginx, Django detecta el HTTPS original.
    if not DEBUG:
        from urllib.parse import urlparse as _urlparse
        _host_prod = _urlparse(BASE_URL_PRODUCCION).hostname or _urlparse('//' + (DOMINIO_GENERAL or '')).hostname or ''
        ALLOWED_HOSTS = [h for h in [_host_prod, f'www.{_host_prod}' if _host_prod else '',
                                     'localhost', '127.0.0.1'] if h]
    SESSION_COOKIE_SECURE = USE_SSL or not DEBUG
    CSRF_COOKIE_SECURE = USE_SSL or not DEBUG
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    if USE_SSL:
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
        SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
        SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    ADMINS = data["ADMINS"]
    ID_GRUPO_ADMINISTRADOR = data['ID_GRUPO_ADMINISTRADOR']
    # Host público del backend (enlaces absolutos en correos). Si
    # credenciales.json no trae `BACKEND_PUBLIC_URL`, cae a `BASE_URL_PRODUCCION` / `DOMINIO_GENERAL`.
    BACKEND_PUBLIC_URL = (
        data.get('BACKEND_PUBLIC_URL')
        or data.get('BASE_URL_PRODUCCION')
        or data.get('DOMINIO_GENERAL')
        or 'http://127.0.0.1:8000'
    ).rstrip('/')
    # Google (OAuth por usuario para Calendar/Meet). Se crean en Google Cloud Console; vacíos = la
    # pantalla «Mis aplicaciones» muestra la conexión como no configurada. La URI de redirección
    # debe registrarse igual en el cliente OAuth.
    GOOGLE_OAUTH_CLIENT_ID = (data.get('GOOGLE_OAUTH_CLIENT_ID') or '').strip()
    GOOGLE_OAUTH_CLIENT_SECRET = (data.get('GOOGLE_OAUTH_CLIENT_SECRET') or '').strip()
    GOOGLE_OAUTH_REDIRECT_URI = (data.get('GOOGLE_OAUTH_REDIRECT_URI') or '').strip() or         f'{BACKEND_PUBLIC_URL}/agenda/aplicaciones/google/'
    # Ruta al ejecutable pg_dump para `manage.py backup_bd` cuando no está en el PATH
    # (típico en Windows). Vacío = busca en el PATH y si no hay, cae a dumpdata.
    PG_DUMP_CMD = (data.get('PG_DUMP_CMD') or '').strip()
WEBPUSH_SETTINGS = {'VAPID_PUBLIC_KEY': '', 'VAPID_PRIVATE_KEY': '', 'VAPID_ADMIN_EMAIL': ''}
try:
    with open(os.path.join(BASE_DIR, 'constantes_vapid.json')) as _vapid_file:
        _vapid_data = json.load(_vapid_file)
        WEBPUSH_SETTINGS = {
            'VAPID_PUBLIC_KEY': _vapid_data.get('VAPID_PUBLIC_KEY', ''),
            'VAPID_PRIVATE_KEY': _vapid_data.get('VAPID_PRIVATE_KEY', ''),
            'VAPID_ADMIN_EMAIL': _vapid_data.get('VAPID_ADMIN_EMAIL', ''),
        }
except (FileNotFoundError, ValueError):
    pass


from pwa.app_settings import *  # noqa: F401,F403


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.postgres',
    # LOCAL APPS
    'autenticacion.apps.AutenticacionConfig',
    'seguridad.apps.SeguridadConfig',
    'area_geografica.apps.AreaGeograficaConfig',
    'public.apps.PublicConfig',
    'agenda.apps.AgendaConfig',
    'pwa.apps.PwaConfig',
    # packages
    'django_select2',
    'for_django_projects.form_utils',
    'webpush',
    'corsheaders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # custom middlewares
    'core.custom_middleware.InitialDataApp',
    'core.custom_middleware.RequestMiddleware',
]

DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440 * 10

ROOT_URLCONF = 'backcalendar.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')]
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'pwa.context_processors.pwa_settings',
                'agenda.context_processors.menu_agenda',
            ],
        },
    },
]

WSGI_APPLICATION = 'backcalendar.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': POSTGRES_DBNAME,
        'USER': POSTGRES_USER,
        'PASSWORD': POSTGRES_PASSWORD,
        'HOST': POSTGRES_HOST,
        'PORT': POSTGRES_PORT,
        'ATOMIC_REQUESTS': False,
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {'connect_timeout': 5, 'options': '-c idle_in_transaction_session_timeout=60000'},
    },

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

LOGIN_URL = '/login/'

LANGUAGE_CODE = 'es-ec'

TIME_ZONE = 'America/Guayaquil'

USE_I18N = True

USE_TZ = False

AUTH_USER_MODEL = "autenticacion.Usuario"

STATIC_URL = '/static/'

if DEBUG:
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, 'static'),
    ]
    # Con DEBUG el estático se sirve desde static/ directo; STATIC_ROOT apunta a otra
    # carpeta solo para que collectstatic no reviente si un deploy lo corre igual
    # (no puede ser la misma carpeta que STATICFILES_DIRS — Django lo rechaza).
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
else:
    STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

TEST_RUNNER = 'django.test.runner.DiscoverRunner'  # If you wish to delay updates to your test suite
# JSON en vez de Pickle (2026-07-10): Pickle en sesiones habilita RCE si el backend de
# sesión o el SECRET_KEY se comprometen. La sesión ya solo guarda tipos JSON (ids, strings,
# listas — 'perfilprincipal' pasó a 'perfilprincipal_id'). Las sesiones Pickle previas se
# invalidan solas (Django las decodifica a vacío → re-login una única vez).
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

DEFAULT_CHARSET = 'utf-8'


CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = []
CORS_URLS_REGEX = r'^/api/.*$'

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CSRF_TRUSTED_ORIGINS = [
    # url produccion
    'http://localhost:3000'
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_ALLOW_CREDENTIALS = False


X_FRAME_OPTIONS = 'SAMEORIGIN'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'backcalendar',
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'scrub_credentials': {'()': 'core.log_filters.ScrubCredentialsFilter'},
    },
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['scrub_credentials'],
        },
    },
    'loggers': {
        'core': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
