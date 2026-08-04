@echo off
title Agent Town - Live Dev Server
echo ========================================================
echo   AGENT TOWN DEV SERVER - INSTALLING AND STARTING
echo ========================================================
echo.

cd /d E:\coding-assistant\agent-town

echo [1/2] Installing pnpm and dependencies...
call npx pnpm@latest install

echo.
echo [2/2] Starting Agent Town Server...
call npx pnpm@latest dev

pause
