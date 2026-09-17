@echo off
REM Product Intelligence Internal Pilot Launcher (PILOT-RELEASE-1)
REM
REM This script:
REM 1. Runs the preflight check (pilot_check)
REM 2. Stops immediately if preflight fails
REM 3. Starts the production WSGI server (Waitress)
REM
REM Configuration comes from environment variables (no hard-coded secrets).
REM Do NOT place secret environment values inside this script.
REM
REM Usage:
REM   scripts\run_internal_pilot.cmd
REM
REM Required environment variables (set before launching):
REM   DJANGO_SECRET_KEY=<server secret>
REM   DJANGO_ALLOWED_HOSTS=<internal host/IP>
REM   PI_SQLITE_PATH=<durable absolute path>
REM   SERPER_API_KEY=<server secret>
REM   PI_SEMANTIC_AMAX_BASE_URL=<server URL>
REM   PI_SEMANTIC_VLLM_262K_BASE_URL=<server URL>
REM
REM Optional:
REM   PI_BIND_PORT=<port>  (default: 8000)
REM   PI_BIND_HOST=<host>  (default: 0.0.0.0 for internal pilot)
REM   PI_SEMANTIC_AMAX_API_KEY=<server secret>
REM   PI_SEMANTIC_VLLM_262K_API_KEY=<server secret>
REM
REM IMPORTANT: Bind to 0.0.0.0 ONLY when network firewall/access control
REM restricts access to the approved internal network.
REM 0.0.0.0 is NOT secure by itself - it only binds to all interfaces.

setlocal enabledelayedexpansion

set "FAIL=0"

REM Change to the project root directory
cd /d "%~dp0.."

REM Run preflight validation
echo Running preflight checks...
python manage.py pilot_check
if errorlevel 1 (
    set "FAIL=1"
    echo.
    echo Preflight failed. Fix the issues above before starting the server.
    echo.
    endlocal
    exit /b 1
)

echo.
echo Preflight passed. Starting server...
echo.

REM Get bind configuration (with defaults)
set "PI_BIND_PORT=%PI_BIND_PORT: =%"
if "%PI_BIND_PORT%"=="" set "PI_BIND_PORT=8000"

set "PI_BIND_HOST=%PI_BIND_HOST: =%"
if "%PI_BIND_HOST%"=="" set "PI_BIND_HOST=0.0.0.0"

echo Binding to %PI_BIND_HOST%:%PI_BIND_PORT%
echo.

REM Start Waitress WSGI server
REM PYTHONPATH ensures Django config module resolves
set "PYTHONPATH=%CD%;%PYTHONPATH%"

python -m waitress --host=%PI_BIND_HOST% --port=%PI_BIND_PORT% config.wsgi:application

endlocal
exit /b %errorlevel%