@echo off
setlocal EnableExtensions

cd /d "%~dp0\..\.."

call "%~dp0resolve-codex.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%

if not exist "AGENTS.md" (
    echo ERROR: AGENTS.md is missing from the Product Intelligence repo root.
    exit /b 1
)
if not exist "CLAUDE.md" (
    echo ERROR: CLAUDE.md is missing from the Product Intelligence repo root.
    exit /b 1
)

echo ============================================================
echo Product Intelligence Codex verification
echo Workdir: %CD%
echo Codex:
echo   %PI_CODEX_EXE%
echo   %PI_CODEX_VERSION%
echo   source: %PI_CODEX_SOURCE%
echo ============================================================
echo.

set "TEMP_DIR=%TEMP%\PI_codex_verify_%TIME::=%.%RANDOM%"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%" >nul 2>&1

:: ============================================================
:: Verification prompt — requires actual file reads, forbids guessing
:: ============================================================
set "VERIFY_PROMPT=You MUST actually read repository files using your file-reading tools, not infer contents from prior context or training data. Step 1: Read the full contents of AGENTS.md in the repository root. Step 2: Read at least the first line and first heading of CLAUDE.md in the repository root. Step 3: Confirm that AGENTS.md states CLAUDE.md is the durable AI operating contract AND CLAUDE.md is for Product Intelligence. If you cannot read the files using your tools, try: C:\\WINDOWS\\system32\\cmd.exe /c type AGENTS.md and C:\\WINDOWS\\system32\\cmd.exe /c type CLAUDE.md. If you cannot successfully read both files with proof of their contents, do NOT emit any success marker. Only after you have confirmed the facts from actual file reads, reply with exactly the success marker and nothing else:"

:: ============================================================
:: [1/3] Qwen3.6-27B-262K direct
:: ============================================================
echo [1/3] Qwen3.6-27B-262K direct
"%PI_CODEX_EXE%" -c apps._default.enabled=false --profile qwen-local -m "Qwen3.6-27B-262K" --sandbox read-only --ask-for-approval never exec --skip-git-repo-check --output-last-message "%TEMP_DIR%\qwen_output.txt" "%VERIFY_PROMPT% PI_QWEN_PROJECT_OK"
set "QWEN_RC=%ERRORLEVEL%"
echo Qwen exit code: %QWEN_RC%
if not errorlevel 1 goto :qwen_success
echo FAIL: Qwen process failed with exit code %QWEN_RC%
set "QWEN_MARKER_RESULT=1"
goto :qwen_done
:qwen_success
call :verify_marker "PI_QWEN_PROJECT_OK" "%TEMP_DIR%\qwen_output.txt"
set "QWEN_MARKER_RESULT=%ERRORLEVEL%"
:qwen_done
echo.

:: ============================================================
:: [2/3] MiniMax M2.7 Thinking
:: ============================================================
echo [2/3] MiniMax M2.7 Thinking
call :ensure_minimax_shim
if errorlevel 1 (
    set "MINIMAX_RC=1"
    set "MINIMAX_MARKER_RESULT=1"
    echo FAIL: MiniMax shim check failed
    echo.
    goto :nemotron_section
)

"%PI_CODEX_EXE%" -c "model_providers.amax_b300.base_url='http://127.0.0.1:18081/v1'" -c apps._default.enabled=false --profile b300-minimax-thinking --sandbox read-only --ask-for-approval never exec --skip-git-repo-check --output-last-message "%TEMP_DIR%\minimax_output.txt" "%VERIFY_PROMPT% PI_MINIMAX_PROJECT_OK"
set "MINIMAX_RC=%ERRORLEVEL%"
echo MiniMax exit code: %MINIMAX_RC%
if not errorlevel 1 goto :minimax_success
echo FAIL: MiniMax process failed with exit code %MINIMAX_RC%
set "MINIMAX_MARKER_RESULT=1"
goto :minimax_done
:minimax_success
call :verify_marker "PI_MINIMAX_PROJECT_OK" "%TEMP_DIR%\minimax_output.txt"
set "MINIMAX_MARKER_RESULT=%ERRORLEVEL%"
:minimax_done
echo.

