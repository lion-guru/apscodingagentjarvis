@echo off
echo ============================================
echo  DevMind Jarvis - Full Installation Setup
echo ============================================
echo.

echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo OK: Python found.

echo [2/5] Creating virtual environment...
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)
echo OK: Virtual environment created.

echo [3/5] Installing Python dependencies...
call venv\Scripts\activate
pip install --upgrade pip setuptools wheel
pip install fastapi uvicorn websockets httpx pydantic jinja2 psutil python-multipart aiofiles
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo OK: Dependencies installed.

echo [4/5] Downloading optional large binaries (Node.js, FFmpeg, Mediapipe WASM)...
echo (ye files GitHub par nahi hain — automatically download ho rahi hain)
python setup_dependencies.py
echo OK: Binary dependencies handled.

echo [5/5] Creating configuration directories...
if not exist "%USERPROFILE%\.devmind\commands" mkdir "%USERPROFILE%\.devmind\commands"
if not exist "%USERPROFILE%\.devmind\sessions" mkdir "%USERPROFILE%\.devmind\sessions"
if not exist "%USERPROFILE%\.devmind\agents"   mkdir "%USERPROFILE%\.devmind\agents"
if not exist "%USERPROFILE%\.devmind\knowledge" mkdir "%USERPROFILE%\.devmind\knowledge"
if not exist "%USERPROFILE%\.devmind\artifacts" mkdir "%USERPROFILE%\.devmind\artifacts"
echo OK: Configuration directories created.

echo.
echo ============================================
echo  DevMind Jarvis installed successfully!
echo ============================================
echo.
echo .env file configure karo (API keys add karo):
echo   copy .env.example .env
echo   (phir .env file mein apni keys add karo)
echo.
echo Server start karo:
echo   START_SERVER.bat
echo   ya:  python server.py
echo.
echo Browser mein kholo:  http://localhost:7860
echo.
pause