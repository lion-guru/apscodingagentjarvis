@echo off
title DevMind AI Studio - Full Stack
echo.
echo ============================================================
echo   DevMind AI Studio - Full Stack Startup
echo ============================================================
echo.

:: Check Python venv
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Python venv not found. Run START_SERVER.bat first to set up.
    pause
    exit /b 1
)

:: Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org
    pause
    exit /b 1
)

:: Kill any existing servers on ports 7860 and 3000
echo [1/4] Cleaning up old processes...
venv\Scripts\python.exe -c "import subprocess, os, re; out=subprocess.run('netstat -ano', capture_output=True, text=True, shell=True).stdout; pids=set(re.findall(r':7860\s+.*?\s+(\d+)', out)); [os.system(f'taskkill /PID {p} /F >nul 2>&1') for p in pids if p!='0']"
venv\Scripts\python.exe -c "import subprocess, os, re; out=subprocess.run('netstat -ano', capture_output=True, text=True, shell=True).stdout; pids=set(re.findall(r':3000\s+.*?\s+(\d+)', out)); [os.system(f'taskkill /PID {p} /F >nul 2>&1') for p in pids if p!='0']"

:: Start DevMind server (background)
echo [2/4] Starting DevMind server on http://127.0.0.1:7860...
set DEVMIND_CWD=E:\coding-assistant
if not defined DEVMIND_MODEL set DEVMIND_MODEL=gemini-2.5-flash
start "DevMind Server" cmd /c "venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 7860 --log-level info"

:: Wait for server to start
echo [3/4] Waiting for server to start...
timeout /t 3 /nobreak >nul

:: Start Agent Town (background)
echo [4/4] Starting Agent Town on http://127.0.0.1:3000...
start "Agent Town" cmd /c "cd /d E:\coding-assistant\agent-town && npx pnpm@latest dev"

echo.
echo ============================================================
echo   Both servers starting!
echo.
echo   DevMind:   http://localhost:7860
echo   Agent Town: http://localhost:3000
echo.
echo   Close this window or press CTRL+C to stop both.
echo ============================================================
echo.
pause
