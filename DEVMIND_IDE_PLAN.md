# DevMind IDE - Comprehensive Implementation Plan (v2)

## Research Date: August 4, 2026

## Vision
Build a professional, web-based AI coding IDE (like Trae, Windsurf/Devin, OpenCode) in Python with a FastAPI backend and browser-based GUI. Optimized for 12GB RAM PCs. One-click install. Local models first. Works solo, offline-capable.

---

## Key Research Findings

### 1. Web-Based GUI vs Electron vs Tauri

| Aspect | Web Browser | Electron | Tauri |
|--------|------------|----------|-------|
| Bundle Size | 0 (already in browser) | 85-250 MB | 3-15 MB |
| RAM Usage | Minimal (browser tab) | 300-500 MB | 42-172 MB |
| Startup Time | Instant | 1-3 sec | 0.4-0.5 sec |
| Cross-platform | Any browser | Win/Mac/Linux | Win/Mac/Linux |
| Native APIs | Limited | Full (Node.js) | Full (Rust) |
| Offline capability | Limited | Full | Full |
| Install complexity | None (URL) | Installer needed | Installer needed |
| Security | Sandboxed | Chromium sandbox | OS WebView |
| Best for | DevMind's use case | Heavy desktop apps | Lightweight desktop apps |

**Decision: Web-based GUI (browser)** — No install needed, zero RAM overhead, works on any PC with a browser. For users who want a desktop app, provide a Tauri wrapper as an optional download. Tauri is 96% smaller and 3.7x faster than Electron.

### 2. Monaco Editor vs CodeMirror 6 vs Ace

| Feature | Monaco | CodeMirror 6 | Ace |
|---------|--------|-------------|-----|
| Bundle Size | ~5 MB | ~50-200 KB | ~1 MB |
| IntelliSense | Full LSP | Plugin-based | Basic |
| Language Support | 60+ built-in | Modular packages | 110+ modes |
| Autocomplete | Built-in, intelligent | Plugin-based | Basic |
| Multi-cursor | Yes | Yes | Yes |
| Theme support | Yes | Yes | Yes |
| Mobile support | Limited | Excellent | Good |
| SSR-safe | No (needs dynamic import) | Yes | Yes |
| Used by | VS Code, GitHub, StackBlitz | Replit, Firefox DevTools | Cloud9, many tools |
| Extensibility | VS Code extensions model | Modular extensions | Plugin system |

