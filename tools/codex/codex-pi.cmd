@echo off
setlocal EnableExtensions

cd /d "%~dp0\..\.."

call "%~dp0resolve-codex.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%

call :require_auto_review
if errorlevel 1 exit /b %ERRORLEVEL%

echo Using Codex:
echo   %PI_CODEX_EXE%
echo   %PI_CODEX_VERSION%
echo   source: %PI_CODEX_SOURCE%
echo   approval mode: Approve for me / Auto Review
echo.

set "CHOICE=%~1"
if "%CHOICE%"=="" set "CHOICE=qwen"

if /I "%CHOICE%"=="qwen" goto qwen
if /I "%CHOICE%"=="qwen36" goto qwen
if /I "%CHOICE%"=="minimax" goto minimax
if /I "%CHOICE%"=="minimax-thinking" goto minimax
if /I "%CHOICE%"=="nemotron" goto nemotron

echo Usage:
echo   tools\codex\codex-pi.cmd [qwen^|minimax^|nemotron]
echo.
echo Default: qwen
exit /b 2

:qwen
set "PI_MODEL=Qwen3.6-27B-262K"
echo ============================================================
echo Product Intelligence Codex
echo Model: %PI_MODEL% direct
echo Profile: qwen-local
echo Approval: Auto Review
echo Model lock: CLI -m override
echo ============================================================
"%PI_CODEX_EXE%" -c apps._default.enabled=false --profile qwen-local -m "%PI_MODEL%" --approve-for-me
exit /b %ERRORLEVEL%

:minimax
set "PI_MODEL=minimax-m2.7-thinking"
call :ensure_minimax_shim
if errorlevel 1 exit /b %ERRORLEVEL%
echo ============================================================
echo Product Intelligence Codex
echo Model: %PI_MODEL%
echo Profile: b300-minimax-thinking
echo Compatibility shim: http://127.0.0.1:18081/v1
echo Approval: Auto Review
echo Model lock: CLI -m override
echo ============================================================
"%PI_CODEX_EXE%" -c "model_providers.amax_b300.base_url='http://127.0.0.1:18081/v1'" -c apps._default.enabled=false --profile b300-minimax-thinking -m "%PI_MODEL%" --approve-for-me
exit /b %ERRORLEVEL%

:nemotron
set "PI_MODEL=nemotron-3-super"
echo ============================================================
echo Product Intelligence Codex
echo Model: %PI_MODEL%
echo Profile: b300-nemotron
echo Approval: Auto Review
echo Model lock: CLI -m override
echo ============================================================
"%PI_CODEX_EXE%" -c apps._default.enabled=false --profile b300-nemotron -m "%PI_MODEL%" --approve-for-me
exit /b %ERRORLEVEL%

:require_auto_review
"%PI_CODEX_EXE%" --help 2>nul | findstr /l /c:"--approve-for-me" >nul
if errorlevel 1 (
    echo ERROR: This Codex build does not advertise --approve-for-me.
    echo.
    echo Resolved Codex:
    echo   %PI_CODEX_EXE%
    echo   %PI_CODEX_VERSION%
    echo.
    echo Product Intelligence launcher will not silently fall back to manual
    echo approval mode. Update Codex Desktop or launch manually with the
    echo approval mode you intend.
    exit /b 1
)
exit /b 0

:ensure_minimax_shim
curl.exe -s --max-time 1 http://127.0.0.1:18081/__pi_minimax_shim_health >nul 2>&1
if not errorlevel 1 (
    curl.exe -s --max-time 1 http://127.0.0.1:18081/__pi_minimax_shim_health | findstr /x /c:"PI_MINIMAX_SHIM_V3_OK" >nul 2>&1
    if not errorlevel 1 exit /b 0
)

where python.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: python.exe was not found in PATH; cannot start MiniMax shim.
    exit /b 1
)

echo Starting temporary MiniMax Codex compatibility shim...
start "PI MiniMax Codex Shim" /min python "%~dp0minimax_reasoning_shim_v3.py"
timeout /t 2 /nobreak >nul

curl.exe -s --max-time 2 http://127.0.0.1:18081/__pi_minimax_shim_health >nul 2>&1
if errorlevel 1 (
    echo ERROR: MiniMax shim did not become reachable on 127.0.0.1:18081.
    exit /b 1
)
curl.exe -s --max-time 1 http://127.0.0.1:18081/__pi_minimax_shim_health | findstr /x /c:"PI_MINIMAX_SHIM_V3_OK" >nul 2>&1
if errorlevel 1 (
    echo ERROR: MiniMax shim health check did not return exact marker.
    exit /b 1
)
exit /b 0
