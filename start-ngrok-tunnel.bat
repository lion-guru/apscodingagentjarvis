@echo off
title ngrok Tunnel Starter
echo [%date% %time%] Starting ngrok tunnel for http://localhost:80...
echo [%date% %time%] Starting ngrok tunnel... >> "%USERPROFILE%\ngrok-tunnel.log"

REM Kill any existing ngrok processes
taskkill /f /im ngrok.exe 2>nul

REM Start ngrok tunnel immediately to localhost:80
start "ngrok-Tunnel" ngrok http 80 --log=stdout

echo.
echo ========================================================
echo   ngrok TUNNEL STARTED SUCCESSFULLY!
echo   Web Dashboard: http://localhost:4040
echo ========================================================
timeout /t 3 >nul
