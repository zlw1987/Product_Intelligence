# Product Intelligence — Internal Pilot Deployment Runbook

**Phase:** PILOT-RELEASE-1  
**Scope:** Internal customer pilot deployment on Windows  
**Security Boundary:** Internal trusted-network pilot only

---

## Overview

This runbook covers the deployment of the Product Intelligence application for an internal customer pilot. The pilot uses the existing Product Intelligence web application with a Windows-compatible production WSGI server.

Section L covers the vendor commercial refresh command (VREF R1) and its O8 deployment-prerequisite host evidence.

**This pilot is for INTERNAL/TRUSTED-NETWORK USE ONLY.** Direct unrestricted public Internet exposure is NOT approved. Authentication/report-visibility remains a future product decision.

---

## Limitations

- Internal/trusted-network pilot only
- No application authentication yet
- SQLite is pilot-only (not a scaling architecture decision)
- Synchronous long-running research requests remain current architecture
- Do not expose directly to unrestricted public Internet
- Structured API 5A is still future
- SAP launcher is future

---

## A. Prerequisites

### Supported Python

- Python 3.10 or later
- Windows-compatible

### Repository Checkout

1. Clone or copy the repository to a working directory
2. The Git checkout should NOT contain the production database

### Virtual Environment

```cmd
cd <project-root>
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Verify Installation

```cmd
python -c "import django; print(django.VERSION)"
python manage.py check
```

---

## B. Required Server Environment

Set these environment variables before starting the application. They can be set via:

- Windows System Properties → Environment Variables
- Command prompt `set VAR=value` (session-scoped)
- A `.cmd` wrapper script that sets them before launching

### Required Variables

| Variable | Description | Example |
|---|---|---|
| `DJANGO_DEBUG` | Must be `0` for production | `0` |
| `DJANGO_SECRET_KEY` | Server secret, minimum 32 characters | `<random-64-char-string>` |
| `DJANGO_ALLOWED_HOSTS` | Internal host/IP addresses, comma-separated | `pi-server.internal.company.com` or `192.168.1.100` |
| `PI_SQLITE_PATH` | **Absolute path** to SQLite database file (outside Git checkout) | `D:\product-intel-data\db.sqlite3` |
| `SERPER_API_KEY` | Server secret for Serper search | `<api-key>` |

### Optional Semantic Provider Variables

The semantic runtime requires both providers to be configured:

| Variable | Required | Description |
|---|---|---|
| `PI_SEMANTIC_AMAX_BASE_URL` | **Required** | Primary model endpoint URL |
| `PI_SEMANTIC_AMAX_API_KEY` | Optional | Primary model API key |
| `PI_SEMANTIC_VLLM_262K_BASE_URL` | **Required** | Fallback model endpoint URL |
| `PI_SEMANTIC_VLLM_262K_API_KEY` | Optional | Fallback model API key |
| `PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS` | Optional | Default 300 |

### Vendor API Base URL

The vendor commercial lookup (research supplemental evidence) and the vendor
refresh command (Section L) both read the internal Vendor API base URL from
the server environment:

| Variable | Description | Example |
|---|---|---|
| `PI_VENDOR_LOOKUP_BASE_URL` | Deployment-owned base URL of the internal Vendor API. Absolute `http(s)` URL with a host; no embedded credentials; no fragment; no query string. | `https://<vendor-api-host>/<vendor-api-path>` |

Requirements and behavior:

- The exact value is deployment-owned (provided by the Vendor API
  operators). It carries no credentials; the adapter sends no Authorization
  header.
- If **absent or blank** in the server environment: normal research runs
  proceed with the vendor lookup NOT attempted (no vendor data, no error);
  a vendor refresh child fails durably with
  `VENDOR_LOOKUP_CONFIG_MISSING` and makes zero network calls.
- If **present but malformed** (non-http(s) scheme, missing host, embedded
  credentials, fragment, or query string): a vendor refresh child fails
  durably with `INTERNAL_ERROR` and makes zero network calls.
- The vendor refresh command MUST be run in the same server environment as
  the application (same virtualenv activation, same `PI_SQLITE_PATH` and
  `PI_VENDOR_LOOKUP_BASE_URL`); otherwise it acts on a different database
  or fails the child with `VENDOR_LOOKUP_CONFIG_MISSING`.

### Example Environment Setup

