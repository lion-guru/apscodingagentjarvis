# DevMind AI Studio - Architecture & Wiring Plan

## Vision: What This Project Is

DevMind is an **AI-Powered IDE** with these core capabilities:
1. **Multi-Provider LLM Chat** - Chat with AI models (Gemini, Groq, OpenRouter, Ollama, Claude, OpenAI)
2. **Agentic Tool System** - AI can read/write/edit files, run commands, search code
3. **IDE Features** - File explorer, inline editor, completions, diagnostics, terminal
4. **Memory & Learning** - Remembers past conversations, learns coding style
5. **Multi-Brain Planning** - Multiple AI models collaborate on complex tasks
6. **Self-Healing** - Auto-recovers from errors
7. **Vector Search** - Semantic code search with embeddings
8. **Verification** - Check syntax/tests before completing tasks
9. **Skill Synthesis** - Auto-generate new capabilities
10. **Offline Fallback** - Works with local Ollama when cloud is down

---

## Current Problems

1. **server.py is 3,249 lines** - everything in one file
2. **33 orphan files** not connected to the server
3. **Duplicate modules** doing similar things
4. **No proper error handling** - all endpoints return HTTP 200
5. **No authentication** on sensitive endpoints
6. **Hardcoded values** everywhere

---

## Proposed Architecture

### Directory Structure

