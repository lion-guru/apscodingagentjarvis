@echo off
title DevMind - Smart Start
color 0A
cls

echo ============================================================
echo   DevMind AI Agent - Smart Startup + Diagnostics
echo ============================================================
echo.

cd /d "E:\coding-assistant"

:: ─── 1. Check Python ───
echo [1/7] Checking Python...
venv\Scripts\python.exe --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: venv Python not found!
    echo  Run: python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('venv\Scripts\python.exe --version 2^>^&1') do echo  OK: %%v

:: ─── 2. Check syntax ───
echo.
echo [2/7] Checking server.py syntax...
venv\Scripts\python.exe -c "import ast; ast.parse(open('server.py',encoding='utf-8').read()); print(' OK: No syntax errors')"
if errorlevel 1 (
    echo  ERROR: Syntax error in server.py!
    pause & exit /b 1
)

:: ─── 3. Check required packages ───
echo.
echo [3/7] Checking required packages...
venv\Scripts\python.exe -c "import fastapi, uvicorn, httpx, websockets; print(' OK: Core packages installed')"
if errorlevel 1 (
    echo  Installing missing packages...
    venv\Scripts\pip install fastapi uvicorn httpx websockets python-multipart aiofiles psutil selenium webdriver-manager
)

venv\Scripts\python.exe -c "import psutil, selenium; print(' OK: psutil & selenium available')" >nul 2>&1
if errorlevel 1 (
    echo  Installing psutil, selenium ^& webdriver-manager...
    venv\Scripts\pip install psutil selenium webdriver-manager
)


:: ─── 4. Check .env file ───
echo.
echo [4/7] Checking .env configuration...
if not exist ".env" (
    echo  WARNING: .env not found - copy .env.example to .env and add your API keys
) else (
    echo  OK: .env file found
    venv\Scripts\python.exe -c "import os; lines=[l.split('=')[0].strip() for l in open('.env',encoding='utf-8') if '=' in l and not l.startswith('#')]; print(' Keys configured:', ', '.join(lines[:5]))"
)

:: ─── 5. Check Node/npm for MCP ───
echo.
echo [5/7] Checking Node.js / npm (for MCP servers)...
where node >nul 2>&1
if errorlevel 1 (
    echo  WARNING: Node.js not found. MCP servers will be disabled.
    echo  Install from: https://nodejs.org/
) else (
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo  OK: Node %%v
    for /f "tokens=*" %%v in ('npm --version 2^>^&1') do echo  OK: npm %%v
)

:: ─── 6. Check Ollama ───
echo.
echo [6/7] Checking Ollama local models...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo  Ollama not running. Local models disabled.
    echo  Start with: ollama serve
) else (
    echo  OK: Ollama is running
    venv\Scripts\python.exe -c "import urllib.request, json; res=json.loads(urllib.request.urlopen('http://localhost:11434/api/tags').read()); print(' Models:', len(res.get('models',[])), 'available')"
)

:: ─── 7. Kill old server if running ───
echo.
echo [7/7] Checking for existing server on port 7860...
venv\Scripts\python.exe -c "import subprocess, os, re; out=subprocess.run('netstat -ano', capture_output=True, text=True, shell=True).stdout; pids=set(re.findall(r':7860\s+.*?\s+(\d+)', out)); [print(f' Stopping old server PID {p}...') or os.system(f'taskkill /PID {p} /F >nul 2>&1') for p in pids if p!='0']"

echo.
echo ============================================================
echo   Starting DevMind server on http://127.0.0.1:7860
echo   Press CTRL+C to stop
echo ============================================================
echo.

set DEVMIND_CWD=E:\coding-assistant
set DEVMIND_MODEL=gemini-2.5-flash

venv\Scripts\uvicorn.exe server:app --host 127.0.0.1 --port 7860 --reload --log-level info

echo.
echo Server stopped. Press any key to exit.
pause
