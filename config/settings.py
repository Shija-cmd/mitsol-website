from pathlib import Path
from decouple import config
import dj_database_url
import os


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    'SECRET_KEY'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config(

    'DEBUG',

    default=False,

    cast=bool

)


CLOUDINARY_ENABLED = config(
    'CLOUDINARY_ENABLED',
    default=False,
    cast=bool
)


ALLOWED_HOSTS = [

    'mitsol.com.se',

    'www.mitsol.com.se',

    '.onrender.com',

    '127.0.0.1',

    'localhost',

]


# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'services',
    'portfolio',
    'contact',
    'about',
    'software_store',
    'learning',
    'django.contrib.sitemaps',
    'django.contrib.humanize',
]

if CLOUDINARY_ENABLED:

    INSTALLED_APPS.insert(
        INSTALLED_APPS.index('django.contrib.staticfiles'),
        'cloudinary_storage'
    )
    INSTALLED_APPS.append('cloudinary')

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
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'learning.context_processors.learning_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {

    'default': dj_database_url.parse(

        config('DATABASE_URL')

    )

}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
)

EMAIL_BACKEND=config(
    'EMAIL_BACKEND'
)

EMAIL_HOST=config(
    'EMAIL_HOST'
)

EMAIL_PORT=config(
    'EMAIL_PORT',
    cast=int
)

EMAIL_USE_TLS=config(
    'EMAIL_USE_TLS',
    cast=bool
)

EMAIL_HOST_USER=config(
    'EMAIL_HOST_USER'
)

EMAIL_HOST_PASSWORD=config(
    'EMAIL_HOST_PASSWORD'
)

DEFAULT_FROM_EMAIL=config(
    'DEFAULT_FROM_EMAIL'
)

SITE_URL = config(
    'SITE_URL',
    default='https://www.mitsol.com.se'
)

DJANGO_ADMIN_URL = config(
    'DJANGO_ADMIN_URL',
    default='admin/'
).strip('/')

MEDIA_URL = '/media/'

MEDIA_ROOT = config(
    'MEDIA_ROOT',
    default=str(BASE_DIR / 'media')
)

if CLOUDINARY_ENABLED:

    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
        'API_KEY': config('CLOUDINARY_API_KEY'),
        'API_SECRET': config('CLOUDINARY_API_SECRET'),
        'SECURE': True,
    }

    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

    STORAGES = {
        'default': {
            'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

# Security settings
SECURE_BROWSER_XSS_FILTER = True

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = 'DENY'

SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

SECURE_SSL_REDIRECT = config(
    'SECURE_SSL_REDIRECT',
    default=True,
    cast=bool
)

SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SECURE = not DEBUG

SECURE_PROXY_SSL_HEADER = (

    'HTTP_X_FORWARDED_PROTO',

    'https'

)

CSRF_TRUSTED_ORIGINS = [

    'https://mitsol.com.se',

    'https://www.mitsol.com.se',

    'https://*.onrender.com',

]

SECURE_HSTS_SECONDS = (

    31536000

    if not DEBUG

    else 0

)

SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG

SECURE_HSTS_PRELOAD = not DEBUG

JAZZMIN_SETTINGS = {
    "site_title": "MITSOL Admin",
    "site_header": "MITSOL",
    "site_brand": "MITSOL",
    "welcome_sign": "Welcome to MITSOL Management Portal",

    "site_logo": "core/images/logo.png",
    "login_logo": "core/images/small_logo.png",
    "login_logo_dark": "core/images/small_logo.png",

    "site_logo_classes": "img-circle elevation-3",
    "copyright": "MITSOL 2026",

    "navigation_expanded": True,
    "show_sidebar": True,

    "custom_css": "core/css/admin.css",

    # Keep your icons and other settings here
}

JAZZMIN_UI_TWEAKS = {
    "theme": "solar",
    "default_theme_mode": "auto",

    "navbar": "navbar-dark",
    "brand_colour": "navbar-dark",
    "sidebar": "sidebar-dark-success",
    "accent": "accent-success",

    "button_classes": {
        "primary": "btn-success",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}

LOGGING = {

    'version': 1,

    'disable_existing_loggers': False,

    'handlers': {

        'console': {

            'class': 'logging.StreamHandler',

        },

    },

    'root': {

        'handlers': ['console'],

        'level': 'INFO',

    },

}

ADMINS = [

    (

        'Juma Shija',

        'info@mitsol.com.se'

    ),

]

SERVER_EMAIL = 'info@mitsol.com.se'

LOGIN_URL = 'login'

LOGIN_REDIRECT_URL = 'learning:dashboard'

LOGOUT_REDIRECT_URL = 'home'