```
E:\coding-assistant\
├── server.py                    # MAIN ENTRY - FastAPI app + uvicorn
├── app/
│   ├── __init__.py
│   ├── config.py                # Settings, env loading, constants
│   ├── auth.py                  # Authentication middleware
│   ├── errors.py                # Error handling, HTTP exceptions
│   │
│   ├── routes/                  # API Routes (grouped by feature)
│   │   ├── __init__.py
│   │   ├── chat.py              # /api/chat, /ws/{session_id}
│   │   ├── files.py             # /api/files/*, /api/file/*
│   │   ├── git.py               # /api/git/*, /api/github/*
│   │   ├── terminal.py          # /api/terminal/*
│   │   ├── agents.py            # /api/agents/*, /api/agent/*
│   │   ├── models.py            # /api/models, /api/model-config, /api/model-quotas
│   │   ├── third_eye.py         # /api/third-eye/*
│   │   ├── ide.py               # /api/ide/*, /api/ide-bridge/*
│   │   ├── memory.py            # /api/memory/* (NEW - wire memory_engine)
│   │   ├── search.py            # /api/search/*, /api/code/* (NEW - wire hybrid_query_engine)
│   │   ├── vector.py            # /api/vector/* (NEW - wire vector_db)
│   │   ├── verify.py            # /api/verify/* (NEW - wire verification_system)
│   │   ├── healing.py           # /api/self-healing/* (NEW - wire self_healing_workflow)
│   │   ├── multi_brain.py       # /api/ai/multi-brain/* (NEW - wire multi_brain_coordinator)
│   │   ├── skills.py            # /api/skills/* (NEW - wire skill_synthesis)
│   │   ├── learning.py          # /api/learning/* (NEW - wire web_learning_engine + learning_engine)
│   │   ├── offline.py           # /api/offline/* (NEW - wire offline_llm)
│   │   ├── mcp.py               # /api/mcp/* (NEW - wire validate_mcp_config)
│   │   ├── setup.py             # /api/setup/* (NEW - wire setup_wizard)
│   │   ├── system.py            # /api/system/* (wire jarvis_autonomy)
│   │   ├── knowledge.py         # /api/knowledge/*
│   │   ├── sessions.py          # /api/session/*
│   │   ├── context.py           # /api/context/*
│   │   ├── spaces.py            # /api/spaces/*
│   │   ├── diagnostics.py       # /api/diagnostics/*
│   │   ├── steering.py          # /api/steering/*
│   │   ├── deploy.py            # /api/deploy/*
│   │   ├── extensions.py        # /api/extensions/*
│   │   ├── mesh.py              # /api/mesh/*
│   │   ├── voice.py             # /api/voice/*
│   │   ├── eval.py              # /api/eval/*
│   │   ├── rag.py               # /api/rag/*
│   │   ├── overnight.py         # /api/overnight/*
│   │   ├── artifacts.py         # /api/artifacts/*
│   │   ├── hermes.py            # /api/hermes/*
│   │   ├── moe.py               # /api/moe/*
│   │   ├── streams.py           # /api/streams/*
│   │   └── reasoning.py         # /api/reasoning/*
│   │
│   ├── services/                # Business Logic (reusable)
│   │   ├── __init__.py
│   │   ├── memory_service.py    # Wraps memory_engine.py
│   │   ├── failover_service.py  # Wraps model_failover.py
│   │   ├── vector_service.py    # Wraps vector_db.py
│   │   ├── search_service.py    # Wraps hybrid_query_engine.py + search_engine.py
│   │   ├── verify_service.py    # Wraps verification_system.py
│   │   ├── healing_service.py   # Wraps self_healing_workflow.py
│   │   ├── brain_service.py     # Wraps multi_brain_coordinator.py
│   │   ├── skill_service.py     # Wraps skill_synthesis.py
│   │   ├── learning_service.py  # Wraps learning_engine.py + web_learning_engine.py
│   │   ├── offline_service.py   # Wraps offline_llm.py
│   │   ├── style_service.py     # Wraps learning_engine.py (style detection)
│   │   └── compress_service.py  # Wraps history_compressor.py
│   │
│   └── core/                    # Shared utilities
│       ├── __init__.py
│       ├── database.py          # Wraps master_db.py
│       ├── models.py            # Pydantic models for requests/responses
│       └── security.py          # Path validation, input sanitization
│
├── agent.py                     # EXISTING - Agent tool system (keep as-is for now)
├── main.py                      # EXISTING - CLI interface
│
├── # --- EXISTING MODULES (keep in root, imported by app/services/) ---
├── memory_engine.py             # Smart memory with relevance scoring
├── model_failover.py            # Auto model switching on quota limits
├── vector_db.py                 # Vector embeddings + semantic search
├── history_compressor.py        # Conversation history compression
├── learning_engine.py           # Codebase style learning
├── hybrid_query_engine.py       # BM25 code search
├── self_healing_workflow.py     # Error recovery
├── verification_system.py       # Pre-completion verification
├── multi_brain_coordinator.py   # Multi-model planning
├── skill_synthesis.py           # Auto skill generation
├── web_learning_engine.py       # Self-learning engine
├── offline_llm.py               # Local Ollama fallback
├── jarvis_autonomy.py           # PC resource monitor
├── validate_mcp_config.py       # MCP config validator
├── setup_wizard.py              # API key diagnostics
├── choose_model.py              # CLI model selector (keep standalone)
│
├── # --- EXISTING MODULES (already wired, keep as-is) ---
├── ast_analyzer.py
├── linter_engine.py
├── terminal_manager.py
├── knowledge_items.py
├── session_manager.py
├── agent_command_center.py
├── project_explorer.py
├── inline_editor.py
├── completion_engine.py
├── context_manager.py
├── spaces_manager.py
├── diagnostics_panel.py
├── steering_engine.py
├── ide_bridge.py
├── deploy_panel.py
├── search_engine.py
├── workspace_index.py
├── mcp_server.py
├── breadcrumb_nav.py
├── agent_core.py
├── agent_specialists.py
├── attention_engine.py
├── stream_manager.py
├── hermes_agent.py
├── moe_router.py
├── multimodal_engine.py
├── reasoning_engine.py
├── hermes_acp_client.py
├── cost_tracker.py
├── master_db.py
├── model_usage_tracker.py
├── free_model_discovery.py
├── third_eye.py
├── devmind_mesh.py
├── jarvis_voice.py
├── devmind_eval.py
├── plugins.py
├── overnight_worker.py
├── inter_ai_communicator.py
├── rag_vector_engine.py
├── self_repair_autofix.py
├── task_queue_runner.py
│
├── # --- TO DELETE ---
├── fix_*.py                     # 26 one-off patch scripts
├── check_*.py                   # 8 diagnostic scripts
├── test_*.py                    # Move to tests/ directory
├── find_append.py
├── compile_check.py
├── list_gemini_models.py        # Has hardcoded API key
├── save_keys_to_db.py           # Has hardcoded API keys
├── extract_keys.py
├── deep_scan_devmind.py
├── run_openrouter_diagnosis.py
├── run_real_task_test.py
├── scratch_git_commit.py
├── clean_index_exact.py
├── import_all_devmind_resources.py
├── organize_devmind_structure.py
├── rebrand_and_cleanup_stonic.py
├── copy_devmind_assets.py
├── copy_hermes_plugins.py
├── copy_hermes_skills.py
├── copy_videos.py
├── rewrite_method.py
├── trim_file.py
├── trim_direct.py
├── verify_myaiagent_key.py
├── inspect_asar.py
├── extract_devmind_assets_deep.py
├── query_mysql.py
│
├── web/                         # Frontend (keep as-is)
├── skills/                      # Skill templates (keep as-is)
├── plugins/                     # Hermes plugins (keep as-is)
├── hermes-runtime/              # Hermes agent (keep as-is)
├── agent-town/                  # Agent Town (keep as-is)
├── bin/                         # Binaries (keep as-is)
└── .env                         # API keys (keep as-is)
```

