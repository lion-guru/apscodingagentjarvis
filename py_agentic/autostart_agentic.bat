@echo off
REM Agentic Dev System - Windows Startup Launcher
REM Launches the Python agentic dev system in continuous mode, minimized
REM Remove this file from Startup folder to disable auto-start

cd /d "C:\Users\abhay\coding-assistant-working\py_agentic"

REM Check Python
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set PYTHON_CMD=python
    ) else (
        exit /b 1
    )
)

REM Launch agentic dev system in background, minimized
%PYTHON_CMD% main.py --cycles 999 --interval 30 > "%~dp0..\..\logs\startup_agentic.log" 2>&1

exit