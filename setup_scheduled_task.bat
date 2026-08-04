@echo off
REM Setup Windows Scheduled Task for Overnight Autonomous Agent
REM This will run start_overnight_agent.bat every night at 1 AM

echo ====================================
echo DevMind Scheduled Task Setup
echo ====================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running with administrator privileges
) else (
    echo [ERROR] Please run this script as Administrator
    echo Right-click the file and select "Run as administrator"
    pause
    exit /b 1
)

REM Delete existing task if it exists
schtasks /delete /tn "DevMindOvernightAgent" /f >nul 2>&1

REM Create new scheduled task
schtasks /create /tn "DevMindOvernightAgent" /tr "E:\coding-assistant\start_overnight_agent.bat" /sc daily /st 01:00 /ru "SYSTEM" /f

if %errorLevel% == 0 (
    echo.
    echo [SUCCESS] Scheduled task created successfully!
    echo.
    echo Task Details:
    echo   Name: DevMindOvernightAgent
    echo   Trigger: Daily at 1:00 AM
    echo   Action: Run E:\coding-assistant\start_overnight_agent.bat
    echo   User: SYSTEM (runs even when logged out)
    echo.
    echo To manually trigger: schtasks /run /tn "DevMindOvernightAgent"
    echo To view schedule: schtasks /query /tn "DevMindOvernightAgent"
    echo To delete task: schtasks /delete /tn "DevMindOvernightAgent" /f
) else (
    echo.
    echo [ERROR] Failed to create scheduled task
    echo Please check the error message above
)

pause
