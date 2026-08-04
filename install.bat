@echo off
echo ============================================
echo  DevMind IDE - Installation Script
echo ============================================
echo.

echo [1/4] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo OK: Python found.

echo [2/4] Creating virtual environment...
python -m venv .venv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)
echo OK: Virtual environment created.

echo [3/4] Installing dependencies...
call .venv\Scripts\activate
pip install --upgrade pip setuptools wheel
pip install fastapi uvicorn websockets httpx pydantic jinja2
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo OK: Dependencies installed.

echo [4/4] Creating configuration directories...
if not exist "%USERPROFILE%\.devmind\commands" mkdir "%USERPROFILE%\.devmind\commands"
if not exist "%USERPROFILE%\.devmind\sessions" mkdir "%USERPROFILE%\.devmind\sessions"
if not exist "%USERPROFILE%\.devmind\agents" mkdir "%USERPROFILE%\.devmind\agents"
if not exist "%USERPROFILE%\.devmind\knowledge" mkdir "%USERPROFILE%\.devmind\knowledge"
if not exist "%USERPROFILE%\.devmind\artifacts" mkdir "%USERPROFILE%\.devmind\artifacts"
echo OK: Configuration directories created.

echo.
echo ============================================
echo  DevMind IDE installed successfully!
echo ============================================
echo.
echo To start the IDE, run:
echo   python server.py
echo.
echo Or activate the venv first:
echo   call .venv\Scripts\activate
echo   python server.py
echo.
echo Open http://localhost:8000 in your browser.
echo.
pause