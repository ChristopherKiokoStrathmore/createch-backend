from pathlib import Path
import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='insecure-dev-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

import os
RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
ALLOWED_HOSTS.append('healthcheck.railway.app')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'storages',
    'orders',
    'arch_media',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'createch_backend.urls'

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

WSGI_APPLICATION = 'createch_backend.wsgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media: metadata in Postgres, file BYTES on disk (Railway volume) or S3/R2.
# Never store image blobs in BYTEA.
MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = Path(config('MEDIA_ROOT', default=str(BASE_DIR / 'media')))
# Django's static() helper only serves in DEBUG. Set SERVE_MEDIA=True on Railway
# when a volume is mounted at MEDIA_ROOT and you are not using S3/R2.
SERVE_MEDIA = config('SERVE_MEDIA', default=DEBUG, cast=bool)

AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
USE_S3_MEDIA = bool(AWS_STORAGE_BUCKET_NAME)

if USE_S3_MEDIA:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='auto')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default='') or None
    AWS_S3_CUSTOM_DOMAIN = config('AWS_S3_CUSTOM_DOMAIN', default='') or None
    AWS_S3_SIGNATURE_VERSION = config('AWS_S3_SIGNATURE_VERSION', default='s3v4')
    AWS_S3_ADDRESSING_STYLE = config('AWS_S3_ADDRESSING_STYLE', default='virtual')
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = config('AWS_QUERYSTRING_AUTH', default=False, cast=bool)
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'public, max-age=86400'}
    DEFAULT_FILE_STORAGE_BACKEND = 'storages.backends.s3.S3Storage'
else:
    DEFAULT_FILE_STORAGE_BACKEND = 'django.core.files.storage.FileSystemStorage'

STORAGES = {
    'default': {'BACKEND': DEFAULT_FILE_STORAGE_BACKEND},
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS — comma-separated, no trailing slashes. Arch Vercel + createch.co.ke
# plus existing Hobbies origins. Override per environment via CORS_ALLOWED_ORIGINS.
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in config(
        'CORS_ALLOWED_ORIGINS',
        default=(
            'http://localhost:3000,'
            'http://localhost:5173,'
            'http://127.0.0.1:3000,'
            'http://127.0.0.1:5173,'
            'https://createch.co.ke,'
            'https://www.createch.co.ke,'
            'https://createatechhobbies1.vercel.app,'
            'https://createchhobbies.vercel.app'
        ),
    ).split(',')
    if origin.strip()
]
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
    'x-api-key', 'x-admin-key',
]

# DRF
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}

# Admin order API key (legacy — kept for backwards compat)
ADMIN_API_KEY = config('ADMIN_API_KEY', default='')
# Admin dashboard secret key — used by X-Admin-Key header on GET /api/orders/
ADMIN_SECRET_KEY = config('ADMIN_SECRET_KEY', default='')
# Arch image library / chrome writes. X-Admin-Key may match this OR ADMIN_SECRET_KEY.
ARCH_ADMIN_SECRET = config('ARCH_ADMIN_SECRET', default='')
ARCH_MAX_UPLOAD_BYTES = config('ARCH_MAX_UPLOAD_BYTES', default=12 * 1024 * 1024, cast=int)
ARCH_ALLOWED_CONTENT_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/svg+xml',
]

# WooCommerce webhook secret — must match the Secret field on the Woo webhook
# (WP admin → WooCommerce → Settings → Advanced → Webhooks)
WOO_WEBHOOK_SECRET = config('WOO_WEBHOOK_SECRET', default='')

# DPO Pay (3G Direct Pay) — card gateway. Used by orders/dpo.py to verify
# transaction tokens server-side. Same API URL for test and live; the
# company token determines which environment.
DPO_COMPANY_TOKEN = config('DPO_COMPANY_TOKEN', default='')
DPO_API_URL       = config('DPO_API_URL', default='https://secure.3gdirectpay.com/API/v6/')
