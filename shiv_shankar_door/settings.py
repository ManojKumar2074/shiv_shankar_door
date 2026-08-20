import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ── Security ──────────────────────────────────────────────
SECRET_KEY = os.environ['SECRET_KEY']

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    'shiv-shankar-door.onrender.com'
).split(',')


# ── Applications ─────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'doors',
    'dashboard',
]


# ── Middleware ────────────────────────────────────────────
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


# ── URL / WSGI ────────────────────────────────────────────
ROOT_URLCONF = 'shiv_shankar_door.urls'

WSGI_APPLICATION = 'shiv_shankar_door.wsgi.application'


# ── Templates ──────────────────────────────────────────────
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

                'doors.context_processors.site_context',
                'dashboard.context_processors.dashboard_context',
            ],
        },
    },
]


# ── Database ──────────────────────────────────────────────
# Render:
#     DATABASE_URL → PostgreSQL
#
# Local development:
#     Falls back to SQLite (db.sqlite3)

import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}


# ── Password Validation ───────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME':
        'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.MinimumLengthValidator'
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.CommonPasswordValidator'
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.NumericPasswordValidator'
    },
]


# ── Internationalization ─────────────────────────────────
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True


# ── Static Files ──────────────────────────────────────────
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static'
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
)


# ── Media / Cloudinary ────────────────────────────────────
MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'


USE_CLOUDINARY = (
    os.environ.get('USE_CLOUDINARY', 'False').lower() == 'true'
)


if USE_CLOUDINARY:

    import cloudinary
    import cloudinary_storage

    INSTALLED_APPS += [
        'cloudinary',
        'cloudinary_storage',
    ]

    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': os.environ['CLOUDINARY_CLOUD_NAME'],
        'API_KEY': os.environ['CLOUDINARY_API_KEY'],
        'API_SECRET': os.environ['CLOUDINARY_API_SECRET'],
    }

    DEFAULT_FILE_STORAGE = (
        'cloudinary_storage.storage.MediaCloudinaryStorage'
    )


# ── Django Defaults ──────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ── Business Settings ────────────────────────────────────
WHATSAPP_NUMBER = os.environ.get(
    'WHATSAPP_NUMBER',
    '917013891509'
)

BUSINESS_PHONE_1 = os.environ.get(
    'BUSINESS_PHONE_1',
    '7013891509'
)

BUSINESS_PHONE_2 = os.environ.get(
    'BUSINESS_PHONE_2',
    '9701694767'
)

BUSINESS_EMAIL = os.environ.get(
    'BUSINESS_EMAIL',
    'litheshpatel1@gmail.com'
)

MAPS_URL = os.environ.get(
    'MAPS_URL',
    'https://maps.app.goo.gl/9TuioXMNQ8v3b3RF6'
)


# ── Dashboard Authentication ─────────────────────────────
LOGIN_URL = '/dashboard/login/'

LOGIN_REDIRECT_URL = '/dashboard/'


# ── File Upload Limits ────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