```cmd
set DJANGO_DEBUG=0
set DJANGO_SECRET_KEY=your-production-secret-key-minimum-32-chars-long
set DJANGO_ALLOWED_HOSTS=pi-server.internal.company.com,192.168.1.100
set PI_SQLITE_PATH=D:\product-intel-data\db.sqlite3
set SERPER_API_KEY=your-serper-api-key
set PI_SEMANTIC_AMAX_BASE_URL=https://api.amax.ai/v1
set PI_SEMANTIC_AMAX_API_KEY=your-amax-api-key
set PI_SEMANTIC_VLLM_262K_BASE_URL=https://your-vllm-server.com/v1
set PI_SEMANTIC_VLLM_262K_API_KEY=your-vllm-api-key
set PI_VENDOR_LOOKUP_BASE_URL=https://<vendor-api-host>/<vendor-api-path>
```

**WARNING:** Never embed these values in source code, CMD files, FoxPro, URLs, or Git.

---

## C. Database Initialization

### First-Time Setup

Before starting the application for the first time:

1. Create the directory for the SQLite database:
   ```cmd
   mkdir D:\product-intel-data
   ```

2. Run migrations:
   ```cmd
   python manage.py migrate
   ```

3. Verify the database was created:
   ```cmd
   dir D:\product-intel-data\db.sqlite3
   ```

### Verify Migrations

```cmd
python manage.py showmigrations
```

All migrations should show `[X]` (applied).

---

## D. Preflight Check

Run the pilot preflight validation before starting the server:

```cmd
python manage.py pilot_check
```

**Expected output:**
```
[FAIL] DEBUG must be disabled         # If DEBUG=1
[FAIL] DJANGO_SECRET_KEY is not production-safe  # If using dev default
...
[FAIL] DJANGO_ALLOWED_HOSTS is non-empty  # If not configured
...
Product Intelligence internal pilot preflight: FAIL
```

**Fix any failures before proceeding.** The preflight checks:

1. DEBUG is False
2. SECRET_KEY is not the repository development default
3. SECRET_KEY is non-empty and has reasonable minimum length
4. ALLOWED_HOSTS is non-empty
5. ALLOWED_HOSTS does not contain unrestricted wildcard "*"
6. SERPER_API_KEY exists and is non-blank
7. SQLite database parent directory exists
8. SQLite database parent directory is writable
9. Django database connectivity succeeds
10. Required migrations are applied
11. Semantic provider configuration is complete

### Run Both Django Check and Pilot Check

```cmd
scripts\check_internal_pilot.cmd
```

---

## E. Start the Application

### Using the Launcher Script

```cmd
scripts\run_internal_pilot.cmd
```

This script:
1. Runs `pilot_check` preflight validation
2. Stops immediately if preflight fails
3. Starts Waitress WSGI server

### Using Custom Configuration

```cmd
set PI_BIND_PORT=8080
set PI_BIND_HOST=0.0.0.0
python -m waitress --host=%PI_BIND_HOST% --port=%PI_BIND_PORT% config.wsgi:application
```

**Note:** Binding to `0.0.0.0` is acceptable for the internal pilot ONLY when your network firewall/access control restricts access to the approved internal network. 0.0.0.0 is NOT secure by itself.

### Verify Server Started

Check the health endpoint:
```cmd
curl http://localhost:8000/healthz
```

Expected response: `{"status": "healthy"}`

---

## F. Smoke Test

### Health Endpoint

```cmd
curl http://localhost:8000/healthz
```

- Healthy: HTTP 200, `{"status": "healthy"}`
- Unhealthy: HTTP 503, `{"status": "unhealthy", "message": "Database unavailable"}`

### Research Form

Open in browser:
```
http://<internal-host>:<port>/research/new
```

### FoxPro Launcher URL Contract

The FoxPro launcher opens this URL pattern:
```
http://<internal-host>:<port>/research/new?mpn=<encoded_mpn>&description=<encoded_description>
```

**FoxPro field mapping** (existing contract, maintained outside this repository):

| FoxPro Field | Mapping |
|---|---|
| `ALLTRIM(partdesc.mfg_partno)` | `mpn` query parameter |
| `ALLTRIM(partdesc.DESC)` | `description` query parameter |

The MPN and description are percent-encoded by the FoxPro launcher before opening the browser.

