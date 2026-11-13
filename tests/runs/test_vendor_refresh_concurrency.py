"""VREF-R1-3 — GENUINE file-backed concurrency (design section 12,
class C: rows 1, 11, 12, 19, 20; infrastructure per OPEN-O6).

Per the design section 12 legend, concurrency is proven ONLY by C
nodes: genuine independent-connection / independent-process
concurrency against a FILE-based SQLite database, asserting
INVARIANTS (exact call counts, claim counts, row shapes, at-most-one-
new-child) — never timing, except where the locking behavior itself
is the property under test (row 12). The in-memory suite database on
one persistent connection CANNOT demonstrate file-lock behavior (a
fresh connection to an in-memory database sees an empty database),
so every C node here runs its workers in CLEAN SUBPROCESSes over a
temporary file database (the production context: autocommit, no
managed transaction, real RESERVED-lock serialization, the 5.0 s
busy timeout), with a ready/go file handshake for near-simultaneous
starts. The deterministic D portions of these rows live in
``test_vendor_refresh_command.py`` (same directory) and the R1-2
execution suites.

Spawn discipline (the R1-2 record): worker stdin/stdout/stderr are
NOT redirected at all — with any redirection CPython duplicates child
handles (``DuplicateHandle`` / ``_make_inheritable``), the exact call
site of the documented load-sensitive WinError 6/50 pipe-setup flake
class of this Windows / Python 3.14 workstation. Workers write their
own result files instead; a bounded spawn retry (3 attempts) remains
as the last-resort guard (no assertion changes).

Covered C nodes:

* Row 1 / Row 19 — 5 rounds x 4 workers: exactly ONE new child,
  exactly ONE claim UPDATE total, exactly ONE lookup total; the
  losers report IN PROGRESS or COOLDOWN REFUSAL with ZERO trigger /
  claim / construction / lookup (LB-3, sentinel-proven per worker).
* Row 11 — section 9 cases 5 and 6 interleavings (4 workers):
  outside the cooldown window both pass the check but only ONE
  INSERTs; --force-repeat is honored EXACTLY ONCE and never "eaten"
  by the race (the only new child is the forced invocation's).
* Row 12 — real SQLite locking behavior: (a) the zero-row
  lock statement serializes a second writer (blocks until the
  holder's commit, then proceeds on the fresh committed state);
  (b) contention beyond the 5 s busy timeout surfaces bounded
  DATABASE BUSY with non-zero exit and ZERO mutation; (c) a killed
  lock holder releases the file lock and its uncommitted INSERT is
  rolled back (no partial row, no wedge); (d) a reader proceeds
  WHILE a writer holds the lock (rollback journal: SHARED is not
  blocked by RESERVED — the web is not wedged).
* Row 20 — the documented privileged-writer limit, GENUINELY
  concurrent: two independent processes each call the post-claim
  executor directly on the same still-RUNNING orphan child; BOTH
  pass the state re-assert and each reach the lookup (two Vendor
  requests demonstrated); the frozen complete service admits
  EXACTLY ONE terminal write (I3): one process's call returns (T1),
  the other's loses the CAS and its pinned read-only reconciliation
  returns the ACTUAL durable COMPLETED shape (T2) with zero further
  writes. The state re-assert is NOT ownership authentication; the
  terminal CAS bounds terminal writes, NOT external requests.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# The canned lookup MPN (matches every parent created below).
TEST_MPN = "BCM957608-P2200GQF00"

# The lookup sleep widens the race window so near-simultaneous
# starters genuinely overlap while the winner's child is still
# RUNNING / mid-terminalization.
LOOKUP_SLEEP = 0.8

WORKER_DRIVER = r'''
"""VREF-R1-3 C-node worker driver (runs in a clean subprocess over a
temporary FILE-based SQLite database — the production context:
autocommit, no managed transaction, real file-lock semantics).

Usage: python WORKER_DRIVER <json-payload>

