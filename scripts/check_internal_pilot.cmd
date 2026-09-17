@echo off
REM Product Intelligence Internal Pilot Check Script (PILOT-RELEASE-1)
REM
REM Runs operational validation checks without network provider calls.
REM
REM Usage:
REM   scripts\check_internal_pilot.cmd

setlocal enabledelayedexpansion

REM Change to the project root directory
cd /d "%~dp0.."

echo Running Django deployment checks...
python manage.py check --deploy
if errorlevel 1 (
    echo.
    echo Django check --deploy reported issues.
    echo.
    endlocal
    exit /b 1
)

echo.
echo Running pilot preflight checks...
python manage.py pilot_check
if errorlevel 1 (
    echo.
    echo Pilot preflight failed.
    echo.
    endlocal
    exit /b 1
)

echo.
echo All checks passed.

endlocal
exit /b 0