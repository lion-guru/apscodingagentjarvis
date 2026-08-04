@echo off
REM APS Dream Home - Python Agentic Dev System Startup Script
REM Windows batch version

setlocal EnableDelayedExpansion

REM Default values
set MAX_ITERATIONS=3
set CONTINUOUS=0
set SKIP_E2E=0

REM Parse arguments
:parse_args
if "%~1"=="" goto :done_args
if /i "%~1"=="-continuous" (set CONTINUOUS=1)
if /i "%~1"=="-skip-e2e" (set SKIP_E2E=1)
if /i "%~1"=="-h" goto :show_help
if /i "%~1"=="--help" goto :show_help
shift
goto :parse_args
:done_args

if %CONTINUOUS%==1 (
    set CYCLES=999
) else (
    set CYCLES=%MAX_ITERATIONS%
)

echo === APS Dream Home - Python Agentic Dev System ===
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Check Python
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    set PYTHON_CMD=py
) else (
    where python >nul 2>&1
    if %ERRORLEVEL%==0 (
        set PYTHON_CMD=python
    ) else (
        echo ERROR: Python not found. Please install Python 3.12+ and try again.
        exit /b 1
    )
)

REM Check Python version
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PY_VERSION=%%i
echo Python: %PY_VERSION%

REM Check Ollama
echo Checking Ollama...
%PYTHON_CMD% -c "import urllib.request; r=urllib.request.urlopen('http://localhost:11434/api/tags', timeout=3); print('Ollama: Connected')" 2>nul
if %ERRORLEVEL%==0 (
    echo Ollama: Connected
) else (
    echo Ollama: Not running (agents will run without AI reasoning)
)

echo.

REM Build command arguments
set CMD_ARGS=--cycles %CYCLES% --interval 30
if %SKIP_E2E%==1 set CMD_ARGS=%CMD_ARGS% --skip-e2e

echo Starting orchestrator...
echo.

%PYTHON_CMD% main.py %CMD_ARGS%

echo.
echo === Orchestrator finished ===
exit /b 0

:show_help
echo APS Dream Home - Python Agentic Dev System
echo.
echo Usage: start.bat [-continuous] [-skip-e2e] [-h]
echo.
echo Options:
echo   -continuous   Run continuously (default: 3 iterations)
echo   -skip-e2e     Skip E2E tests
echo   -h, --help    Show this help message
echo.
echo Examples:
echo   start.bat                   Run 3 cycles
echo   start.bat -continuous       Run forever
echo   start.bat -skip-e2e         Run 3 cycles, skip E2E tests
exit /b 0
