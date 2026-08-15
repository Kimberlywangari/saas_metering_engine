"""
Production settings.

Fails loudly at startup if required secrets are missing rather than
silently falling back to insecure defaults. Database configuration is
derived from the DATABASE_URL environment variable.
"""

from urllib.parse import urlparse

from .base import *  # noqa: F401,F403
from .base import os

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. Refusing to start "
        "with an insecure or missing secret key in production."
    )

DEBUG = False

if not ALLOWED_HOSTS:
    raise RuntimeError(
        "ALLOWED_HOSTS environment variable is not set. Refusing to start "
        "in production without an explicit allowed-hosts list."
    )


def _database_config_from_url(database_url: str) -> dict:
    """
    Translate a DATABASE_URL connection string into a Django DATABASES
    entry without requiring a third-party parsing library.

    Supports the two schemes this project cares about:
      - sqlite:///relative/or/absolute/path.sqlite3
      - postgres://user:password@host:port/dbname
    """
    parsed = urlparse(database_url)

    if parsed.scheme == "sqlite":
        # sqlite:///db.sqlite3 -> parsed.path == "/db.sqlite3"
        db_path = parsed.path.lstrip("/")
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / db_path,
        }

    if parsed.scheme in ("postgres", "postgresql"):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
        }

    raise RuntimeError(
        f"Unsupported DATABASE_URL scheme: '{parsed.scheme}'. "
        "Expected 'sqlite' or 'postgres'."
    )


_database_url = os.environ.get("DATABASE_URL", "")
if not _database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. Refusing to start "
        "in production without an explicit database configuration."
    )

DATABASES = {"default": _database_config_from_url(_database_url)}

# Standard hardening for a production deployment sitting behind HTTPS.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
