"""
Configuración principal de Django para el proyecto Dulce Arte.
Evaluación Parcial N°3 - Desarrollo Backend.
Autor: Rodrigo Alejandro Gallardo Martínez.
"""
from pathlib import Path
import environ

# ---------------------------------------------------------------------------
# Rutas y Directorios Base del Proyecto
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Carga de Variables de Entorno (django-environ)
# ---------------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / '.env')

# ---------------------------------------------------------------------------
# Configuración Principal y Seguridad Básica
# ---------------------------------------------------------------------------
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['http://localhost:8000'])

# ---------------------------------------------------------------------------
# Definición de Aplicaciones Instaladas
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    # Módulos nativos de Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Paquetes y librerías de terceros
    'rest_framework',
    'drf_spectacular',
    'storages',

    # Aplicaciones del dominio de negocio Dulce Arte
    'apps.usuarios',
    'apps.catalogo',
    'apps.pedidos',
    'apps.inventario',
    'apps.despachos',
    'apps.dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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
ASGI_APPLICATION = 'config.asgi.application'

# ---------------------------------------------------------------------------
# Base de Datos — PostgreSQL 16 con psycopg
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        **env.db('DATABASE_URL'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'options': '-c timezone=America/Santiago',
        },
    }
}

# ---------------------------------------------------------------------------
# Autenticación y Control de Acceso (RBAC)
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'usuarios.Usuario'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ---------------------------------------------------------------------------
# Internacionalización y Zona Horaria (Chile Continental)
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos Estáticos y Multimedia (Soporte Dual: Local y AWS S3)
# ---------------------------------------------------------------------------
USE_S3 = env.bool('USE_S3', default=False)

if USE_S3:
    # Configuración de credenciales de AWS S3
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='dulcearte-media-bucket')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_DEFAULT_ACL = 'public-read'

    # Almacenamiento multimedia remoto en S3 (Fotos de Tortas y Firmas)
    DEFAULT_FILE_STORAGE = 'config.storage_backends.MediaStorage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

    # Configuración de estáticos con fallback a WhiteNoise
    if env.bool('USE_S3_FOR_STATIC', default=False):
        STATICFILES_STORAGE = 'config.storage_backends.StaticStorage'
        STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    else:
        STATIC_URL = '/static/'
        STATIC_ROOT = BASE_DIR / 'staticfiles'
        STATICFILES_DIRS = [BASE_DIR / 'static']
        STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
else:
    # Almacenamiento local para desarrollo y servidores independientes
    STATIC_URL = '/static/'
    STATIC_ROOT = BASE_DIR / 'staticfiles'
    STATICFILES_DIRS = [BASE_DIR / 'static']
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# AWS SNS (Simple Notification Service) - Alertas y Mensajería Cloud
# ---------------------------------------------------------------------------
AWS_SNS_TOPIC_ARN = env('AWS_SNS_TOPIC_ARN', default='')

# ---------------------------------------------------------------------------
# Gestión de Sesiones de Usuario
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 28800  # 8 horas de duración de sesión activa

# ---------------------------------------------------------------------------
# Control Transaccional Explícito
# ---------------------------------------------------------------------------
ATOMIC_REQUESTS = False  # Usamos @transaction.atomic() explícito en servicios críticos

# ---------------------------------------------------------------------------
# Identificador Primario por Defecto (Big Auto Field)
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Cabeceras de Seguridad HTTP
# ---------------------------------------------------------------------------
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# ---------------------------------------------------------------------------
# Configuración de Django REST Framework (DRF)
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ---------------------------------------------------------------------------
# Documentación OpenAPI / Swagger con drf-spectacular
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    'TITLE': 'Dulce Arte API',
    'DESCRIPTION': 'API REST para el sistema de gestión de Dulce Arte — Proyecto EVA 3',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# ---------------------------------------------------------------------------
# Registro de Bitácora y Auditoría de Logs
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO' if DEBUG else 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
