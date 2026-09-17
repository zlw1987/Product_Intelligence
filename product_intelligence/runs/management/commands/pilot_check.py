"""Internal pilot preflight validation command (PILOT-RELEASE-1).

This is an OPERATIONAL validation command. It does NOT:
- Execute research
- Call the search provider
- Call an LLM
- Make network calls (beyond minimal Django database check)
- Mutate database/business state

It validates production-readiness checks at minimum:
1. DEBUG is False
2. SECRET_KEY is not the repository development default
3. SECRET_KEY is non-empty and has a reasonable minimum length
4. ALLOWED_HOSTS is non-empty
5. ALLOWED_HOSTS does not contain unrestricted wildcard "*"
6. Search provider API key exists and is non-blank
7. SQLite database parent directory exists
8. SQLite database parent directory is writable (non-destructive check)
9. Django database connectivity succeeds
10. Required migrations are applied
11. Semantic production configuration can be validated WITHOUT network calls

Exit codes:
- 0: All checks passed
- Non-zero: One or more checks failed

Output is safe: no secret values appear in failure messages.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Run internal pilot preflight validation checks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="Stop at the first failure (default: run all checks)",
        )

    def handle(self, *args, **options):
        fail_fast = options["fail_fast"]
        all_passed = True
        failures: list[str] = []

        checks = [
            ("DEBUG must be disabled", self._check_debug),
            ("DJANGO_SECRET_KEY is not production-safe", self._check_secret_key),
            ("DJANGO_SECRET_KEY is non-empty and has minimum length", self._check_secret_key_length),
            ("DJANGO_ALLOWED_HOSTS is non-empty", self._check_allowed_hosts_not_empty),
            ("DJANGO_ALLOWED_HOSTS contains no wildcard", self._check_allowed_hosts_no_wildcard),
            ("search provider API key is present", self._check_search_api_key),
            ("SQLite database parent directory exists", self._check_db_parent_exists),
            ("SQLite database parent directory is writable", self._check_db_parent_writable),
            ("database connection succeeds", self._check_db_connection),
            ("required migrations are applied", self._check_migrations),
            ("semantic provider configuration is complete", self._check_semantic_config),
        ]

        for name, check_fn in checks:
            passed, message = check_fn()
            if passed:
                self.stdout.write(f"[PASS] {name}")
            else:
                self.stdout.write(f"[FAIL] {name}")
                if message:
                    self.stdout.write(f"       {message}")
                all_passed = False
                failures.append(name)
                if fail_fast:
                    break

        self.stdout.write("")
        if all_passed:
            self.stdout.write(self.style.SUCCESS("Product Intelligence internal pilot preflight: PASS"))
            sys.exit(0)
        else:
            self.stdout.write(self.style.ERROR("Product Intelligence internal pilot preflight: FAIL"))
            self.stdout.write("")
            self.stdout.write("Failed checks:")
            for f in failures:
                self.stdout.write(f"  - {f}")
            sys.exit(1)

    # -------------------------------------------------------------------------
    # Individual checks
    # -------------------------------------------------------------------------

    def _check_debug(self) -> tuple[bool, str | None]:
        """Check that DEBUG is False."""
        from django.conf import settings
        if settings.DEBUG:
            return False, "DEBUG is True; production requires DEBUG=0"
        return True, None

    def _check_secret_key(self) -> tuple[bool, str | None]:
        """Check that SECRET_KEY is not the development default."""
        from django.conf import settings
        dev_default = "dev-only-insecure-key-do-not-use-outside-local-development"
        if settings.SECRET_KEY == dev_default:
            return False, None
        return True, None

    def _check_secret_key_length(self) -> tuple[bool, str | None]:
        """Check that SECRET_KEY is non-empty and has minimum length."""
        from django.conf import settings
        key = settings.SECRET_KEY
        if not key or len(key) < 32:
            return False, f"Secret key too short ({len(key)} chars); minimum 32 required"
        return True, None

    def _check_allowed_hosts_not_empty(self) -> tuple[bool, str | None]:
        """Check that ALLOWED_HOSTS is non-empty."""
        from django.conf import settings
        if not settings.ALLOWED_HOSTS:
            return False, None
        return True, None

    def _check_allowed_hosts_no_wildcard(self) -> tuple[bool, str | None]:
        """Check that ALLOWED_HOSTS contains no unrestricted wildcard."""
        from django.conf import settings
        if "*" in settings.ALLOWED_HOSTS:
            return False, None
        return True, None

    def _check_search_api_key(self) -> tuple[bool, str | None]:
        """Check that the search provider API key exists and is non-blank."""
        key = os.environ.get("SERPER_API_KEY", "").strip()
        if not key:
            return False, None
        return True, None

    def _check_db_parent_exists(self) -> tuple[bool, str | None]:
        """Check that the SQLite database parent directory exists."""
        from django.conf import settings
        db_name = settings.DATABASES["default"]["NAME"]
        parent = Path(db_name).parent
        if not parent.exists():
            return False, f"Database parent directory does not exist: {parent}"
        return True, None

    def _check_db_parent_writable(self) -> tuple[bool, str | None]:
        """Check that the SQLite database parent directory is writable.

        Uses a NON-DESTRUCTIVE check: creates and immediately removes a
        temporary file in the directory. This does not affect existing data.
        """
        from django.conf import settings
        db_name = settings.DATABASES["default"]["NAME"]
        parent = Path(db_name).parent

        try:
            # Non-destructive: create temp file and remove it immediately
            with tempfile.NamedTemporaryFile(dir=parent, delete=True, prefix="pilot_check_") as f:
                pass  # File is created and automatically deleted when context exits
            return True, None
        except (OSError, PermissionError, IOError) as e:
            return False, f"Database parent directory is not writable: {parent} ({e})"

    def _check_db_connection(self) -> tuple[bool, str | None]:
        """Check that Django can connect to the database."""
        try:
            with connection.cursor() as cursor:
                # Simple connectivity check - just execute a no-op
                cursor.execute("SELECT 1")
            return True, None
        except Exception as e:
            return False, f"Database connection failed: {type(e).__name__}"

    def _check_migrations(self) -> tuple[bool, str | None]:
        """Check that all required migrations are applied.

        Uses Django's MigrationExecutor for a direct read-only inspection
        of the migration graph. Fails closed if the graph cannot be read.
        """
        from django.db.migrations.executor import MigrationExecutor

        try:
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if plan:
                return False, f"{len(plan)} migration(s) are not applied"
            return True, None
        except Exception:
            return False, "Migration state could not be verified"

    def _check_semantic_config(self) -> tuple[bool, str | None]:
        """Validate semantic provider configuration without making network calls.

        This reuses the frozen production configuration/transport-construction
        boundaries. It does NOT duplicate the semantic provider/model route or
        alter frozen runtime code. It validates the EXISTING required
        configuration inputs through an operational adapter.

        No API keys, endpoint URLs, or credentials appear in output.
        """
        # Check primary provider configuration
        amax_base_url = os.environ.get("PI_SEMANTIC_AMAX_BASE_URL", "").strip()
        if not amax_base_url:
            return False, "PI_SEMANTIC_AMAX_BASE_URL is not set"

        # Check fallback provider configuration
        vllm_base_url = os.environ.get("PI_SEMANTIC_VLLM_262K_BASE_URL", "").strip()
        if not vllm_base_url:
            return False, "PI_SEMANTIC_VLLM_262K_BASE_URL is not set"

        # Validate that the config can be constructed (without calling the network)
        try:
            from product_intelligence.semantic.runtime import SemanticRuntimeConfig
            from product_intelligence.semantic.runtime import validate_runtime_config

            config = SemanticRuntimeConfig.from_environment()
            validate_runtime_config(config)
            return True, None
        except Exception:
            # Don't expose exception details; just report the check failed
            return False, "Semantic runtime configuration validation failed"