**Decision: CodeMirror 6** — For DevMind's web-based GUI, CodeMirror 6 is the right choice. It's modular (load only what you need), lightweight (~50-200KB vs Monaco's ~5MB), excellent for custom editor integrations, and used by Replit and Firefox DevTools. Monaco is better for full VS Code parity but too heavy for a web-based IDE targeting 12GB RAM PCs.

### 3. What Makes Trae/Windsurf/Devin GUI Look Good

**Trae's Design Principles:**
- SOLO mode: simplified, focused, immersive interface
- Browser preview with device switching (mobile/desktop)
- Element selection: click any visual element to edit it directly
- Text-to-image API integration for dynamic visuals
- Rounded cards with real gaps, pill-style panel tabs, 40px tab bar
- Clean, minimal interface with AI at the center

**Windsurf/Devin Design Principles:**
- Agent Command Center: Kanban-style dashboard for all agent sessions
- Spaces: context bundles for organizing agent sessions, PRs, files
- Cascade flow awareness: real-time tracking of edits, terminal, clipboard
- Devin cloud agents: plan locally, execute in cloud
- SWE-1.6 model: zero quota cost, 950 tok/s
- Persistent Memories: session memory across days
- Codemaps: AI-annotated visual code structure
- Bidirectional terminal: closed-loop code → test → deploy

**Key GUI Principles for DevMind:**
1. Activity bar (left): Explorer, Search, Git, Chat, Terminal, Settings
2. Side bar: file tree, symbols, search results
3. Editor area: tabs, breadcrumbs, line numbers, minimap
4. Chat panel: streaming responses, code blocks, tool results
5. Terminal panel: persistent sessions, command history
6. Status bar: model name, token usage, cwd, file info
7. Agent Command Center: Kanban view for all agent sessions
8. Spaces: context bundles for organizing work
9. Diff preview with accept/decline before applying
10. Rounded cards, pill-style tabs, smooth animations

### 4. Antigravity's RAG/Context Technology

Antigravity (Google's agent-first IDE) uses a **system-level memory** approach that goes beyond traditional RAG:

**Three Pillars:**
1. **Knowledge Items (KIs)** — Persistent, distilled knowledge from past conversations. Stored in `~/.devmind/knowledge/` with metadata.json and artifacts. Automatically loaded at session start.
2. **Skills (SKILL.md files)** — Reusable instruction sets for specific capabilities. Like custom agents with tools, skills, and logic.
3. **Artifacts** — Structured Markdown documents that make agent work transparent:
   - `task.md` — checklist tracking progress
   - `implementation_plan.md` — architecture plan before coding
   - `walkthrough.md` — step-by-step execution log
   - `screenshots/` — visual proof of work

**How It Works:**
- The model's native context window stays finite (e.g., 1M tokens for Gemini 3 Pro)
- The system's memory can be effectively unbounded through external stores
- At each step, the system retrieves the right pieces of memory and routes them into the model's context
- This is "operational infinite context" — not a bigger native window, but better recall

**Key Innovation: RAG + Context Windows Working Together**
- RAG retrieves the freshest and most relevant information
- Large context windows give the model room to reason across it
- Context compression (hierarchical summarization) when approaching limits
- The "infinite context" is really a hybrid of RAG + large context + memory management

**For DevMind:** Implement KIs, Skills, and Artifacts as the context management system. Use BM25 + vector hybrid search for RAG. Add context compression for long conversations.

### 5. Local Model Preference for Solo Developers

**Why Solo Developers Prefer Local Models:**
- Privacy: code never leaves the machine
- Cost: $0/month after hardware
- No rate limits: always available
- No API key management: simpler setup
- Offline capability: works without internet

**Recommended Local Models for 12GB RAM PC:**
| Model | Size | VRAM Needed | Quality |
|-------|------|-------------|---------|
| gemma3:1b | 1B params | ~2GB | Good for completions |
| llama3.2:1b | 1B params | ~2GB | Good for chat |
| qwen2.5-coder:1.5b | 1.5B params | ~3GB | Good for code gen |
| deepseek-coder-v2-lite | 16B params | ~10GB | Excellent (if GPU available) |
| qwen2.5-coder:7b | 7B params | ~8GB | Excellent (if GPU available) |

**DevMind Default Strategy:**
- Default to local Ollama models (free, private, no API keys)
- Fallback to free cloud models (Zen, OmniRoute) when local models are insufficient
- Paid models as last resort (OpenRouter, Groq)

### 6. Best Practices for PC-Installed IDE Software

**One-Click Installer Requirements:**
1. Auto-detect OS (Windows/Mac/Linux)
2. Install Ollama if not present
3. Pull default models (gemma3:1b, llama3.2:1b, qwen2.5-coder:1.5b)
4. Install Python dependencies
5. Create desktop shortcut
6. Configure DevMind to start on boot (optional)
7. First-run wizard: select models, set API keys, configure workspace
8. Auto-configure all AI tiers (Gemini, Groq, Zen, OmniRoute)

**For Windows (our primary target):**
- Use PowerShell installer script
- Portable installation (no admin rights needed)
- `$PSScriptRoot` for all paths (portable)
- Create `.devmind` directory in user's home
- Desktop shortcut with proper icon

---

## Architecture (Updated)

```
┌─────────────────────────────────────────────────────────┐
│              Web Browser (Primary GUI)                    │
│  CodeMirror 6 Editor | File Explorer | Chat | Terminal │
│  Activity Bar | Agent Command Center | Spaces | RAG   │
│  Breadcrumbs | Status Bar | Settings | Knowledge Items│
└──────────────────────┬──────────────────────────────────┘
                        │ WebSocket + REST
┌──────────────────────▼──────────────────────────────────┐
│              FastAPI Backend (server.py)                  │
│  Agent Engine | Tool Registry | MCP | RAG | Linter    │
│  AST Analyzer | Linter Engine | Terminal Manager     │
│  Inline Editor | IDE Bridge | Diagnostics Panel      │
│  Knowledge Items | Skills | Artifacts | Context Mgmt │
└──────────────────────┬──────────────────────────────────┘
                        │
┌──────────────────────▼──────────────────────────────────┐
│              AI Model Layer                              │
│  Local: Ollama (gemma3:1b, llama3.2:1b, qwen2.5-coder)│
│  Free Cloud: OpenCode Zen | OmniRoute                  │
│  Paid Fallback: OpenRouter | Groq | Gemini             │
└─────────────────────────────────────────────────────────┘

Optional: Tauri Desktop Wrapper (for users who want a native app)
┌─────────────────────────────────────────────────────────┐
│              Tauri Desktop App                          │
│  WebView2 (Windows) / WKWebView (Mac) / WebKitGTK    │
│  Rust Backend | System Tray | Auto-Start | Desktop    │
└─────────────────────────────────────────────────────────┘
```

---

## Feature Priority Matrix (Updated)

### P0 — Must Have (Core IDE)
| # | Feature | Inspired By | Implementation |
|---|---------|-------------|----------------|
| 1 | Web-based GUI with CodeMirror 6 | All web IDEs | `web/index.html` + CodeMirror 6 |
| 2 | IDE-style layout (activity bar, side bar, editor, chat, terminal) | Trae, Windsurf, VS Code | `web/index.html` redesign |
| 3 | File explorer with type icons | Trae, Windsurf | `project_explorer.py` |
| 4 | Chat with codebase context (RAG) | All IDEs | Enhanced `rag_vector_engine.py` |
| 5 | Terminal integration with persistent sessions | Windsurf (Cascade) | `terminal_manager.py` |
| 6 | Inline editing (select → describe → edit) | Windsurf, Cursor | `inline_editor.py` + agent.py |
| 7 | Multi-file editing with diff preview | Cursor (Composer) | Agent.py multi-file edit |
| 8 | Accept/decline diffs before applying | Cursor, Windsurf | Web UI diff view |
| 9 | MCP support for external tools | Windsurf, OpenCode, Cursor | `mcp_server.py` |
| 10 | Git integration (commit, diff, branch, PR) | All IDEs | agent.py git tools |
| 11 | Local model support (Ollama) | Antigravity, all local-first IDEs | Ollama integration |
| 12 | Free model-first strategy | Trae (free), OpenCode (BYOK) | Zen + OmniRoute + Ollama |

### P1 — Should Have (Professional Features)
| # | Feature | Inspired By | Implementation |
|---|---------|-------------|----------------|
| 13 | Agent Command Center (Kanban view) | Devin Desktop (Windsurf) | Web UI agent panel |
| 14 | Spaces (context bundles) | Devin Desktop (Windsurf) | Session management |
| 15 | Knowledge Items (persistent memory) | Antigravity | `knowledge_items.py` |
| 16 | Skills (reusable agent instructions) | Antigravity | `skills/` directory |
| 17 | Artifacts (task.md, plan.md, walkthrough.md) | Antigravity | Artifact generation |
| 18 | Agentic coding (autonomous multi-step) | Trae SOLO, Windsurf Cascade | Enhanced agent.py |
| 19 | Tab completion / Supercomplete | Cursor (Sonic), Windsurf (Supercomplete) | `completion_engine.py` |
| 20 | RAG with BM25 + hybrid search | Windsurf (M-Query), OpenCode | Enhanced `rag_vector_engine.py` |
| 21 | AST parser / LSP diagnostics | OpenCode (LSP-in-loop), Cursor | `ast_analyzer.py` + `linter_engine.py` |
| 22 | Diagnostics panel | Cursor, OpenCode, VS Code | `diagnostics_panel.py` |
| 23 | Custom agents/skills | Trae (custom agents), Cursor (Skills) | Skill/agent system |
| 24 | Code review (Bugbot-style) | Cursor (Bugbot) | agent.py code review |
| 25 | Test generation | Cursor, Kiro, Claude Code | agent.py test generation |
| 26 | Refactoring tools | Cursor, Windsurf | agent.py refactoring |
| 27 | Session persistence across days | Windsurf (Memories), Kiro (Steering) | `session_manager.py` |
| 28 | Steering files (persistent instructions) | Kiro | `steering_engine.py` |
| 29 | Browser preview | Trae (browser preview) | Web preview panel |
| 30 | Open source (MIT license) | OpenCode, Kiro | License + public repo |

### P2 — Nice to Have
| # | Feature | Inspired By | Implementation |
|---|---------|-------------|----------------|
| 31 | Parallel agents | Cursor (8 parallel), OpenCode | Sub-agent spawning |
| 32 | Cloud agent offloading | Windsurf (Devin), Cursor (Background) | Future cloud VM |
| 33 | Go-to-definition / find references | OpenCode (LSP), Cursor | AST analyzer |
| 34 | Code outline / symbol tree | OpenCode, Cursor | Project explorer |
| 35 | Breadcrumb navigation | Cursor, VS Code | `breadcrumb_nav.py` |
| 36 | One-click deploy | Bolt.new, Replit | Deploy panel |
| 37 | Self-hosted (Docker) | OpenCode, Windsurf | Docker support |
| 38 | Cross-IDE plugin bridge | Windsurf (40+ IDEs) | `ide_bridge.py` |
| 39 | Tauri desktop wrapper | Tauri vs Electron research | Optional Tauri app |
| 40 | Image generation | Trae (text-to-image) | OmniRoute images API |

### P3 — Future (Vision)
| # | Feature | Inspired By | Implementation |
|---|---------|-------------|----------------|
| 41 | Visual element editing | Trae (element selection) | Browser DOM inspector |
| 42 | Multi-modal input (images, voice) | Trae (multi-modal) | File upload + voice |
| 43 | Real-time collaboration | VS Code (Live Share), Replit | WebSocket multi-user |
| 44 | Enterprise security (SSO, audit) | Windsurf (SOC 2), Kiro (GovCloud) | Enterprise features |

---

## Implementation Plan

### Phase 1: Core Web GUI + CodeMirror 6 (Week 1-2) — P0
- Redesign `web/index.html` with CodeMirror 6 editor
- Activity bar (left): Explorer, Search, Git, Chat, Terminal, Settings
- Side bar: file tree with type icons, symbols, search results
- Editor area: CodeMirror 6 with tabs, breadcrumbs, line numbers
- Chat panel: streaming responses, code blocks, tool results
- Terminal panel: persistent shell sessions
- Status bar: model name, token usage, cwd, file info
- Settings panel: model selector, API keys, preferences
- Install CodeMirror 6 via npm: `@codemirror/view`, `@codemirror/state`, `@codemirror/lang-javascript`, `@codemirror/lang-python`, etc.

### Phase 2: AST Parser & Linter (Week 2-3) — P1
- Create `ast_analyzer.py` — Python AST-based symbol extraction
- Create `linter_engine.py` — pylint/flake8/mypy/ruff integration
- Add diagnostics panel to web UI (`diagnostics_panel.py`)
- Add go-to-definition and find references
- Add code outline panel in side bar

### Phase 3: RAG & Indexing (Week 3-4) — P1
- Enhance `rag_vector_engine.py` with BM25 scoring
- Add incremental indexing with file hash caching
- Add hybrid search pipeline (BM25 + vector)
- Add RAG panel to web UI
- Add @-mention context in chat

### Phase 4: Terminal with PTY (Week 4-5) — P0
- Create `terminal_manager.py` with persistent sessions
- Cross-platform terminal abstraction (subprocess on Windows, PTY on Unix)
- Add terminal panel to web UI
- Add command history and output streaming
- Add auto-iterate on error (Cascade-style)

### Phase 5: Inline Editing & Diff Preview (Week 5-6) — P0/P1
- Add inline edit tool to `agent.py`
- Add command mode (Ctrl+I) to web UI
- Add diff preview before applying (accept/decline)
- Add multi-file editing support
- Add checkpoint system for reverting AI edits

### Phase 6: Knowledge Items, Skills & Artifacts (Week 6-7) — P1
- Create `knowledge_items.py` — persistent memory across sessions
- Create `skills/` directory — reusable agent instructions
- Create `artifacts/` directory — task.md, plan.md, walkthrough.md
- Add context management system (retrieve → compress → route)
- Add KI summaries at session start

### Phase 7: Agentic Coding & Custom Agents (Week 7-8) — P1
- Add autonomous agent loop to `agent.py`
- Three modes: Normal, Agent, Ask
- Agent picks files, runs terminal, iterates on errors
- Agent memory and session persistence
- Pre-built agents: code-review, security-audit, refactor, test-gen
- Agent Command Center (Kanban view) in web UI
- Spaces (context bundles) in web UI

### Phase 8: MCP Support & IDE Bridges (Week 8-9) — P0/P2
- Create `mcp_server.py` — MCP server for external tools
- Streamable HTTP MCP support (already in agent.py)
- Create `ide_bridge.py` for Cursor/Windsurf/OpenCode integration
- Add `.cursor/rules/` generation
- Add MCP server config for Windsurf
- Add OpenCode plugin config

### Phase 9: One-Click Installer (Week 9-10) — P0
- Create `setup.py` with `pyproject.toml`
- Create `install.bat` for Windows (portable with `$PSScriptRoot`)
- Auto-install Ollama if not present
- Auto-pull default models (gemma3:1b, llama3.2:1b, qwen2.5-coder:1.5b)
- Auto-install all Python dependencies
- Create desktop shortcut
- Auto-configure all AI tiers
- First-run wizard: select models, set API keys, configure workspace

### Phase 10: Tauri Desktop Wrapper (Optional, Week 10-11) — P2
- Create Tauri app wrapper for desktop installation
- Uses system WebView (WebView2 on Windows, WKWebView on Mac)
- System tray integration
- Auto-start on boot
- Native file dialogs, notifications

### Phase 11: Polish & Testing (Week 11-12) — P0
- Unit tests for all new modules
- Integration tests for end-to-end workflows
- Performance optimization (target <4GB RAM)
- Documentation (README, SETUP.md, inline docs)
- Final QA across all AI tiers

---

## Files to Create/Modify

### New Files (20 files):
| File | Purpose |
|------|---------|
| `ast_analyzer.py` | AST-based code analysis, symbol extraction, go-to-definition |
| `linter_engine.py` | Multi-linter integration (pylint, flake8, mypy, ruff, ESLint) |
| `terminal_manager.py` | Persistent terminal sessions with PTY/subprocess |
| `ide_bridge.py` | Cursor/Windsurf/OpenCode integration, config generation |
| `inline_editor.py` | Inline editing tool with diff preview |
| `search_engine.py` | Enhanced RAG search with BM25 + hybrid pipeline |
| `project_explorer.py` | File tree with type icons, symbol tree, breadcrumbs |
| `breadcrumb_nav.py` | Breadcrumb navigation for file paths |
| `diagnostics_panel.py` | Linting diagnostics, error highlighting |
| `mcp_server.py` | MCP server for external tools, tool registry |
| `knowledge_items.py` | Persistent memory across sessions (Antigravity KIs) |
| `skills/` | Reusable agent instruction sets (Antigravity Skills) |
| `artifacts/` | Task/plan/walkthrough documents (Antigravity Artifacts) |
| `session_manager.py` | Save/load agent sessions, checkpoints |
| `steering_engine.py` | Persistent coding standards, project rules |
| `completion_engine.py` | Tab completion, Supercomplete-style predictions |
| `context_manager.py` | RAG + context compression + memory routing |
| `agent_command_center.py` | Kanban view for agent sessions (Devin Desktop) |
| `spaces_manager.py` | Context bundles for organizing work (Devin Desktop) |
| `deploy_panel.py` | One-click deploy panel in web UI |

### Modified Files (7 files):
| File | Changes |
|------|---------|
| `server.py` | Add 50+ new REST endpoints + WebSocket message types for IDE features |
| `web/index.html` | Complete IDE-style redesign with CodeMirror 6 (+1500 lines) |
| `agent.py` | Add 30+ new tools (inline edit, refactor, lint, test-gen, git, MCP, agentic loop, KIs, skills, artifacts) |
| `rag_vector_engine.py` | BM25 + incremental indexing, hybrid search, @-mention support, context compression |
| `workspace_index.py` | AST symbols + import graph + cross-file references |
| `setup.py` | Enhanced installer with pyproject.toml, auto-configure all models, Ollama auto-install |
| `requirements.txt` | Add CodeMirror 6, linter/PTY/AST dependencies |

---

## Model Strategy (Local-First, Free-First)

| Task | Local Model (Free) | Free Cloud Fallback | Paid Fallback |
|------|-------------------|--------------------|---------------|
| Code completion | `gemma3:1b` (Ollama) | `big-pickle` (Zen) | `google/gemini-2.5-flash` (OmniRoute) |
| Chat | `llama3.2:1b` (Ollama) | `nemotron-3-ultra-free` (Zen) | `google/gemini-2.5-flash` (OmniRoute) |
| Code generation | `qwen2.5-coder:1.5b` (Ollama) | `deepseek-v4-flash-free` (Zen) | `google/gemini-2.5-flash` (OmniRoute) |
| RAG search | `nomic-embed-text` (Ollama) | `google/gemini-2.5-flash` (OmniRoute) | N/A |
| Linting | Local (pylint/ruff) | N/A | N/A |
| AST analysis | Local (Python ast) | N/A | N/A |
| Terminal | Local | N/A | N/A |
| Code review | `ling-3.0-flash-free` (Zen) | `google/gemini-2.5-flash` (OmniRoute) | N/A |
| Test generation | `nemotron-3-ultra-free` (Zen) | `google/gemini-2.5-flash` (OmniRoute) | N/A |
| Inline edit | `deepseek-v4-flash-free` (Zen) | `google/gemini-2.5-flash` (OmniRoute) | N/A |
| Agentic loop | `ling-3.0-flash-free` (Zen) | `google/gemini-2.5-flash` (OmniRoute) | N/A |

---

## RAM Optimization
- CodeMirror 6 is modular (~50-200KB vs Monaco's ~5MB) — much lighter bundle
- Web GUI uses browser rendering (no Electron, no Tauri overhead)
- All models are 1B-1.5B parameters (3.2GB total Ollama)
- RAG index uses JSON-based storage (no heavy DB)
- Terminal uses subprocess (no PTY overhead on Windows)
- AST analysis is local and lightweight (Python `ast` module)
- Linting runs on-demand, not continuously
- Target: <4GB RAM usage for full DevMind stack

---

## Testing
- Unit tests for all new modules (`tests/` directory)
- Integration tests for end-to-end workflows
- Test fixtures for AST, linter, RAG, terminal
- Regression suite: `test_all_tiers.py` (existing) + new IDE feature tests
- CI/CD workflow for automated testing
- Coverage reporting

---

## Verification
1. Run `python -m pytest tests/` — all tests pass
2. Start DevMind: `python start.py` — one-click launch
3. Open browser at `http://127.0.0.1:7860` — IDE loads with full layout
4. Test inline editing, linting, RAG, terminal
5. Verify all 4 AI tiers work (Gemini, Groq, Zen, OmniRoute)
6. Check RAM usage stays under 4GB
7. Test IDE bridges (Cursor, Windsurf, OpenCode)
8. Run one-click installer on fresh PC
9. Test P0 features: layout, inline edit, terminal, MCP, git, chat
10. Test P1 features: autocomplete, agentic coding, diagnostics, diff preview, KIs, skills, artifacts

---

## Expected Outcome
A professional, web-based AI coding IDE that:
- Looks and feels like Trae / Windsurf/Devin / OpenCode / Cursor
- Works with local models first (Ollama, free) — no API costs for basic use
- Falls back to free cloud models (Zen, OmniRoute) when needed
- Runs on a 12GB RAM PC without hanging (<4GB RAM usage)
- Has one-click install and configure
- Supports Cursor, Windsurf, and OpenCode workflows
- Includes RAG, AST parser, linter, terminal, inline editing
- Has MCP support for external tools
- Has Knowledge Items, Skills, and Artifacts (Antigravity-style context management)
- Has Agent Command Center and Spaces (Devin Desktop-style)
- Is fully open-source and self-hosted
- Has diff preview with accept/decline (Cursor-style)
- Has agentic coding with autonomous multi-step tasks (Trae SOLO-style)
- Has session persistence and steering files (Kiro/Windsurf-style)
- Has CodeMirror 6 editor (lightweight, modular, web-native)
- Has LSP integration for diagnostics and navigation (OpenCode-style)
- Has parallel agent support (Cursor-style)
- Has IDE bridges for Cursor, Windsurf, and OpenCode
- Optional Tauri desktop wrapper for native app experience

---

## Competitive Advantage of DevMind
1. **Web-based** — no install needed (like Trae Cloud IDE, Bolt.new, Replit)
2. **Local models first** — free, private, no API keys needed (like Antigravity local mode)
3. **Model-agnostic** — Zen + OmniRoute + Ollama (like OpenCode's 75+ providers)
4. **Lightweight** — CodeMirror 6 (~200KB) vs Monaco (~5MB), <4GB RAM total
5. **Self-hosted** — full data privacy, no vendor lock-in (like OpenCode, Kiro)
6. **One-click install** — simpler than any competitor (like Trae's ease of use)
7. **Python-native** — easier to customize and extend than compiled alternatives
8. **MCP-first** — built-in MCP support from day one (like Windsurf/OpenCode)
9. **Knowledge Items + Skills + Artifacts** — Antigravity's context management system
10. **Agent Command Center + Spaces** — Devin Desktop's agent management
