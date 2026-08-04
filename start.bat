@echo off
echo DevMind - Local AI Coding Assistant
echo =====================================

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python from https://python.org
    pause
    exit /b 1
)

:: Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate.bat

:: Install requirements
echo Installing dependencies...
pip install -q -r requirements.txt

:: Check Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Ollama not found!
    echo Download from: https://ollama.com/download/windows
    echo After installing, run: ollama pull qwen2.5-coder:7b
    echo.
    pause
    exit /b 1
)

:: Model Selection — Dynamic (lists ALL installed Ollama models + Gemini)
echo.
python choose_model.py
if errorlevel 1 (
    echo ERROR: Model selection failed.
    pause
    exit /b 1
)

:: Read selected model from temp file
set /p selected_model=<_selected_model.tmp
del _selected_model.tmp >nul 2>&1

echo.
echo Using model: %selected_model%

:: Start DevMind
echo.
echo =====================================
echo Choose Interface Mode:
echo [1] CLI Mode (Terminal Chat)
echo [2] Web UI Mode (Browser Interface)
echo =====================================
set /p mode="Enter choice [1 or 2, default 2]: "

if "%mode%"=="1" (
    echo Starting CLI Mode with model %selected_model%...
    python main.py --model %selected_model% %*
) else (
    echo Starting Web UI on http://localhost:7860 with model %selected_model%...
    echo Open your browser: http://localhost:7860
    set DEVMIND_MODEL=%selected_model%
    python server.py
)


