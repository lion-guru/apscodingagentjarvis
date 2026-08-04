@echo off
title DevMind Executable Builder — PyInstaller Bundle
echo ========================================================
echo   DEVMIND PORTABLE AI SUITE - BUILDING STANDALONE EXE
echo ========================================================
echo.

set PORTABLE_DIR=%~dp0
cd /d "%PORTABLE_DIR%"

:: Activate local venv
if exist "%PORTABLE_DIR%venv\Scripts\activate.bat" (
    call "%PORTABLE_DIR%venv\Scripts\activate.bat"
)

:: Install PyInstaller if missing
pip install pyinstaller -q

echo [1/2] Packaging DevMind AI Server into standalone executable...
pyinstaller --noconfirm --onedir --windowed --name "DevMind_AI_Studio" ^
    --add-data "web;web" ^
    --add-data "config.json;." ^
    --add-data "skills;skills" ^
    --add-data "dev_wake_word_bg.py;." ^
    server.py

echo.
echo ========================================================
echo   EXE BUILD COMPLETE! OUTPUT DIRECTORY:
echo   %PORTABLE_DIR%dist\DevMind_AI_Studio\
echo ========================================================
pause
