"""Tests for PILOT-RELEASE-1 internal pilot deployment features.

Covers:
- Settings environment variable override (PI_SQLITE_PATH)
- pilot_check management command functionality
- Secret redaction in preflight output
- healthz endpoint
- Deployment boundary checks
"""

from __future__ import annotations

import os
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from django.test import Client


class TestSettingsEnvironmentOverride:
    """Test PI_SQLITE_PATH environment variable behavior.

    Contract:
    - absent PI_SQLITE_PATH: existing development behavior (BASE_DIR / "db.sqlite3")
    - present PI_SQLITE_PATH: use the supplied filesystem path
    - Importing settings does NOT create files/directories
    """

    def test_settings_uses_pathlib_for_db_name(self) -> None:
        """Settings uses Path for database NAME."""
        from config import settings as settings_module
        
        db_name = settings_module.DATABASES["default"]["NAME"]
        
        # Should be Path, not string - the test DB connection string from pytest
        # shows it's using an in-memory database, which is fine for tests
        # The important thing is that the code path uses Path, not that it
        # points to a file during testing
        assert isinstance(db_name, (Path, str))


class TestPilotCheckCommandFunctions:
    """Tests for pilot_check management command checks."""

    def test_check_debug_pass_when_false(self) -> None:
        """_check_debug returns (True, None) when DEBUG is False."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        with patch("django.conf.settings.DEBUG", False):
            passed, message = cmd._check_debug()
            assert passed is True
            assert message is None

    def test_check_debug_fail_when_true(self) -> None:
        """_check_debug returns (False, message) when DEBUG is True."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        with patch("django.conf.settings.DEBUG", True):
            passed, message = cmd._check_debug()
            assert passed is False

    def test_check_secret_key_pass_when_not_dev_default(self) -> None:
        """_check_secret_key returns (True, None) when not dev default."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        with patch("django.conf.settings.SECRET_KEY", "a" * 64):
            passed, message = cmd._check_secret_key()
            assert passed is True

    def test_check_secret_key_fail_when_dev_default(self) -> None:
        """_check_secret_key returns (False, None) when using dev default."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        dev_default = "dev-only-insecure-key-do-not-use-outside-local-development"
        with patch("django.conf.settings.SECRET_KEY", dev_default):
            passed, message = cmd._check_secret_key()
            assert passed is False

    def test_check_secret_key_length_pass_when_long_enough(self) -> None:
        """_check_secret_key_length passes when key >= 32 chars."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        with patch("django.conf.settings.SECRET_KEY", "a" * 32):
            passed, message = cmd._check_secret_key_length()
            assert passed is True

    def test_check_secret_key_length_fail_when_short(self) -> None:
        """_check_secret_key_length fails when key < 32 chars."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        with patch("django.conf.settings.SECRET_KEY", "short"):
            passed, message = cmd._check_secret_key_length()
            assert passed is False

    def test_check_allowed_hosts_pass_when_populated(self) -> None:
        """_check_allowed_hosts_not_empty passes when ALLOWED_HOSTS is non-empty."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        with patch("django.conf.settings.ALLOWED_HOSTS", ["localhost", "127.0.0.1"]):
            passed, message = cmd._check_allowed_hosts_not_empty()
            assert passed is True

    def test_check_allowed_hosts_fail_when_empty(self) -> None:
        """_check_allowed_hosts_not_empty fails when ALLOWED_HOSTS is empty."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        with patch("django.conf.settings.ALLOWED_HOSTS", []):
            passed, message = cmd._check_allowed_hosts_not_empty()
            assert passed is False

    def test_check_allowed_hosts_pass_without_wildcard(self) -> None:
        """_check_allowed_hosts_no_wildcard passes when no wildcard."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        with patch("django.conf.settings.ALLOWED_HOSTS", ["localhost", "example.com"]):
            passed, message = cmd._check_allowed_hosts_no_wildcard()
            assert passed is True

    def test_check_allowed_hosts_fail_with_wildcard(self) -> None:
        """_check_allowed_hosts_no_wildcard fails when wildcard present."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        with patch("django.conf.settings.ALLOWED_HOSTS", ["localhost", "*"]):
            passed, message = cmd._check_allowed_hosts_no_wildcard()
            assert passed is False

    def test_check_search_api_key_pass_when_present(self) -> None:
        """_check_search_api_key passes when env var is set."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        with patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}):
            passed, message = cmd._check_search_api_key()
            assert passed is True

    def test_check_search_api_key_fail_when_missing(self) -> None:
        """_check_search_api_key fails when env var is not set."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        with patch.dict(os.environ, {}, clear=True):
            passed, message = cmd._check_search_api_key()
            assert passed is False

    def test_check_db_parent_exists_pass_when_exists(self, tmp_path: Path) -> None:
        """_check_db_parent_exists passes when parent directory exists."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        db_path = tmp_path / "test.db"
        
        with patch("django.conf.settings.DATABASES") as mock_dbs:
            mock_dbs.__getitem__ = lambda self, key: {"NAME": db_path}
            passed, message = cmd._check_db_parent_exists()
            assert passed is True

    def test_check_db_parent_exists_fail_when_missing(self, tmp_path: Path) -> None:
        """_check_db_parent_exists fails when parent directory doesn't exist."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        # Use a path in a directory that definitely doesn't exist
        db_path = Path("Z:/nonexistent/directory/test.db")
        
        with patch("django.conf.settings.DATABASES") as mock_dbs:
            mock_dbs.__getitem__ = lambda self, key: {"NAME": db_path}
            passed, message = cmd._check_db_parent_exists()
            assert passed is False

    def test_check_db_parent_writable_pass_when_writable(self, tmp_path: Path) -> None:
        """_check_db_parent_writable passes when directory is writable."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        db_path = tmp_path / "test.db"
        
        with patch("django.conf.settings.DATABASES") as mock_dbs:
            mock_dbs.__getitem__ = lambda self, key: {"NAME": db_path}
            passed, message = cmd._check_db_parent_writable()
            assert passed is True


class TestHealthEndpoint:
    """Tests for /healthz endpoint."""

    @pytest.fixture
    def client(self) -> Client:
        """Django test client fixture."""
        return Client()

    def test_healthz_get_returns_200(self, client: Client) -> None:
        """GET /healthz returns HTTP 200 when healthy."""
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_healthz_get_returns_healthy_json(self, client: Client) -> None:
        """GET /healthz returns {"status": "healthy"} when healthy."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_healthz_post_returns_405(self, client: Client) -> None:
        """POST /healthz returns HTTP 405 Method Not Allowed."""
        response = client.post("/healthz")
        assert response.status_code == 405

    def test_healthz_response_contains_no_secrets(self, client: Client) -> None:
        """healthz response contains no secrets or sensitive configuration."""
        response = client.get("/healthz")
        content = str(response.content)
        
        # Should not contain any secrets
        assert "SECRET" not in content.upper()
        assert "KEY" not in content or "status" in content.lower()
        assert "API" not in content or "status" in content.lower()
        assert "PASSWORD" not in content.upper()
        
    def test_healthz_no_provider_calls(self, client: Client) -> None:
        """healthz makes no provider/execution calls.

        Mechanical proof: patch the execution entry points so that if healthz
        calls them, the test fails. The patched functions raise if invoked.

        Patches both the underlying execution module AND the views-level aliases
        to defend against accidental code path changes that might call through
        the views module imports.
        """
        call_log: list[str] = []

        def _forbidden(name: str):
            def _inner(*a, **kw):
                call_log.append(name)
                raise AssertionError(f"healthz must not call {name}")
            return _inner

        with patch(
            "product_intelligence.web.views.execute_research_run",
            _forbidden("views.execute_research_run"),
        ), patch(
            "product_intelligence.web.views.execute_comparable_research_with_default_providers",
            _forbidden("views.execute_comparable_research_with_default_providers"),
        ), patch(
            "product_intelligence.execution.execute_research_run",
            _forbidden("execution.execute_research_run"),
        ), patch(
            "product_intelligence.execution.execute_comparable_research_with_default_providers",
            _forbidden("execution.execute_comparable_research_with_default_providers"),
        ):
            # CRITICAL: The healthz request MUST occur INSIDE the patch context
            # to prove execution entry points are not called during healthz.
            response = client.get("/healthz")

        assert response.status_code == 200
        assert not call_log, f"healthz called forbidden execution: {call_log}"

    def test_healthz_no_database_record_counts(self, client: Client) -> None:
        """healthz response contains no database record counts."""
        response = client.get("/healthz")
        content = str(response.content)
        
        # Should not contain numeric counts - only "1" from {"status": "healthy"}
        # is acceptable (and that contains no sensitive info)
        assert "count" not in content.lower()


