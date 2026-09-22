"""Django settings for the Product Intelligence project.

Minimal on purpose. This provides a working Django project that passes
``manage.py check``, persists research runs (PRODUCT-INTEL.1A), and serves the
standalone intake form and report shell (PRODUCT-INTEL.1B). It adds no
authentication, caching, or background processing. Those arrive with the phases
that need them.

Deployment note: the report shell is reachable by anyone who can reach the
server, and a run's UUID is not access control. Report visibility and
authentication are still open questions (§19 of the canonical plan), so this
configuration is for local development and trusted internal use only — a public
deployment needs that decision made first, plus ``DJANGO_DEBUG=0``, a real
``DJANGO_SECRET_KEY``, and real ``DJANGO_ALLOWED_HOSTS``.

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
    # PRODUCT-INTEL.1B: the standalone intake form and report shell. An
    # application only so its templates and URLs have a home — it defines no
    # model, and must not.
    "product_intelligence.web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    # The intake form is a POST, so CSRF protection is required (1B). It is
    # cookie-based and needs no session framework, no user model, and no
    # authentication — none of which this phase introduces.
    "django.middleware.csrf.CsrfViewMiddleware",
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
# PILOT-RELEASE-1: SQLite database location is configurable via environment
# variable to allow the database to live outside the Git checkout. This way
# application upgrades do not risk the durable customer data file.
#
# Contract:
#   - absent PI_SQLITE_PATH: preserve exact current development behavior
#     (BASE_DIR / "db.sqlite3")
#   - present PI_SQLITE_PATH: use the supplied filesystem path for the SQLite
#     database NAME (parent directory must exist; no auto-creation)
#
# SQLite is pilot-only and NOT a scaling architecture decision. PostgreSQL
# may follow after the pilot phase.
_sqlite_path_env = os.environ.get("PI_SQLITE_PATH")
if _sqlite_path_env:
    _db_name = Path(_sqlite_path_env)
else:
    _db_name = BASE_DIR / "db.sqlite3"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _db_name,
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True

# Evidence timestamps must be timezone-aware end to end.
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# PRODUCT-INTEL.4D-C-SEC: Vendor commercial price network access gate.
# Comma-separated CIDR notation (e.g. "10.0.0.0/8,192.168.50.0/24").
# Absent or blank -> DENY all vendor commercial price visibility (fail-closed).
# This setting controls presentation-layer access only; it does not introduce
# authentication, sessions, user models, or modify any research logic.
PI_VENDOR_PRICE_ALLOWED_CIDRS = os.environ.get("PI_VENDOR_PRICE_ALLOWED_CIDRS")
if PI_VENDOR_PRICE_ALLOWED_CIDRS is not None and not PI_VENDOR_PRICE_ALLOWED_CIDRS.strip():
    # Treat blank string as unset — explicit blank still denies.
    PI_VENDOR_PRICE_ALLOWED_CIDRS = None
