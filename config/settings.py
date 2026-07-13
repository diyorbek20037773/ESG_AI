from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-in-production')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')

# Railway: trust the public domain automatically (any *.railway.app host).
RAILWAY_DOMAIN = config('RAILWAY_PUBLIC_DOMAIN', default='')
if RAILWAY_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_DOMAIN)
ALLOWED_HOSTS += ['.railway.app', '.up.railway.app', 'novdai.uz', 'www.novdai.uz']

CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='').split(',') if config('CSRF_TRUSTED_ORIGINS', default='') else []
if RAILWAY_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RAILWAY_DOMAIN}')
CSRF_TRUSTED_ORIGINS += ['https://*.railway.app', 'https://*.up.railway.app',
                         'https://novdai.uz', 'https://www.novdai.uz']


INSTALLED_APPS = [
    'modeltranslation',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'ckeditor',
    'ckeditor_uploader',
    # Local apps
    'src.apps.core.apps.CoreConfig',
    'src.apps.news.apps.NewsConfig',
    'src.apps.blog.apps.BlogConfig',
    'src.apps.users.apps.UsersConfig',
    'src.apps.dashboard.apps.DashboardConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
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
        'DIRS': [BASE_DIR / 'src' / 'templates'],
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


# Database priority:
#   1. DATABASE_URL  (Railway Postgres plugin sets this automatically)
#   2. DB_ENGINE=postgresql + DB_* vars  (manual Postgres)
#   3. SQLite fallback  (local dev / first deploy with no DB configured)
DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600),
    }
else:
    DB_ENGINE = config('DB_ENGINE', default='django.db.backends.sqlite3')
    DB_HOST = config('DB_HOST', default='')
    # Only use manual Postgres when a REAL remote host is given (e.g. docker-compose
    # "db"). Placeholder/localhost values on Railway fall back to SQLite so the app
    # always boots instead of crashing on an unreachable DB.
    if (DB_ENGINE == 'django.db.backends.postgresql' and config('DB_NAME', default='')
            and DB_HOST and DB_HOST not in ('localhost', '127.0.0.1')):
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': config('DB_NAME', default='esg_db'),
                'USER': config('DB_USER', default='postgres'),
                'PASSWORD': config('DB_PASSWORD', default=''),
                'HOST': DB_HOST,
                'PORT': config('DB_PORT', default='5432'),
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
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]



LANGUAGE_CODE = 'uz'

LANGUAGES = [
    ('uz', 'O\'zbek'),
    ('en', 'English'),
    ('ru', 'Русский'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise — serve compressed static files directly from the app (no nginx).
# Non-manifest storage: never raises on a missing/changed reference, so a single
# odd third-party static file can't crash the whole app at request time.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'src' / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Auth
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/welcome/'   # users.post_login_redirect → role-based home
LOGOUT_REDIRECT_URL = '/'

# Email (SMTP)
EMAIL_BACKEND       = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST          = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT          = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS       = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = EMAIL_HOST_USER

# Gemini AI — multiple keys supported for rotation / rate-limit fallback.
# Use GEMINI_API_KEYS for many keys in one variable (comma/space separated),
# or GEMINI_API_KEY / _2 / _3 for separate ones.
GEMINI_API_KEY    = config('GEMINI_API_KEY', default='')
GEMINI_API_KEY_2  = config('GEMINI_API_KEY_2', default='')
GEMINI_API_KEY_3  = config('GEMINI_API_KEY_3', default='')
GEMINI_API_KEYS   = config('GEMINI_API_KEYS', default='')

# Behind Railway's proxy — honour the forwarded HTTPS header.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CKEditor
CKEDITOR_UPLOAD_PATH = 'blog/uploads/'
CKEDITOR_IMAGE_BACKEND = 'pillow'

# Custom CKEditor configuration
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent'],
            ['JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
            ['Link', 'Unlink'],
            ['Image', 'Table', 'HorizontalRule', 'SpecialChar'],
            ['Format', 'FontSize'],
            ['TextColor', 'BGColor'],
            ['CodeSnippet'],
            ['Maximize'],
            ['Source'],
        ],
        'height': 400,
        'width': '100%',
        'extraPlugins': ','.join(['codesnippet']),
        'removePlugins': 'stylesheetparser',
        'allowedContent': True,
    }
}
