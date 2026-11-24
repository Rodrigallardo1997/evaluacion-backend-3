"""
Configuración principal de Django para el proyecto Dulce Arte.
Evaluación N.º 4 - Programación Backend (Arquitectura AWS, JWT y Seguridad).
Autor: Rodrigo Alejandro Gallardo Martínez.
"""
from datetime import timedelta
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
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
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
    'corsheaders.middleware.CorsMiddleware',
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

# Configuración explícita de hashers criptográficos (PBKDF2-HMAC-SHA256 con 720.000 iteraciones + salt)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

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
# Archivos Estáticos y Multimedia (Django 5 STORAGES — Soporte Dual Local / AWS S3)
# ---------------------------------------------------------------------------
USE_S3 = env.bool('USE_S3', default=False)
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_ROOT = BASE_DIR / 'media'

if USE_S3:
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='dulcearte-rodrigo-frontend-2026')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_DEFAULT_ACL = None  # Compatible con S3 BucketOwnerEnforced (sin ACLs legadas)

    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    if env.bool('USE_S3_FOR_STATIC', default=False):
        STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
        _staticfiles_backend = 'config.storage_backends.StaticStorage'
    else:
        STATIC_URL = '/static/'
        _staticfiles_backend = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

    STORAGES = {
        'default': {'BACKEND': 'config.storage_backends.MediaStorage'},
        'staticfiles': {'BACKEND': _staticfiles_backend},
    }
else:
    STATIC_URL = '/static/'
    MEDIA_URL = '/media/'
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
    }

# ---------------------------------------------------------------------------
# AWS SNS & Lambda (Alertas y Mensajería Serverless)
# ---------------------------------------------------------------------------
AWS_SNS_TOPIC_ARN = env('AWS_SNS_TOPIC_ARN', default='arn:aws:sns:us-east-1:596205176716:dulcearte-alertas-sns')
AWS_LAMBDA_SNS_URL = env(
    'AWS_LAMBDA_SNS_URL',
    default='https://wsa4lyofyakp3pxazuyg55d7fm0zpsaf.lambda-url.us-east-1.on.aws/',
)

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
# Cabeceras de Seguridad HTTP y Proxy TLS
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# ---------------------------------------------------------------------------
# Configuración CORS Explícita (Sin Wildcard + Credenciales)
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'http://dulcearte-rodrigo-frontend-2026.s3-website-us-east-1.amazonaws.com',
        'http://32.196.211.81',
        'https://32.196.211.81',
        'http://dulce-arte.duckdns.org',
        'https://dulce-arte.duckdns.org',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ],
)
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Configuración de Django REST Framework (DRF)
# Incluye Autenticación JWT (Evaluación N°4), Token y Rate Limiting real (DoS)
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': env('THROTTLE_ANON_RATE', default='60/minute'),
        'user': env('THROTTLE_USER_RATE', default='300/minute'),
        'catalogo_publico': env('THROTTLE_CATALOGO_RATE', default='15/minute'),
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ---------------------------------------------------------------------------
# Configuración de JSON Web Token (JWT - SimpleJWT)
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ---------------------------------------------------------------------------
# Documentación OpenAPI / Swagger con drf-spectacular
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    'TITLE': 'Dulce Arte API',
    'DESCRIPTION': 'API RESTful para Dulce Arte — Evaluación N.º 4 (AWS, JWT y Seguridad)',
    'VERSION': '2.0.0',
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
