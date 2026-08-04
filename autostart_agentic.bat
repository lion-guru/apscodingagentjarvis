@echo off
REM Agentic Dev System - Windows Auto-Start Launcher
REM Launches the Python agentic dev system in continuous mode
REM Place in Windows Startup folder for auto-start on login

setlocal
cd /d "%~dp0py_agentic"

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set PYTHON_CMD=python
    ) else (
        echo ERROR: Python not found
        exit /b 1
    )
)

%PYTHON_CMD% main.py --cycles 999 --interval 30
exit /b 0
