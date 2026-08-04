# 👁️ THIRD EYE — Jarvis Multi-Agent Oversight System

## Overview

**Third Eye** is DevMind/Jarvis's autonomous oversight and intervention system. It acts as a "third eye" that watches over your entire development workflow — IDEs (OpenCode, Windsurf, Cursor, Trae), browsers, terminals, and any running application — and automatically keeps things running smoothly using only **free AI models**.

Think of it as Iron Man's Jarvis watching over Tony's work: it detects when something hangs, when tokens run out, when an API key fails, and **automatically fixes it** by switching models, restarting apps, or spawning sub-agents to carry on the task.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Free Model Discovery](#free-model-discovery)
3. [IDE / App Monitoring](#ide--app-monitoring)
4. [Auto-Recovery Engine](#auto-recovery-engine)
5. [Multi-Agent Spawning](#multi-agent-spawning)
6. [Usage](#usage)
7. [API Endpoints](#api-endpoints)
8. [Supported Free Models](#supported-free-models)
9. [Troubleshooting](#troubleshooting)

---

## Architecture

```
third_eye.py           # Main ThirdEyeSystem orchestrator
├── ModelManager       # Free model discovery, categorization, failover chain
│   ├── discover_all()  # Tests all providers → working_models.json
│   ├── health_check   # Continuous health monitoring
│   ├── select_model   # Picks best model for task type (coding/reasoning/speed)
│   └── failover_chain # Tested ordered list of models
├── AppMonitor         # Watches running IDEs/apps
│   ├── detect_running_ide()  # Which app is active?
│   ├── monitor_window_activity()
│   ├── detect_hang()  # Frozen UI / stuck tool calls
│   └── detect_token_exhaustion()  # Quota/rate-limit errors in logs
├── BrowserOperator    # Controls browser-based IDEs (OpenCode web, Windsurf, Cursor)
│   ├── detect_ide_in_browser()  # Which IDE is open in browser?
│   ├── read_ide_output()  # Read visible content from IDE
│   ├── detect_error_in_ide()  # Scan for errors/hangs in browser
│   ├── switch_ide_model()  # Switch model in browser IDE dropdown
│   └── click_retry_or_resubmit()  # Click retry/resume in browser
├── AutoRecoveryEngine # Fixes problems automatically
│   ├── diagnose_and_recover()
│   │   ├── quota_exhausted   → switch provider/model
│   │   ├── timeout/hang      → switch to faster model
│   │   ├── auth_failure      → fall back to local/uncached model
│   │   └── app_crash         → restart app
│   └── recover_from_hang()
└── MultiAgentOrchestrator  # Spawns sub-agents
    ├── spawn_agent(name, specialty)
    ├── assign_task(agent, task, context)
    └── parallel_execution(tasks)  # Run multiple agents concurrently
```

---

## Free Model Discovery

The system automatically discovers and tests **all** free AI model providers, categorizing them by speed and quality.

### Running Discovery

```bash
# Full discovery + test
python third_eye.py --test-models

# Or via the agent's tool
/agent.py → use tool: third_eye(action="discover")
```

### What Gets Tested

| Provider   | Env Var               | Models Tested               | Status  |
|------------|-----------------------|-----------------------------|---------|
| Google     | `GEMINI_API_KEY`      | 2.5-flash, 2.5-pro, 2.0-flash | ✅ 2.5-flash working (quota-free) |
| Groq       | `GROQ_API_KEY`        | Llama 3.3 70B, 3.1 8B       | ✅ Working (free) |
| OpenRouter | `OPENROUTER_API_KEY`  | Nemotron, Gemma, Llama free   | ❌ Key invalid (needs refresh) |
| HuggingFace| `HUGGING_FACE_API_KEY`| Qwen, Llama, Phi, Gemma       | ❌ DNS blocked |
| Local Ollama| (no key needed)      | All pulled models           | ✅ Working (local) |

### Currently Working Models (tested 2026-08-01)

| Model                     | Provider | Latency  | Notes                          |
|---------------------------|----------|----------|--------------------------------|
| `gemini-2.5-flash`        | Google   | 7.61s    | Best quality, 500 req/day free |
| `llama-3.1-8b-instant`    | Groq     | 0.75s    | Fastest, good coding           |
| `llama-3.3-70b-versatile` | Groq     | 0.77s    | High quality                   |
| `moondream:latest`        | Ollama   | 2.75s    | Local, vision-capable          |
| `gemma3:1b`               | Ollama   | 9.56s    | Local, lightweight             |
| `qwen2.5-coder:1.5b`      | Ollama   | 9.64s    | Local, coding-focused          |
| `llama3.2:1b`             | Ollama   | 9.96s    | Local, tiny                    |
| `qwen2.5:3b-instruct`     | Ollama   | 12.62s   | Local, multilingual            |
| `stable-code:latest`      | Ollama   | 13.16s   | Local, coding-focused          |
| `llama3.2:3b`             | Ollama   | 14.55s   | Local, balanced                |

**Current Failover Chain**: `gemini-2.5-flash → llama-3.1-8b-instant → moondream:latest`

### Results Storage

Discovery results are saved to `working_models.json`, which the agent loads on startup. Each model entry includes:
- `model` — the model identifier
- `provider` — which service (groq/google/openrouter/huggingface/ollama)
- `latency_s` — measured response time
- `categories` — what kind of tasks it excels at
- `free_tier` — always `true`

### Auto-Re-discovery

If `working_models.json` is stale (>24h), the system re-runs discovery automatically on next startup. You can also force a refresh:
```bash
python third_eye.py --test-models
```

---

## IDE / App Monitoring

### What It Watches

- **IDEs**: OpenCode, Windsurf, Cursor, Trae, VS Code
- **Browsers**: Chrome, Edge, Firefox
- **Terminals**: PowerShell, CMD, Terminal, Python
- **Any app**: If the process is running, Third Eye can watch it

### Detection Capabilities

| Scenario                | Detection Method              | Threshold            |
|-------------------------|-------------------------------|----------------------|
| IDE hang / freeze       | Process alive but idle        | >30s idle            |
| Token exhaustion        | Log scanning                  | Rate limit patterns  |
| API key failure         | Error in tool output          | "invalid key"/"401"  |
| Quota exceeded          | API error response            | "quota"/"429"        |
| Context overflow        | Error response                | "context length"     |
| App crash               | Process disappeared           | Sudden exit           |
| Stuck tool call         | No activity + long duration   | >300s on one task    |

### Usage

```bash
# Watch specific processes
python third_eye.py --watch opencode.py windsurf.exe code.exe

# Watch all known IDEs
python third_eye.py
```

---

## Auto-Recovery Engine

When a problem is detected, the recovery engine **automatically fixes it** without user intervention.

### Recovery Decisions

| Error Type           | Action Taken                                           |
|----------------------|--------------------------------------------------------|
| Quota exhausted (429)| Switch to next model in failover chain (different provider) |
| Timeout / hang       | Switch to a faster (lower-latency) model                |
| Auth failure         | Fall back to local Ollama model                         |
| API key error        | Rotate to model from different provider                |
| App crash            | Attempt to restart the application                      |
| Context overflow     | Switch to model with larger context window              |

### Example Recovery Flow

1. User runs a coding task in OpenCode
2. OpenCode uses `meta-llama/llama-3.2-1b-instruct:free` (OpenRouter)
3. API returns 429 (rate limit exceeded)
4. Third Eye detects the error → classifies as `quota_exhausted`
5. Recovery engine switches to `llama-3.3-70b-versatile` (Groq — different provider)
6. Task resumes automatically with the new model

### Manual Recovery

```python
# Via the agent tool
third_eye(action="recover", query="Quota exceeded for model X", context="coding task")
```

---

## Multi-Agent Spawning

Third Eye can spawn **sub-agents** to handle tasks autonomously — whether you're in an IDE, terminal, browser, or any app. Each sub-agent:
- Picks the best free model for its task
- Operates independently (no blocking your main workflow)
- Can be spawned with a custom specialty

### Spawn an Agent

```python
# Via CLI
python third_eye.py
→ spawn_agent "Fix PHP syntax errors in index.php"

# Via agent tool
third_eye(action="spawn_agent", query="Write unit tests for auth", context="Laravel project")

# Via API
POST /api/third-eye/spawn
{"task": "Audit SQL queries for injection", "context": "backend"}
```

### Parallel Execution

```python
# Run 3 agents in parallel
third_eye(action="spawn_agent", query="task1 | task2 | task3", context="parallel")
```

### Agent Specialties (auto-detected by task)

| Task Keywords             | Best Category   | Example Models                        |
|---------------------------|-----------------|---------------------------------------|
| code, bug, function, fix  | coding          | Groq Llama 3.3 70B, Ollama qwen2.5    |
| reason, analyze, plan     | reasoning       | Groq Llama 3.3, Ollama stable-code    |
| fast, quick, simple       | speed           | Groq Llama 3.1 8B, Ollama gemma3:1b   |
| explain, write, email     | general         | Any free model                        |
| local, offline            | local           | Any Ollama model                      |

---

## Browser IDE Operator

The `BrowserOperator` lets Third Eye **see and interact** with browser-based IDEs (OpenCode web, Windsurf, Cursor, Trae). Like Copilot — it can read the IDE output, detect errors, and fix them.

### What It Does

| Action               | Description                                              |
|----------------------|----------------------------------------------------------|
| `detect_ide_in_browser` | Detect which IDE is open in the browser tab            |
| `read_ide_output`    | Read visible text from the IDE (chat output, terminal)   |
| `detect_error_in_ide`| Scan browser output for errors (rate limits, hangs, etc.)|
| `switch_ide_model`   | Switch the model dropdown inside the browser IDE         |
| `click_retry_or_resubmit` | Click "Retry" / re-submit button to resume work       |

### Example: Auto-Recover a Browser IDE Error

```
1. You're working in OpenCode web (browser)
2. OpenCode hangs — "thinking..." for 30+ seconds
3. Third Eye detects the hang via BrowserOperator
4. Switches model in the browser dropdown to a faster free model
5. Clicks "Retry" to resume the task
6. Task continues with the new model
```

### Usage

```bash
# Requires: pip install selenium + Chrome with --remote-debugging-port=9222
python third_eye.py  # monitoring thread auto-checks browser
```

Via the agent tool:
```
third_eye(action="browser", query="detect")      # which IDE is in browser?
third_eye(action="browser", query="read")        # read IDE output
third_eye(action="browser", query="check_error") # scan + auto-recover
```

Via API:
```
GET /api/third-eye/browser?action=detect
GET /api/third-eye/browser?action=read
GET /api/third-eye/browser?action=check_error
```

---

## Usage

### 1. Start the system (daemon mode — full monitoring)

```bash
python third_eye.py --daemon --watch opencode.py windsurf.exe
```

### 2. Interactive mode (CLI with commands)

```bash
python third_eye.py
```
Available commands:
- `models` — List all working free models
- `status` — Full system status
- `spawn <name> <task>` — Spawn a sub-agent
- `discover` — Re-run model discovery
- `dashboard` — Quick health dashboard
- `exit` — Stop

### 3. One-shot operations

```bash
python third_eye.py --test-models    # Just test all models
python third_eye.py --status         # Show current status
python third_eye.py --models         # List models
```

### 4. Via the agent (inside agentic mode)

```
# Discover working free models
third_eye(action="discover")

# Pick the best free model for a coding task
third_eye(action="best", query="Write a React component with hooks")

# Spawn a sub-agent to do a task (like Copilot in any IDE)
third_eye(action="spawn_agent", query="Fix all PHP syntax errors in the controllers")

# Auto-recover from model errors
third_eye(action="recover", query="429 rate limit exceeded for model X")

# Control browser-based IDEs
third_eye(action="browser", query="check_error")  # scan + auto-recover browser IDE
third_eye(action="browser", query="detect")       # which IDE is in browser?
```

### 5. Via API (web UI integration)

```
GET  /api/third-eye/status       # System status & working models
POST /api/third-eye/discover     # Re-run discovery
GET  /api/third-eye/best/{task}  # Best model for a task type
```

---

## API Endpoints (Server)

| Method | Endpoint                   | Description                            |
|--------|----------------------------|----------------------------------------|
| GET    | `/api/models`              | All models (including Third Eye found) |
| GET    | `/api/third-eye/status`    | Working models + failover chain        |
| POST   | `/api/third-eye/discover`  | Run fresh model discovery              |
| GET    | `/api/third-eye/best/{t}`  | Best free model for a task type        |

---

## Supported Free Models (as of last discovery)

The system dynamically discovers models. Current known working free models:

| Provider | Model                        | Speed (tested) | Best For          |
|----------|------------------------------|----------------|-------------------|
| Groq     | `llama-3.3-70b-versatile`    | ~1.0s          | Coding/quality    |
| Groq     | `llama-3.1-8b-instant`       | ~0.7s          | Speed/general     |
| Ollama   | `llama3.2:3b`                | ~5-17s         | Local general     |
| Ollama   | `qwen2.5-coder:1.5b`         | ~12s           | Local coding      |
| Ollama   | `gemma3:1b`                  | ~11s           | Local speed       |

### Models NOT working (with reason)

| Provider | Model                        | Problem                                  |
|----------|------------------------------|------------------------------------------|
| Google   | All Gemini models            | API key leaked / quota exhausted         |
| OpenRouter| All `:free` models           | API key not recognized / rate limits     |
| HuggingFace | All models               | Network/DNS blocked                      |
| Ollama   | `qwen2.5-coder:7b`            | Too slow (times out at 30s)              |

> **Tip**: If you have a fresh Gemini API key, re-run discovery: `python third_eye.py --test-models`. Models that pass will be added to the failover chain automatically.

---

## How It Works End-to-End

```
1. ┌─────────────────────────────────────────────┐
  │ Start JARVIS (agent.py / server.py)         │
  │ → Loads third_eye.py → ModelManager         │
  │ → Loads working_models.json (9 models)      │
  │ → Builds failover chain                     │
  └────────────────────────┬────────────────────┘
                           │
2. ┌────────────────────────▼────────────────────┐
  │ User submits task in OpenCode IDE           │
  │ → Agent picks best model for task type      │
  │ → Sends to Groq llama-3.3-70b (0.97s)       │
  └────────────────────────┬────────────────────┘
                           │
3. ┌────────────────────────▼────────────────────┐
  │ Model returns "429 rate limit exceeded"     │
  │ → Third Eye AutoRecoveryEngine kicks in     │
  │ → Diagnoses: quota_exhausted                │
  └────────────────────────┬────────────────────┘
                           │
4. ┌────────────────────────▼────────────────────┐
  │ Recovery: switches to llama-3.1-8b (Groq)   │
  │ (different model, same provider, fast)      │
  └────────────────────────┬────────────────────┘
                           │
5. ┌────────────────────────▼────────────────────┐
  │ Task completes successfully                 │
  │ → Health score updated in ModelManager      │
  │ → Continuous monitoring continues...        │
  └─────────────────────────────────────────────┘
```

---

## Troubleshooting

### "All models in failover chain failed"

1. Run `python third_eye.py --test-models` to re-discover working models
2. Check your API keys in `.env`:
   ```bash
   GEMINI_API_KEY=    # Google (if quota available)
   GROQ_API_KEY=      # Groq (fastest free tier)
   OPENROUTER_API_KEY=# OpenRouter (if key works)
   ```
3. Local Ollama should always be a fallback: start `ollama serve`

### OpenRouter models return "User not found"

Your `OPENROUTER_API_KEY` may be invalid or from a different provider. Either:
- Generate a new key at https://openrouter.ai
- Or rely on Groq + local Ollama (both work reliably)

### Gemini API key "leaked"

Google auto-revoke keys that appear in public repos. Generate a new key at https://aistudio.google.com.

### "Ollama not running"

```bash
# Install Ollama: https://ollama.com
ollama serve
ollama pull llama3.2:3b  # or qwen2.5-coder:1.5b
```

---

## Quick Start

```bash
# 1. Discover working models
python third_eye.py --test-models

# 2. Start the agent (uses discovered models automatically)
python main.py --model "llama-3.3-70b-versatile"

# 3. Or start the web server with Third Eye monitoring
python server.py
# Then open http://localhost:7860

# 4. Use the third_eye tool in any agent session:
#    third_eye(action="discover")
#    third_eye(action="best", query="write a Python web scraper")
#    third_eye(action="spawn_agent", query="Fix all syntax errors in the PHP controllers")
```

---

**Inspired by:** Iron Man's Jarvis ("third eye" monitoring), Claude Code's observability layer, pguilp25/jarvis multi-agent coordination, and OpenCode's autonomous agent design.
