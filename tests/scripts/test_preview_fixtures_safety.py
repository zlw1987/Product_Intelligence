"""PILOT-UX-WORKBENCH-A1-FU1 — preview database safety (BLOCKER 2).

``scripts/preview_fixtures.py`` previously did::

    name = connections["default"].settings_dict["NAME"]
    if os.path.exists(name):
        os.remove(name)
    call_command("migrate", verbosity=0)

i.e. it DELETED whatever database the configured ``PI_SQLITE_PATH`` pointed
at — production, staging, or the developer's default ``db.sqlite3`` — before
migrating. The correction protects real data BY CONSTRUCTION:

* the script refuses to run without an explicit ``PI_PREVIEW_DB_DIR``;
* it plans a fresh, uniquely named file strictly inside that directory;
* it fails closed if the planned file already exists;
* it never deletes, truncates, overwrites, or replaces any database;
* paths are canonicalized (realpath) before verification;
* the repository root (the default ``db.sqlite3`` location) and
  production / staging / deployment-like directory names are refused;
* every check happens before any database write or migration;
* a pre-existing ``PI_SQLITE_PATH`` is overridden, never honored.

The nodes below prove the rejection matrix. No test uses a real existing
database as a fixture: every "existing database" is a throwaway byte file
created inside pytest's tmp directory, and its byte identity is verified
after every run.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "preview_fixtures.py"
SENTINEL = b"SENTINEL-DATABASE-BYTES-DO-NOT-TOUCH-" * 64


def _load_script_module():
    spec = importlib.util.spec_from_file_location("preview_fixtures_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def pf():
    return _load_script_module()


@pytest.fixture()
def sentinel_file(tmp_path: Path) -> Path:
    f = tmp_path / "realdata" / "db.sqlite3"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(SENTINEL)
    return f


def _sha(f: Path) -> str:
    return hashlib.sha256(f.read_bytes()).hexdigest()


def _fixed_now() -> datetime:
    return datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)


class TestPreviewPlanning:
    """The pure planner: fail-closed, canonical, never destructive."""

    def test_missing_preview_configuration_is_refused(self, pf, monkeypatch, sentinel_file) -> None:
        for bad in (None, "", "   "):
            with pytest.raises(pf.PreviewConfigurationError, match="PI_PREVIEW_DB_DIR"):
                pf.plan_preview_database(
                    bad, base_dir=REPO, now=_fixed_now(), token="t" * 12
                )
        # main() refuses before any database access: a hostile
        # PI_SQLITE_PATH pointing at the sentinel must survive untouched.
        monkeypatch.delenv(pf.PREVIEW_DB_DIR_ENV, raising=False)
        monkeypatch.setenv("PI_SQLITE_PATH", str(sentinel_file))
        assert pf.main() == 2
        assert _sha(sentinel_file) == hashlib.sha256(SENTINEL).hexdigest()

    def test_existing_database_at_target_is_refused(self, pf, tmp_path) -> None:
        preview = tmp_path / "preview"
        preview.mkdir()
        token = "ab12cd34ef56"
        planned = pf.plan_preview_database(
            preview, base_dir=REPO, now=_fixed_now(), token=token
        )
        assert not planned.exists()  # the planner itself never creates files
        # A file with that name (a previous run's database) must be refused,
        # not deleted or overwritten.
        planned.write_bytes(SENTINEL)
        with pytest.raises(pf.PreviewConfigurationError, match="already exists"):
            pf.plan_preview_database(
                preview, base_dir=REPO, now=_fixed_now(), token=token
            )
        assert _sha(planned) == hashlib.sha256(SENTINEL).hexdigest()

    def test_repository_root_is_not_an_authorized_preview_location(self, pf, tmp_path) -> None:
        with pytest.raises(pf.PreviewConfigurationError, match="repository root"):
            pf.plan_preview_database(
                str(REPO), base_dir=REPO, now=_fixed_now(), token="t" * 12
            )
        # ...including when spelled with redundant segments that canonicalize
        # back to the repository root.
        with pytest.raises(pf.PreviewConfigurationError, match="repository root"):
            pf.plan_preview_database(
                str(REPO / "tmp_preview" / ".."),
                base_dir=REPO,
                now=_fixed_now(),
                token="t" * 12,
            )

    def test_production_like_directories_are_refused_matrix(self, pf, tmp_path) -> None:
        module = pf
        for component in sorted(module.FORBIDDEN_PREVIEW_DIR_COMPONENTS):
            d = tmp_path / component
            d.mkdir(exist_ok=True)
            with pytest.raises(module.PreviewConfigurationError, match=re.escape(component)):
                module.plan_preview_database(
                    str(d), base_dir=REPO, now=_fixed_now(), token="t" * 12
                )
        # A nested production-like component is refused too.
        nested = tmp_path / "outer" / "production" / "inner"
        nested.mkdir(parents=True, exist_ok=True)
        with pytest.raises(module.PreviewConfigurationError, match="production"):
            module.plan_preview_database(
                str(nested), base_dir=REPO, now=_fixed_now(), token="t" * 12
            )

    def test_paths_are_canonicalized_before_verification(self, pf, tmp_path) -> None:
        # Traversal that resolves to the repository root is refused on its
        # canonical form, whatever the redundant spelling.
        sneaky_root = REPO / "tmp_preview" / ".."
        with pytest.raises(pf.PreviewConfigurationError, match="repository root"):
            pf.plan_preview_database(
                str(sneaky_root), base_dir=REPO, now=_fixed_now(), token="t" * 12
            )
        # A harmless traversal resolves to the canonical directory and the
        # planned target is canonical (no ".." segments, absolute).
        target_dir = tmp_path / "real"
        target_dir.mkdir()
        spelled = tmp_path / "alias" / ".." / "real"
        planned = pf.plan_preview_database(
            str(spelled), base_dir=REPO, now=_fixed_now(), token="t" * 12
        )
        assert ".." not in planned.parts
        assert planned.is_absolute()
        assert planned.parent == target_dir.resolve()

    def test_planned_target_is_strictly_inside_the_preview_directory(self, pf, tmp_path) -> None:
        nested = tmp_path / "one" / "two"
        nested.mkdir(parents=True)
        planned = pf.plan_preview_database(
            str(nested), base_dir=REPO, now=_fixed_now(), token="ab12cd34ef56"
        )
        assert nested.resolve() in planned.parents  # strictly inside
        assert planned.name.startswith("preview_")
        assert planned.suffix == ".sqlite3"
        assert re.fullmatch(
            r"preview_\d{8}T\d{6}_[0-9a-f]{12}\.sqlite3", planned.name
        ), planned.name


class TestScriptSourceContract:
    """The corrected script cannot delete a database even in principle."""

    def test_script_source_never_deletes_a_database(self, pf) -> None:
        src = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("os.remove", "os.unlink", ".unlink(", "shutil", "rmtree"):
            assert forbidden not in src, f"preview_fixtures.py must not use {forbidden!r}"
        # django.setup() must not run at module import time (no side effects
        # before validation): every occurrence is indented inside a function.
        for line in src.splitlines():
            if "django.setup()" in line:
                assert line.startswith(" "), "django.setup() must not be module-level"

    def test_module_import_has_no_side_effects(self, pf, tmp_path) -> None:
        before = set(tmp_path.iterdir())
        _load_script_module()  # import a second time: still no files created
        assert set(tmp_path.iterdir()) == before
        assert callable(pf.plan_preview_database)
        assert callable(pf.main)
        assert callable(pf.build)


class TestSubprocessFailClosed:
    """End-to-end: the script as an operator would run it."""

    def _run(self, env_overrides: dict, sentinel: Path) -> subprocess.CompletedProcess:
        env = {k: v for k, v in __import__("os").environ.items()
               if k not in ("PI_SQLITE_PATH", "PI_PREVIEW_DB_DIR")}
        env.update(env_overrides)
        # This Windows / Python 3.14 workstation has a documented load-
        # sensitive subprocess-boundary flake class (OSError [WinError 6]
        # "handle is invalid" / [WinError 50] in CreateProcess pipe setup,
        # see the domain-boundaries test history). It corrupts the pipe
        # handles BEFORE the child process exists, so a bounded retry of
        # the spawn is safe and changes no assertion below.
        attempt = 0
        while True:
            attempt += 1
            try:
                return subprocess.run(
                    [sys.executable, "scripts/preview_fixtures.py"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    cwd=REPO,
                    timeout=600,
                )
            except OSError as exc:
                flake = ("WinError 6" in str(exc)) or ("WinError 50" in str(exc))
                if attempt >= 3 or not flake:
                    raise
                __import__("time").sleep(0.5 * attempt)

    def test_refusal_happens_before_any_database_access(self, sentinel_file) -> None:
        r = self._run(
            {"PI_SQLITE_PATH": str(sentinel_file)}, sentinel_file
        )
        assert r.returncode == 2
        assert "REFUSED" in r.stderr
        assert "no database file was created" in r.stderr
        # Nothing was deleted, migrated, or created anywhere near the
        # sentinel: its directory holds exactly the sentinel.
        assert sorted(p.name for p in sentinel_file.parent.iterdir()) == ["db.sqlite3"]
        assert _sha(sentinel_file) == hashlib.sha256(SENTINEL).hexdigest()

    def test_successful_run_creates_only_a_new_unique_file(self, tmp_path, sentinel_file) -> None:
        preview = tmp_path / "preview_run"
        preview.mkdir()
        old = preview / "preview_20200101T000000_deadbeef0001.sqlite3"
        old.write_bytes(SENTINEL)  # a previous run's database
        r = self._run(
            {
                "PI_PREVIEW_DB_DIR": str(preview),
                "PI_SQLITE_PATH": str(sentinel_file),  # hostile: must be ignored
            },
            sentinel_file,
        )
        assert r.returncode == 0, r.stderr
        # The configured PI_SQLITE_PATH database (the sentinel) was never
        # opened, truncated, or deleted.
        assert _sha(sentinel_file) == hashlib.sha256(SENTINEL).hexdigest()
        # The previous preview database is byte-identical.
        assert _sha(old) == hashlib.sha256(SENTINEL).hexdigest()
        new_files = [
            p for p in preview.glob("preview_*.sqlite3") if p != old
        ]
        assert len(new_files) == 1, [p.name for p in preview.iterdir()]
        new_db = new_files[0]
        # The new file is a real migrated, seeded preview database with the
        # eight synthetic runs.
        con = sqlite3.connect(str(new_db))
        try:
            count = con.execute("SELECT COUNT(*) FROM runs_researchrun").fetchone()[0]
        finally:
            con.close()
        assert count == 8
        manifest = json.loads((preview / "preview_urls.json").read_text(encoding="utf-8"))
        assert manifest["preview_db"] == str(new_db)
        assert set(manifest["runs"]) == {
            "multiquote", "zeroquote", "noevidence", "aireview",
            "comparable", "running", "failed", "created",
        }
        assert "nothing deleted" in r.stdout
