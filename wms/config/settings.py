from pathlib import Path
from decouple import config, Csv
import dj_database_url
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Core secrets — from environment, with a safe local-dev fallback so the
#    app runs out-of-the-box on first unzip. In real production you MUST
#    set a real SECRET_KEY in .env (the app will still run without one,
#    but never deploy publicly using the fallback key below).
SECRET_KEY = config(
    'SECRET_KEY',
    default='dev-only-fallback-key-CHANGE-ME-before-any-public-deployment-9f8a7b6c5d4e3f2a1b'
)
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0', cast=Csv())

# Local development hosts are ALWAYS allowed, no matter what .env says.
# This app repeatedly broke with "Bad Request (400)" because ALLOWED_HOSTS
# in .env got set to something that didn't include 127.0.0.1/localhost
# (e.g. copied from .env.example, or DEBUG/host values edited by hand).
# Guaranteeing these core local addresses work regardless of .env content
# means that specific failure class can no longer happen again — add your
# real production domain(s) via ALLOWED_HOSTS in .env on top of this.
for _local_host in ('localhost', '127.0.0.1', '0.0.0.0'):
    if _local_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_local_host)

# Shows the quick-login demo buttons on the login page. Independent of
# DEBUG on purpose — flipping DEBUG for any reason shouldn't silently
# hide/show unrelated test tooling. Defaults ON; set to False (or just
# delete the block in templates/base/login.html) before going live —
# see REMOVE_BEFORE_PRODUCTION.md.
SHOW_DEMO_LOGIN = config('SHOW_DEMO_LOGIN', default=True, cast=bool)

# Wildcard subdomain support for multi-tenant SaaS (e.g. *.cliniq.com)
BASE_DOMAIN = config('BASE_DOMAIN', default='')
if BASE_DOMAIN:
    ALLOWED_HOSTS.append(f'.{BASE_DOMAIN}')

# Shared secret for Direct Analyzer Interfacing webhook (Lab machines push results here).
#ANALYZER_API_KEY = config('ANALYZER_API_KEY', default='')
ANALYZER_API_KEY = config('ANALYZER_API_KEY', default='wahabix-medicare-default-analyzer-key')

# WhatsApp notifications — see apps/core/services/notifications.py.
# Empty by default (safe no-op) until you have a real WhatsApp Business
# API account and fill these in .env.
WHATSAPP_API_URL = config('WHATSAPP_API_URL', default='')
WHATSAPP_API_TOKEN = config('WHATSAPP_API_TOKEN', default='')
WHATSAPP_FROM_NUMBER = config('WHATSAPP_FROM_NUMBER', default='')
if not ANALYZER_API_KEY and not DEBUG:
    raise RuntimeError('ANALYZER_API_KEY must be set in production environment.')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Wahabix Medicare Apps
    'apps.core.apps.CoreConfig',
    'apps.superadmin_panel.apps.SuperadminPanelConfig',
    'apps.clinic_admin.apps.ClinicAdminConfig',
    'apps.reception.apps.ReceptionConfig',
    'apps.laboratory.apps.LaboratoryConfig',
    'apps.doctor.apps.DoctorConfig',
    'apps.pharmacy.apps.PharmacyConfig',
    'apps.hr_payroll.apps.HrPayrollConfig',
    'apps.billing.apps.BillingConfig',
    'apps.assets.apps.AssetsConfig',
    'apps.licensing.apps.LicensingConfig',
    'apps.patient_portal.apps.PatientPortalConfig',
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
    'apps.core.middleware.SubdomainTenantMiddleware',
    'apps.core.middleware.TenantMiddleware',
    'apps.licensing.middleware.SubscriptionStatusMiddleware',
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
                'apps.core.context_processors.global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ── Database — reads DATABASE_URL if present (Postgres in prod/Docker),
#    falls back to local SQLite for zero-config development. ────────────────
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
#STATIC_URL = '/static/'
#STATICFILES_DIRS = [BASE_DIR / 'static']
#STATIC_ROOT = BASE_DIR / 'staticfiles'

# This app has repeatedly broken with "no CSS at all" whenever DEBUG=False
# and `collectstatic` hadn't been run — WhiteNoise's default Manifest
# storage only serves files from STATIC_ROOT, which stays empty until
# collectstatic runs. WHITENOISE_USE_FINDERS makes it serve straight from
# STATICFILES_DIRS instead (same as Django's dev server does), so styling
# works immediately regardless of DEBUG or whether collectstatic has ever
# been run. For a real production deployment behind Nginx/a CDN you'd
# still want to run collectstatic + turn this off for best performance,
# but for this app's actual deployment pattern (single small server,
# `python manage.py runserver` or gunicorn), reliability matters more.
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # NOT the Manifest variant on purpose: ManifestStaticFilesStorage
        # requires `collectstatic` to have run (it needs a manifest file
        # mapping names to hashed filenames), and raises a hard error via
        # {% static %} — including inside Django Admin's own templates —
        # if that manifest doesn't exist. This plain Compressed storage
        # still gzips/brotli-compresses responses but resolves URLs
        # directly, so the app (including /django-admin/) never breaks
        # just because collectstatic wasn't run.
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/home/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# ── Security ─────────────────────────────────────────────────────────────
SESSION_COOKIE_AGE = 28800  # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Cookie/HSTS security is controlled by its OWN explicit switch, not tied
# to DEBUG. This matters: if DEBUG=False is set for a normal local test
# server (http://127.0.0.1, no SSL), Secure cookies would silently stop
# being sent by the browser -> every POST form site-wide fails CSRF
# validation with no obvious cause. Only flip this on once you have a
# real HTTPS domain in front of the app.
USE_HTTPS_SECURE_COOKIES = config('USE_HTTPS_SECURE_COOKIES', default=False, cast=bool)
CSRF_COOKIE_SECURE = USE_HTTPS_SECURE_COOKIES
SESSION_COOKIE_SECURE = USE_HTTPS_SECURE_COOKIES
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = USE_HTTPS_SECURE_COOKIES
SECURE_HSTS_PRELOAD = USE_HTTPS_SECURE_COOKIES

# Simple login-attempt throttling (see apps.core.middleware / views_auth)
LOGIN_ATTEMPT_LIMIT = config('LOGIN_ATTEMPT_LIMIT', default=5, cast=int)
LOGIN_ATTEMPT_WINDOW_SECONDS = config('LOGIN_ATTEMPT_WINDOW_SECONDS', default=300, cast=int)

# ── App metadata ─────────────────────────────────────────────────────────
APP_NAME = "Wahabix Medicare Solution"
APP_VERSION = "1.0"
APP_DEVELOPER = "WAHABIX (Shah Abdul Wahab)"
APP_YEAR = "2026"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO' if not DEBUG else 'DEBUG'},
}