:nemotron_section
:: ============================================================
:: [3/3] Nemotron-3-Super
:: ============================================================
echo [3/3] Nemotron-3-Super
"%PI_CODEX_EXE%" -c apps._default.enabled=false --profile b300-nemotron --sandbox read-only --ask-for-approval never exec --skip-git-repo-check --output-last-message "%TEMP_DIR%\nemotron_output.txt" "%VERIFY_PROMPT% PI_NEMOTRON_PROJECT_OK"
set "NEMOTRON_RC=%ERRORLEVEL%"
echo Nemotron exit code: %NEMOTRON_RC%
if not errorlevel 1 goto :nemotron_success
echo FAIL: Nemotron process failed with exit code %NEMOTRON_RC%
set "NEMOTRON_MARKER_RESULT=1"
goto :nemotron_done
:nemotron_success
call :verify_marker "PI_NEMOTRON_PROJECT_OK" "%TEMP_DIR%\nemotron_output.txt"
set "NEMOTRON_MARKER_RESULT=%ERRORLEVEL%"
:nemotron_done
echo.

:: ============================================================
:: Final summary
:: ============================================================
echo ============================================================
echo Expected final model markers:
echo   PI_QWEN_PROJECT_OK
echo   PI_MINIMAX_PROJECT_OK
echo   PI_NEMOTRON_PROJECT_OK
echo.
echo Exit codes:
echo   Qwen:     %QWEN_RC%
echo   MiniMax:  %MINIMAX_RC%
echo   Nemotron: %NEMOTRON_RC%
echo.
echo Exact-marker validation:
echo   Qwen:     %QWEN_MARKER_RESULT% (0=PASS,1=FAIL)
echo   MiniMax:  %MINIMAX_MARKER_RESULT% (0=PASS,1=FAIL)
echo   Nemotron: %NEMOTRON_MARKER_RESULT% (0=PASS,1=FAIL)
echo ============================================================

if not "%QWEN_RC%"=="0" exit /b 1
if not "%MINIMAX_RC%"=="0" exit /b 1
if not "%NEMOTRON_RC%"=="0" exit /b 1
if not "%QWEN_MARKER_RESULT%"=="0" exit /b 1
if not "%MINIMAX_MARKER_RESULT%"=="0" exit /b 1
if not "%NEMOTRON_MARKER_RESULT%"=="0" exit /b 1

:: Clean up temp files
rmdir /s /q "%TEMP_DIR%" 2>nul
exit /b 0

:verify_marker
set "EXPECTED_MARKER=%~1"
set "OUTPUT_FILE=%~2"

if not exist "%OUTPUT_FILE%" (
    echo ERROR: Verification output file not found: %OUTPUT_FILE%
    exit /b 1
)

:: Robust exact comparison via python — avoids CMD parse failures on arbitrary model output
:: (ampersands, parens, quotes, etc. in model responses would break CMD IF syntax)
:: python exits: 0 = exact match, 1 = empty file, 2 = mismatch
python -c "import sys,pathlib; p=pathlib.Path(sys.argv[1]); t=p.read_text(encoding='utf-8-sig').strip(chr(13)+chr(10)); e=sys.argv[2]; s=len(t)==0; sys.exit(1 if s else (0 if t==e else 2))" "%OUTPUT_FILE%" "%EXPECTED_MARKER%"
set "_VM_RC=%ERRORLEVEL%"
if "%_VM_RC%"=="0" (
    echo PASS: Exact marker matched
    exit /b 0
)
if "%_VM_RC%"=="1" (
    echo FAIL: Output file is empty
    exit /b 1
)
echo FAIL: Marker mismatch
echo   Expected: %EXPECTED_MARKER%
exit /b 1

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