**Do NOT change the FoxPro field mapping.** The client-side code is maintained outside this repository.

---

## G. Pilot Acceptance Smoke Test

Use one known safe test MPN to verify the complete flow:

### Steps

1. **Open the launcher** from FoxPro or manually navigate to the research form with prefill:
   ```
   http://<internal-host>:<port>/research/new?mpn=XP15360SE70005&description=Seagate%20Nytro%205350H%2015.36TB%20SSD
   ```

2. **Verify MPN prefill is exact** — the form should show `XP15360SE70005`

3. **Verify Description prefill is exact** — the form should show the description

4. **Click Start Research** — wait for completion (may take 1-2 minutes)

5. **Verify price report renders** — price evidence should be visible

6. **Verify durable report reload** — refresh the page, data persists

7. **Test human review** (if AI-assisted candidates exist):
   - View candidates
   - Confirm or reject a candidate
   - Verify reviewed prices update

8. **Test comparable trigger**:
   - Click "Find Comparable Products" button
   - Wait for completion

9. **Verify comparable result renders** — comparable products should display

10. **Verify no duplicate on repeated POST** — clicking trigger again should be idempotent

11. **Verify DEBUG is off** — no Django debug toolbar in browser

12. **Verify no credentials in URL** — no API keys in browser address bar

---

## H. Backup

**Before any upgrade, create a database backup while the application is stopped.**

**Also ensure that no vendor refresh command (Section L) is running.** A
vendor refresh invocation commits its child (durably `RUNNING`) before its
Vendor HTTP call; a backup taken while such a command is still executing can
miss the child's terminal write, and running the command while the
application is stopped for backup (against a copied/stopped database) is
operator error. Before copying the database:

1. Stop the application (Waitress) — required as above.
2. Confirm no `vendor_refresh` invocation is in flight: its command window
   has printed its `outcome:` line and finished. If an invocation was
   killed or its window closed while executing, the child may remain
   `RUNNING`; that row is inert (no live process writes it) but note the
   child id in the backup record and treat it per Section L.5 (reported
   HOLD, no automatic recovery).

```cmd
REM Stop the application first
REM Confirm no vendor refresh command is running (Section L)

REM Create a timestamped backup
copy D:\product-intel-data\db.sqlite3 D:\product-intel-data\db_backup_%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.sqlite3
```

**Or use this simpler approach:**

```cmd
REM Stop the application first
REM Confirm no vendor refresh command is running (Section L)
set BACKUP_NAME=db_backup_2024-01-15.sqlite3
copy D:\product-intel-data\db.sqlite3 D:\product-intel-data\%BACKUP_NAME%
```

**Do NOT use Git for database backup.** Git is for source code, not data.

---

## I. Upgrade

### Standard Upgrade Procedure

1. **Stop the application**

2. **Backup the database** (see Section H)

3. **Update the application checkout:**
   ```cmd
   git pull
   ```
   Or manually copy new files from the update package.

4. **Install new requirements:**
   ```cmd
   pip install -r requirements.txt
   ```

5. **Run migrations:**
   ```cmd
   python manage.py migrate
   ```

6. **Run preflight check:**
   ```cmd
   python manage.py pilot_check
   ```
   Fix any failures before proceeding.

7. **Start the application:**
   ```cmd
   scripts\run_internal_pilot.cmd
   ```

---

## J. Rollback

### If Migration is Backward-Compatible (no data restoration needed)

1. **Stop the application**

2. **Return application to previous commit** according to your normal deployment process (this is an operator decision)

3. **Start the application**

### If Database Restoration is Required

1. **Stop the application** (and confirm no vendor refresh command is running, Section H)

2. **Restore the pre-upgrade database backup:**
   ```cmd
   copy D:\product-intel-data\<pre-upgrade-backup> D:\product-intel-data\db.sqlite3
   ```

3. **Start the application**

---

## K. Pilot Smoke / Acceptance Checklist

Use this checklist to sign off on the pilot:

```
[ ] /healthz returns 200
[ ] pilot_check PASS
[ ] FoxPro opens correct URL
[ ] MPN prefill exact
[ ] Description prefill exact
[ ] Normal research execution succeeds
[ ] Durable report reload succeeds
[ ] Price evidence visible
[ ] Human review works when applicable
[ ] Comparable trigger works
[ ] Comparable result renders
[ ] No duplicate comparable child on repeated completed POST
[ ] DEBUG is off
[ ] No credentials appear in browser URL
[ ] DB backup created before upgrade
```

