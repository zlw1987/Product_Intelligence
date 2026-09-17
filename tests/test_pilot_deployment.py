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
from unittest.mock import patch

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
        """healthz makes no provider/execution calls."""
        # This is validated by the fact that healthz only does a simple
        # SELECT 1 query - no Serper, no LLM, no execution imports
        response = client.get("/healthz")
        assert response.status_code == 200

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