@echo off
title JARVIS Git Commit & Push
echo.
echo ============================================================
echo  JARVIS DevMind - Git Commit and Push
echo ============================================================
echo.

cd /d "e:\coding-assistant"

echo [1/3] Staging all changes...
git add -A
if errorlevel 1 (
    echo ERROR: git add failed!
    pause
    exit /b 1
)

echo.
echo [2/3] Changed files:
git status --short

echo.
echo [3/3] Committing...
git commit -m "fix: self_repair bug fix + improved .gitignore + deep scan cleanup

- Fixed critical syntax bug in self_repair_autofix.py (missing 'self' in scan_and_repair)
- Improved .gitignore: added scratch fix scripts, state/logs/artifacts dirs, generated output files
- Codebase deeply scanned: hybrid_query_engine, cost_tracker, jarvis_voice, plugins all verified
- setup_wizard.py and pyrightconfig.json reviewed and confirmed correct"

if errorlevel 1 (
    echo Nothing to commit or commit failed.
)

echo.
echo [4/4] Pushing to GitHub...
git push origin main
if errorlevel 1 (
    echo Push failed - check your credentials or network!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  SUCCESS! All changes committed and pushed to GitHub!
echo ============================================================
echo.
pause