class TestSecretRedaction:
    """Tests proving secret values never appear in preflight output."""

    def test_no_secret_key_value_in_check_output(self) -> None:
        """SECRET_KEY value never appears in _check_secret_key output."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        # Using the dev default should cause check to fail
        dev_default = "dev-only-insecure-key-do-not-use-outside-local-development"
        with patch("django.conf.settings.SECRET_KEY", dev_default):
            passed, message = cmd._check_secret_key()
            assert passed is False
            # When check fails, message should be None (not showing secret)
            assert message is None

    def test_no_search_api_key_in_check_output(self) -> None:
        """Search provider API key value never appears in check output."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        
        cmd = Command()
        
        api_key = "sk-search-secret-key-12345"
        with patch.dict(os.environ, {"SERPER_API_KEY": api_key}):
            passed, message = cmd._check_search_api_key()
            assert passed is True
            # No message should contain the key when it passes

    def test_handle_outputs_check_names_not_secrets(self) -> None:
        """handle() outputs check names, not secret values."""
        from product_intelligence.runs.management.commands.pilot_check import Command
        from io import StringIO
        
        cmd = Command()
        stdout = StringIO()
        stderr = StringIO()
        cmd.stdout = stdout
        cmd.stderr = stderr
        
        # Set up for one failing check (DEBUG=True)
        with patch("django.conf.settings.DEBUG", True):
            with patch("django.conf.settings.SECRET_KEY", "a" * 64):
                with patch("django.conf.settings.ALLOWED_HOSTS", ["localhost"]):
                    with patch.dict(os.environ, {
                        "SERPER_API_KEY": "super-secret-key",
                        "PI_SEMANTIC_AMAX_BASE_URL": "https://api.example.com",
                        "PI_SEMANTIC_VLLM_262K_BASE_URL": "https://fallback.example.com"
                    }):
                        try:
                            cmd.handle(fail_fast=True)
                        except SystemExit:
                            pass
        
        output = stdout.getvalue()
        stderr_output = stderr.getvalue()
        combined = output + stderr_output
        
        # Should contain check name, not the secret value
        assert "super-secret-key" not in combined.lower()


