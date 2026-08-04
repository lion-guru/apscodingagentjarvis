@echo off
echo ========================================================
echo DevMind AI Agent System — APSDreamHome Connection
echo Target Workspace: c:\xampp\htdocs\apsdreamhome
echo ========================================================

set DEVMIND_CWD=c:\xampp\htdocs\apsdreamhome

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python.
    pause
    exit /b 1
)

:: Activate virtual environment if available
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Model Selection
python choose_model.py
if errorlevel 1 (
    echo Model selection cancelled or failed.
    pause
    exit /b 1
)

if exist "_selected_model.tmp" (
    set /p selected_model=<_selected_model.tmp
    del _selected_model.tmp >nul 2>&1
) else (
    set selected_model=gemini-2.0-flash
)

set DEVMIND_MODEL=%selected_model%
echo.
echo Active Model: %selected_model%
echo Target Path:  %DEVMIND_CWD%
echo.
echo ========================================================
echo Choose Mode to Activate DevMind:
echo [1] Launch DevMind 3-Panel Web UI (Monaco + Git + Chat)
echo [2] Launch Autonomous Task Queue Runner (Sleep Mode)
echo [3] Launch Terminal CLI Mode
echo ========================================================
set /p mode="Enter choice [1, 2, or 3, default 1]: "

if "%mode%"=="2" (
    echo Starting Autonomous Task Queue Runner...
    python task_queue_runner.py --cwd %DEVMIND_CWD% --model %selected_model%
) else if "%mode%"=="3" (
    echo Starting Terminal CLI Mode...
    python main.py --model %selected_model% %*
) else (
    echo Starting DevMind Web UI on http://localhost:7860...
    echo Open http://localhost:7860 in your browser.
    python server.py
)