The payload carries: db (path), scenario, result (path), ready (path,
optional), go (path, optional — when present the worker writes ready
after full setup and waits for go before acting), and scenario
parameters. The worker writes its JSON result to ``result``; on any
uncaught failure it writes {"error": <traceback>} there instead.
"""
import json
import os
import sys
import time
import traceback

def main():
    payload = json.loads(sys.argv[1])
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    os.environ["PI_SQLITE_PATH"] = payload["db"]
    scenario = payload["scenario"]

    ready = payload.get("ready")
    go = payload.get("go")

    if scenario in ("init", "command", "busy_command", "executor",
                    "lock_a", "lock_b", "uncommitted_insert",
                    "post_kill_writer", "reader", "read_children"):
        import django
        django.setup()

    if scenario == "init":
        out = do_init(payload)
    elif scenario == "command":
        if go is not None:
            handshake(ready, go)
        out = do_command(payload)
    elif scenario == "busy_command":
        time.sleep(payload["delay"])
        out = do_command(payload)
    elif scenario == "executor":
        if go is not None:
            handshake(ready, go)
        out = do_executor(payload)
    elif scenario == "lock_a":
        if go is not None:
            handshake(ready, go)
        out = do_lock_a(payload)
    elif scenario == "lock_b":
        if go is not None:
            handshake(ready, go)
        time.sleep(payload["delay"])
        out = do_lock_b(payload)
    elif scenario == "raw_holder":
        out = do_raw_holder(payload)
    elif scenario == "uncommitted_insert":
        out = do_uncommitted_insert(payload)
    elif scenario == "post_kill_writer":
        out = do_post_kill_writer(payload)
    elif scenario == "reader":
        if go is not None:
            handshake(ready, go)
        time.sleep(payload["delay"])
        out = do_reader(payload)
    elif scenario == "read_children":
        out = {"children": child_rows(payload["parent"])}
    else:
        raise ValueError(f"unknown scenario {scenario!r}")
    with open(payload["result"], "w", encoding="utf-8") as f:
        json.dump(out, f)

def handshake(ready, go):
    with open(ready, "w", encoding="utf-8") as f:
        f.write("ready")
    deadline = time.time() + 120
    while not os.path.exists(go):
        if time.time() > deadline:
            raise TimeoutError("no go signal")
        time.sleep(0.02)

def make_completed_run(mpn, description, tag):
    from product_intelligence.domain import ResearchRequest
    from product_intelligence.domain.enums import ResearchRunState
    from product_intelligence.runs.models import (
        PriceIntelligenceSnapshot, ResearchRun,
    )
    request = ResearchRequest(manufacturer_part_number=mpn, description=description)
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)
    PriceIntelligenceSnapshot.objects.create(
        run=run, schema_version=1,
        payload={
            "request": {"manufacturer_part_number": mpn, "description": description},
            "assessments": [], "buckets": [], "exclusions": [],
            "verification_status": "VERIFIED",
        },
    )
    return run

def frozen_payload():
    from datetime import datetime, timezone as dt_tz
    from product_intelligence.research.commercial_supplement_codec import (
        ResearchSupplementResult, VendorCommercialResult,
        encode_research_supplement_result,
    )
    return encode_research_supplement_result(
        ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="FAILED", retrieved_at=None,
                observations=(), source_issues=(),
            )
        )
    )

def child_rows(parent_id):
    from product_intelligence.runs.models import VendorRefreshExecution
    rows = []
    for c in VendorRefreshExecution.objects.filter(parent_run_id=parent_id).order_by("id"):
        payload = c.result_payload if isinstance(c.result_payload, dict) else {}
        vcr = payload.get("vendor_commercial_result") or {}
        rows.append({
            "id": str(c.id),
            "state": c.state,
            "operator": c.operator,
            "trigger_source": c.trigger_source,
            "requested_mpn": c.requested_mpn,
            "active_slot": c.active_slot,
            "finished_at": c.finished_at.isoformat() if c.finished_at is not None else None,
            "failure_reason": c.failure_reason,
            "lookup_status": vcr.get("lookup_status"),
        })
    return rows

def do_init(payload):
    from datetime import datetime, timedelta, timezone as dt_tz
    from django.core.management import call_command
    from product_intelligence.runs import (
        claim_vendor_refresh, complete_vendor_refresh, trigger_vendor_refresh,
    )
    call_command("migrate", run_syncdb=True, verbosity=0)
    parents = [
        make_completed_run(p["mpn"], p["description"], str(i))
        for i, p in enumerate(payload["parents"])
    ]
    children = {}
    for spec in payload.get("prestate", []):
        parent = parents[spec["parent_index"]]
        if spec["kind"] == "terminal":
            child = claim_vendor_refresh(
                trigger_vendor_refresh(parent.id, operator=spec["operator"]).id
            )
            finished_at = datetime.now(dt_tz.utc) - timedelta(
                seconds=spec.get("finished_offset_seconds", 0)
            )
            complete_vendor_refresh(child.id, 1, frozen_payload(), at=finished_at)
        elif spec["kind"] == "pending":
            child = trigger_vendor_refresh(parent.id, operator=spec["operator"])
        elif spec["kind"] == "running":
            child = claim_vendor_refresh(
                trigger_vendor_refresh(parent.id, operator=spec["operator"]).id
            )
        else:
            raise ValueError(f"unknown prestate kind {spec['kind']!r}")
        children.setdefault(spec["parent_index"], []).append(str(child.id))
    return {
        "parents": [str(p.id) for p in parents],
        "children": children,
    }

def install_command_fakes(payload):
    import product_intelligence.runs.management.commands.vendor_refresh as cmd_module
    from product_intelligence.execution.vendor_refresh import (
        execute_claimed_vendor_refresh,
    )
    from product_intelligence.providers.commercial import (
        CommercialSourceResponse, LookupStatus,
    )
    sleep = payload.get("lookup_sleep", 0.0)
    counters = {"constructions": 0, "lookups": 0, "trigger_calls": 0, "claim_calls": 0}

    class CannedAdapter:
        def lookup(self, query):
            counters["lookups"] += 1
            if sleep:
                time.sleep(sleep)
            return CommercialSourceResponse(
                status=LookupStatus.SUCCESS, retrieved_at=None,
                candidates=(), issues=(),
            )

    def counting_factory():
        counters["constructions"] += 1
        return CannedAdapter()

    real_trigger = cmd_module.trigger_vendor_refresh
    def trigger_spy(*a, **k):
        counters["trigger_calls"] += 1
        return real_trigger(*a, **k)
    real_claim = cmd_module.claim_vendor_refresh
    def claim_spy(*a, **k):
        counters["claim_calls"] += 1
        return real_claim(*a, **k)
    cmd_module.trigger_vendor_refresh = trigger_spy
    cmd_module.claim_vendor_refresh = claim_spy
    def fake_entry(child_id):
        return execute_claimed_vendor_refresh(
            child_id, vendor_adapter_factory=counting_factory
        )
    cmd_module.execute_claimed_vendor_refresh_with_default_providers = fake_entry
    return counters

def do_command(payload):
    from io import StringIO
    from django.core.management import call_command
    counters = install_command_fakes(payload)
    parent_id = payload["parent"]
    args = [parent_id, "--operator", payload["operator"]]
    if payload.get("force"):
        args.append("--force-repeat")
    out = StringIO()
    code = None
    try:
        call_command("vendor_refresh", *args, stdout=out)
    except SystemExit as exc:
        code = exc.code
    return {
        "exit_code": code,
        "stdout": out.getvalue(),
        "constructions": counters["constructions"],
        "lookups": counters["lookups"],
        "trigger_calls": counters["trigger_calls"],
        "claim_calls": counters["claim_calls"],
        "children": child_rows(parent_id),
    }

def do_executor(payload):
    from product_intelligence.execution.vendor_refresh import (
        VendorRefreshExecutionError, execute_claimed_vendor_refresh,
    )
    from product_intelligence.providers.commercial import (
        CommercialSourceResponse, LookupStatus,
    )
    sleep = payload.get("lookup_sleep", 0.0)
    counters = {"constructions": 0, "lookups": 0}

    class CannedAdapter:
        def lookup(self, query):
            counters["lookups"] += 1
            if sleep:
                time.sleep(sleep)
            return CommercialSourceResponse(
                status=LookupStatus.SUCCESS, retrieved_at=None,
                candidates=(), issues=(),
            )

    def counting_factory():
        counters["constructions"] += 1
        return CannedAdapter()

    result = {"returned": False, "error": None, "durable_state": None}
    child_id = payload["child"]
    try:
        row = execute_claimed_vendor_refresh(
            child_id, vendor_adapter_factory=counting_factory
        )
        result["returned"] = True
        result["row_id"] = str(row.id)
        result["state"] = row.state
        payload_ = row.result_payload if isinstance(row.result_payload, dict) else {}
        vcr = payload_.get("vendor_commercial_result") or {}
        result["lookup_status"] = vcr.get("lookup_status")
    except VendorRefreshExecutionError as exc:
        result["error"] = exc.reason
        result["durable_state"] = exc.durable_state
    result["constructions"] = counters["constructions"]
    result["lookups"] = counters["lookups"]
    result["children"] = child_rows(payload["parent"])
    return result

def do_lock_a(payload):
    from django.db import transaction
    from product_intelligence.runs.models import VendorRefreshExecution
    parent_id = payload["parent"]
    hold = payload["hold"]
    with transaction.atomic():
        rows = VendorRefreshExecution.objects.filter(
            parent_run_id=parent_id, active_slot=2
        ).update(active_slot=2)
        t_lock = time.time()
        time.sleep(hold)
        t_pre_commit = time.time()
    t_commit = time.time()
    return {"rows": rows, "t_lock": t_lock, "t_pre_commit": t_pre_commit, "t_commit": t_commit}

def do_lock_b(payload):
    from django.db import transaction
    from product_intelligence.runs.models import VendorRefreshExecution
    parent_id = payload["parent"]
    t0 = time.time()
    with transaction.atomic():
        rows = VendorRefreshExecution.objects.filter(
            parent_run_id=parent_id, active_slot=2
        ).update(active_slot=2)
    t_done = time.time()
    count_after = VendorRefreshExecution.objects.filter(parent_run_id=parent_id).count()
    return {"rows": rows, "t0": t0, "t_done": t_done, "count_after": count_after}

def do_raw_holder(payload):
    import sqlite3
    conn = sqlite3.connect(payload["db"])
    conn.execute("BEGIN IMMEDIATE")
    t0 = time.time()
    conn.execute(
        "UPDATE runs_vendorrefreshexecution SET active_slot=active_slot WHERE 1=0"
    )
    time.sleep(payload["hold"])
    t1 = time.time()
    conn.commit()
    conn.close()
    return {"t0": t0, "t1": t1}

def do_uncommitted_insert(payload):
    from django.db import transaction
    from product_intelligence.runs import trigger_vendor_refresh
    parent_id = payload["parent"]
    with transaction.atomic():
        child = trigger_vendor_refresh(parent_id, operator=payload["operator"])
        # The INSERT is IN FLIGHT (uncommitted; the write lock is held).
        # Signal the parent, then hold the transaction open until killed.
        if payload.get("ready"):
            with open(payload["ready"], "w", encoding="utf-8") as f:
                f.write(json.dumps({"insert_id": str(child.id)}))
        time.sleep(180)
    return {"unreached": True}

def do_post_kill_writer(payload):
    from product_intelligence.runs.models import VendorRefreshExecution
    parent_id = payload["parent"]
    t0 = time.time()
    rows = VendorRefreshExecution.objects.filter(
        parent_run_id=parent_id, active_slot=2
    ).update(active_slot=2)
    t_done = time.time()
    children = child_rows(parent_id)
    return {
        "rows": rows,
        "t0": t0,
        "t_done": t_done,
        "child_count": len(children),
        "children": children,
    }

def do_reader(payload):
    from product_intelligence.runs.models import VendorRefreshExecution
    parent_id = payload["parent"]
    t0 = time.time()
    count = VendorRefreshExecution.objects.filter(parent_run_id=parent_id).count()
    t_done = time.time()
    return {"count": count, "t0": t0, "t_done": t_done}

try:
    main()
except Exception:
    try:
        payload = json.loads(sys.argv[1])
        with open(payload["result"], "w", encoding="utf-8") as f:
            json.dump({"error": traceback.format_exc()}, f)
    except Exception:
        pass
    raise
'''


# ---------------------------------------------------------------------------
# Orchestration helpers (the parent side; no assertion lives here)
# ---------------------------------------------------------------------------


class WorkerError(AssertionError):
    """A worker subprocess failed or produced no result."""


def _worker_env(db_file: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    env["PI_SQLITE_PATH"] = str(db_file)
    # The deployment base URL is present (S5 passes) — but NO network
    # call can occur: every worker's execution entry is patched to the
    # counting canned-response fake before the command runs.
    env["PI_VENDOR_LOOKUP_BASE_URL"] = "http://vendor.internal/api"
    return env


def _popen_one(payload: dict, driver_path: Path, env: dict) -> subprocess.Popen:
    for attempt in range(1, 4):
        try:
            # Spawn discipline (the R1-2 record): stdin/stdout/stderr
            # are NOT redirected at all (the documented load-sensitive
            # WinError 6/50 pipe-setup flake class); the worker writes
            # its own result file.
            return subprocess.Popen(
                [sys.executable, str(driver_path), json.dumps(payload)],
                env=env,
                cwd=str(REPO_ROOT),
            )
        except OSError as exc:
            flake = ("WinError 6" in str(exc)) or ("WinError 50" in str(exc))
            if attempt >= 3 or not flake:
                raise
            time.sleep(0.5 * attempt)
    raise WorkerError("unreachable")


def _wait_all(procs: list[subprocess.Popen], timeout: float = 300.0) -> None:
    for proc in procs:
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=30)
            raise WorkerError("worker timed out") from None


def _read_result(path: Path) -> dict:
    if not path.exists():
        raise WorkerError(f"worker produced no result file: {path.name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    # The driver writes {"error": <traceback>} ONLY on failure; the
    # executor scenario's legitimate result field is "error": null.
    if data.get("error") is not None:
        raise WorkerError(f"worker raised:\n{data['error']}")
    return data


def _driver_path(work_dir: Path) -> Path:
    """The worker driver script inside the scenario work dir (written
    once; identical bytes for every worker of the scenario)."""
    driver_path = work_dir / "worker_driver.py"
    if not driver_path.exists():
        driver_path.write_text(WORKER_DRIVER, encoding="utf-8")
    return driver_path


def _run_scenario(work_dir: Path, payloads: list[dict], timeout: float = 300.0) -> list[dict]:
    """Spawn one worker per payload (concurrently), wait, and return
    the per-worker results in payload order."""
    driver_path = _driver_path(work_dir)
    env = _worker_env(work_dir / "concurrency.sqlite3")
    procs = [_popen_one(payload, driver_path, env) for payload in payloads]
    _wait_all(procs, timeout=timeout)
    return [_read_result(Path(payload["result"])) for payload in payloads]


def _with_ready_go(work_dir: Path, payloads: list[dict], use_handshake: bool) -> list[dict]:
    if not use_handshake:
        return payloads
    for i, payload in enumerate(payloads):
        payload["ready"] = str(work_dir / f"ready_{i}")
        payload["go"] = str(work_dir / "go")
    return payloads


def _handshake_start(work_dir: Path, payloads: list[dict], timeout: float = 120.0) -> None:
    """Wait for all ready files, then release the go signal."""
    deadline = time.time() + timeout
    for payload in payloads:
        ready = Path(payload["ready"])
        while not ready.exists():
            if time.time() > deadline:
                raise WorkerError("worker never became ready")
            time.sleep(0.02)
    (work_dir / "go").write_text("go", encoding="utf-8")


# ---------------------------------------------------------------------------
# Row 1 / Row 19 — the four-worker command race (5 rounds x 4 workers)
# ---------------------------------------------------------------------------


class TestCommandRace:
    """GENUINE concurrency (C): 5 rounds x 4 simultaneous command
    invocations over a file database. Invariants per round (design
    section 12 rows 1 / 19): exactly ONE new child, exactly ONE claim
    UPDATE total, exactly ONE lookup total; the losers report IN
    PROGRESS or COOLDOWN REFUSAL with zero trigger / claim /
    construction / lookup (LB-3, sentinel-proven per worker)."""

    def _spawn(self, work_dir: Path, payloads: list[dict]) -> list[subprocess.Popen]:
        driver_path = _driver_path(work_dir)
        env = _worker_env(work_dir / "concurrency.sqlite3")
        return [_popen_one(p, driver_path, env) for p in payloads]

    def test_five_rounds_x_four_workers_one_child_one_claim_one_lookup(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix="vref_r13_race_"))
        try:
            payloads = [{"scenario": "init", "db": str(work_dir / "concurrency.sqlite3"),
                         "result": str(work_dir / "init.json"),
                         "parents": [{"mpn": TEST_MPN, "description": f"race {i}"}
                                     for i in range(5)]}]
            init = _run_scenario(work_dir, payloads)[0]
            parents = init["parents"]
            assert len(parents) == 5

            for round_ in range(5):
                payloads = [
                    {
                        "scenario": "command",
                        "db": str(work_dir / "concurrency.sqlite3"),
                        "result": str(work_dir / f"r{round_}_w{i}.json"),
                        "parent": parents[round_],
                        "operator": f"r{round_}-w{i}",
                        "force": False,
                        "lookup_sleep": LOOKUP_SLEEP,
                    }
                    for i in range(4)
                ]
                _with_ready_go(work_dir, payloads, use_handshake=True)
                procs = self._spawn(work_dir, payloads)
                try:
                    _handshake_start(work_dir, payloads)
                    _wait_all(procs)
                finally:
                    for proc in procs:
                        if proc.poll() is None:
                            proc.kill()
                            proc.wait(timeout=30)
                results = [
                    _read_result(Path(p["result"])) for p in payloads
                ]
                # Exactly ONE winner: exit 0 + COMPLETED + the child-created line.
                winners = [
                    r for r in results
                    if r["exit_code"] == 0 and "outcome: COMPLETED" in r["stdout"]
                ]
                assert len(winners) == 1, (
                    f"round {round_}: expected exactly one winner, "
                    f"got {[(r['exit_code'], r['stdout'][-200:]) for r in results]}"
                )
                losers = [r for r in results if r is not winners[0]]
                # The parent has EXACTLY ONE new child — terminal COMPLETED.
                for r in results:
                    assert len(r["children"]) == 1
                child = winners[0]["children"][0]
                assert child["state"] == "COMPLETED"
                assert child["active_slot"] is None
                # The winner is the invocation that created the child:
                # its operator is recorded verbatim on the row.
                assert f"child-created {child['id']} operator={child['operator']}" in winners[0]["stdout"]
                assert child["trigger_source"] == "MANAGEMENT_COMMAND"
                assert child["lookup_status"] == "SUCCESS"
                # Aggregate counts: one trigger, one claim, one
                # construction, one lookup — across ALL workers.
                assert sum(r["trigger_calls"] for r in results) == 1
                assert sum(r["claim_calls"] for r in results) == 1  # row 19 C
                assert sum(r["constructions"] for r in results) == 1
                assert sum(r["lookups"] for r in results) == 1
                # The losers: bounded report, zero calls (LB-3).
                for r in losers:
                    assert r["exit_code"] == 0
                    assert (
                        "outcome: IN_PROGRESS" in r["stdout"]
                        or "outcome: COOLDOWN_REFUSAL" in r["stdout"]
                    ), f"loser outcome: {r['stdout']}"
                    assert r["trigger_calls"] == 0
                    assert r["claim_calls"] == 0
                    assert r["constructions"] == 0
                    assert r["lookups"] == 0
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Row 11 — section 9 cases 5 and 6 under genuine concurrency
# ---------------------------------------------------------------------------


class TestCooldownInterleavings:
    """Section 9 case 5 (all workers outside the cooldown window: both
    pass the check but only ONE can INSERT) and case 6 (--force-repeat
    competing with non-forced workers: the force flag is honored
    EXACTLY ONCE and never "eaten" by the race)."""

    def _spawn(self, work_dir: Path, payloads: list[dict]) -> list[subprocess.Popen]:
        driver_path = _driver_path(work_dir)
        env = _worker_env(work_dir / "concurrency.sqlite3")
        return [_popen_one(p, driver_path, env) for p in payloads]

    def _handshake_round(self, work_dir: Path, payloads: list[dict]) -> list[dict]:
        _with_ready_go(work_dir, payloads, use_handshake=True)
        procs = self._spawn(work_dir, payloads)
        try:
            _handshake_start(work_dir, payloads)
            _wait_all(procs)
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=30)
        return [_read_result(Path(p["result"])) for p in payloads]

    def test_case5_outside_cooldown_exactly_one_new_child(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix="vref_r13_case5_"))
        try:
            init_payload = {
                "scenario": "init",
                "db": str(work_dir / "concurrency.sqlite3"),
                "result": str(work_dir / "init.json"),
                "parents": [{"mpn": TEST_MPN, "description": "case 5"}],
                "prestate": [
                    {
                        "parent_index": 0,
                        "kind": "terminal",
                        "operator": "op-pre",
                        # Just OUTSIDE the 300 s window.
                        "finished_offset_seconds": 301.0,
                    }
                ],
            }
            init = _run_scenario(work_dir, [init_payload])[0]
            payloads = [
                {
                    "scenario": "command",
                    "db": str(work_dir / "concurrency.sqlite3"),
                    "result": str(work_dir / f"w{i}.json"),
                    "parent": init["parents"][0],
                    "operator": f"op-case5-{i}",
                    "force": False,
                    "lookup_sleep": LOOKUP_SLEEP,
                }
                for i in range(4)
            ]
            results = self._handshake_round(work_dir, payloads)
            # The authoritative final state (after all workers): one
            # pre-terminal + exactly ONE new child.
            final = _run_scenario(
                work_dir,
                [
                    {
                        "scenario": "read_children",
                        "db": str(work_dir / "concurrency.sqlite3"),
                        "result": str(work_dir / "final.json"),
                        "parent": init["parents"][0],
                    }
                ],
            )[0]
            assert len(final["children"]) == 2
            for r in results:
                assert len(r["children"]) >= 1
            assert sum(r["trigger_calls"] for r in results) == 1
            assert sum(r["claim_calls"] for r in results) == 1
            assert sum(r["constructions"] for r in results) == 1
            assert sum(r["lookups"] for r in results) == 1
            winners = [
                r for r in results if r["exit_code"] == 0 and "outcome: COMPLETED" in r["stdout"]
            ]
            assert len(winners) == 1
            for r in results:
                if r is winners[0]:
                    continue
                assert r["exit_code"] == 0
                assert (
                    "outcome: IN_PROGRESS" in r["stdout"]
                    or "outcome: COOLDOWN_REFUSAL" in r["stdout"]
                )
                assert r["trigger_calls"] == 0
                assert r["claim_calls"] == 0
                assert r["constructions"] == 0
                assert r["lookups"] == 0
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def test_case6_force_honored_exactly_once(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix="vref_r13_case6_"))
        try:
            init_payload = {
                "scenario": "init",
                "db": str(work_dir / "concurrency.sqlite3"),
                "result": str(work_dir / "init.json"),
                "parents": [{"mpn": TEST_MPN, "description": "case 6"}],
                "prestate": [
                    {
                        "parent_index": 0,
                        "kind": "terminal",
                        "operator": "op-pre",
                        # Freshly terminal (inside the window): the
                        # non-forced workers MUST refuse (or report the
                        # forced child in progress); only the forced
                        # worker may create.
                        "finished_offset_seconds": 10.0,
                    }
                ],
            }
            init = _run_scenario(work_dir, [init_payload])[0]
            payloads = [
                {
                    "scenario": "command",
                    "db": str(work_dir / "concurrency.sqlite3"),
                    "result": str(work_dir / f"w{i}.json"),
                    "parent": init["parents"][0],
                    "operator": "op-force" if i == 0 else f"op-nonforce-{i}",
                    "force": i == 0,
                    "lookup_sleep": LOOKUP_SLEEP,
                }
                for i in range(4)
            ]
            results = self._handshake_round(work_dir, payloads)
            # The authoritative final state (after all workers): the
            # pre-terminal + exactly ONE new child.
            final = _run_scenario(
                work_dir,
                [
                    {
                        "scenario": "read_children",
                        "db": str(work_dir / "concurrency.sqlite3"),
                        "result": str(work_dir / "final.json"),
                        "parent": init["parents"][0],
                    }
                ],
            )[0]
            assert len(final["children"]) == 2
            # Force honored EXACTLY ONCE: the only new child is the
            # forced invocation's.
            pre_id = init["children"]["0"][0]
            new_ids = [c["id"] for c in final["children"] if c["id"] != pre_id]
            assert len(new_ids) == 1
            new_child = next(c for c in final["children"] if c["id"] == new_ids[0])
            assert new_child["operator"] == "op-force"
            assert new_child["state"] == "COMPLETED"
            # The forced worker is the sole creator / claimer.
            forced = results[0]
            assert forced["trigger_calls"] == 1
            assert forced["claim_calls"] == 1
            assert forced["constructions"] == 1
            assert forced["lookups"] == 1
            assert "outcome: COMPLETED" in forced["stdout"]
            # The forced worker's own read saw both children (it
            # created the new one).
            assert len(forced["children"]) == 2
            for r in results[1:]:
                assert r["exit_code"] == 0
                assert (
                    "outcome: IN_PROGRESS" in r["stdout"]
                    or "outcome: COOLDOWN_REFUSAL" in r["stdout"]
                )
                assert r["trigger_calls"] == 0
                assert r["claim_calls"] == 0
                assert r["constructions"] == 0
                assert r["lookups"] == 0
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Row 12 — real SQLite transaction / locking behavior (C)
# ---------------------------------------------------------------------------


class TestSqliteLockingBehavior:
    """The verified SQLite facts (design section 1.6 / Appendix A)
    demonstrated IN-TEST over a file database: lock-statement
    serialization, the bounded busy error beyond the 5 s timeout,
    kill-release + rollback, and reader non-blocking."""

    def _spawn(self, work_dir: Path, payloads: list[dict]) -> list[subprocess.Popen]:
        driver_path = _driver_path(work_dir)
        env = _worker_env(work_dir / "concurrency.sqlite3")
        return [_popen_one(p, driver_path, env) for p in payloads]

    def _init_parent(self, work_dir: Path, tag: str, prestate: list | None = None) -> str:
        init_payload = {
            "scenario": "init",
            "db": str(work_dir / "concurrency.sqlite3"),
            "result": str(work_dir / "init.json"),
            "parents": [{"mpn": TEST_MPN, "description": tag}],
        }
        if prestate is not None:
            init_payload["prestate"] = prestate
        init = _run_scenario(work_dir, [init_payload])[0]
        return init["parents"][0]

    def _handshake_round(self, work_dir: Path, payloads: list[dict]) -> list[dict]:
        _with_ready_go(work_dir, payloads, use_handshake=True)
        procs = self._spawn(work_dir, payloads)
        try:
            _handshake_start(work_dir, payloads)
            _wait_all(procs)
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=30)
        return [_read_result(Path(p["result"])) for p in payloads]

    def test_lock_statement_serializes_a_second_writer(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix="vref_r13_locka_"))
        try:
            parent = self._init_parent(work_dir, "lock-a")
            payloads = [
                {
                    "scenario": "lock_a",
                    "db": str(work_dir / "concurrency.sqlite3"),
                    "result": str(work_dir / "a.json"),
                    "parent": parent,
                    "hold": 2.0,
                },
                {
                    "scenario": "lock_b",
                    "db": str(work_dir / "concurrency.sqlite3"),
                    "result": str(work_dir / "b.json"),
                    "parent": parent,
                    # B's statement fires 0.4 s after the common go
                    # signal — inside A's 2.0 s hold window, so the
                    # ordering is deterministic (A holds, B blocks).
                    "delay": 0.4,
                },
            ]
            _with_ready_go(work_dir, payloads, use_handshake=True)
            results = self._handshake_round(work_dir, payloads)
            a, b = results[0], results[1]
            assert a["rows"] == 0  # the lock statement mutates NOTHING
            assert b["rows"] == 0
            # B's statement began while A held the lock (inside the
            # handshake-aligned window) and completed only AFTER A's
            # commit — blocked, then proceeded against the fresh
            # committed state (Appendix A.7 pattern, in-test).
            assert a["t_lock"] < b["t0"] < a["t_pre_commit"]
            assert b["t_done"] >= a["t_pre_commit"]
            assert (b["t_done"] - b["t0"]) >= 1.2  # blocked for the hold window
            assert b["count_after"] == 0  # fresh committed state: no row
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def test_contention_beyond_busy_timeout_surfaces_database_busy(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix="vref_r13_busy_"))
        try:
            parent = self._init_parent(
                work_dir,
                "busy",
                prestate=[
                    {
                        "parent_index": 0,
                        "kind": "terminal",
                        "operator": "op-pre",
                        "finished_offset_seconds": 400.0,
                    }
                ],
            )
            pre_children = _run_scenario(
                work_dir,
                [
                    {
                        "scenario": "lock_a",
                        "db": str(work_dir / "concurrency.sqlite3"),
                        "result": str(work_dir / "pre.json"),
                        "parent": parent,
                        "hold": 0.0,
                    }
                ],
            )[0]
            assert pre_children["rows"] == 0  # the lock statement mutates nothing
            payloads = [
                {
                    "scenario": "raw_holder",
                    "db": str(work_dir / "concurrency.sqlite3"),
                    "result": str(work_dir / "holder.json"),
                    "hold": 8.0,
                },
                {
                    "scenario": "busy_command",
                    "db": str(work_dir / "concurrency.sqlite3"),
                    "result": str(work_dir / "busy.json"),
                    "parent": parent,
                    "operator": "op-busy",
                    "delay": 1.0,
                    "lookup_sleep": 0.0,
                },
            ]
            results = _run_scenario(work_dir, payloads, timeout=120)
            busy = results[1]
            # Bounded DATABASE BUSY, non-zero exit, ZERO mutation.
            assert busy["exit_code"] == 4
            assert "outcome: DATABASE_BUSY" in busy["stdout"]
            assert "no state changed" in busy["stdout"]
            assert busy["trigger_calls"] == 0
            assert busy["claim_calls"] == 0
            assert busy["constructions"] == 0
            assert busy["lookups"] == 0
            # The row set is exactly the pre-existing terminal child
            # (a completed pre-state; the lookup-status in its payload
            # is FAILED, the child STATE is COMPLETED).
            assert len(busy["children"]) == 1
            assert busy["children"][0]["state"] == "COMPLETED"
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def test_killed_lock_holder_releases_and_rolls_back(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix="vref_r13_kill_"))
        try:
            parent = self._init_parent(work_dir, "kill")
            driver_path = _driver_path(work_dir)
            env = _worker_env(work_dir / "concurrency.sqlite3")
            victim_payload = {
                "scenario": "uncommitted_insert",
                "db": str(work_dir / "concurrency.sqlite3"),
                "result": str(work_dir / "victim.json"),
                "parent": parent,
                "operator": "op-victim",
                "ready": str(work_dir / "victim_ready"),
            }
            victim = _popen_one(victim_payload, driver_path, env)
            try:
                # Wait until the victim's INSERT is in flight (the
                # uncommitted transaction holds the write lock).
                ready = work_dir / "victim_ready"
                deadline = time.time() + 60
                while not ready.exists():
                    if victim.poll() is not None:
                        raise WorkerError("victim exited before its INSERT")
                    if time.time() > deadline:
                        raise WorkerError("victim never reached its INSERT")
                    time.sleep(0.05)
                # GENUINE kill: the process is terminated mid-
                # transaction (the OS releases the file lock; the
                # uncommitted INSERT rolls back).
                victim.terminate()
                victim.wait(timeout=30)
            finally:
                if victim.poll() is None:
                    victim.kill()
                    victim.wait(timeout=30)
            # A fresh writer proceeds IMMEDIATELY (no wedge) and sees
            # ZERO children (the INSERT did not survive the kill).
            writer_payload = {
                "scenario": "post_kill_writer",
                "db": str(work_dir / "concurrency.sqlite3"),
                "result": str(work_dir / "writer.json"),
                "parent": parent,
            }
            writer = _run_scenario(work_dir, [writer_payload])[0]
            assert writer["rows"] == 0
            assert writer["child_count"] == 0  # the uncommitted INSERT rolled back
            assert (writer["t_done"] - writer["t0"]) < 2.0  # no blocking
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def test_reader_proceeds_while_a_writer_holds_the_lock(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix="vref_r13_reader_"))
        try:
            parent = self._init_parent(work_dir, "reader")
            payloads = [
                {
                    "scenario": "lock_a",
                    "db": str(work_dir / "concurrency.sqlite3"),
                    "result": str(work_dir / "a.json"),
                    "parent": parent,
                    "hold": 2.0,
                },
                {
                    "scenario": "reader",
                    "db": str(work_dir / "concurrency.sqlite3"),
                    "result": str(work_dir / "r.json"),
                    "parent": parent,
                    "delay": 0.4,
                },
            ]
            results = self._handshake_round(work_dir, payloads)
            a, r = results[0], results[1]
            # The read occurred DURING the holder's lock window and
            # was NOT blocked (rollback journal: SHARED is not blocked
            # by RESERVED — the web is not wedged).
            assert a["t_lock"] <= r["t0"] < a["t_pre_commit"]
            assert (r["t_done"] - r["t0"]) < 0.5
            assert a["rows"] == 0
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Row 20 — genuine concurrent direct executor reuse (the documented
# privileged-writer limit)
# ---------------------------------------------------------------------------


class TestDirectExecutorReuseConcurrent:
    """The ONLY shape in which two direct executor calls EACH reach
    the lookup (FU2-F1 / FU3-F2): both independent processes read the
    still-RUNNING orphan, both pass the state re-assert, and both
    reach the lookup before either terminalizes. The frozen complete
    service admits EXACTLY ONE terminal write (I3): one process
    returns (T1), the other loses the CAS and its pinned read-only
    reconciliation returns the ACTUAL durable COMPLETED shape (T2)
    with zero further writes. The state re-assert is NOT ownership
    authentication; the terminal CAS bounds terminal writes, NOT
    external requests — this node demonstrates that documented limit
    (privileged-writer class, outside the frozen threat model)."""

    def test_two_processes_two_lookups_one_terminal_write(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix="vref_r13_reuse_"))
        try:
            init_payload = {
                "scenario": "init",
                "db": str(work_dir / "concurrency.sqlite3"),
                "result": str(work_dir / "init.json"),
                "parents": [{"mpn": TEST_MPN, "description": "reuse"}],
                "prestate": [
                    {
                        "parent_index": 0,
                        "kind": "running",  # the crash-orphan shape
                        "operator": "op-orphan",
                    }
                ],
            }
            init = _run_scenario(work_dir, [init_payload])[0]
            parent = init["parents"][0]
            orphan_id = init["children"]["0"][0]
            payloads = [
                {
                    "scenario": "executor",
                    "db": str(work_dir / "concurrency.sqlite3"),
                    "result": str(work_dir / f"e{i}.json"),
                    "parent": parent,
                    "child": orphan_id,
                    "lookup_sleep": 1.0,
                }
                for i in range(2)
            ]
            _with_ready_go(work_dir, payloads, use_handshake=True)
            driver_path = _driver_path(work_dir)
            env = _worker_env(work_dir / "concurrency.sqlite3")
            procs = [_popen_one(p, driver_path, env) for p in payloads]
            try:
                _handshake_start(work_dir, payloads)
                _wait_all(procs)
            finally:
                for proc in procs:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait(timeout=30)
            results = [_read_result(Path(p["result"])) for p in payloads]
            # BOTH processes reached the lookup (two Vendor requests
            # demonstrated — the documented limit).
            assert results[0]["lookups"] == 1
            assert results[1]["lookups"] == 1
            assert results[0]["constructions"] == 1
            assert results[1]["constructions"] == 1
            # The frozen complete service admitted EXACTLY ONE
            # terminal write: BOTH calls returned the ACTUAL durable
            # COMPLETED row (one via T1, the other via its pinned
            # read-only T2 reconciliation — no exception, no second
            # write, no retry).
            for r in results:
                assert r["returned"] is True, f"worker outcome: {r}"
                assert r["state"] == "COMPLETED"
                assert r["row_id"] == orphan_id
                assert r["lookup_status"] == "SUCCESS"
            # The row is terminal, single, byte-stable: exactly one
            # child for the parent, COMPLETED, slot released.
            children = results[0]["children"]
            assert children == results[1]["children"]
            assert len(children) == 1
            assert children[0]["state"] == "COMPLETED"
            assert children[0]["active_slot"] is None
            assert children[0]["operator"] == "op-orphan"
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
