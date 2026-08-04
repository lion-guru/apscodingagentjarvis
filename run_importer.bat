@echo off
title Importing and Deep Unpacking All DevMind Resources
echo ========================================================
echo   DEEPLY EXTRACTING DEVMIND RUNTIMES, PROMPTS AND ASSETS
echo ========================================================
echo.

cd /d E:\coding-assistant

echo [1/4] Importing portable runtimes (Python, Node, FFmpeg, Chromium, Skills, Plugins)...
python import_all_devmind_resources.py

echo.
echo [2/4] Deep extracting app container (Prompts, System Instructions, Assets)...
python extract_devmind_assets_deep.py

echo.
echo [3/4] Running Forensic Scan for API Keys, Cloud Endpoints and Configs...
python deep_scan_devmind.py
python save_keys_to_db.py

echo.
echo [4/4] Organizing DevMind files into clean directory structure...
python organize_devmind_structure.py
python rebrand_and_cleanup_stonic.py

echo.
echo ========================================================
echo   DEVMIND DEEP EXTRACTION AND DB SAVING COMPLETE!
echo ========================================================
timeout /t 3 >nul
