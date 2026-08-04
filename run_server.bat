@echo off
title DevMind AI Web Server
echo ========================================================
echo Starting DevMind Web Server on http://localhost:7860...
echo Target Workspace: c:\xampp\htdocs\apsdreamhome
echo ========================================================
echo.

cd /d "%~dp0"

:: Activate virtual environment if present
if exist "venv\Scripts\activate.bat" (
    echo Activating Virtual Environment...
    call venv\Scripts\activate.bat
)

set DEVMIND_CWD=c:\xampp\htdocs\apsdreamhome
set DEVMIND_MODEL=gemini-2.0-flash

echo Launching python server.py...
echo Open http://localhost:7860 in your web browser.
echo.

python server.py

echo.
echo Server stopped or crashed. Press any key to exit.
pause
