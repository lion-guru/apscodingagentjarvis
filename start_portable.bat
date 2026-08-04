@echo off
title DevMind Portable AI Suite — Complete Launcher
echo ========================================================
echo   DEVMIND PORTABLE AI SUITE - STARTING ALL SERVICES
echo ========================================================
echo.

set PORTABLE_DIR=%~dp0
cd /d "%PORTABLE_DIR%"

:: Determine Portable Python Executable
if exist "%PORTABLE_DIR%python-embedded\python.exe" (
    set PY_EXE="%PORTABLE_DIR%python-embedded\python.exe"
    echo [SYSTEM] Using Portable Embedded Python: %PY_EXE%
) else if exist "%PORTABLE_DIR%venv\Scripts\python.exe" (
    set PY_EXE="%PORTABLE_DIR%venv\Scripts\python.exe"
    echo [SYSTEM] Using Portable Venv Python: %PY_EXE%
) else (
    set PY_EXE=python
    echo [SYSTEM] Using System Python
)

:: Determine Portable Node Executable
if exist "%PORTABLE_DIR%bin\node.exe" (
    set NODE_EXE="%PORTABLE_DIR%bin\node.exe"
    echo [SYSTEM] Using Portable Standalone Node: %NODE_EXE%
) else (
    set NODE_EXE=node
)

:: 1. Launch DevMind Agent Town Pixel Workspace (Port 3000)
echo.
echo [1/3] Launching DevMind Agent Town Pixel Workspace (http://localhost:3000)...
if exist "%PORTABLE_DIR%agent-town" (
    start "DevMind-AgentTown" /min cmd /c "cd /d "%PORTABLE_DIR%agent-town" && npx pnpm@latest dev"
) else if exist "%PORTABLE_DIR%agent-town-dist" (
    start "DevMind-AgentTown" /min cmd /c "cd /d "%PORTABLE_DIR%agent-town-dist" && %NODE_EXE% server.js"
)

:: 2. Launch DevMind AI IDE Backend Server (Port 7860)
echo.
echo [2/3] Launching DevMind AI IDE Server (http://localhost:7860)...
start "DevMind-Server" /min cmd /c "cd /d "%PORTABLE_DIR%" && %PY_EXE% server.py"

:: 3. Launch "DEV" Background Wake Word Listener
echo.
echo [3/3] Launching "DEV" Background Wake Word Listener...
start "DEV-WakeWord" /min cmd /c "cd /d "%PORTABLE_DIR%" && %PY_EXE% dev_wake_word_bg.py"

echo.
echo ========================================================
echo   ALL DEVMIND PORTABLE SERVICES STARTED SUCCESSFULLY!
echo   DevMind IDE:   http://localhost:7860
echo   Agent Town:    http://localhost:3000
echo   Wake Word:     Listening for "DEV" / "Hey Dev"
echo ========================================================
timeout /t 5 >nul
