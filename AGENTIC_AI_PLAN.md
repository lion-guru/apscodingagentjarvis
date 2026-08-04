# DevMind IDE — Agentic AI Implementation Plan

## 🎯 Vision
Transform DevMind from a coding interface into a **Fully Autonomous Software Engineering System** that can plan, code, test, debug, and deploy — inspired by Devin, Windsurf Agent, Cursor Agent, and OpenCode's subagent architecture.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Frontend (CodeMirror 6)            │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────┐ │
│  │ Agent Panel  │ │ DAG Executor │ │ Tool Inspector│ │
│  │ (Modes)      │ │ (Visual)     │ │ (Live Logs)  │ │
│  └──────┬──────┘ └──────┬───────┘ └──────┬──────┘ │
│         │                │                │         │
│  ┌──────▼────────────────▼────────────────▼──────┐  │
│  │          Agent Command Center (UI)            │  │
│  └────────────────────┬──────────────────────────┘  │
│                       │ WebSocket / SSE             │
├───────────────────────┼─────────────────────────────┤
│  FastAPI Backend      │                             │
│  ┌────────────────────▼──────────────────────────┐  │
│  │         Agent Orchestrator (agent.py)         │  │
│  │  ┌─────────┐ ┌──────────┐ ┌───────────────┐ │  │
│  │  │ Planner │ │ Coder    │ │ Reviewer      │ │  │
│  │  │ Agent   │ │ Agent    │ │ Agent         │ │  │
│  │  └────┬────┘ └─────┬────┘ └──────┬────────┘ │  │
│  │       │            │             │           │  │
│  │  ┌────▼────────────▼─────────────▼────────┐  │  │
│  │  │     Subagent Pool (async workers)      │  │  │
│  │  └────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────┘  │
│                       │                             │
│  ┌────────────────────▼──────────────────────────┐  │
│  │         Steering Engine (steering_engine.py)  │  │
│  │  - HITL Approval Matrix                       │  │
│  │  - Rule-based Guardrails                      │  │
│  │  - Context Window Management                  │  │
│  └──────────────────────────────────────────────┘  │
│                       │                             │
│  ┌────────────────────▼──────────────────────────┐  │
│  │         Self-Healing Agent                    │  │
│  │  - Auto-fix lint errors                       │  │
│  │  - Auto-fix test failures                     │  │
│  │  - Rollback on critical failures              │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Phases

### Phase 1: Agent Core (`agent.py` + `agent_command_center.py`)
**Priority: P0 — Foundation**

#### 1.1 Agent Class Architecture
```python
class Agent:
    """Base agent with role, tools, and execution context."""
    role: str                    # "planner", "coder", "reviewer", "healer"
    tools: List[Tool]            # Available tools for this agent
    context_window: int          # Max tokens in context
    model: str                   # Model to use (gemma3:1b, etc.)
    subagents: List[Agent]       # Child subagents for delegation
    
    async def execute(self, task: Task) -> Result:
        """Execute a task using available tools and model."""
        
    async def delegate(self, subagent: Agent, subtask: Task) -> Result:
        """Delegate a subtask to a specialized subagent."""
```

#### 1.2 Specialized Agents
- **PlannerAgent**: Reads codebase via `workspace_index.py`, creates DAG execution plans
- **CoderAgent**: Applies edits via `inline_editor.py`, follows code style rules
- **ReviewerAgent**: Runs `linter_engine.py` + `diagnostics_panel.py`, validates changes
- **HealerAgent**: Intercepts errors, generates auto-fix patches via `self_repair_autofix.py`

#### 1.3 Agent Command Center (Backend)
- New endpoints in `server.py`:
  - `POST /api/agent/execute` — Execute an agent task
  - `GET /api/agent/status/{task_id}` — Get task status
  - `POST /api/agent/delegate` — Delegate to subagent
  - `GET /api/agent/logs/{task_id}` — Stream agent logs
  - `POST /api/agent/approve` — Human approval for destructive operations
  - `POST /api/agent/steer` — Send steering rules to agent

#### 1.4 Subagent Pool
- Async worker pool using `asyncio` for parallel subagent execution
- Max concurrent subagents configurable (default: 4)
- Subagent results aggregated and reported to parent agent

---

### Phase 2: Steering Engine (`steering_engine.py`)
**Priority: P1 — Control & Safety**

#### 2.1 HITL Approval Matrix
| Operation | Auto-Approve | Requires Approval |
|-----------|-------------|-------------------|
| Read files | ✅ | ❌ |
| Edit files (non-destructive) | ✅ | ❌ |
| Delete files | ❌ | ✅ |
| Shell commands (safe) | ✅ | ❌ |
| Shell commands (destructive) | ❌ | ✅ |
| Install packages | ❌ | ✅ |
| Deploy to cloud | ❌ | ✅ |
| Modify config files | ❌ | ✅ |
| Git operations (commit/push) | ❌ | ✅ |

#### 2.2 Rule-Based Guardrails
- Load rules from `.devmind/rules.mdc` and `.cursor/rules/devmind.mdc`
- Rules format: `DENY: delete *.py in src/` / `ALLOW: edit files in tests/`
- Context-aware: rules change based on project type (Python, JS, etc.)

#### 2.3 Context Window Management
- Automatic summarization of old conversation turns
- Knowledge Items and Artifacts injected into context automatically
- RAG results included in agent context window
- Token budget tracking per agent session

