@echo off
rem Product Intelligence Codex executable resolver.
rem Called by codex-pi.cmd and verify-codex-pi.cmd.
rem
rem Selection order:
rem   1. Newest Desktop build subdirectory under:
rem      %LOCALAPPDATA%\OpenAI\Codex\bin\<build>\codex.exe
rem   2. Existing CODEX_EXE, if it points to a real file
rem   3. Legacy/stable %LOCALAPPDATA%\OpenAI\Codex\bin\codex.exe
rem   4. First codex.exe found on PATH
rem
rem The resolved path is stored only in PI_CODEX_EXE for this process.
rem This script never writes Windows environment variables.

set "PI_CODEX_EXE="
set "PI_CODEX_SOURCE="
set "PI_CODEX_VERSION="

set "PI_CODEX_BIN=%LOCALAPPDATA%\OpenAI\Codex\bin"

if exist "%PI_CODEX_BIN%\" (
    for /f "delims=" %%D in ('dir /b /ad /o:-d "%PI_CODEX_BIN%" 2^>nul') do (
        if not defined PI_CODEX_EXE (
            if exist "%PI_CODEX_BIN%\%%D\codex.exe" (
                set "PI_CODEX_EXE=%PI_CODEX_BIN%\%%D\codex.exe"
                set "PI_CODEX_SOURCE=latest Desktop build"
            )
        )
    )
)

if not defined PI_CODEX_EXE (
    if defined CODEX_EXE (
        if exist "%CODEX_EXE%" (
            set "PI_CODEX_EXE=%CODEX_EXE%"
            set "PI_CODEX_SOURCE=CODEX_EXE"
        )
    )
)

if not defined PI_CODEX_EXE (
    if exist "%PI_CODEX_BIN%\codex.exe" (
        set "PI_CODEX_EXE=%PI_CODEX_BIN%\codex.exe"
        set "PI_CODEX_SOURCE=legacy bin\codex.exe fallback"
    )
)

if not defined PI_CODEX_EXE (
    for /f "delims=" %%F in ('where codex.exe 2^>nul') do (
        if not defined PI_CODEX_EXE (
            set "PI_CODEX_EXE=%%F"
            set "PI_CODEX_SOURCE=PATH"
        )
    )
)

if not defined PI_CODEX_EXE (
    echo ERROR: Unable to locate a usable Codex CLI executable.
    echo Checked:
    echo   %PI_CODEX_BIN%\^<build^>\codex.exe
    echo   CODEX_EXE
    echo   %PI_CODEX_BIN%\codex.exe
    echo   PATH
    exit /b 1
)

for /f "delims=" %%V in ('""%PI_CODEX_EXE%" --version 2^>nul"') do (
    if not defined PI_CODEX_VERSION set "PI_CODEX_VERSION=%%V"
)

if not defined PI_CODEX_VERSION (
    echo ERROR: Located Codex executable but could not run it:
    echo   %PI_CODEX_EXE%
    exit /b 1
)

exit /b 0
