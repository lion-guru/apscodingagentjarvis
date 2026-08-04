# DevMind / Jarvis Setup Guide

Run the DevMind AI coding agent locally on Windows. Includes OmniRoute gateway (290+ providers, 90+ free tiers) and OpenCode Zen (7 free models).

## Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Python | 3.14+ | Main server + agent |
| Node.js | 24+ | OmniRoute gateway |
| npm | 11+ | Install OmniRoute |
| PowerShell | 5.1+ | All commands run in PowerShell |
| Ollama | latest | Local models (optional but recommended) |
| Git | latest | Clone repo |

## 1. Clone the repo

```powershell
git clone <repo-url> E:\coding-assistant
cd E:\coding-assistant
```

## 2. Python environment

```powershell
# Create venv
python -m venv venv

# Activate
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## 3. OmniRoute gateway (local AI router)

OmniRoute provides one endpoint (`localhost:20128/v1`) that auto-routes across 290+ providers with 90+ free tiers.

```powershell
# Install globally on D: drive (avoids filling C:)
npm install -g omniroute --prefix D:\npm-global

# Add to PATH (one-time)
$env:Path += ";D:\npm-global"
[Environment]::SetEnvironmentVariable("Path", $env:Path, "User")

# Start OmniRoute (runs on localhost:20128)
omniroute
```

OmniRoute auto-starts with keyless free providers (OpenCode Free, Felo). No API keys needed for the free tier.

## 4. Environment variables

Copy `.env.example` to `.env` and fill in your API keys:

```powershell
copy .env.example .env
```

Edit `.env` with your keys:

```
# Required
GEMINI_API_KEY=your-gemini-key
OPENCODE_API_KEY=your-opencode-zen-key

# Optional (for more models)
GROQ_API_KEY=your-groq-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
OPENROUTER_API_KEY=sk-or-v1-...   # format must be sk-or-v1-*
```

### Key formats
- Gemini: `AIza...` (starts with `AQ.` or `AIza`)
- OpenCode Zen: `sk-6KPQ...` (OpenCode platform key)
- Groq: `gsk_...`
- OpenRouter: `sk-or-v1-...` (NOT `sk-...`)
- OpenAI: `sk-proj-...` or `sk-...`

## 5. Start the server

```powershell
# Activate venv first
.\venv\Scripts\Activate.ps1

# Start DevMind server (auto-reloads on code changes)
E:\coding-assistant\venv\Scripts\uvicorn.exe server:app --host 127.0.0.1 --port 7860 --reload
```

The server starts hidden. Verify it's running:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:7860/api/agent/system_status" -TimeoutSec 5
```

Expected output: `workspace`, `project_type`, `keys_loaded`, `mcp_servers_count`.

## 6. Verify everything works

### Check OmniRoute
```powershell
curl http://localhost:20128/v1/models
```
Should return a list of 100+ models.

### Check Zen models
```powershell
curl http://localhost:20128/v1/models  # OmniRoute already includes Zen
```

### Run a quick WS test
Connect to `ws://127.0.0.1:7860/ws/chat/test` and send:
```json
{"type": "chat", "content": "Create a file named hello.txt with content 'IT WORKS'.", "model": "auto/cheap", "agentic_mode": true}
```
The agent should create `hello.txt` in the workspace and report DONE.

## 7. Model failover chain

The agent automatically rotates through models when one is rate-limited or exhausted:

1. **Gemini** (free, 500/day) — primary
2. **Groq** (free, 14400/day) — fallback
3. **OpenCode Zen** (7 free models, 500/day each) — omniroute pool
4. **OmniRoute** (290+ providers, auto-fallback) — universal gateway
5. **Ollama** (local, unlimited) — last resort

The failover chain is configurable in `~/.devmind/model_config.json`.

## 8. Troubleshooting

| Problem | Fix |
|---------|-----|
| `EADDRINUSE: 20128` | OmniRoute already running. Kill it: `Stop-Process -Name node -Force` then restart |
| `401 Missing Authentication` | OpenRouter key format wrong — must be `sk-or-v1-*`, not `sk-*` |
| `401 OPENCODE_API_KEY` | Key format invalid for OpenRouter — OpenCode Zen keys are `sk-6KPQ...` |
| `ModuleNotFoundError` | Activate venv: `.\venv\Scripts\Activate.ps1` |
| `npm ENOSPC` | Disk full. Free space on C: or install OmniRoute to D: with `--prefix D:\npm-global` |
| `getaddrinfo failed` | Network/DNS issue for remote MCP servers (github-cloud, etc.). Local MCP works fine |
| Server not picking up code changes | Restart uvicorn or wait for `--reload` (checks file timestamps) |

## 9. Project structure

```
E:\coding-assistant\
├── server.py              # FastAPI + WebSocket server
├── agent.py               # Core agent logic, dispatch, failover
├── model_usage_tracker.py # Quota tracking, proactive switching
├── workspace_index.py     # Cached project index for system prompt
├── third_eye.py           # Model discovery, working_models.json
├── main.py                # Tool extraction, utility functions
├── .env                   # API keys (gitignored)
├── .env.example           # Template for .env
├── requirements.txt       # Python dependencies
├── model_config.json      # Manual failover chain config
├── skills/                # Agent skills (code-review, security-audit, etc.)
└── venv/                  # Python virtual environment
```

## 10. Useful commands

```powershell
# Check system status
curl http://127.0.0.1:7860/api/agent/system_status

# Check model quotas
curl http://127.0.0.1:7860/api/model-quotas

# Update model config
curl -X POST http://127.0.0.1:7860/api/model-config -Body '{"failover_chain":["auto/cheap","gemini-2.5-flash"]}' -ContentType "application/json"

# Test OmniRoute directly
curl http://localhost:20128/v1/chat/completions -Body '{"model":"auto/cheap","messages":[{"role":"user","content":"Hello"}]}' -ContentType "application/json"

# Test Zen directly
curl https://opencode.ai/zen/v1/chat/completions -Body '{"model":"big-pickle","messages":[{"role":"user","content":"Hello"}]}' -Header "Authorization: Bearer <OPENCODE_API_KEY>" -ContentType "application/json"
```
