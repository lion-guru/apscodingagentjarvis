@echo off
taskkill /F /IM ollama.exe 2>nul
timeout /t 2 /nobreak >nul
set OLLAMA_NUM_THREADS=2
set OLLAMA_CONTEXT_LENGTH=2048
start "" ollama serve