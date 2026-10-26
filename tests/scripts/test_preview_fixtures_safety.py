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

PILOT-UX-WORKBENCH-A1-FU2 adds the explicit containment policy: preview
output is permitted ONLY beneath the canonical, repository-local
disposable preview root (``<worktree>/tmp_preview``), and the real
Product Intelligence production directory names (the AMAX application /
data / backup / service directories — ``C:\\Product_Intelligence``,
``C:\\ProductIntelligenceData``, ``C:\\ProductIntelligenceBackup``,
``C:\\ProductIntelligenceService``) are refused in any case spelling and
at any depth, on canonical paths (never by string prefix). The preview
URL manifest (``preview_urls.json``) must also stay inside the authorized
directory and is never overwritten.

The nodes below prove the rejection matrix. No test uses a real existing
database as a fixture: every "existing database" is a throwaway byte file
created inside pytest's tmp directory, and its byte identity is verified
after every run. Where the FU2 containment rule requires it, test
fixtures point at uniquely named, self-cleaning subdirectories of the
authorized repository-local preview root instead of at arbitrary tmp
directories; every assertion is preserved or strengthened.
"""

from __future__ import annotations

import builtins
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import types
import uuid
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


@pytest.fixture()
def authorized_preview_subdir() -> Path:
    """A fresh, uniquely named subdirectory of the authorized repository-
    local disposable preview root (``REPO/tmp_preview``), as the FU2
    containment policy requires. The test owns it; it is removed in
    teardown (it contains only test artifacts, never existing files).
    """
    root = REPO / "tmp_preview"
    root.mkdir(parents=True, exist_ok=True)
    sub = root / f"pytest_{uuid.uuid4().hex}"
    sub.mkdir()
    yield sub
    shutil.rmtree(sub)


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

    def test_existing_database_at_target_is_refused(self, pf, authorized_preview_subdir) -> None:
        # FU2: the designated preview directory must be inside the
        # authorized repository-local root; the fixture adapts to that.
        preview = authorized_preview_subdir
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

    def test_paths_are_canonicalized_before_verification(self, pf, authorized_preview_subdir) -> None:
        # Traversal that resolves to the repository root is refused on its
        # canonical form, whatever the redundant spelling.
        sneaky_root = REPO / "tmp_preview" / ".."
        with pytest.raises(pf.PreviewConfigurationError, match="repository root"):
            pf.plan_preview_database(
                str(sneaky_root), base_dir=REPO, now=_fixed_now(), token="t" * 12
            )
        # A harmless traversal resolves to the canonical directory and the
        # planned target is canonical (no ".." segments, absolute). FU2:
        # the authorized location is a subdirectory of the repository-
        # local preview root, reached through a redundant ".." spelling.
        target_dir = authorized_preview_subdir / "real"
        target_dir.mkdir()
        spelled = authorized_preview_subdir / "alias" / ".." / "real"
        planned = pf.plan_preview_database(
            str(spelled), base_dir=REPO, now=_fixed_now(), token="t" * 12
        )
        assert ".." not in planned.parts
        assert planned.is_absolute()
        assert planned.parent == target_dir.resolve()

    def test_planned_target_is_strictly_inside_the_preview_directory(self, pf, authorized_preview_subdir) -> None:
        # FU2: the preview directory is inside the authorized root.
        nested = authorized_preview_subdir / "one" / "two"
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

    def test_successful_run_creates_only_a_new_unique_file(self, sentinel_file) -> None:
        # FU2: the designated preview directory must be inside the
        # authorized repository-local root (REPO/tmp_preview), not an
        # arbitrary tmp directory. A unique, self-cleaning subdirectory is
        # used so the test never touches pre-existing operator files.
        preview = REPO / "tmp_preview" / f"preview_run_{uuid.uuid4().hex[:12]}"
        preview.mkdir(parents=True)
        try:
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
            # The configured PI_SQLITE_PATH database (the sentinel) was
            # never opened, truncated, or deleted.
            assert _sha(sentinel_file) == hashlib.sha256(SENTINEL).hexdigest()
            # The previous preview database is byte-identical.
            assert _sha(old) == hashlib.sha256(SENTINEL).hexdigest()
            new_files = [
                p for p in preview.glob("preview_*.sqlite3") if p != old
            ]
            assert len(new_files) == 1, [p.name for p in preview.iterdir()]
            new_db = new_files[0]
            # The new file is a real migrated, seeded preview database with
            # the eight synthetic runs.
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
        finally:
            shutil.rmtree(preview)


class TestAMAXProductionDirectoryNames:
    """PILOT-UX-WORKBENCH-A1-FU2 — the real Product Intelligence
    production directory names (the AMAX application, data, backup, and
    service directories) are refused: top-level, nested, and in any case
    spelling, by canonical path component (never by string prefix).
    """

    #: The production directory names exactly as documented for the AMAX
    #: production layout.
    AMAX_PRODUCTION_COMPONENTS = (
        "Product_Intelligence",
        "ProductIntelligenceData",
        "ProductIntelligenceBackup",
        "ProductIntelligenceService",
    )

    def test_the_production_name_set_covers_the_amax_layout(self, pf) -> None:
        protected = {c.lower() for c in self.AMAX_PRODUCTION_COMPONENTS}
        assert protected <= set(pf.PRODUCTION_PREVIEW_DIR_COMPONENTS)

    def test_amax_production_directory_names_are_refused(self, pf, tmp_path) -> None:
        for component in self.AMAX_PRODUCTION_COMPONENTS:
            d = tmp_path / component
            d.mkdir(exist_ok=True)
            with pytest.raises(
                pf.PreviewConfigurationError, match=re.escape(component)
            ):
                pf.plan_preview_database(
                    str(d), base_dir=REPO, now=_fixed_now(), token="t" * 12
                )
            # The planner is pure: a refused directory is left untouched.
            assert list(d.iterdir()) == []

    def test_nested_production_names_are_refused(self, pf, tmp_path) -> None:
        for component in self.AMAX_PRODUCTION_COMPONENTS:
            nested = tmp_path / "outer" / component / "inner"
            nested.mkdir(parents=True)
            with pytest.raises(
                pf.PreviewConfigurationError, match=re.escape(component)
            ):
                pf.plan_preview_database(
                    str(nested), base_dir=REPO, now=_fixed_now(), token="t" * 12
                )

    def test_differently_cased_production_names_are_refused(self, pf, tmp_path) -> None:
        variants = (
            "product_intelligence",
            "PRODUCT_INTELLIGENCE",
            "ProductIntelligence",
            "productintelligencedata",
            "PRODUCTINTELLIGENCEDATA",
            "ProductIntelligenceBACKUP",
            "productintelligencebackup",
            "PRODUCTINTELLIGENCEBACKUP",
            "productintelligenceservice",
            "ProductIntelligenceSERVICE",
            "PRODUCTINTELLIGENCESERVICE",
        )
        for index, variant in enumerate(variants):
            # A distinct parent per variant: the filesystem is
            # case-insensitive, and each variant must exist on disk under
            # exactly the spelling being asserted in the refusal message.
            d = tmp_path / f"case_{index}" / variant
            d.mkdir(parents=True)
            with pytest.raises(
                pf.PreviewConfigurationError, match=re.escape(variant)
            ):
                pf.plan_preview_database(
                    str(d), base_dir=REPO, now=_fixed_now(), token="t" * 12
                )

    def test_documented_amax_production_paths_are_refused(self, pf) -> None:
        # The exact documented production paths, top-level and nested.
        # They do not exist on this workstation; the planner is pure (no
        # I/O) and refuses them by canonical name without touching them.
        # The same refusal holds if they do exist.
        for raw in (
            r"C:\Product_Intelligence",
            r"C:\Product_Intelligence\sub",
            r"C:\ProductIntelligenceData",
            r"C:\ProductIntelligenceData\sqlite",
            r"C:\ProductIntelligenceBackup",
            r"C:\ProductIntelligenceBackup\full",
            r"C:\ProductIntelligenceService",
            r"C:\ProductIntelligenceService\bin",
        ):
            with pytest.raises(pf.PreviewConfigurationError, match="production"):
                pf.plan_preview_database(
                    raw, base_dir=REPO, now=_fixed_now(), token="t" * 12
                )


class TestPreviewContainmentRoot:
    """PILOT-UX-WORKBENCH-A1-FU2 — preview output is permitted only
    beneath the canonical repository-local disposable preview root
    (``<worktree>/tmp_preview``), checked on canonical paths, and the
    preview URL manifest is never overwritten.
    """

    def test_paths_outside_the_authorized_preview_root_are_refused(self, pf, tmp_path) -> None:
        for d in (tmp_path / "elsewhere", tmp_path / "elsewhere" / "nested"):
            d.mkdir(parents=True, exist_ok=True)
            with pytest.raises(pf.PreviewConfigurationError, match="tmp_preview"):
                pf.plan_preview_database(
                    str(d), base_dir=REPO, now=_fixed_now(), token="t" * 12
                )

    def test_allowed_paths_within_the_canonical_preview_root(self, pf, authorized_preview_subdir) -> None:
        # A subdirectory of the canonical root is an authorized location;
        # the planned target stays strictly inside it with the unique name
        # and the planner itself creates nothing.
        planned = pf.plan_preview_database(
            str(authorized_preview_subdir),
            base_dir=REPO,
            now=_fixed_now(),
            token="ab12cd34ef56",
        )
        assert authorized_preview_subdir.resolve() in planned.parents
        assert planned.name == "preview_20261023T120000_ab12cd34ef56.sqlite3"
        assert not planned.exists()  # the planner itself never creates files
        # Deeper subdirectories of the authorized root are allowed too.
        deeper = authorized_preview_subdir / "deeper"
        deeper.mkdir()
        planned_deeper = pf.plan_preview_database(
            str(deeper), base_dir=REPO, now=_fixed_now(), token="cd34ef56ab12"
        )
        assert deeper.resolve() in planned_deeper.parents

    def test_symlinked_directory_escaping_the_root_is_refused(self, pf, tmp_path, authorized_preview_subdir) -> None:
        # A directory symlink inside the authorized root whose canonical
        # target is OUTSIDE it is refused on its canonical form — no
        # symlink escape.
        outside = tmp_path / "outside"
        outside.mkdir()
        link = authorized_preview_subdir / "escape"
        os.symlink(str(outside), str(link), target_is_directory=True)
        try:
            with pytest.raises(pf.PreviewConfigurationError, match="tmp_preview"):
                pf.plan_preview_database(
                    str(link), base_dir=REPO, now=_fixed_now(), token="t" * 12
                )
        finally:
            link.unlink()  # remove the test's own symlink
        # The planner is pure: the escape target is untouched.
        assert list(outside.iterdir()) == []

    def test_preview_directory_that_is_a_file_is_refused(self, pf, authorized_preview_subdir) -> None:
        f = authorized_preview_subdir / "not_a_directory"
        f.write_bytes(b"blocked")
        with pytest.raises(pf.PreviewConfigurationError, match="not a directory"):
            pf.plan_preview_database(
                str(f), base_dir=REPO, now=_fixed_now(), token="t" * 12
            )
        assert f.read_bytes() == b"blocked"

    def test_preview_urls_manifest_never_overwritten(self, pf, authorized_preview_subdir) -> None:
        # A pre-existing preview_urls.json in the designated directory is
        # an unrelated pre-existing file: the run is refused before any
        # write and the manifest's bytes survive unchanged.
        manifest = authorized_preview_subdir / "preview_urls.json"
        manifest.write_bytes(SENTINEL)
        with pytest.raises(pf.PreviewConfigurationError, match="preview_urls.json"):
            pf.plan_preview_database(
                str(authorized_preview_subdir),
                base_dir=REPO,
                now=_fixed_now(),
                token="ab12cd34ef56",
            )
        assert _sha(manifest) == hashlib.sha256(SENTINEL).hexdigest()
        # No database file was planned or created in the refused directory.
        assert [p.name for p in authorized_preview_subdir.iterdir()] == ["preview_urls.json"]


class TestExclusiveCreation:
    """PILOT-UX-WORKBENCH-A1-FU3 — atomic exclusive creation (open mode
    ``"x"`` / O_CREAT|O_EXCL).

    The FU2 checks were fail-closed but TOCTOU-open: a file that appears
    BETWEEN validation and the write could still be truncated (manifest)
    or migrated (database). The exclusive-create mechanism closes that
    window: creation either atomically takes a fresh path or refuses.
    The nodes below occupy the window deterministically — a competing
    creation at the exact moment of the exclusive open, patched into
    ``builtins.open`` (the competing write itself uses C-level
    ``os.open`` and cannot recurse) — and verify byte-for-byte
    preservation of the pre-existing sentinel content. No retries are
    used anywhere: a refused creation is a refusal, not a retryable
    condition.
    """

    def _simulate_late_creation(
        self, monkeypatch: pytest.MonkeyPatch, victim: Path, sentinel: bytes
    ) -> None:
        """A competing process creates ``victim`` at the exact moment the
        script performs its exclusive open on it (the validation->open
        window). The delegated real open then sees the path taken and
        raises FileExistsError, exactly as a concurrent creator would.
        """
        real_open = builtins.open

        def racing_open(file, *args, **kwargs):
            if (
                isinstance(file, (str, os.PathLike))
                and Path(file) == victim
                and not victim.exists()
            ):
                fd = os.open(
                    str(victim), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644
                )
                with os.fdopen(fd, "wb") as competing:
                    competing.write(sentinel)
            return real_open(file, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", racing_open)

    def _fake_django(
        self, monkeypatch: pytest.MonkeyPatch, configured_name: str
    ) -> dict:
        """Install a fake ``django`` package in sys.modules whose only
        behavior is to report the configured database name and to record
        any call_command (refusing it loudly). monkeypatch restores the
        real modules after the test. build() raises at the exclusive
        creation step, long before any project import runs, so no real
        Django machinery is touched while the fakes are installed.
        """
        state = {"call_command_calls": []}

        def _refuse_migration(*args, **kwargs):
            state["call_command_calls"].append((args, kwargs))
            raise AssertionError(
                "migrate must never run against a pre-existing database"
            )

        fake_django = types.ModuleType("django")
        fake_django.setup = lambda: None
        fake_core = types.ModuleType("django.core")
        fake_management = types.ModuleType("django.core.management")
        fake_management.call_command = _refuse_migration
        fake_db = types.ModuleType("django.db")
        fake_db.connections = {
            "default": types.SimpleNamespace(
                settings_dict={"NAME": configured_name}
            )
        }
        fake_django.core = fake_core
        fake_core.management = fake_management
        fake_django.db = fake_db
        monkeypatch.setitem(sys.modules, "django", fake_django)
        monkeypatch.setitem(sys.modules, "django.core", fake_core)
        monkeypatch.setitem(sys.modules, "django.core.management", fake_management)
        monkeypatch.setitem(sys.modules, "django.db", fake_db)
        return state

    def test_exclusive_database_creation_succeeds_on_a_fresh_path(
        self, pf, tmp_path
    ) -> None:
        planned = tmp_path / "fresh_preview.sqlite3"
        pf.create_preview_database_exclusively(planned)
        assert planned.is_file() and not planned.is_symlink()
        assert planned.stat().st_size == 0
        # SQLite compatibility: the fresh 0-byte file is a valid empty
        # database that migrate can create a schema inside.
        con = sqlite3.connect(str(planned))
        try:
            assert con.execute("PRAGMA schema_version").fetchone()[0] == 0
        finally:
            con.close()

    def test_exclusive_database_creation_refuses_a_pre_existing_file_byte_for_byte(
        self, pf, tmp_path
    ) -> None:
        planned = tmp_path / "existing_preview.sqlite3"
        planned.write_bytes(SENTINEL)
        with pytest.raises(RuntimeError, match="preview database"):
            pf.create_preview_database_exclusively(planned)
        assert planned.read_bytes() == SENTINEL
        assert _sha(planned) == hashlib.sha256(SENTINEL).hexdigest()

    def test_exclusive_database_creation_refuses_a_late_appearance_race_byte_for_byte(
        self, pf, tmp_path, monkeypatch
    ) -> None:
        # The planned file does NOT exist at validation time; a competing
        # creator takes it at the exact moment of the exclusive open.
        planned = tmp_path / "race_preview.sqlite3"
        assert not planned.exists()
        self._simulate_late_creation(monkeypatch, planned, SENTINEL)
        with pytest.raises(RuntimeError, match="preview database"):
            pf.create_preview_database_exclusively(planned)
        assert planned.read_bytes() == SENTINEL
        assert _sha(planned) == hashlib.sha256(SENTINEL).hexdigest()

    def test_exclusive_database_creation_refuses_a_dangling_symlink(
        self, pf, tmp_path
    ) -> None:
        planned = tmp_path / "dangling_preview.sqlite3"
        os.symlink(str(tmp_path / "never_created_target"), str(planned))
        with pytest.raises(RuntimeError, match="preview database"):
            pf.create_preview_database_exclusively(planned)
        # The symlink itself is untouched (never followed, never deleted)
        # and its target was never created.
        assert planned.is_symlink()
        assert not (tmp_path / "never_created_target").exists()

    def test_exclusive_manifest_write_creates_the_exact_payload_bytes(
        self, pf, tmp_path
    ) -> None:
        manifest = tmp_path / "preview_urls.json"
        payload = {
            "preview_db": "db",
            "generated_at": "2026-10-23T12:00:00+00:00",
            "runs": {"multiquote": "/research/1"},
        }
        pf.write_preview_manifest_exclusively(manifest, payload)
        assert manifest.read_text(encoding="utf-8") == (
            json.dumps(payload, indent=2) + "\n"
        )

    def test_exclusive_manifest_write_refuses_a_pre_existing_file_byte_for_byte(
        self, pf, tmp_path
    ) -> None:
        manifest = tmp_path / "preview_urls.json"
        manifest.write_bytes(SENTINEL)
        with pytest.raises(RuntimeError, match="preview URL manifest"):
            pf.write_preview_manifest_exclusively(manifest, {"runs": {}})
        assert manifest.read_bytes() == SENTINEL
        assert _sha(manifest) == hashlib.sha256(SENTINEL).hexdigest()

    def test_exclusive_manifest_write_refuses_a_late_appearance_race_byte_for_byte(
        self, pf, tmp_path, monkeypatch
    ) -> None:
        # The TOCTOU window: no manifest at validation time, a competing
        # creator takes the path at the exact moment of the exclusive
        # open. The pre-existing file must survive byte-for-byte.
        manifest = tmp_path / "preview_urls.json"
        assert not manifest.exists()
        self._simulate_late_creation(monkeypatch, manifest, SENTINEL)
        with pytest.raises(RuntimeError, match="preview URL manifest"):
            pf.write_preview_manifest_exclusively(manifest, {"runs": {}})
        assert manifest.read_bytes() == SENTINEL
        assert _sha(manifest) == hashlib.sha256(SENTINEL).hexdigest()

    def test_build_never_migrates_a_database_that_appeared_after_planning(
        self, pf, monkeypatch, authorized_preview_subdir
    ) -> None:
        planned = pf.plan_preview_database(
            str(authorized_preview_subdir),
            base_dir=REPO,
            now=_fixed_now(),
            token="ab12cd34ef56",
        )
        manifest = planned.parent / "preview_urls.json"
        # Late appearance: a concurrent process / newly appearing file
        # takes the planned path AFTER the planner validated it.
        planned.write_bytes(SENTINEL)
        state = self._fake_django(monkeypatch, str(planned))
        with pytest.raises(RuntimeError, match="preview database"):
            pf.build(planned, manifest)
        assert state["call_command_calls"] == []  # no migration ran
        assert planned.read_bytes() == SENTINEL  # byte-for-byte preserved
        assert not manifest.exists()  # nothing else was written

    def test_build_never_migrates_when_the_database_appears_between_check_and_open(
        self, pf, monkeypatch, authorized_preview_subdir
    ) -> None:
        planned = pf.plan_preview_database(
            str(authorized_preview_subdir),
            base_dir=REPO,
            now=_fixed_now(),
            token="cd34ef56ab12",
        )
        manifest = planned.parent / "preview_urls.json"
        # The window the TOCTOU race lives in: the file passes the
        # exists() re-check and is created by a competing process at the
        # exact moment of the exclusive open, immediately before migrate.
        self._simulate_late_creation(monkeypatch, planned, SENTINEL)
        state = self._fake_django(monkeypatch, str(planned))
        with pytest.raises(RuntimeError, match="preview database"):
            pf.build(planned, manifest)
        assert state["call_command_calls"] == []  # no migration ran
        assert planned.read_bytes() == SENTINEL  # byte-for-byte preserved
        assert not manifest.exists()  # nothing else was written