---

## Wiring Map: Orphan Files → Endpoints

### Tier 1: Critical Infrastructure

| File | What It Does | New Endpoint | Integration Point |
|------|-------------|--------------|-------------------|
| `memory_engine.py` | Smart memory with relevance scoring + decay | `GET /api/memory/search?query=X` | Agent system prompt: inject relevant memories |
| | | `POST /api/memory/add` | After tool execution: store learnings |
| `model_failover.py` | Auto-switch models on quota limits | `GET /api/model/failover-status` | WebSocket handler: wrap LLM calls |
| | | `POST /api/model/reset-failures` | |
| `vector_db.py` | Vector embeddings + semantic search | `POST /api/vector/index` | Replace/augment RAG endpoint |
| | | `POST /api/vector/search` | Agent tool: semantic code search |
| `history_compressor.py` | Compress long conversations | `POST /api/session/compress` | WebSocket: auto-compress when token limit hit |

### Tier 2: High-Value Features

| File | What It Does | New Endpoint | Integration Point |
|------|-------------|--------------|-------------------|
| `learning_engine.py` | Detect project coding style | `GET /api/project/style-guide` | Agent system prompt: inject style conventions |
| | | `POST /api/project/learn-rule` | After file save: learn user patterns |
| `hybrid_query_engine.py` | BM25 code search | `POST /api/code/search` | Frontend code search, agent tool |
| | | `POST /api/code/index` | |
| `self_healing_workflow.py` | Error recovery | `GET /api/self-healing/report` | WebSocket: on tool failure, suggest healing |
| | | `POST /api/self-healing/attempt` | |
| `verification_system.py` | Check syntax/tests | `POST /api/verify/syntax` | Before file save: verify changes |
| | | `POST /api/verify/checkpoint` | |
| | | `POST /api/verify/restore` | |
| `multi_brain_coordinator.py` | Multi-model planning | `POST /api/ai/multi-brain/coordinate` | When user asks "plan this" |
| | | `GET /api/ai/multi-brain/status` | |
| `web_learning_engine.py` | Self-learning | `GET /api/learning/knowledge-base` | Show accumulated knowledge |
| | | `POST /api/learning/research` | |

### Tier 3: Supporting Features

