# Product Intelligence — Internal Pilot Deployment Runbook

**Phase:** PILOT-RELEASE-1  
**Scope:** Internal customer pilot deployment on Windows  
**Security Boundary:** Internal trusted-network pilot only

---

## Overview

This runbook covers the deployment of the Product Intelligence application for an internal customer pilot. The pilot uses the existing Product Intelligence web application with a Windows-compatible production WSGI server.

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
python -m waitress dispatch "config.wsgi:application" --host=%PI_BIND_HOST% --port=%PI_BIND_PORT%
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
   http://<internal-host>:<port>/research/new?mpn=XP15360SE70005&description=Seagate%20Nytro%205050%202TB%20SSD
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

```cmd
REM Stop the application first

REM Create a timestamped backup
copy D:\product-intel-data\db.sqlite3 D:\product-intel-data\db_backup_%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.sqlite3
```

**Or use this simpler approach:**

```cmd
REM Stop the application first
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

1. **Stop the application**

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