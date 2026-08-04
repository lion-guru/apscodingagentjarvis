@echo off
REM DevMind Overnight Autonomous Coding Agent
REM Runs autonomous tasks when user is sleeping (1 AM - 6 AM)

echo ====================================
echo DevMind Overnight Agent Launcher
echo ====================================
echo Starting at: %date% %time%
echo.

REM Check if it's nighttime (1 AM - 6 AM)
for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "datetime=%%a"
set "hour=%datetime:~8,2%"
set /a hour=%hour%

echo Current hour: %hour%

if %hour% GEQ 1 if %hour% LSS 6 (
    echo [SUCCESS] Nighttime detected (1 AM - 6 AM)
    echo Starting autonomous task runner...
    echo.

    REM Activate virtual environment
    if exist venv\Scripts\activate.bat (
        call venv\Scripts\activate.bat
    ) else (
        echo [WARNING] Virtual environment not found, using system Python
    )

    REM Run autonomous task queue
    py task_queue_runner.py --cwd "c:\xampp\htdocs\apsdreamhome" --model gemini-2.0-flash

    echo.
    echo ====================================
    echo Overnight tasks completed at: %date% %time%
    echo ====================================
) else (
    echo [SKIP] Not nighttime (Current: %hour%)
    echo Agent only runs between 1 AM - 6 AM
    echo.
    echo To run manually, use: .\task_queue_runner.py
    echo To force run now, use: .\task_queue_runner.py --task "your task"
)

pause