| File | What It Does | New Endpoint | Integration Point |
|------|-------------|--------------|-------------------|
| `skill_synthesis.py` | Auto-generate skills | `GET /api/skills/active` | Skill management UI |
| | | `POST /api/skills/synthesize` | |
| `offline_llm.py` | Local Ollama fallback | `GET /api/offline/status` | Failover chain: last resort |
| | | `POST /api/offline/generate` | |
| `jarvis_autonomy.py` | PC resource monitor | `POST /api/system/ensure-services` | Auto-launch Ollama |
| | | (fix bugs first) | After file save: learn patterns |
| `validate_mcp_config.py` | MCP config validator | `GET /api/mcp/validate` | MCP status dashboard |
| `setup_wizard.py` | API key diagnostics | `POST /api/setup/run-diagnostics` | Setup wizard UI |

### Tier 4: Standalone (No Wiring Needed)

| File | Purpose | Action |
|------|---------|--------|
| `choose_model.py` | CLI model selector | Keep as standalone CLI tool |
| `gui_launcher.py` | Tkinter desktop GUI | Keep as standalone app |
| `setup_dependencies.py` | One-time setup | Keep as standalone script |
| `refine_model.py` | Training pipeline | Keep as standalone |
| `distill_dataset.py` | Training pipeline | Keep as standalone |
| `train_autopilot.py` | Training pipeline | Keep as standalone |

---

## Bug Fixes Required

### 1. jarvis_autonomy.py:44 - Syntax Error
```python
# WRONG:
def ensure_services_running((self) -> dict:
# CORRECT:
def ensure_services_running(self) -> dict:
```

### 2. jarvis_autonomy.py:66 - Wrong Import
```python
# WRONG:
from master_db import master_db
master_db.add_memory(...)
# CORRECT:
from master_db import add_master_memory
add_master_memory(...)
```

### 3. web_learning_engine.py:50 - Wrong Import
```python
# WRONG:
from master_db import master_db
master_db.add_memory(...)
# CORRECT:
from master_db import add_master_memory
add_master_memory(...)
```

### 4. vector_db.py:232 - Missing Import
```python
# MISSING: import re at top of file
# Add: import re (already exists at line 257, move to top)
```

### 5. server.py:862 - Hardcoded Password
```python
# WRONG:
passwords = ["apsdreamhome", ""]
# CORRECT:
password = os.getenv("MYSQL_PASSWORD", "")
```

---

## Implementation Order

### Phase 1: Bug Fixes (30 minutes)
1. Fix jarvis_autonomy.py syntax error
2. Fix jarvis_autonomy.py wrong import
3. Fix web_learning_engine.py wrong import
4. Fix vector_db.py missing import
5. Fix server.py hardcoded password
6. Remove --reload from START_SERVER.bat (DONE)

### Phase 2: Create App Structure (1 hour)
1. Create `app/` directory
2. Create `app/config.py` with settings
3. Create `app/errors.py` with error handling
4. Create `app/models.py` with Pydantic models
5. Create `app/services/` with service wrappers
6. Create `app/routes/` with route modules

