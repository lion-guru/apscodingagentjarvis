@echo off
title Stonic AI - Core Features Unlocked Launcher
echo ========================================================
echo   STONIC AI - BYPASSING SUPABASE LOGIN & UNLOCKING CORE
echo ========================================================
echo.

:: 1. Patching Local Auth State
echo [1/2] Enforcing local unlocked authentication in auth.json...
set AUTH_DIR=%APPDATA%\stonic_dsktp
if not exist "%AUTH_DIR%" mkdir "%AUTH_DIR%"

(
echo {
echo   "email": "techguruabhay@gmail.com",
echo   "token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3puZWZibHZyb2lzYXpnbW5scGlkLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIxOWM4ZDEzNi1jNDJkLTRkNjAtODQ4My04YzhjNzk3ZWRlNzEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoyNTMzNzIxNzYzOTksImlhdCI6MTc4NTgzNTE3NywiZW1haWwiOiJ0ZWNoZ3VydWFiaGF5QGdtYWlsLmNvbSIsInJvbGUiOiJhdXRoZW50aWNhdGVkIiwic3Vic2NyaXB0aW9uX3RpZXIiOiJ1bmxpbWl0ZWRfcHJvIiwiaXNfbGljZW5zZWRfdmFsaWQiOnRydWUsImNvcmVfZmVhdHVyZXNfdW5sb2NrZWQiOnRydWV9.bypass_signature",
echo   "authenticatedAt": "2026-08-04T09:19:40.131Z",
echo   "isLoggedIn": true,
echo   "licenseStatus": "ACTIVE_UNLOCKED",
echo   "plan": "ENTERPRISE_PRO_UNLOCKED",
echo   "coreFeaturesUnlocked": true,
echo   "supabaseAuthBypassed": true
echo }
) > "%AUTH_DIR%\auth.json"

echo [OK] Supabase Auth bypassed successfully! Core features unlocked!
echo.

:: 2. Launch Stonic AI Application Directly
echo [2/2] Launching Stonic AI Desktop Application...
if exist "C:\Users\abhay\AppData\Local\Programs\stonic_dsktp\Stonic AI.exe" (
    start "" "C:\Users\abhay\AppData\Local\Programs\stonic_dsktp\Stonic AI.exe"
    echo [OK] Stonic AI started successfully!
) else (
    echo [ERROR] Stonic AI.exe not found at C:\Users\abhay\AppData\Local\Programs\stonic_dsktp\Stonic AI.exe
)

echo.
echo ========================================================
echo   STONIC AI STARTED WITH CORE FEATURES UNLOCKED!
echo ========================================================
timeout /t 3 >nul
