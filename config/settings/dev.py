"""
Development settings.

Optimized for local iteration: verbose errors, permissive host list, and a
local SQLite database so no external services are required to get started.
"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, os

# Local development is allowed to run with DEBUG on even if the .env file
# doesn't explicitly set it, since there is no risk of leaking a production
# secret key here.
DEBUG = os.environ.get("DEBUG", "True") == "True"

# A hardcoded fallback is acceptable here ONLY because this file is never
# used in production (prod.py requires SECRET_KEY to be set via the
# environment and will refuse to start otherwise).
if not SECRET_KEY:
    SECRET_KEY = "django-insecure-dev-only-secret-key-do-not-use-in-production"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Surface every email that would otherwise be sent to stdout during local
# development instead of attempting a real SMTP connection.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