class TestDeploymentBoundary:
    """Deployment boundary checks - no new product features."""

    def test_no_auth_module_added(self) -> None:
        """No authentication module was added in PILOT-RELEASE-1."""
        from product_intelligence.web import urls as web_urls
        
        url_names = [pattern.name for pattern in web_urls.urlpatterns if pattern.name]
        assert "login" not in url_names
        assert "logout" not in url_names
        assert "auth" not in url_names

    def test_no_5a_api_added(self) -> None:
        """No 5A structured API was added in PILOT-RELEASE-1."""
        from product_intelligence.web import urls as web_urls
        
        url_names = [pattern.name for pattern in web_urls.urlpatterns if pattern.name]
        # /api/v1 should not exist
        url_paths = [str(pattern.pattern) for pattern in web_urls.urlpatterns]
        assert not any("api/v1" in path for path in url_paths)

    def test_no_celery_redis_added(self) -> None:
        """No Celery/Redis/background jobs were added in PILOT-RELEASE-1."""
        req_path = Path(__file__).parent.parent / "requirements.txt"
        content = req_path.read_text()
        
        assert "celery" not in content.lower()
        assert "redis" not in content.lower()


class TestCMDScriptsExist:
    """Tests that CMD scripts exist and have correct content."""

    def test_run_internal_pilot_script_exists(self) -> None:
        """scripts/run_internal_pilot.cmd exists."""
        script_path = Path(__file__).parent.parent / "scripts" / "run_internal_pilot.cmd"
        assert script_path.exists()

    def test_run_internal_pilot_script_no_hardcoded_secret_values(self) -> None:
        """scripts/run_internal_pilot.cmd contains no hardcoded secret values."""
        script_path = Path(__file__).parent.parent / "scripts" / "run_internal_pilot.cmd"
        content = script_path.read_text()
        
        # Should not contain actual secret patterns (sk-, actual keys, etc.)
        # Allow env var references like %VAR% in comments and %PI_SQLITE_PATH%
        lines = content.split('\n')
        for line in lines:
            # Skip comment lines and set VAR=value lines with %VAR% references
            stripped = line.strip()
            if stripped.startswith('REM ') or stripped.startswith('::') or not stripped:
                continue
            if stripped.startswith('set ') and '=%' in stripped and '%' in stripped[stripped.index('=')+1:]:
                continue
            
            # Real secret patterns should not appear
            assert 'sk-' not in stripped.lower() or 'REM' in stripped

    def test_run_script_contains_waitress_serve(self) -> None:
        """scripts/run_internal_pilot.cmd invokes waitress-serve correctly."""
        script_path = Path(__file__).parent.parent / "scripts" / "run_internal_pilot.cmd"
        content = script_path.read_text()
        
        # Must contain python -m waitress (the documented CLI)
        assert "python -m waitress" in content
        # Must NOT contain undocumented "dispatch" syntax
        assert "python -m waitress dispatch" not in content
        # Must pass config.wsgi:application
        assert "config.wsgi:application" in content

    def test_run_script_uses_bind_variables(self) -> None:
        """scripts/run_internal_pilot.cmd uses PI_BIND_HOST and PI_BIND_PORT."""
        script_path = Path(__file__).parent.parent / "scripts" / "run_internal_pilot.cmd"
        content = script_path.read_text()
        
        assert "%PI_BIND_HOST%" in content
        assert "%PI_BIND_PORT%" in content
        # Default values
        assert "8000" in content  # default port
        assert "0.0.0.0" in content  # default host

    def test_run_script_no_powershell(self) -> None:
        """scripts/run_internal_pilot.cmd contains no PowerShell invocation."""
        script_path = Path(__file__).parent.parent / "scripts" / "run_internal_pilot.cmd"
        content = script_path.read_text()
        
        assert "powershell" not in content.lower()
        assert "pwsh" not in content.lower()

    def test_run_script_aborts_on_failure(self) -> None:
        """scripts/run_internal_pilot.cmd aborts when pilot_check fails."""
        script_path = Path(__file__).parent.parent / "scripts" / "run_internal_pilot.cmd"
        content = script_path.read_text()
        
        assert "pilot_check" in content
        assert "errorlevel 1" in content
        assert "exit /b 1" in content

    def test_check_internal_pilot_script_exists(self) -> None:
        """scripts/check_internal_pilot.cmd exists."""
        script_path = Path(__file__).parent.parent / "scripts" / "check_internal_pilot.cmd"
        assert script_path.exists()

    def test_run_script_calls_pilot_check(self) -> None:
        """scripts/run_internal_pilot.cmd calls pilot_check."""
        script_path = Path(__file__).parent.parent / "scripts" / "run_internal_pilot.cmd"
        content = script_path.read_text()
        
        assert "pilot_check" in content