---

## L. Vendor Refresh (VREF R1) — Deployment Preparation

**Status.** The vendor refresh implementation (R1-1…R1-3) is complete and
integration-approved (R1-5 gate) at frozen implementation SHA
`8914892ce143f812aac29ee718abed2ca81d2658`. **Production deployment of any
R1 surface remains HOLD until the O8 host-evidence checklist (L.6) is
completed and recorded.** The R1-4 recovery surface — the only mechanism
that can terminalize a stuck `RUNNING` child — is BLOCKED pending O8 and
does not exist in this implementation.

### L.1 What the command does

`vendor_refresh` triggers, claims, and executes exactly ONE vendor commercial
refresh for ONE COMPLETED parent research run. The refresh performs ONE
internal Vendor API lookup for the parent's MPN and durably records the
result (child `COMPLETED`) or the bounded failure (child `FAILED`).

- **Host-side surface only.** A Windows management command on the deployment
  host. There is no web form, URL, or POST surface.
- **Authorization is the controlled Windows host access itself** (the OS
  account running the command). `--operator` is mandatory SELF-REPORTED
  provenance, recorded verbatim on the child row — it is NOT authentication
  and must not be treated as identity proof.
- **Bounded blast radius.** One invocation creates at most ONE child,
  claims it at most once, and performs at most ONE Vendor API call. A
  reported in-progress child, a cooldown refusal, and an ineligible parent
  all leave zero mutation and zero network calls.
- **No secrets on the command line.** The command line carries only the
  parent UUID and the operator identity string.

### L.2 Configuration requirement

The command reads `PI_VENDOR_LOOKUP_BASE_URL` from the server environment
(see Section B, "Vendor API Base URL"). Run it in the SAME environment the
application runs in (same virtualenv activation, same `PI_SQLITE_PATH` and
`PI_VENDOR_LOOKUP_BASE_URL`). Missing/blank configuration fails the child
durably with `VENDOR_LOOKUP_CONFIG_MISSING` (zero network calls); malformed
configuration fails it with `INTERNAL_ERROR` (zero network calls).

### L.3 Canonical invocation

The canonical form below is the ONLY documented launch form. The R1-4
recovery evidence predicate (when that gate is unblocked) assumes exactly
this form; wrapped, renamed, or argument-hiding launches are non-canonical
and must not be used.

```cmd
cd <project-root>
venv\Scripts\activate
python manage.py vendor_refresh <parent-run-uuid> --operator <id> [--force-repeat]
```

| Argument | Requirement |
|---|---|
| `<parent-run-uuid>` | Exactly ONE positional: the UUID of the PARENT research run. The parent must be COMPLETED, have a price snapshot, and have a non-empty MPN. |
| `--operator <id>` | Required. 1..128 characters, recorded verbatim. Self-reported operator identity (provenance, not authentication). Use a distinct, attributable value per operator. |
| `--force-repeat` | Optional. Bypasses ONLY the five-minute repeat safeguard (`COOLDOWN_REFUSAL`). It does not bypass the in-progress report and it records nothing on the row. |

There is NO child-id positional and NO other flag. There is no retry,
reclaim, reset, or recovery flag in R1-1…R1-3.

Per invocation: at most one new child, at most one claim, at most one Vendor
API call. The child is committed durably `RUNNING` BEFORE the Vendor HTTP
call.

### L.4 Bounded output and exit codes

Every stdout line starts with `vendor refresh: `. Lines carry the parent run
id, child ids, bounded state/reason/lookup-status vocabulary values, the
recorded operator, bounded timestamps, and the command outcome class. The
output contains NO secrets, NO raw exception text, NO raw Vendor response
content, NO base URL, and it does NOT echo untrusted or invalid input. The
operator may redirect stdout to a file for the audit trail.

Each invocation prints an informational state read first (`parent-run`,
then `no-prior-child` or `active-child` / `latest-terminal` lines), then
exactly one `outcome:` line. Example of a successful invocation:

```
vendor refresh: parent-run <uuid>
vendor refresh: no-prior-child
vendor refresh: child-created <child-uuid> operator=<id> trigger-source=MANAGEMENT_COMMAND
vendor refresh: outcome: COMPLETED lookup-status=SUCCESS retrieved-at=<iso-8601>
```

