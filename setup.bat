@echo off
echo ============================================
echo   DevMind / Jarvis — Setup Script
echo ============================================
echo.
echo Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo Python found.
echo.
echo Installing dependencies...
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Some dependencies may have failed to install.
)
echo.
echo Installing ChromeDriver for browser automation...
python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()" 2>nul
echo.
echo Setup complete!
echo.
echo Next steps:
echo   1. Edit .env and add your API keys
echo   2. Run: py -m uvicorn server:app --host 127.0.0.1 --port 7860 --reload
echo   3. Open: http://127.0.0.1:7860
echo.
pause