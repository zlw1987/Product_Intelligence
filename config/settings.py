"""Django settings for the Product Intelligence project.

Minimal on purpose. This provides a working Django project that passes
``manage.py check`` and persists research runs (PRODUCT-INTEL.1A); it adds no
authentication, caching, or background processing. Those arrive with the phases
that need them.

Nothing here imports from ``product_intelligence.domain``: the domain layer
must stay usable without Django.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Development default only. Any real deployment must supply
# DJANGO_SECRET_KEY from the server environment. Secrets never live in the
# repository, and never in a calling system.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-insecure-key-do-not-use-outside-local-development",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    # PRODUCT-INTEL.1A: the persistent research-run lifecycle. It is the only
    # application with models. `product_intelligence.domain` stays importable
    # without any of this.
    "product_intelligence.runs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Relational persistence is the approved direction. SQLite is the development
# database for this phase; it is deliberately not swapped for a server database
# merely because one is planned, and no production deployment configuration is
# introduced here.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True

# Evidence timestamps must be timezone-aware end to end.
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
