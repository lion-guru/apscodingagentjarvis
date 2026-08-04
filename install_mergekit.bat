@echo off
echo ==================================================
echo 🧠 DevMind: Installing Mergekit in Stable Environment
echo ==================================================
echo.

echo [Step 1] Creating Python 3.12 Virtual Environment...
py -3.12 -m venv .venv_merge
if errorlevel 1 (
    echo.
    echo [Warning] Python 3.12 launcher not found. Trying Python 3.11...
    py -3.11 -m venv .venv_merge
)
if errorlevel 1 (
    echo.
    echo [Warning] Trying default python environment...
    python -m venv .venv_merge
)

echo.
echo [Step 2] Activating Virtual Environment...
call .venv_merge\Scripts\activate

echo.
echo [Step 3] Upgrading pip & installing Mergekit...
python -m pip install --upgrade pip
python -m pip install mergekit

echo.
echo ==================================================
echo ✅ Mergekit Setup Completed Successfully!
echo ==================================================
echo.
echo To merge models later, always activate this environment by running:
echo   call .venv_merge\Scripts\activate
echo.
pause
