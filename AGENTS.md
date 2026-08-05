# DevMind AI Studio — Agent System Guide

## Overview
DevMind is a local-first AI coding assistant with a multi-agent architecture. It runs 100% locally via Ollama, with optional cloud model fallback.

## Architecture

### Core Agent Files
| File | Purpose |
|------|---------|
| `agent.py` | Main agent engine — tool registry, LLM chat, refactor tool (2350+ lines) |
| `agent_core.py` | Base classes: Agent, Task, ToolResult, Orchestrator |
| `agent_command_center.py` | Command hub for agent orchestration |
| `agent_specialists.py` | Specialist sub-agents (Planner, Coder, Reviewer, Healer) |
| `hermes_agent.py` | Hermes high-speed agent (reasoning + tool calling) |
| `hermes_acp_client.py` | Hermes ACP protocol client |

### AI/ML Engines
| File | Purpose |
|------|---------|
| `reasoning_engine.py` | Chain-of-thought reasoning |
| `moe_router.py` | Mixture-of-Experts task routing |
| `attention_engine.py` | Hybrid linear attention (KDA + Kimi Delta) |
| `multimodal_engine.py` | VLM/BigPixel/MIMO architecture |
| `rag_vector_engine.py` | RAG + BM25 code search |
| `search_engine.py` | Enhanced BM25 + semantic search |
| `hybrid_query_engine.py` | BM25 code query engine (real BM25 scoring) |
| `vector_db.py` | Embedding + vector DB (Gemini/Ollama) |
| `memory_engine.py` | Memory indexing with decay (real relevance scoring) |
| `trajectory_compressor.py` | Hermes-grade conversation compression (LLM-assisted, zero deps) |
| `stt_engine.py` | Faster-Whisper local speech-to-text (base model, CPU int8) |
| `tts_engine.py` | Edge-TTS (Microsoft, free) + pyttsx3 offline fallback |
| `ram_monitor.py` | RAM monitor with auto-swap to cloud model at 90% |
| `history_compressor.py` | Backward-compatible wrapper → trajectory_compressor |
| `context_manager.py` | RAG + context compression |

### Model Management
| File | Purpose |
|------|---------|
| `model_failover.py` | Model failover chain (real switching logic) |
| `model_performance_tracker.py` | Performance tracking per model |
| `model_usage_tracker.py` | Quota tracking + proactive switching |
| `free_model_discovery.py` | Auto-discover free AI models |
| `offline_llm.py` | Local Ollama accelerator (real Ollama integration) |
| `multi_brain_coordinator.py` | Multi-model coordination (real API calls) |
| `third_eye.py` | Multi-agent monitoring system (1389 lines) |

### IDE Features
| File | Purpose |
|------|---------|
| `ast_analyzer.py` | AST parsing for Python/JS/TS |
| `linter_engine.py` | Multi-linter (ruff/pylint/flake8) — fixed eval() → json.loads() |
| `diagnostics_panel.py` | Real-time diagnostics — fixed import |
| `completion_engine.py` | Tab completion + Supercomplete — fixed missing import |
| `inline_editor.py` | Inline diff editing |
| `project_explorer.py` | File tree + symbol browser |
| `breadcrumb_nav.py` | Path breadcrumbs |
| `terminal_manager.py` | Terminal session management — fixed wrapper args |
| `steering_engine.py` | Persistent coding rules |
| `spaces_manager.py` | Context bundles (Devin-style Spaces) |
| `ide_bridge.py` | Cursor/Windsurf/OpenCode config gen |
| `deploy_panel.py` | Docker/Cloud deploy config |
| `workspace_index.py` | AST symbols + import graph |

### Knowledge & Data
| File | Purpose |
|------|---------|
| `knowledge_items.py` | Knowledge item CRUD — fixed wrapper args |
| `session_manager.py` | Session persistence |
| `master_db.py` | SQLite database manager |
| `plugins.py` | Extension marketplace |
| `mcp_server.py` | MCP tool server management |

### Infrastructure
| File | Purpose |
|------|---------|
| `server.py` | FastAPI backend (3249+ lines, 225+ routes) |
| `main.py` | CLI REPL interface — fixed return→continue bug |
| `cost_tracker.py` | Token cost tracking |
| `overnight_worker.py` | Background task queue (real queue management) |
| `task_queue_runner.py` | Autonomous task executor (real LLM execution) |

