"""
Base settings shared by all environments.

Environment-specific settings (dev.py, prod.py) import everything from this
module with `from .base import *` and then override or extend as needed.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# BASE_DIR points at the repository root (two levels up from this file:
# config/settings/base.py -> config/settings -> config -> repo root).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load variables from a .env file at the repo root, if present. In real
# deployments the platform may inject environment variables directly, in
# which case this is a harmless no-op.
load_dotenv(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
# We deliberately do NOT hardcode a fallback secret for production use;
# dev.py supplies a safe insecure default for local development only.
SECRET_KEY = os.environ.get("SECRET_KEY", "")

# DEBUG is off by default here; dev.py flips it on explicitly.
DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.subscriptions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Default database configuration. dev.py and prod.py override this to point
# at SQLite (local development) or a DATABASE_URL-driven backend
# (production) respectively.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
