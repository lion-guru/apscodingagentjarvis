@echo off
title Agent Town Source Code Setup
echo ========================================================
echo   CLONING AND SETTING UP AGENT-TOWN SOURCE CODE FROM GITHUB
echo ========================================================
echo.

set TARGET_DIR=E:\coding-assistant\agent-town

if not exist "%TARGET_DIR%" (
    echo [1/3] Cloning repository from https://github.com/geezerrrr/agent-town.git...
    git clone https://github.com/geezerrrr/agent-town.git "%TARGET_DIR%"
) else (
    echo [1/3] Repository already exists at %TARGET_DIR%. Updating...
    cd /d "%TARGET_DIR%"
    git pull
)

cd /d "%TARGET_DIR%"

echo.
echo [2/3] Installing dependencies using npm...
call npm install

echo.
echo ========================================================
echo   SETUP COMPLETE! STARTING DEV SERVER (http://localhost:3000)
echo ========================================================
call npm run dev

pause