### Orphan Files — ALL NOW WIRED AND FUNCTIONAL
| File | Endpoint(s) | Purpose |
|------|-------------|---------|
| `memory_engine.py` | `GET/POST /api/memory/*` | Smart memory with relevance scoring + decay |
| `model_failover.py` | `GET/POST /api/model/failover-*` | Auto model switching |
| `vector_db.py` | `POST /api/vector/*` | Vector embeddings + semantic search |
| `trajectory_compressor.py` | `POST /api/session/compress` | Hermes-grade compression (LLM-assisted) |
| `learning_engine.py` | `GET/POST /api/project/*` | Codebase style detection |
| `hybrid_query_engine.py` | `POST /api/code/*` | BM25 code search |
| `self_healing_workflow.py` | `GET/POST /api/self-healing/*` | Error recovery |
| `verification_system.py` | `GET/POST /api/verify/*` | Pre-completion verification |
| `multi_brain_coordinator.py` | `GET/POST /api/ai/multi-brain/*` | Multi-model planning |
| `web_learning_engine.py` | `GET/POST /api/learning/*` | Self-learning engine |
| `skill_synthesis.py` | `GET/POST /api/skills/*` | Auto skill generation |
| `offline_llm.py` | `GET/POST /api/offline/*` | Local Ollama fallback |
| `jarvis_autonomy.py` | `GET/POST /api/system/*` | PC resource monitor |
| `validate_mcp_config.py` | `GET /api/mcp/validate` | MCP config validator |
| `setup_wizard.py` | `GET/POST /api/setup/*` | API key diagnostics |
| `model_usage_tracker.py` | `GET /api/model/usage`, `/quota` | Quota prediction |
| `inter_ai_communicator.py` | `POST /api/ai/communicate` | AI-to-AI messaging |
| `devmind_mesh.py` | `GET/POST /api/mesh/*` | Multi-device sync |
| `devmind_eval.py` | `GET/POST /api/eval/*` | Model benchmarking |
| `jarvis_voice.py` | `GET/POST /api/voice/*` | Wake word listener |
| `rag_vector_engine.py` | `POST /api/rag/*` | RAG + code search |
| `task_queue_runner.py` | `GET/POST /api/tasks/*` | Autonomous tasks |
| `overnight_worker.py` | `GET/POST /api/worker/*` | Background tasks |
| `attention_engine.py` | `POST /api/attention/compress` | Token compression |

### Agent Town Integration (Pixel-Art Visual Interface)
| File | Purpose |
|------|---------|
| `agent_town_bridge.py` | Agent registry (12 agents), activity feed, smart task routing, WebSocket broadcast |
| `agent-town/lib/devmind-hub.tsx` | Unified React context: sessions, theme, voice, favorites, pins, search, import/delete, all persisted |
| `agent-town/lib/voice-engine.ts` | Web Speech API: TTS with 12 agent-specific voices (unique pitch/rate), STT for voice input |
| `agent-town/lib/useKeyboardShortcuts.ts` | Global keyboard shortcut system (6 shortcuts incl. command palette) |
| `agent-town/components/hud/DevMindHubPanel.tsx` | 7-tab unified panel with 60+ features, memo-wrapped, ARIA-labeled |
| `agent-town/components/hud/DevMindErrorBoundary.tsx` | Error boundary for crash protection |
| `agent-town/components/hud/GameHud.tsx` | Hub provider wrapper |
| `agent-town/app/api/devmind/*/route.ts` | API proxies (chat, agents, activity, performance, workspace, system, file) |
| `agent-town/server.ts` | WebSocket proxy: port 3000 → port 7860 + auggie-bridge |

#### Agent Town Endpoints (DevMind Server)
| Endpoint | Purpose |
|----------|---------|
| `GET /api/agent-town/agents` | List all 12 agents with status |
| `GET /api/agent-town/activity` | Recent activity feed (50 entries) |
| `POST /api/agent-town/chat` | Smart-routed chat (intent → best agent) |
| `WebSocket /ws/agent-town` | Real-time agent status + activity stream |
| `GET /api/model/performance` | Per-model success rate, avg response time |
| `GET /api/token-summary` | Token usage + cost summary |
| `GET /api/system/metrics` | CPU/RAM/Disk/GPU real-time metrics |

#### Smart Task Router (11 Intent Patterns → 11 Agents)
| Input Pattern | Agent |
|---------------|-------|
| review, audit | Reviewer |
| fix, bug, debug | Healer |
| plan, design | Planner |
| test, spec | Test Runner |
| deploy, docker | Deployer |
| search, find | Researcher |
| lint, format | Linter |
| memory, context | Memory |
| monitor, status, performance | Monitor |
| write, create, code | Coder |
| refactor, improve, restructure | Architect |