---

### Phase 3: Self-Healing & Test Automation
**Priority: P1 — Reliability**

#### 3.1 Auto-Fix Pipeline
1. Agent makes code change → runs `linter_engine.lint_file()`
2. If lint errors → agent generates fix → re-lints → repeat (max 3 iterations)
3. If test failures → agent analyzes failure → generates fix → re-runs tests
4. If still failing → escalate to human with error report

#### 3.2 Test Generation Agent
- `POST /api/agent/generate-tests` — Generate unit tests for a file
- Uses `ast_analyzer.py` to understand code structure
- Generates pytest-compatible test files
- Runs tests via `terminal_manager.py` and reports results

#### 3.3 Rollback Mechanism
- Git-based rollback on critical failures
- `POST /api/agent/rollback` — Revert last agent changes
- Snapshot before each agent operation for safe rollback

---

### Phase 4: Superior Frontend UI (`web/index.html`)
**Priority: P2 — Experience**

#### 4.1 Agent Command Panel (Sidebar)
- Agent mode selector: `Chat` | `Inline Ctrl+K` | `Full Autonomous`
- Active task list with status indicators
- One-click shortcuts:
  - 🔧 **Auto-Fix All Problems** — Runs linter, fixes all issues
  - 🧪 **Generate Test Suite** — Creates tests for current file
  - 🔄 **Refactor Selection** — Refactors selected code
  - 📊 **Architectural Review** — Reviews project structure
  - 🚀 **Deploy App** — Deploys to Azure (if configured)

#### 4.2 DAG Execution Tree View
- Visual tree showing agent task decomposition
- Each node shows: task name, agent role, status (pending/running/completed/failed)
- Click node to see tool calls, arguments, and output
- Expand/collapse subagent branches

#### 4.3 Tool Call Inspector
- Real-time log of all tool calls made by agents
- Shows: tool name, arguments, timestamp, duration, result
- Color-coded: green (success), red (error), yellow (pending)
- Copy individual tool call results

#### 4.4 Agent Chat Interface
- Chat-like interface for agent interactions
- Supports streaming responses (SSE)
- Shows agent reasoning steps inline
- Quick actions on agent suggestions (accept/reject/modify)

#### 4.5 Agent Mode Switcher
- **Chat Mode**: Agent suggests, human approves each step
- **Inline Ctrl+K**: Agent makes inline edits with preview
- **Full Autonomous**: Agent runs end-to-end with HITL checkpoints only

---

## 🔌 New API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/execute` | POST | Execute an agent task |
| `/api/agent/status/{id}` | GET | Get task status |
| `/api/agent/logs/{id}` | GET | Stream agent logs (SSE) |
| `/api/agent/delegate` | POST | Delegate to subagent |
| `/api/agent/approve` | POST | Approve/deny destructive operation |
| `/api/agent/steer` | POST | Send steering rules |
| `/api/agent/rollback` | POST | Rollback last agent changes |
| `/api/agent/generate-tests` | POST | Generate unit tests |
| `/api/agent/modes` | GET | Get available agent modes |
| `/api/agent/shortcuts` | POST | Execute one-click agent shortcut |

---

## 🧠 Model Strategy for Agents

| Agent Role | Model | Reason |
|------------|-------|--------|
| Planner | gemma3:1b (local) | Fast planning, low cost |
| Coder | gemma3:1b (local) | Inline edits, fast turnaround |
| Reviewer | gemma3:1b (local) | Linting and review |
| Healer | gemma3:1b (local) | Auto-fix simple issues |
| Complex Tasks | Zen/OmniRoute (free cloud) | Complex reasoning |
| Architecture | OpenRouter (paid) | High-quality design |

---

## 📁 Files to Create/Modify

### New Files
- `agent_core.py` — Base Agent class and subagent pool
- `agent_planner.py` — PlannerAgent implementation
- `agent_coder.py` — CoderAgent implementation
- `agent_reviewer.py` — ReviewerAgent implementation
- `agent_healer.py` — SelfHealingAgent implementation
- `agent_command_center.py` — Agent orchestration and API endpoints
- `steering_engine.py` — HITL approval and rule-based guardrails
- `agent_ui_components.py` — Frontend agent panel components

### Modified Files
- `agent.py` — Add agent tools (execute_agent, delegate_subagent, approve_operation, steer_agent)
- `server.py` — Add agent API endpoints
- `web/index.html` — Add agent command panel, DAG view, tool inspector
- `agent_command_center.py` — Extend with agent execution logic

---

## 🎯 Success Metrics

1. **Agent Task Completion Rate**: >80% of agent tasks complete without human intervention
2. **Auto-Fix Success Rate**: >70% of lint errors auto-fixed on first attempt
3. **Test Generation Coverage**: >60% of functions get generated tests
4. **Response Time**: Agent commands respond within 2 seconds (local model)
5. **User Satisfaction**: Agent suggestions accepted >75% of the time

---

## 🚀 Quick Start (After Implementation)

1. Open DevMind IDE
2. Click Agent Panel icon in sidebar
3. Select agent mode (Chat / Inline / Autonomous)
4. Type or select a task: "Add input validation to login form"
5. Agent decomposes task → plans → codes → reviews → deploys
6. Human approves only destructive operations
7. Monitor progress in DAG Execution Tree view