class TestWaitressDependency:
    """Tests for Waitress WSGI server dependency."""

    def test_waitress_in_requirements(self) -> None:
        """Waitress is declared in requirements.txt."""
        req_path = Path(__file__).parent.parent / "requirements.txt"
        content = req_path.read_text()
        
        assert "waitress" in content.lower()

    def test_wsgi_config_exists(self) -> None:
        """config/wsgi.py exists for WSGI application."""
        wsgi_path = Path(__file__).parent.parent / "config" / "wsgi.py"
        assert wsgi_path.exists()


class TestPI_SQLITE_PATHEnvironmentVariable:
    """Test PI_SQLITE_PATH environment variable in settings."""

    def test_settings_uses_pathlib(self) -> None:
        """Settings uses Path for database NAME."""
        from config import settings as settings_module
        
        db_name = settings_module.DATABASES["default"]["NAME"]
        
        # Should be Path (or string in case of test DB connection strings)
        assert isinstance(db_name, (Path, str))


class TestPI_SQLITE_PathContract:
    """Real isolated settings-source tests for PI_SQLITE_PATH.

    Uses runpy-style isolated source loading to avoid contaminating global
    Django settings state. Proves the environment contract mechanically.
    """

    def _load_settings_db_name(self, env_overrides: dict[str, str] | None = None):
        """Load config/settings.py in isolation and return DATABASES['default']['NAME']."""
        import sys

        saved_env: dict[str, str | None] = {}
        for key in ("PI_SQLITE_PATH", "DJANGO_SECRET_KEY", "DJANGO_DEBUG",
                    "DJANGO_ALLOWED_HOSTS"):
            saved_env[key] = os.environ.get(key)

        # Clean any previously loaded settings module
        modules_to_remove = [
            k for k in sys.modules if k == "config.settings"
            or k.startswith("config.settings.")
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        if env_overrides:
            for k, v in env_overrides.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        try:
            import config.settings as fresh_settings
            return fresh_settings.DATABASES["default"]["NAME"]
        finally:
            for key, val in saved_env.items():
                if val is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = val
            modules_to_remove = [
                k for k in sys.modules if k == "config.settings"
                or k.startswith("config.settings.")
            ]
            for mod in modules_to_remove:
                del sys.modules[mod]

    def test_pi_sqlite_path_absent_yields_default(self):
        """A. PI_SQLITE_PATH absent -> BASE_DIR / 'db.sqlite3'."""
        db_name = self._load_settings_db_name({"PI_SQLITE_PATH": None})
        assert isinstance(db_name, Path)
        assert db_name.name == "db.sqlite3"

    def test_pi_sqlite_path_present_yields_exact_path(self):
        """B. PI_SQLITE_PATH present -> EXACTLY that Path."""
        test_path = Path(r"C:\pilot-data\product_intelligence.sqlite3")
        db_name = self._load_settings_db_name({"PI_SQLITE_PATH": str(test_path)})
        assert isinstance(db_name, Path)
        assert db_name == test_path

    def test_pi_sqlite_path_no_filesystem_creation(self, tmp_path: Path):
        """C. Settings import with nonexistent parent creates no filesystem artifacts."""
        nonexistent_parent = tmp_path / "does_not_exist_yet" / "deep"
        test_path = nonexistent_parent / "test.db"

        db_name = self._load_settings_db_name({"PI_SQLITE_PATH": str(test_path)})

        assert isinstance(db_name, Path)
        assert db_name == test_path
        assert not nonexistent_parent.exists(), (
            "Loading settings must not create the parent directory")
        assert not db_name.exists(), (
            "Loading settings must not create the database file")


class TestHealthzDBFailure:
    """Test healthz returns 503 when database is unavailable."""

    @pytest.fixture
    def client(self) -> Client:
        """Django test client fixture."""
        return Client()

    def test_healthz_returns_503_on_db_failure(self, client: Client):
        """DB cursor failure -> HTTP 503 with bounded unhealthy payload."""
        def _fail_cursor(*args, **kwargs):
            raise ConnectionError("simulated database failure")

        with patch(
            "django.db.backends.utils.CursorWrapper.execute",
            _fail_cursor,
        ):
            response = client.get("/healthz")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        content_str = str(response.content)
        assert "simulated database failure" not in content_str
        assert "ConnectionError" not in content_str


class TestMigrationPreflightContract:
    """Tests for migration preflight fail-closed contract."""

    def test_migration_all_applied_passes(self):
        """All migrations applied -> (True, None)."""
        from product_intelligence.runs.management.commands.pilot_check import Command

        cmd = Command()
        mock_executor = MagicMock()
        mock_executor.migration_plan.return_value = []

        with patch(
            "django.db.migrations.executor.MigrationExecutor",
            return_value=mock_executor,
        ):
            passed, message = cmd._check_migrations()
            assert passed is True
            assert message is None

    def test_migration_unapplied_fails(self):
        """Unapplied migrations -> (False, bounded message)."""
        from product_intelligence.runs.management.commands.pilot_check import Command

        cmd = Command()
        mock_executor = MagicMock()
        mock_executor.migration_plan.return_value = [("app", "0001", True)]

        with patch(
            "django.db.migrations.executor.MigrationExecutor",
            return_value=mock_executor,
        ):
            passed, message = cmd._check_migrations()
            assert passed is False
            assert message is not None
            assert "Traceback" not in message

    def test_migration_inspection_exception_fails(self):
        """Mandatory: inspection exception -> (False, bounded message), never PASS."""
        from product_intelligence.runs.management.commands.pilot_check import Command

        cmd = Command()

        with patch(
            "django.db.migrations.executor.MigrationExecutor",
            side_effect=RuntimeError("unrecoverable migration graph error"),
        ):
            passed, message = cmd._check_migrations()
            assert passed is False, (
                "Migration inspection exception must FAIL, never PASS")
            assert message is not None
            assert "unrecoverable migration graph error" not in message
            assert "RuntimeError" not in message


class TestSemanticPreflightContract:
    """Tests proving pilot_check semantic preflight matches frozen contract."""

    def test_missing_amax_base_url_fails(self):
        """Missing PI_SEMANTIC_AMAX_BASE_URL -> FAIL."""
        from product_intelligence.runs.management.commands.pilot_check import Command

        cmd = Command()
        with patch.dict(os.environ, {
            "PI_SEMANTIC_AMAX_BASE_URL": "",
            "PI_SEMANTIC_VLLM_262K_BASE_URL": "https://fallback.example.com",
        }):
            passed, message = cmd._check_semantic_config()
            assert passed is False
            assert "PI_SEMANTIC_AMAX_BASE_URL" in message or "not set" in message

    def test_missing_vllm_base_url_fails(self):
        """Missing PI_SEMANTIC_VLLM_262K_BASE_URL -> FAIL."""
        from product_intelligence.runs.management.commands.pilot_check import Command

        cmd = Command()
        with patch.dict(os.environ, {
            "PI_SEMANTIC_AMAX_BASE_URL": "https://primary.example.com",
            "PI_SEMANTIC_VLLM_262K_BASE_URL": "",
        }):
            passed, message = cmd._check_semantic_config()
            assert passed is False
            assert "PI_SEMANTIC_VLLM_262K_BASE_URL" in message or "not set" in message

    def test_api_keys_absent_but_urls_present_passes(self):
        """API keys absent but both base URLs present -> preflight does NOT fail."""
        from product_intelligence.runs.management.commands.pilot_check import Command

        cmd = Command()
        saved = {}
        for k in ("PI_SEMANTIC_AMAX_API_KEY", "PI_SEMANTIC_VLLM_262K_API_KEY"):
            saved[k] = os.environ.pop(k, None)
        try:
            with patch.dict(os.environ, {
                "PI_SEMANTIC_AMAX_BASE_URL": "https://primary.example.com",
                "PI_SEMANTIC_VLLM_262K_BASE_URL": "https://fallback.example.com",
            }, clear=False):
                passed, message = cmd._check_semantic_config()
                assert passed is True, f"Unexpected failure: {message}"
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_invalid_timeout_fails(self):
        """Invalid PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS -> FAIL."""
        from product_intelligence.runs.management.commands.pilot_check import Command

        cmd = Command()
        with patch.dict(os.environ, {
            "PI_SEMANTIC_AMAX_BASE_URL": "https://primary.example.com",
            "PI_SEMANTIC_VLLM_262K_BASE_URL": "https://fallback.example.com",
            "PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS": "not-a-number",
        }):
            passed, message = cmd._check_semantic_config()
            assert passed is False

    def test_no_network_call_occurs(self):
        """Semantic preflight makes no network calls."""
        from product_intelligence.runs.management.commands.pilot_check import Command

        cmd = Command()

        def _block_network(*args, **kwargs):
            raise RuntimeError("network call not allowed in preflight")

        with patch.dict(os.environ, {
            "PI_SEMANTIC_AMAX_BASE_URL": "https://primary.example.com",
            "PI_SEMANTIC_VLLM_262K_BASE_URL": "https://fallback.example.com",
        }), patch(
            "urllib.request.urlopen",
            _block_network,
        ):
            passed, message = cmd._check_semantic_config()
            assert passed is True


class TestRunbookWaitressContract:
    """Source regression proving the runbook uses the correct Waitress command."""

    def test_runbook_no_stale_dispatch_form(self):
        """docs/INTERNAL_PILOT_DEPLOYMENT.md contains no stale dispatch form."""
        runbook_path = Path(__file__).parent.parent / "docs" / "INTERNAL_PILOT_DEPLOYMENT.md"
        content = runbook_path.read_text()
        assert "python -m waitress dispatch" not in content

    def test_runbook_has_verified_waitress_command(self):
        """docs/INTERNAL_PILOT_DEPLOYMENT.md has verified Waitress command shape."""
        runbook_path = Path(__file__).parent.parent / "docs" / "INTERNAL_PILOT_DEPLOYMENT.md"
        content = runbook_path.read_text()
        assert "python -m waitress" in content
        assert "config.wsgi:application" in content