#### DevMindHubPanel Features (7 Tabs)
| Tab | Features |
|-----|----------|
| **Chat** | Session management (create/switch/delete/rename), session stats, chat search with highlighting, pinned messages panel, message pinning/copy/delete/expand, quick reply suggestions, export/import as .md |
| **Agents** | Workload balance bar, agent search + status filter chips (all/idle/running/failed), agent cards with favorite star + info button + quick task assignment |
| **Log** | Activity feed with filters (all/started/completed/failed/chat), CSV export |
| **Stats** | Performance dashboard with token usage + model quotas |
| **Health** | Agent health dashboard (success rate, task count, avg response time per agent) |
| **Files** | Workspace browser + file preview |
| **System** | CPU/RAM/GPU/disk metrics (auto-refreshing) |
| **Overlays** | Command palette (Ctrl+P), agent detail modal with task history, agent comparison view, onboarding tour, shortcuts help |
| **Header** | Model selector, theme toggle (dark/light/midnight), voice controls, keyboard shortcuts |
| **Performance** | React.memo on 6 sub-components, try-catch + mounted flag on all fetch effects, ARIA labels on interactive elements |

#### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| Ctrl+K | Focus chat input |
| Ctrl+Shift+A | Toggle agents tab |
| Ctrl+Shift+L | Toggle voice listen |
| Ctrl+M | Toggle voice mute |
| Ctrl+P | Open command palette |
| Ctrl+/ | Show shortcuts help |
| Escape | Close overlay/modal |

## How to Add a New Agent

1. Create a new file `my_agent.py`:
```python
from agent_core import Agent, Task, ToolResult

class MyAgent(Agent):
    def __init__(self):
        super().__init__(
            role="my_agent",
            model="qwen2.5-coder:7b",
            description="Does something useful"
        )

    async def execute(self, task: Task) -> ToolResult:
        # Your logic here
        return ToolResult(success=True, output="Done!")
```

2. Register in `agent_specialists.py`:
```python
def create_default_agents():
    agents = {
        # ... existing agents ...
        "my_agent": MyAgent(),
    }
    return agents
```

3. Add API endpoint in `server.py`:
```python
@app.post("/api/my-agent/run")
async def my_agent_run(request: Request):
    data = await request.json()
    from my_agent import MyAgent
    agent = MyAgent()
    result = await agent.execute(Task(description=data.get("task", "")))
    return {"status": "ok", "result": result.output}
```

## How to Add a New Tool to agent.py

1. Define the tool function in `create_tool_registry()`:
```python
def my_new_tool(param1: str, param2: int = 10) -> str:
    """Description of what this tool does."""
    # Tool logic
    return "result"
```

2. Register it:
```python
tools["my_new_tool"] = Tool(
    name="my_new_tool",
    description="Description for the LLM",
    function=my_new_tool,
    params_schema={"param1": "description", "param2": "description"}
)
```

## Environment Variables (.env)
```
OLLAMA_HOST=http://127.0.0.1:11434
DEFAULT_MODEL=qwen2.5-coder:7b
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
OPENROUTER_API_KEY=your_key
ZENMUX_API_KEY=your_key
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=
```

## Running the Server
```bash
# Start server
python server.py

# Or with batch file
START_SERVER.bat

# Access at http://localhost:7860
```

## API Endpoints Summary
- **230 HTTP routes** covering AI, IDE, system, knowledge, and infrastructure
- **2 WebSocket endpoints** for real-time streaming
- **64+ agent tools** in the tool registry
- **24 orphan modules** now wired and fully functional
- **ZenMux free chat** — unlimited free AI conversations via `/api/zenmux/chat`
- **STT/TTS** — `/api/stt/transcribe`, `/api/tts/synthesize`, `/api/tts/voices`
- **RAM Monitor** — `/api/ram/status`, `/api/ram/check` (auto-swap at 90%)

## Bug Fixes Applied
1. `jarvis_autonomy.py:44` — Fixed syntax error (double parenthesis)
2. `diagnostics_panel.py:20` — Fixed wrong import (DevMindLinter → LinterEngine)
3. `linter_engine.py:60,91` — Fixed eval() → json.loads() (security)
4. `completion_engine.py` — Added missing `import datetime`
5. `knowledge_items.py:92-99` — Fixed wrapper function argument mismatches
6. `terminal_manager.py:147` — Fixed wrapper passing extra arg
7. `main.py:314` — Fixed return→continue in /models handler
8. `server.py:862` — Removed hardcoded MySQL password, now uses env vars
9. `list_gemini_models.py:4` — Removed hardcoded API key, now uses env var
10. `setup_wizard.py:40` — Removed hardcoded MySQL credentials, now uses env vars

## Security Improvements
- All hardcoded credentials removed from source code
- MySQL connection now uses environment variables
- API keys loaded from .env file
- eval() replaced with json.loads() for JSON parsing