Outcome classes and exit codes:

| Outcome | Exit | Meaning / operator interpretation |
|---|---|---|
| `IN_PROGRESS` | 0 | An active child (`PENDING` or `RUNNING`) exists; it was reported (id, state, recorded operator, timestamps) and left untouched. Zero mutation, zero network. Wait; do not "clear" it (L.5). |
| `COOLDOWN_REFUSAL` | 0 | The latest terminal child finished less than 300 s ago. No new child, zero network. Retry later, or use `--force-repeat` only when the earlier attempt genuinely needs superseding. |
| `COMPLETED` | 0 | The child is durably COMPLETED. `lookup-status` is `SUCCESS`, `PARTIAL`, or `FAILED`: `FAILED` means the Vendor API call itself failed at transport level (bounded; no vendor data, `retrieved-at=-`) — a completed refresh attempt, NOT a command defect. |
| `FAILED` | 0 | The child is durably FAILED by this invocation's single bounded defect write, with one of: `MPN_BINDING_VIOLATION`, `VENDOR_LOOKUP_CONFIG_MISSING`, `MPN_QUERY_NORMALIZATION_MISMATCH`, `RESULT_ENCODING_FAILED`, `INTERNAL_ERROR`. |
| `TERMINAL_REPORTED` | 0 | The actual durable terminal state (including `state=ABSENT`) was reported verbatim; no second terminal write was attempted. |
| `INELIGIBLE` | 2 | Invalid parent UUID, invalid operator bound, or a bounded parent-eligibility refusal (`parent_not_found`, `parent_not_completed`, `no_snapshot`, `no_mpn`, `invalid_operator`, `invalid_trigger_source`). Zero mutation. |
| `TERMINALIZATION_NOT_RECORDED` | 3 | The terminal write is not durably recorded; a fresh read establishes the child is NOT terminal. Manual re-check (L.5). |
| `TERMINALIZATION_OUTCOME_UNKNOWN` | 3 | Neither terminal outcome is established. Manual re-check (L.5). |
| `UNEXPECTED_ERROR` | 3 | A contract defect or a non-bounded exception; the bounded output carries the exception type name or bounded reason only. Manual re-check (L.5). |
| `DATABASE_BUSY` | 4 | The database was locked beyond the busy timeout or otherwise unavailable at the serialization point; the transaction rolled back (zero mutation). Re-run manually — there is NO automatic retry. |

**Interpret exit codes together with the outcome line.** Exit 0 includes
bounded refusals and reports (`IN_PROGRESS`, `COOLDOWN_REFUSAL`,
`TERMINAL_REPORTED`), not only success. Non-zero exits never leave the
command's own decision half-applied: `INELIGIBLE` and `DATABASE_BUSY` paths
have zero mutation by construction; exit-3 paths require the manual re-check
described in L.5.

### L.5 Stuck PENDING / RUNNING — report-only HOLD; no automatic recovery

- A `RUNNING` child means an invocation is (or was) executing it. While it
  exists, every further invocation for that parent reports `IN_PROGRESS`
  and does nothing else (zero mutation, zero network).
- If the command process dies (window closed, kill, host reboot) after the
  claim commit, the child remains `RUNNING`. **This implementation has NO
  recovery surface**: no reclaim, no reset, no retry, no reserved-reason
  writer. The command prints a note that the recovery gate (R1-4) is blocked
  pending O8 and asks for a manual re-check.
- The stuck row is a **reported HOLD**: it is safe (the external Vendor
  outcome is held as explicitly unknown; on the command surface no overlap
  is possible — the claim CAS is single-winner and the command never
  re-claims a RUNNING child), but it blocks further refreshes for THAT
  parent until the R1-4 recovery gate is unblocked (O8 completed and
  recorded) and separately approved.
- Orphaned `PENDING` children (created by a non-command trigger) are never
  claimed or executed by this command; they are likewise reported HOLDS.
- Operator duties: note the child id, state, and recorded operator; do not
  attempt to edit the row with SQL or to "restart" it through another
  command form; escalate to the Product Intelligence team with the bounded
  stdout. There is no documented manual repair in R1-1…R1-3.

### L.6 O8 host-evidence checklist (deployment gate)

