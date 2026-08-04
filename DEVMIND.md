# 🤖 DevMind & Jarvis AI Coding Assistant — Project Rules

Welcome to DevMind! This repository powers the **Jarvis local AI coding assistant**.

---

## 📐 Architecture Conventions & Rules

1. **Python Environment**:
   - Always run Python scripts inside `venv\Scripts\python.exe` or `venv/bin/python`.
   - Keep requirements in `requirements.txt`.

2. **Web Assistant Server**:
   - Backend: FastAPI + WebSockets (`server.py`).
   - Server runs on `http://127.0.0.1:7860`.
   - UI: 3-panel Monaco Editor Web Workspace (`web/index.html`).

3. **Tool Calling & Safety Rules**:
   - Always verify code execution results.
   - Do NOT delete critical files without user approval.
   - Use fuzzy matching in `apply_edit` for resilient file modifications.

4. **Multi-Agent & Model Failover**:
   - Primary Free Cloud Model: `gemini-2.5-flash` / `llama-3.3-70b-versatile`.
   - Primary Local Model: `llama3.2:3b` / `qwen2.5-coder:7b`.
   - Sub-Agents: Use `spawn_agent`, `send_message`, `task_stop` for complex background tasks.
