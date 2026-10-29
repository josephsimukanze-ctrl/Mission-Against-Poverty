# config/settings.py — Mission Against Poverty
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = [
    "127.0.0.1", "localhost",
    ".ngrok-free.app", ".ngrok-free.dev", ".ngrok.io", ".ngrok.app",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    "crispy_forms",
    "crispy_tailwind",
    "widget_tweaks",
    "django_ngrok",
    "core",
    "accounts",
    "pages",
    "programs",
    "projects",
    "donations",
    "payments",
    "volunteers",
    "partnerships",
    "beneficiaries",
    "events",
    "inventory",
    "finance",
    "news",
    "notifications",
    "contact",
    "reports",
    "audit",
    "settings_app",
    "newsletter",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "audit.middleware.AuditRequestMiddleware",
]

ROOT_URLCONF = "config.urls"

# Root templates dir is optional — only included if it exists.
_ROOT_TEMPLATES = BASE_DIR / "templates"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [_ROOT_TEMPLATES] if _ROOT_TEMPLATES.exists() else [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── Database (Postgres) ─────────────────────────────────────────────
# Production credentials MUST come from .env. The defaults below are
# only for local development and are intentionally obvious placeholders
# so they can't accidentally be valid in production.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="map_db"),
        "USER": config("DB_USER", default="map_user"),
        "PASSWORD": config("DB_PASSWORD", default="CHANGE-ME-IN-ENV"),
        "HOST": config("DB_HOST", default="127.0.0.1"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lusaka"
USE_I18N = True
USE_TZ = True

# ── Static files ────────────────────────────────────────────────────
STATIC_URL = "static/"
STATICFILES_DIRS = [d for d in [BASE_DIR / "static"] if d.exists()]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# ── Media files ─────────────────────────────────────────────────────
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ── Cookies & security headers ──────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Trust proxies (ngrok) for HTTPS detection — safe in both dev and prod.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ── Email ───────────────────────────────────────────────────────────
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@map.local")

# ── Crispy forms ────────────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# ── Organization defaults ───────────────────────────────────────────
ORG_NAME = config("ORG_NAME", default="Mission Against Poverty")
ORG_CURRENCY = config("ORG_CURRENCY", default="ZMW")

# ── Payment provider ────────────────────────────────────────────────
PAYMENT_PROVIDER = config("PAYMENT_PROVIDER", default="mock")
PAYMENT_WEBHOOK_SECRET = config("PAYMENT_WEBHOOK_SECRET", default="dev-secret")

# ── Upload limits ───────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ── CSRF trusted origins ────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = [
    "https://*.ngrok-free.app",
    "https://*.ngrok-free.dev",
    "https://*.ngrok.io",
    "https://*.ngrok.app",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

# ── Organization bank details (shown on /donate/) ───────────────────
ORG_BANK_NAME           = config("ORG_BANK_NAME", default="Zambia National Commercial Bank")
ORG_BANK_ACCOUNT_NAME   = config("ORG_BANK_ACCOUNT_NAME", default="Mission Against Poverty")
ORG_BANK_ACCOUNT_NUMBER = config("ORG_BANK_ACCOUNT_NUMBER", default="1234567890123")
ORG_BANK_BRANCH         = config("ORG_BANK_BRANCH", default="Lusaka Main Branch")
ORG_BANK_SWIFT          = config("ORG_BANK_SWIFT", default="ZANAZMLX")
ORG_PAYMENT_INSTRUCTIONS = config(
    "ORG_PAYMENT_INSTRUCTIONS",
    default=(
        "Please transfer the amount to the account below and include the "
        "reference number. Your donation will be confirmed within 24 hours."
    ),
)
ORG_PAYMENT_CONFIRMATION_HOURS = config("ORG_PAYMENT_CONFIRMATION_HOURS", default=24, cast=int)