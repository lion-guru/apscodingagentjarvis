# DevMind AI Studio — AI-Powered Coding IDE

DevMind AI Studio is a local-first AI coding assistant with a multi-agent architecture. It runs 100% locally via Ollama, with optional cloud model fallback (Gemini, Groq, OpenRouter, ZenMux).

---

## Architecture

### Core Modules
| File | Purpose |
|------|---------|
| `server.py` | FastAPI backend (3150+ lines, 97+ HTTP routes, 2 WebSocket endpoints) |
| `agent.py` | Agent engine (5234+ lines, 64+ tools, LLM chat, refactor tool) |
| `main.py` | CLI REPL interface |
| `agent_core.py` | Base classes: Agent, Task, ToolResult, Orchestrator |
| `agent_specialists.py` | Specialist sub-agents (Planner, Coder, Reviewer, Healer) |
| `agent_command_center.py` | Command hub for agent orchestration |

### Modular Routes (`app/routes/`)
| File | Prefix | Endpoints |
|------|--------|-----------|
| `ai.py` | `/api` | models, health, third-eye, moe, vlm, mimo, reasoning, hermes |
| `ide.py` | `/api` | ide, lint, complete, diagnostics, terminal, explorer, editor, steering, spaces, bridge, deploy |
| `system.py` | `/api` | memory, model/failover, model/usage, vector, session/compress, system/metrics, mesh, offline, attention |
| `knowledge.py` | `/api` | project/style, code/search, self-healing, verify, multi-brain, learning, skills, eval, voice, zenmux, rag, tasks, worker, mcp/validate, setup, knowledge, cost |

### AI/ML Engines
| File | Purpose |
|------|---------|
| `reasoning_engine.py` | Chain-of-thought reasoning |
| `moe_router.py` | Mixture-of-Experts task routing |
| `attention_engine.py` | Hybrid linear attention (KDA + Kimi Delta) |
| `multimodal_engine.py` | VLM/BigPixel/MIMO architecture |
| `rag_vector_engine.py` | RAG + BM25 code search |
| `search_engine.py` | Enhanced BM25 + semantic search |
| `hybrid_query_engine.py` | BM25 code query engine |
| `vector_db.py` | Embedding + vector DB (Gemini/Ollama) |
| `memory_engine.py` | Memory indexing with decay |
| `trajectory_compressor.py` | Hermes-grade conversation compression (LLM-assisted, zero deps) |
| `context_manager.py` | RAG + context compression |

### Model Management
| File | Purpose |
|------|---------|
| `model_failover.py` | Model failover chain (Gemini → Groq → OpenRouter → ZenMux → Ollama) |
| `model_usage_tracker.py` | Quota tracking + proactive switching |
| `free_model_discovery.py` | Auto-discover free AI models |
| `offline_llm.py` | Local Ollama accelerator |
| `multi_brain_coordinator.py` | Multi-model coordination |
| `third_eye.py` | Multi-agent monitoring system (1389 lines) |

### IDE Features
| File | Purpose |
|------|---------|
| `ast_analyzer.py` | AST parsing for Python/JS/TS |
| `linter_engine.py` | Multi-linter (ruff/pylint/flake8) |
| `diagnostics_panel.py` | Real-time diagnostics |
| `completion_engine.py` | Tab completion + Supercomplete |
| `inline_editor.py` | Inline diff editing |
| `project_explorer.py` | File tree + symbol browser |
| `terminal_manager.py` | Terminal session management |
| `steering_engine.py` | Persistent coding rules |
| `spaces_manager.py` | Context bundles (Devin-style Spaces) |
| `ide_bridge.py` | Cursor/Windsurf/OpenCode config gen |
| `deploy_panel.py` | Docker/Cloud deploy config |
| `workspace_index.py` | AST symbols + import graph |

### Knowledge & Data
| File | Purpose |
|------|---------|
| `knowledge_items.py` | Knowledge item CRUD |
| `session_manager.py` | Session persistence |
| `master_db.py` | SQLite database manager |
| `plugins.py` | Extension marketplace |
| `mcp_server.py` | MCP tool server management |

### Infrastructure
| File | Purpose |
|------|---------|
| `cost_tracker.py` | Token cost tracking |
| `overnight_worker.py` | Background task queue |
| `task_queue_runner.py` | Autonomous task executor |
| `self_healing_workflow.py` | Error recovery |
| `verification_system.py` | Pre-completion verification |
| `inter_ai_communicator.py` | AI-to-AI messaging |
| `devmind_mesh.py` | Multi-device sync |
| `devmind_eval.py` | Model benchmarking |
| `jarvis_voice.py` | Wake word listener |
| `jarvis_autonomy.py` | PC resource monitor |
| `validate_mcp_config.py` | MCP config validator |
| `setup_wizard.py` | API key diagnostics |
| `skill_synthesis.py` | Auto skill generation |
| `web_learning_engine.py` | Self-learning engine |

---

## Running

```bash
# Start server (http://localhost:7860)
python server.py

# Or with batch file
START_SERVER.bat

# Run tests
python -m pytest tests/ -v
```

## Environment Variables (`.env`)
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

## Test Results
- **28/28** unit tests passing (orphan modules)
- **24/24** integration tests passing (API endpoints)
- **0** critical bugs remaining

## Security Fixes Applied
1. `eval()` → `json.loads()` in `linter_engine.py` (security)
2. Hardcoded MySQL password → `os.getenv()` in `server.py`
3. Hardcoded API keys → env vars in `list_gemini_models.py`, `setup_wizard.py`
4. All credentials now loaded from `.env` file

## API Endpoints Summary
- **230 HTTP routes** covering AI, IDE, system, knowledge, and infrastructure
- **2 WebSocket endpoints** for real-time streaming
- **64+ agent tools** in the tool registry
- **24 orphan modules** now wired and fully functional
- **STT/TTS** — `/api/stt/transcribe`, `/api/tts/synthesize`, `/api/tts/voices`
- **RAM Monitor** — `/api/ram/status`, `/api/ram/check` (auto-swap at 90%)