O8 is the frozen deployment prerequisite (DESIGN2 §4.5): an explicit host
permissions and operational audit review, completed and recorded, BEFORE any
R1 surface is deployed. It is also the R1-4 (recovery gate) unblock
condition. The following host evidence is still needed on the actual
deployment host. **Until each item is evidenced and recorded, it remains
NOT VERIFIED; this runbook asserts no account names, no ACLs, and no
logging capabilities.**

| # | Evidence required | Status |
|---|---|---|
| 1 | **Windows command-execution accounts.** Inventory of the Windows accounts that can run `python manage.py ...` (host/CMD access) on the deployment host — the account is the real authorization boundary. Note whether accounts are distinct per operator or shared administrative (shared accounts reduce actor attribution; `--operator` mitigates but does not solve this). | NOT VERIFIED |
| 2 | **SQLite file and directory ACLs.** Evidence of the ACLs controlling the database file (`PI_SQLITE_PATH`) and its parent directory — which accounts can read, modify, or delete it (including the backup copy location used by Section H). | NOT VERIFIED |
| 3 | **Host-level command logging.** Evidence of whether command invocations (account + command line) are actually captured on the host (for example, Windows Security/Event logs or an equivalent mechanism), and where and how long they are retained. No trustworthy-OS-audit claim is made until verified in production. | NOT VERIFIED |
| 4 | **Backup and command coordination.** Confirmation that the Section H backup procedure is performed with the application stopped AND with no vendor refresh command running (L.3), and that non-canonical launch forms (wrapped/renamed) are not in use. | NOT VERIFIED (procedure documented in H/L.3; host practice not yet evidenced) |

R1-4 unblock additions (also part of O8, required before the recovery gate):
administrator process-table visibility on the host, and the evidence
retention location/duration for recovery records. Both: NOT VERIFIED.

**Deployment of any R1 surface remains HOLD until items 1–4 above are
completed and recorded** (and, for R1-4 specifically, until its additions
are as well).

---

## Troubleshooting

### Preflight Fails: DEBUG must be disabled

Set `DJANGO_DEBUG=0` in environment.

### Preflight Fails: SECRET_KEY is not production-safe

Set `DJANGO_SECRET_KEY` to a random value at least 32 characters long.

### Preflight Fails: ALLOWED_HOSTS is empty

Set `DJANGO_ALLOWED_HOSTS` to your server's hostname or IP.

### Preflight Fails: SERPER_API_KEY is missing

Set `SERPER_API_KEY` environment variable.

### Preflight Fails: Semantic provider configuration incomplete

Ensure both `PI_SEMANTIC_AMAX_BASE_URL` and `PI_SEMANTIC_VLLM_262K_BASE_URL` are set.

### Preflight Fails: Database parent directory not writable

Check permissions on the database parent directory.

### Vendor refresh: `FAILED failure-reason=VENDOR_LOOKUP_CONFIG_MISSING`

`PI_VENDOR_LOOKUP_BASE_URL` is absent or blank in the environment the
command ran in. Set it (Section B) and re-run as a NEW explicit invocation
(the failed child remains a durable FAILED row; note the five-minute
`COOLDOWN_REFUSAL` safeguard — `--force-repeat` is required if you re-run
within 300 s).

### Vendor refresh: repeated `IN_PROGRESS` over the same child

The child is active (`PENDING` or `RUNNING`). If the original invocation is
still running, wait for its `outcome:` line. If the original invocation is
known to be dead, the child is a stuck reported HOLD (L.5): no automatic
recovery exists in R1-1…R1-3; escalate with the bounded stdout.

### Vendor refresh: `DATABASE_BUSY`

Another writer held the database lock beyond the busy timeout. The command
changed nothing. Re-run manually once the other writer (typically the
application or a manual operation) has finished.

### Server Won't Start

Check that no other process is using the same port.

### FoxPro Launcher Doesn't Open

Verify the URL pattern matches: `/research/new?mpn=<encoded>&description=<encoded>`

---

## Security Notes

- **Internal network only.** This application must NOT be exposed to unrestricted public Internet.
- **Bind/access restrictions** must be enforced by network firewall or reverse proxy.
- **No application authentication** exists in this phase.
- **Report UUIDs are NOT access control.** Anyone with the URL can view the report.
- **No credentials in source code, CMD files, or URLs.**

---

## Contact

For deployment issues, contact the Product Intelligence team.