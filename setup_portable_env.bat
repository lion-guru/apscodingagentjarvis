@echo off
title Portable DevMind AI Suite — Environment Setup
echo ========================================================
echo   DEVMIND PORTABLE AI SUITE - SETUP ENVIRONMENT
echo ========================================================
echo.

set PORTABLE_DIR=%~dp0
cd /d "%PORTABLE_DIR%"

:: 1. Setup local virtual environment if not present
if not exist "%PORTABLE_DIR%venv\Scripts\activate.bat" (
    echo [1/4] Creating portable Python virtual environment in venv...
    python -m venv "%PORTABLE_DIR%venv"
) else (
    echo [1/4] Portable Python venv already initialized.
)

:: 2. Activate venv
call "%PORTABLE_DIR%venv\Scripts\activate.bat"

:: 3. Install required packages
echo.
echo [2/4] Installing Python dependencies (FastAPI, WebSockets, SpeechRecognition)...
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install SpeechRecognition pyaudio -q

:: 4. Import futuristic audio sound effects and visual assets from stonic_dsktp
echo.
echo [3/4] Importing futuristic audio effects and branding assets...
python copy_stonic_assets.py

:: 5. Setup Agent Town Pixel Workspace dependencies
echo.
echo [4/4] Setting up Agent Town Pixel Workspace...
if exist "%PORTABLE_DIR%agent-town" (
    cd /d "%PORTABLE_DIR%agent-town"
    call npx pnpm@latest install
    cd /d "%PORTABLE_DIR%"
)

echo.
echo ========================================================
echo   PORTABLE ENVIRONMENT READY! RUN start_portable.bat
echo ========================================================
pause