### Phase 3: Wire Tier 1 Files (2 hours)
1. Wire memory_engine.py → /api/memory/*
2. Wire model_failover.py → /api/model/failover-status
3. Wire vector_db.py → /api/vector/*
4. Wire history_compressor.py → /api/session/compress

### Phase 4: Wire Tier 2 Files (2 hours)
1. Wire learning_engine.py → /api/project/style-guide
2. Wire hybrid_query_engine.py → /api/code/search
3. Wire self_healing_workflow.py → /api/self-healing/*
4. Wire verification_system.py → /api/verify/*
5. Wire multi_brain_coordinator.py → /api/ai/multi-brain/*
6. Wire web_learning_engine.py → /api/learning/*

### Phase 5: Wire Tier 3 Files (1 hour)
1. Wire skill_synthesis.py → /api/skills/*
2. Wire offline_llm.py → /api/offline/*
3. Wire jarvis_autonomy.py → /api/system/*
4. Wire validate_mcp_config.py → /api/mcp/validate
5. Wire setup_wizard.py → /api/setup/run-diagnostics

### Phase 6: Cleanup (30 minutes)
1. Delete all fix_*.py scripts (26 files)
2. Delete all check_*.py scripts (8 files)
3. Delete dead utility scripts
4. Move test scripts to tests/

---

## How Each Orphan File Connects

### memory_engine.py
```
User types message
  → WebSocket handler calls memory_engine.get_memory_context(user_prompt)
  → Returns relevant past memories as text
  → Injected into agent system prompt
  → Agent has better context from past conversations
```

### model_failover.py
```
LLM call fails (quota/rate limit)
  → handle_model_error(model_name, error)
  → Marks model as failed
  → Returns next available model
  → WebSocket handler retries with new model
```

### vector_db.py
```
User searches code semantically
  → POST /api/vector/search {query: "how does auth work"}
  → vector_db.query_database(cwd, query)
  → Returns top 5 code chunks with similarity scores
  → Frontend shows relevant code snippets
```

### history_compressor.py
```
Conversation gets too long (>8000 tokens)
  → compress_conversation_history(messages)
  → Protects system prompt + first user turn + last 4 turns
  → Summarizes middle tool execution turns
  → Returns compressed history that fits in context window
```

### learning_engine.py
```
Agent starts coding session
  → learning_engine.generate_style_prompt_extension(cwd)
  → Scans project for PHP framework, JS module system, indentation
  → Returns text block: "Use tabs, Laravel, ES6 modules..."
  → Injected into agent system prompt
  → Agent writes code matching project conventions
```

### hybrid_query_engine.py
```
User searches for code
  → POST /api/code/search {query: "database connection"}
  → query_engine.search(query)
  → BM25 scoring ranks files by relevance
  → Returns top 10 files with scores
```

### self_healing_workflow.py
```
Tool execution fails
  → attempt_heal(task, error, context)
  → Classifies error (syntax/permission/timeout/network)
  → Records failure pattern
  → Returns healing strategy + actions
  → Agent can retry with healing guidance
```

### verification_system.py
```
Agent wants to complete a task
  → verify_changes(file_path, project_path)
  → Creates checkpoint (backup)
  → Verifies syntax (Python/JS/TS/PHP)
  → Runs tests if available
  → Returns pass/fail + checkpoint ID
  → If fails, can restore from checkpoint
```

### multi_brain_coordinator.py
```
User asks "plan this complex task"
  → POST /api/ai/multi-brain/coordinate
  → Phase 1: Gemini + GPT-4o-mini plan independently
  → Phase 2: Claude critiques both plans
  → Phase 3: Gemini merges best elements
  → Returns merged plan with reasoning
```

### web_learning_engine.py
```
Agent completes research task
  → learning_engine.research_and_upgrade(topic)
  → Records new capability in knowledge base
  → Persists to Master DB memory
  → System learns from each session
```

### skill_synthesis.py
```
User needs a new capability
  → POST /api/skills/synthesize {task: "compress images"}
  → Generates Python skill file
  → Auto-tests the skill
  → Records in synthesis history
  → Skill available for future use
```

### offline_llm.py
```
All cloud models fail
  → offline_accelerator.check_availability()
  → Checks if Ollama is running
  → Lists available local models
  → Falls back to local generation
  → System never goes fully offline
```

### jarvis_autonomy.py
```
Server starts
  → autonomy_engine.ensure_services_running()
  → Checks if Ollama is running, launches if not
  → Checks if OpenCode IDE is running
  → Reports system metrics (CPU/RAM/disk)
```

### validate_mcp_config.py
```
MCP system check
  → GET /api/mcp/validate
  → Reads .devmind/mcp_config.json
  → Validates structure
  → Categorizes servers (local/cloud/disabled)
  → Returns validation report
```

### setup_wizard.py
```
First-time setup
  → POST /api/setup/run-diagnostics
  → Tests Gemini, OpenRouter, Groq API keys
  → Checks Ollama availability
  → Seeds keys from MySQL if available
  → Returns diagnostic report
```

---

## Testing Plan

After each phase:
1. `python -m py_compile server.py` - syntax check
2. `python -c "from server import app"` - import check
3. Start server and test endpoints
4. Test WebSocket connection
5. Verify all new endpoints respond correctly
