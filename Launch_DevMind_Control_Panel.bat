@echo off
title DevMind AI Control Panel
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python gui_launcher.py

if errorlevel 1 (
    echo.
    echo ERROR: Python failed to start gui_launcher.py
    pause
)
