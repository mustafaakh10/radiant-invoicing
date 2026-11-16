"""Radiant Billing: Django settings.

Everything that differs between your laptop and the server comes from environment
variables, so the same code runs in both places:

  RL_SECRET_KEY         long random string (required on the server)
  RL_DEBUG              "1" on your laptop, unset on the server
  RL_ALLOWED_HOSTS      comma-separated, e.g. "billing.radiantlighting.pk,yourname.pythonanywhere.com"
  RL_CSRF_ORIGINS       comma-separated https origins, e.g. "https://billing.radiantlighting.pk"
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("RL_SECRET_KEY", "")
DEBUG = os.environ.get("RL_DEBUG", "1" if not SECRET_KEY else "0") == "1"
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("Set RL_SECRET_KEY before running with RL_DEBUG off.")
    SECRET_KEY = "dev-only-not-secret"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get(
    "RL_ALLOWED_HOSTS", "localhost,127.0.0.1,.pythonanywhere.com").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("RL_CSRF_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "billing",
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
]

ROOT_URLCONF = "radiant_web.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "radiant_web.wsgi.application"

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_I18N = False
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_USE_FINDERS = True          # works without collectstatic too
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"        # product photos, logo, signature

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 60  # stay signed in on your phone for 60 days

DATA_UPLOAD_MAX_MEMORY_SIZE = 60 * 1024 * 1024   # restoring a backup with photos
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_CONTENT_TYPE_NOSNIFF = True
