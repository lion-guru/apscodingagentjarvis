# DevMind IDE — Comprehensive Implementation Plan

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (Web GUI)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  Monaco   │ │  File    │ │   Chat   │ │   Terminal       │  │
│  │  Editor   │ │  Explorer│ │   Panel  │ │   (xterm.js)     │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  Search   │ │  Git     │ │  Outline │ │  Diagnostics     │  │
│  │  & Replace│ │  Diff    │ │  (AST)   │ │  Panel           │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ WebSocket (ws://) + REST (fetch)
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend (server.py)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  REST     │ │ WebSocket│ │  Static  │ │  CORS Middleware │  │
│  │  API      │ │ Router   │ │  Files   │ │                  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  AST      │ │  Linter  │ │  Debug   │ │  Test Runner     │  │
│  │  Analyzer │ │  Engine  │ │  Server  │ │  Controller      │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  RAG      │ │  Vector  │ │  Workspace│ │  Terminal (PTY)  │  │
│  │  Engine   │ │  Index   │ │  Indexer  │ │  Manager         │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  Git      │ │  Memory  │ │  Skills  │ │  MCP Client      │  │
│  │  Integration│          │ │  Engine  │ │  (stdio/HTTP)    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                    Python Backend (agent.py)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  Tool     │ │  Model   │ │  Multi-  │ │  Auto-Failover   │  │
│  │  Registry │ │  Router  │ │  Model   │ │  Engine          │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Communication Protocol

| Direction | Protocol | Purpose |
|-----------|----------|---------|
| Browser → Backend | WebSocket `/ws/{session_id}` | Chat, tool execution, real-time streaming |
| Browser → Backend | REST `/api/*` | File ops, git, models, config, terminal |
| Backend → Browser | WebSocket push | Token streaming, tool results, events |
| Backend → LLM | HTTP/SSE | Gemini, Groq, OpenAI, Anthropic, OpenRouter, Ollama |
| Backend → OS | subprocess/PTY | Terminal execution, git commands, file ops |

### 1.3 Key Design Principles

1. **All Python** — No Node.js/Electron dependency; saves RAM
2. **Web-based GUI** — Browser renders Monaco editor + UI; no Electron overhead
3. **One-click install** — `setup.py` handles everything; `pip install devmind` works
4. **IDE-agnostic** — Works standalone, integrates with Cursor/Windsurf/OpenCode
5. **RAM-efficient** — No heavy frameworks; uses FastAPI + vanilla JS frontend
6. **Extensible** — Plugin API for third-party extensions

---

## 2. New Modules to Create

### 2.1 AST Analysis Engine

**File:** `ast_analyzer.py` (new, ~400 lines)

```
Purpose: Parse Python source files into AST, extract symbols,
         provide go-to-definition, find references, code outline.
```

Key classes and functions:
- `class ASTAnalyzer` — Main analyzer class
  - `analyze_file(path: str) -> ASTResult` — Parse a single file
  - `analyze_workspace(workspace: str) -> dict` — Batch analyze all Python files
  - `get_symbols(path: str) -> list[Symbol]` — Extract classes, functions, variables
  - `find_definition(path: str, line: int, col: int) -> Definition | None` — Go-to-definition
  - `find_references(path: str, line: int, col: int) -> list[Reference]` — Find all references
  - `get_outline(path: str) -> list[OutlineItem]` — Code outline/symbol tree
  - `get_diagnostics(path: str) -> list[Diagnostic]` — AST-level diagnostics
- `class Symbol` — Represents a symbol (class, function, variable)
  - `name: str`, `kind: str` (class/function/variable/import), `line: int`, `col: int`, `path: str`
- `class Diagnostic` — Represents a diagnostic message
  - `message: str`, `severity: str` (error/warning/info), `line: int`, `col: int`, `source: str`
- `class Definition` — Represents a go-to-definition result
  - `path: str`, `line: int`, `col: int`, `name: str`, `kind: str`
- `class Reference` — Represents a reference location
  - `path: str`, `line: int`, `col: int`, `name: str`
- `class OutlineItem` — Represents an item in the code outline
  - `name: str`, `kind: str`, `line: int`, `children: list[OutlineItem]`

Supported languages (Phase 1: Python; Phase 2: JS/TS/Go/Rust):
- Python: `ast` module (built-in)
- JS/TS: `esprima` (via PyExecJS or node subprocess)
- Go: `go/ast` (via subprocess)
- Rust: `syn` crate (via subprocess)

### 2.2 Linter Integration Engine

**File:** `linter_engine.py` (new, ~350 lines)

```
Purpose: Integrate linters (pylint, flake8, mypy, eslint, etc.)
         and display diagnostics in the IDE.
```

Key classes and functions:
- `class LinterEngine`
  - `run_linter(file_path: str, language: str) -> list[Diagnostic]` — Run appropriate linter
  - `run_all_linters(workspace: str) -> dict[str, list[Diagnostic]]` — Run all linters on workspace
  - `get_available_linters() -> list[LinterInfo]` — Check which linters are installed
  - `install_linter(linter_name: str) -> bool` — Install a missing linter
- `class LinterInfo`
  - `name: str`, `command: str`, `args: list[str]`, `parser: str` (regex pattern for output)
  - `installed: bool`, `languages: list[str]`

Linter configurations:
| Language | Linter | Command | Output Parser |
|----------|--------|---------|---------------|
| Python | pylint | `pylint --output-format=json {file}` | JSON |
| Python | flake8 | `flake8 --format=json {file}` | JSON |
| Python | mypy | `mypy --show-error-codes {file}` | Regex |
| Python | ruff | `ruff check --output-format=json {file}` | JSON |
| JS/TS | eslint | `eslint --format=json {file}` | JSON |
| Go | golint | `golint {file}` | Regex |
| Rust | clippy | `cargo clippy --message-format=json` | JSON |
| JSON | jsonlint | `jsonlint {file}` | Regex |

### 2.3 Debugger Server

**File:** `debugger_server.py` (new, ~500 lines)

```
Purpose: Provide breakpoint management, step execution,
         variable inspection via WebSocket.
```

Key classes and functions:
- `class DebuggerServer`
  - `start_session(file_path: str, breakpoints: list[Breakpoint]) -> str` — Start a debug session
  - `step_over(session_id: str) -> DebugState` — Step over current line
  - `step_into(session_id: str) -> DebugState` — Step into function call
  - `step_out(session_id: str) -> DebugState` — Step out of current function
  - `continue_execution(session_id: str) -> DebugState` — Continue to next breakpoint
  - `get_variables(session_id: str) -> list[Variable]` — Get current scope variables
  - `set_breakpoint(session_id: str, file: str, line: int) -> bool` — Set/remove breakpoint
  - `evaluate_expression(session_id: str, expr: str) -> any` — Evaluate expression in context
- `class Breakpoint` — `file: str`, `line: int`, `condition: str | None`
- `class DebugState` — `current_file: str`, `current_line: int`, `variables: list[Variable]`, `stack_trace: list[Frame]`
- `class Variable` — `name: str`, `value: str`, `type: str`, `children: list[Variable]`

Implementation approach: Use `debugpy` (Microsoft's Python debugger) as the backend, communicate via DAP (Debug Adapter Protocol).

### 2.4 Test Runner

**File:** `test_runner.py` (new, ~300 lines)

```
Purpose: Discover and run tests (pytest, unittest, etc.)
         with results displayed in the IDE.
```

Key classes and functions:
- `class TestRunner`
  - `discover_tests(workspace: str, test_pattern: str = "test_*.py") -> list[TestFile]` — Find test files
  - `run_all_tests(workspace: str) -> TestResult` — Run all discovered tests
  - `run_single_test(workspace: str, test_path: str, test_name: str) -> TestResult` — Run specific test
  - `run_with_coverage(workspace: str) -> CoverageResult` — Run with coverage reporting
- `class TestResult`
  - `total: int`, `passed: int`, `failed: int`, `errors: int`, `skipped: int`
  - `results: list[TestCaseResult]`
- `class TestCaseResult`
  - `name: str`, `status: str` (pass/fail/error/skip), `duration: float`, `output: str`, `file: str`, `line: int`

### 2.5 Git Diff Viewer

**File:** `git_diff_viewer.py` (new, ~200 lines)

```
Purpose: Generate and serve git diffs with syntax highlighting
         for the web UI diff panel.
```

Key classes and functions:
- `class GitDiffViewer`
  - `get_diff(cwd: str, file_path: str = None) -> DiffResult` — Get diff for file or all
  - `get_diff_for_range(cwd: str, file_path: str, start: int, end: int) -> DiffResult` — Get diff for line range
  - `get_staged_diff(cwd: str) -> DiffResult` — Get staged changes diff
  - `get_commit_diff(cwd: str, commit_sha: str) -> DiffResult` — Get diff for a specific commit
  - `get_blame(cwd: str, file_path: str) -> list[BlameLine]` — Get blame information
- `class DiffResult`
  - `files: list[DiffFile]`, `total_additions: int`, `total_deletions: int`
- `class DiffFile`
  - `path: str`, `status: str` (added/modified/deleted/renamed), `additions: int`, `deletions: int`, `hunks: list[DiffHunk]`
- `class DiffHunk`
  - `old_start: int`, `old_lines: int`, `new_start: int`, `new_lines: int`, `lines: list[DiffLine]`
- `class DiffLine`
  - `type: str` (add/delete/context), `old_number: int | None`, `new_number: int | None`, `content: str`
- `class BlameLine`
  - `line_number: int`, `commit_sha: str`, `author: str`, `date: str`, `message: str`

### 2.6 Terminal Manager (PTY Support)

**File:** `terminal_manager.py` (new, ~350 lines)

```
Purpose: Manage persistent terminal sessions with PTY support,
         allowing interactive command execution with state.
```

Key classes and functions:
- `class TerminalManager`
  - `create_session(name: str = "default") -> str` — Create a new PTY session, return session_id
  - `run_command(session_id: str, command: str) -> TerminalResult` — Run command in session
  - `get_output(session_id: str) -> str` — Get current session output
  - `clear(session_id: str) -> None` — Clear session output
  - `kill(session_id: str) -> None` — Kill the session process
  - `list_sessions() -> list[TerminalSession]` — List all active sessions
  - `resize(session_id: str, cols: int, rows: int) -> None` — Resize PTY
- `class TerminalSession`
  - `id: str`, `name: str`, `cwd: str`, `pid: int`, `created_at: datetime`
- `class TerminalResult`
  - `output: str`, `exit_code: int | None`, `error: str | None`, `running: bool`

Implementation: Use `ptyprocess` library for PTY support on Unix, and `subprocess` with `CREATE_NEW_PROCESS_GROUP` on Windows. For cross-platform PTY, use `pexpect` or `ptyprocess`.

### 2.7 IDE Integration Bridge

**File:** `ide_bridge.py` (new, ~250 lines)

```
Purpose: Provide integration hooks for Cursor, Windsurf, and OpenCode IDEs.
```

Key classes and functions:
- `class IDEBridge`
  - `detect_ide() -> str | None` — Detect which IDE is running
  - `get_ide_config(ide_name: str) -> dict` — Get configuration for the detected IDE
  - `launch_in_ide(file_path: str, ide_name: str) -> bool` — Open file in the IDE
  - `sync_settings(ide_name: str, settings: dict) -> bool` — Sync DevMind settings to IDE
  - `generate_ide_config(ide_name: str) -> dict` — Generate IDE-specific config
  - `register_command(ide_name: str, command: str) -> bool` — Register a DevMind command in the IDE

IDE-specific integrations:
- **Cursor**: Modify `.cursorrules` and `cursor/settings.json`; inject DevMind as a custom command
- **Windsurf**: Modify `.windsurfrules` and `windsurf/config.json`; use Windsurf's MCP server support
- **OpenCode**: Modify `~/.config/opencode/user/settings.json`; inject DevMind as a plugin/command

### 2.8 Theme Manager

**File:** `theme_manager.py` (new, ~200 lines)

```
Purpose: Manage IDE themes (dark, light, custom) with CSS variable support.
```

Key classes and functions:
- `class ThemeManager`
  - `get_themes() -> list[Theme]` — List available themes
  - `get_theme(name: str) -> Theme` — Get a specific theme
  - `apply_theme(theme_name: str) -> dict` — Apply theme, return CSS variables
  - `create_theme(name: str, variables: dict) -> Theme` — Create custom theme
  - `export_theme(theme_name: str) -> str` — Export theme as JSON
  - `import_theme(json_str: str) -> Theme` — Import theme from JSON
- `class Theme`
  - `name: str`, `author: str`, `version: str`, `variables: dict[str, str]`, `is_dark: bool`

Built-in themes:
- `dark` (default — current dark theme)
- `light` (light theme for daytime use)
- `high-contrast` (accessibility-focused)
- `monokai` (Monokai color scheme)
- `dracula` (Dracula color scheme)
- `solarized-dark` (Solarized dark)
- `solarized-light` (Solarized light)

### 2.9 Keybinding System

**File:** `keybinding_manager.py` (new, ~200 lines)

```
Purpose: Manage keyboard shortcuts for IDE actions.
```

Key classes and functions:
- `class KeybindingManager`
  - `get_keybindings() -> list[Keybinding]` — Get all keybindings
  - `get_keybinding(action: str) -> Keybinding | None` — Get keybinding for action
  - `set_keybinding(action: str, key: str) -> bool` — Set keybinding
  - `reset_keybinding(action: str) -> bool` — Reset to default
  - `export_keybindings() -> str` — Export as JSON
  - `import_keybindings(json_str: str) -> bool` — Import from JSON
- `class Keybinding`
  - `action: str`, `key: str`, `mac: str | None`, `linux: str | None`, `windows: str | None`, `when: str | None`

Default keybindings:
| Action | Windows/Linux | macOS |
|--------|--------------|-------|
| Save file | Ctrl+S | Cmd+S |
| Find | Ctrl+F | Cmd+F |
| Find & Replace | Ctrl+H | Cmd+H |
| Go to definition | F12 | F12 |
| Go to line | Ctrl+G | Cmd+G |
| Toggle sidebar | Ctrl+B | Cmd+B |
| Toggle terminal | Ctrl+` | Cmd+` |
| Format code | Shift+Alt+F | Shift+Option+F |
| Run tests | Ctrl+Shift+T | Cmd+Shift+T |
| Debug start | F5 | F5 |
| Debug step over | F10 | F10 |
| Debug step into | F11 | F11 |
| Debug step out | Shift+F11 | Shift+F11 |
| Quick fix | Ctrl+. | Cmd+. |
| Comment line | Ctrl+/ | Cmd+/ |
| Undo | Ctrl+Z | Cmd+Z |
| Redo | Ctrl+Shift+Z | Cmd+Shift+Z |
| Copy line | Ctrl+Alt+Down | Cmd+Option+Down |
| Delete line | Ctrl+Shift+K | Cmd+Shift+K |
| Move line up | Alt+Up | Option+Up |
| Move line down | Alt+Down | Option+Down |
| Split editor | Ctrl+\ | Cmd+\ |
| Close editor | Ctrl+W | Cmd+W |

### 2.10 Extension API Framework

**File:** `extension_api.py` (new, ~300 lines)

```
Purpose: Provide an API for third-party IDE extensions to register
         commands, views, and functionality.
```

Key classes and functions:
- `class ExtensionAPI`
  - `register_command(name: str, handler: Callable) -> bool` — Register a new command
  - `register_view(view_id: str, view_class: type) -> bool` — Register a new sidebar view
  - `register_editor_action(name: str, handler: Callable) -> bool` — Register an editor action
  - `register_diagnostics_provider(language: str, provider: DiagnosticsProvider) -> bool` — Register diagnostics
  - `get_registered_commands() -> list[Command]` — List all registered commands
  - `execute_command(name: str, *args) -> any` — Execute a registered command
- `class Extension`
  - `id: str`, `name: str`, `version: str`, `description: str`, `main: str`, `commands: list[Command]`, `views: list[View]`
- `class Command`
  - `id: str`, `title: str`, `handler: Callable`, `when: str | None`
- `class View`
  - `id: str`, `title: str`, `icon: str`, `position: str` (left/right/bottom)

Extension manifest format (`devmind-extension.json`):
```json
{
  "id": "my-extension",
  "name": "My Extension",
  "version": "1.0.0",
  "description": "A sample DevMind extension",
  "main": "extension.js",
  "commands": [
    { "id": "myExtension.doSomething", "title": "Do Something" }
  ],
  "views": [
    { "id": "myExtension.view", "title": "My View", "position": "left" }
  ]
}
```

### 2.11 Find & Replace Across Files

**File:** `search_engine.py` (new, ~250 lines)

```
Purpose: Provide find/replace across all workspace files
         with regex support and file filtering.
```

Key classes and functions:
- `class SearchEngine`
  - `find(query: str, cwd: str, file_pattern: str = "**/*", use_regex: bool = False) -> list[SearchResult]` — Find matches
  - `replace(query: str, replacement: str, cwd: str, file_pattern: str = "**/*", use_regex: bool = False) -> ReplaceResult` — Replace across files
  - `replace_in_file(file_path: str, query: str, replacement: str, use_regex: bool = False) -> list[ReplaceResult]` — Replace in single file
- `class SearchResult`
  - `file: str`, `line: int`, `col: int`, `line_content: str`, `match: str`
- `class ReplaceResult`
  - `file: str`, `replacements: int`, `success: bool`

### 2.12 Breadcrumb Navigation

**File:** `breadcrumb_nav.py` (new, ~100 lines)

```
Purpose: Generate breadcrumb navigation for the current file path.
```

Key classes and functions:
- `class BreadcrumbNav`
  - `generate(path: str, cwd: str) -> list[BreadcrumbItem]` — Generate breadcrumb trail
  - `navigate(cwd: str, path: str) -> str` — Navigate to a breadcrumb segment
- `class BreadcrumbItem`
  - `label: str`, `path: str`, `is_dir: bool`

### 2.13 Project Explorer with Type Icons and File Grouping

**File:** `project_explorer.py` (new, ~200 lines)

```
Purpose: Enhanced file explorer with file type icons,
         grouping by extension/folder, and tree navigation.
```

Key classes and functions:
- `class ProjectExplorer`
  - `get_file_tree(cwd: str, expanded_paths: list[str] = None) -> FileNode` — Get file tree with icons
  - `get_file_type_icon(file_path: str) -> str` — Get icon for file type
  - `group_by_type(files: list[str]) -> dict[str, list[str]]` — Group files by type
  - `group_by_folder(files: list[str]) -> dict[str, list[str]]` — Group files by folder
- `class FileNode`
  - `name: str`, `path: str`, `is_dir: bool`, `icon: str`, `children: list[FileNode]`, `extension: str`

File type icons mapping:
| Extension | Icon |
|-----------|------|
| `.py` | 🐍 |
| `.js` | 📜 |
| `.ts` | 🔷 |
| `.tsx` | ⚛️ |
| `.jsx` | ⚛️ |
| `.html` | 🌐 |
| `.css` | 🎨 |
| `.json` | 📋 |
| `.md` | 📝 |
| `.yaml` | 📄 |
| `.yml` | 📄 |
| `.toml` | 📄 |
| `.sql` | 🗄️ |
| `.vue` | 🟢 |
| `.svelte` | 🔴 |
| `.go` | 🔵 |
| `.rs` | 🦀 |
| `.c` | 🔧 |
| `.cpp` | 🔧 |
| `.h` | 📐 |
| `.java` | ☕ |
| `.rb` | 💎 |
| `.php` | 🐘 |
| `.sh` | 🐚 |
| `.bat` | 🖥️ |
| `.ps1` | 🟠 |
| `.txt` | 📄 |
| `.png` | 🖼️ |
| `.jpg` | 🖼️ |
| `.svg` | 🖼️ |
| `.gif` | 🖼️ |
| `.pdf` | 📕 |
| `.zip` | 📦 |
| `.tar` | 📦 |
| `.gz` | 📦 |
| `.lock` | 🔒 |
| `.env` | 🔑 |
| `.gitignore` | 🔀 |
| `.dockerfile` | 🐳 |
| `.dockerignore` | 🐳 |
| `.vscode` | 💻 |
| `.devmind` | 🧠 |
| Default | 📄 |

---

## 3. Existing Modules to Modify

### 3.1 `server.py` — Add New API Routes and WebSocket Handlers

**File:** `E:\coding-assistant\server.py` (2067 lines → ~2800 lines)

#### 3.1.1 New REST API Routes to Add

| Method | Route | Handler | Description |
|--------|-------|---------|-------------|
| GET | `/api/ast/analyze` | `ast_analyze_endpoint` | Analyze file with AST parser |
| GET | `/api/ast/outline` | `ast_outline_endpoint` | Get code outline for a file |
| GET | `/api/ast/definition` | `ast_definition_endpoint` | Go-to-definition |
| GET | `/api/ast/references` | `ast_references_endpoint` | Find references |
| GET | `/api/ast/diagnostics` | `ast_diagnostics_endpoint` | Get AST-level diagnostics |
| GET | `/api/linter/run` | `linter_run_endpoint` | Run linter on a file |
| GET | `/api/linter/all` | `linter_run_all_endpoint` | Run all linters on workspace |
| GET | `/api/linter/status` | `linter_status_endpoint` | Check installed linters |
| POST | `/api/linter/install` | `linter_install_endpoint` | Install a linter |
| POST | `/api/debug/start` | `debug_start_endpoint` | Start debug session |
| POST | `/api/debug/step` | `debug_step_endpoint` | Step debugger |
| POST | `/api/debug/continue` | `debug_continue_endpoint` | Continue execution |
| POST | `/api/debug/variables` | `debug_variables_endpoint` | Get variables |
| POST | `/api/debug/breakpoint` | `debug_breakpoint_endpoint` | Set/remove breakpoint |
| POST | `/api/debug/evaluate` | `debug_evaluate_endpoint` | Evaluate expression |
| POST | `/api/test/run` | `test_run_endpoint` | Run tests |
| GET | `/api/test/discover` | `test_discover_endpoint` | Discover test files |
| GET | `/api/test/result` | `test_result_endpoint` | Get test results |
| GET | `/api/git/diff` | `git_diff_endpoint` | Get git diff with syntax highlighting |
| GET | `/api/git/diff-range` | `git_diff_range_endpoint` | Get diff for line range |
| GET | `/api/git/blame` | `git_blame_endpoint` | Get blame info |
| GET | `/api/terminal/sessions` | `terminal_sessions_endpoint` | List terminal sessions |
| POST | `/api/terminal/create` | `terminal_create_endpoint` | Create new PTY session |
| POST | `/api/terminal/run` | `terminal_run_endpoint` | Run command in PTY session |
| POST | `/api/terminal/resize` | `terminal_resize_endpoint` | Resize PTY session |
| POST | `/api/terminal/kill` | `terminal_kill_endpoint` | Kill terminal session |
| GET | `/api/search/find` | `search_find_endpoint` | Find text across files |
| POST | `/api/search/replace` | `search_replace_endpoint` | Replace text across files |
| GET | `/api/themes` | `themes_endpoint` | List available themes |
| POST | `/api/themes/apply` | `theme_apply_endpoint` | Apply a theme |
| GET | `/api/keybindings` | `keybindings_endpoint` | Get all keybindings |
| POST | `/api/keybindings/set` | `keybinding_set_endpoint` | Set a keybinding |
| GET | `/api/extensions` | `extensions_endpoint` | List installed extensions |
| POST | `/api/extensions/install` | `extension_install_endpoint` | Install extension |
| GET | `/api/ide/config` | `ide_config_endpoint` | Get IDE integration config |
| POST | `/api/ide/sync` | `ide_sync_endpoint` | Sync settings to IDE |
| GET | `/api/breadcrumb` | `breadcrumb_endpoint` | Get breadcrumb navigation |
| GET | `/api/explorer` | `explorer_endpoint` | Get enhanced file tree with icons |

#### 3.1.2 WebSocket Message Types to Add

Add to the existing WebSocket handler in `server.py`:

| Type | Direction | Description |
|------|-----------|-------------|
| `terminal_input` | Client → Server | Send terminal input to PTY session |
| `terminal_resize` | Client → Server | Resize PTY terminal |
| `terminal_output` | Server → Client | Stream terminal output |
| `debug_start` | Client → Server | Start debug session |
| `debug_step` | Client → Server | Step debugger |
| `debug_state` | Server → Client | Send debug state update |
| `diagnostics` | Server → Client | Push linting diagnostics |
| `search_results` | Server → Client | Return search results |
| `theme_changed` | Server → Client | Notify theme change |
| `file_saved` | Server → Client | Notify file save (trigger re-index) |
| `outline_updated` | Server → Client | Push updated code outline |

#### 3.1.3 Modifications to Existing Routes

- **`/api/terminal/run`** (line 620): Replace with PTY-based terminal that uses persistent sessions instead of one-shot subprocess calls
- **`/api/files`** (line 457): Enhance to return file type icons and grouping information
- **`/api/git/status`** (line 489): Add diff preview data
- **`/api/model-config`** (line 668): Add theme and keybinding configuration storage

### 3.2 `web/index.html` — Enhanced UI with New Features

**File:** `E:\coding-assistant\web\index.html` (1862 lines → ~2800 lines)

#### 3.2.1 New UI Components to Add

1. **Diff Viewer Panel** — Side-by-side or unified diff view with syntax highlighting
   - Add a new dock tab "Diff" in the terminal panel
   - Use a simple diff rendering algorithm (line-by-line comparison)
   - Color-coded additions (green) and deletions (red)
   - Click on a diff line to navigate to the file/line

2. **Enhanced File Explorer** — With type icons and file grouping
   - Update the `file-tree` div to show icons based on file extension
   - Add collapsible folder grouping
   - Add file type filter chips at the top

3. **Breadcrumb Bar** — Above the editor
   - Add a breadcrumb navigation bar between the editor tabs and the editor content
   - Clickable path segments for quick navigation

4. **Find & Replace Panel** — Overlay panel (Ctrl+F / Ctrl+H)
   - Add a find/replace overlay that appears when Ctrl+F is pressed
   - Support regex toggle, case sensitivity toggle, whole word toggle
   - Show match count and navigation arrows
   - Replace all with preview

5. **Code Outline Panel** — In the sidebar or as a panel
   - Add an "Outline" view in the sidebar that shows the AST-derived symbol tree
   - Clicking a symbol navigates to that location in the editor

6. **Diagnostics Panel** — In the sidebar or bottom panel
   - Add a "Problems" view showing linting/diagnostic errors
   - Color-coded severity (error=red, warning=yellow, info=blue)
   - Click to navigate to the error location

7. **Test Runner Panel** — In the bottom panel
   - Add a "Tests" tab in the terminal dock
   - Show test results with pass/fail icons
   - Click on a test to navigate to the test file/line

8. **Debug Panel** — In the bottom panel
   - Add a "Debug" tab with breakpoints list, variables inspector, call stack
   - Debug toolbar with step over, step into, step out, continue buttons

9. **Theme Switcher** — In settings modal
   - Add theme selection dropdown
   - Support dark/light/custom themes
   - Preview theme before applying

10. **Keybinding Reference** — In settings modal
    - Add a keybindings table showing all shortcuts
    - Allow editing keybindings inline

11. **Search & Replace Overlay** — Modal overlay
    - Ctrl+F opens find overlay at top of editor
    - Ctrl+H opens find+replace overlay
    - Ctrl+Shift+H opens replace all

#### 3.2.2 JavaScript Architecture Changes

Add to the existing `<script>` section in `index.html`:

```javascript
// New modules to add to the existing script section:

// Terminal Manager (PTY support)
class TerminalManager {
    constructor(wsUrl) { ... }
    createSession(name) { ... }
    runCommand(sessionId, command) { ... }
    getOutput(sessionId) { ... }
    resize(sessionId, cols, rows) { ... }
    kill(sessionId) { ... }
}

// AST Analyzer Client
class ASTAnalyzerClient {
    constructor(wsUrl) { ... }
    analyzeFile(path) { ... }
    getOutline(path) { ... }
    getDefinition(path, line, col) { ... }
    getReferences(path, line, col) { ... }
    getDiagnostics(path) { ... }
}

// Linter Client
class LinterClient {
    constructor(wsUrl) { ... }
    runLinter(filePath) { ... }
    runAllLinters() { ... }
    getStatus() { ... }
}

// Search Engine Client
class SearchClient {
    constructor(wsUrl) { ... }
    find(query, options) { ... }
    replace(query, replacement, options) { ... }
}

// Diff Viewer
class DiffViewer {
    constructor() { ... }
    showDiff(filePaths) { ... }
    showStagedDiff() { ... }
    showBlame(filePath) { ... }
}

// Theme Manager
class ThemeManager {
    constructor() { ... }
    getThemes() { ... }
    applyTheme(name) { ... }
    createTheme(name, variables) { ... }
}

// Keybinding Manager
class KeybindingManager {
    constructor() { ... }
    getKeybindings() { ... }
    setKeybinding(action, key) { ... }
    handleKeydown(event) { ... }
}

// Project Explorer (enhanced)
class ProjectExplorer {
    constructor() { ... }
    renderFileTree(files) { ... }
    getFileIcon(filePath) { ... }
    groupByType(files) { ... }
    groupByFolder(files) { ... }
}

// Breadcrumb Navigation
class BreadcrumbNav {
    constructor() { ... }
    generate(path) { ... }
    render(items) { ... }
}

// Test Runner Client
class TestRunnerClient {
    constructor(wsUrl) { ... }
    discoverTests() { ... }
    runAllTests() { ... }
    runSingleTest(testPath, testName) { ... }
    getResults() { ... }
}

// Debugger Client
class DebuggerClient {
    constructor(wsUrl) { ... }
    startSession(filePath, breakpoints) { ... }
    stepOver() { ... }
    stepInto() { ... }
    stepOut() { ... }
    continueExecution() { ... }
    getVariables() { ... }
    setBreakpoint(file, line) { ... }
    evaluateExpression(expr) { ... }
}

// IDE Bridge Client
class IDEBridgeClient {
    constructor() { ... }
    detectIDE() { ... }
    getConfig(ideName) { ... }
    syncSettings(ideName, settings) { ... }
}
```

### 3.3 `agent.py` — Enhance Tool System

**File:** `E:\coding-assistant\agent.py` (5131 lines → ~5400 lines)

#### 3.3.1 New Tools to Add to the Tool Registry

Add these tools to `create_tool_registry()` (around line 4262):

1. **`ast_analyze`** — Analyze a file using AST parser
   - Params: `file_path`, `analysis_type` (symbols/outline/definition/references/diagnostics)
   - Returns: AST analysis results

2. **`linter_run`** — Run linter on a file
   - Params: `file_path`, `linter` (optional, auto-detect)
   - Returns: Linting diagnostics

3. **`linter_install`** — Install a linter
   - Params: `linter_name`
   - Returns: Installation status

4. **`debug_start`** — Start a debug session
   - Params: `file_path`, `breakpoints` (optional)
   - Returns: Session ID

5. **`debug_step`** — Step debugger
   - Params: `session_id`, `action` (over/into/out/continue)
   - Returns: Debug state

6. **`debug_variables`** — Get variables in current scope
   - Params: `session_id`
   - Returns: Variable list

7. **`debug_evaluate`** — Evaluate expression
   - Params: `session_id`, `expression`
   - Returns: Evaluation result

8. **`test_run`** — Run tests
   - Params: `workspace`, `test_path` (optional), `test_name` (optional)
   - Returns: Test results

9. **`terminal_create`** — Create a new PTY terminal session
   - Params: `name` (optional)
   - Returns: Session ID

10. **`terminal_run`** — Run command in PTY session
    - Params: `session_id`, `command`
    - Returns: Command output

11. **`terminal_output`** — Get terminal session output
    - Params: `session_id`
    - Returns: Output text

12. **`terminal_kill`** — Kill terminal session
    - Params: `session_id`
    - Returns: Kill status

13. **`search_find`** — Find text across files
    - Params: `query`, `cwd`, `file_pattern`, `use_regex`
    - Returns: Search results with file/line/col

14. **`search_replace`** — Replace text across files
    - Params: `query`, `replacement`, `cwd`, `file_pattern`, `use_regex`
    - Returns: Replace results

15. **`git_diff`** — Get git diff with syntax highlighting
    - Params: `file_path` (optional), `cwd`
    - Returns: Formatted diff

16. **`git_blame`** — Get blame info for a file
    - Params: `file_path`, `cwd`
    - Returns: Blame information

17. **`theme_apply`** — Apply an IDE theme
    - Params: `theme_name`
    - Returns: Theme application status

18. **`keybinding_set`** — Set a keyboard shortcut
    - Params: `action`, `key`
    - Returns: Keybinding status

### 3.4 `rag_vector_engine.py` — Enhance RAG Engine

**File:** `E:\coding-assistant\rag_vector_engine.py` (87 lines → ~250 lines)

#### 3.4.1 Enhancements

1. **Add TF-IDF weighting** to the token overlap scoring
2. **Add chunk overlap** (50% overlap between chunks) for better context
3. **Add metadata indexing** (file type, last modified, import count)
4. **Add incremental indexing** — only re-index changed files
5. **Add BM25 scoring** as an alternative to simple token overlap
6. **Add hybrid search** — combine keyword search with semantic similarity
7. **Add file content caching** to avoid re-reading unchanged files
8. **Add embedding support** — integrate with sentence-transformers for true semantic search (optional, Phase 2)

Key new functions:
- `index_file(file_path: str) -> dict` — Index a single file
- `reindex_changed_files(workspace: str) -> dict` — Re-index only changed files
- `delete_from_index(file_path: str) -> bool` — Remove a file from the index
- `get_index_stats() -> dict` — Get index statistics (file count, chunk count, last indexed)
- `search_with_filters(query: str, file_type: str = None, min_score: float = 0.1) -> list` — Search with filters
- `_compute_tfidf(documents: list) -> dict` — Compute TF-IDF scores
- `_compute_bm25(documents: list, query_tokens: list) -> dict` — Compute BM25 scores
- `_get_file_hash(file_path: str) -> str` — Get file hash for change detection

### 3.5 `workspace_index.py` — Enhance Workspace Indexer

**File:** `E:\coding-assistant\workspace_index.py` (235 lines → ~350 lines)

#### 3.5.1 Enhancements

1. **Add AST-based symbol extraction** for Python files (using the new `ast_analyzer.py`)
2. **Add import graph** — track which files import which other files
3. **Add dependency analysis** — identify project dependencies
4. **Add change detection** — use file hashes to detect changes and only re-index changed files
5. **Add type information** — for TypeScript/JS files, extract type annotations
6. **Add test file detection** — identify which files are test files
7. **Add configuration file detection** — identify package.json, pyproject.toml, etc. and extract relevant info

Key new functions:
- `build_import_graph(workspace: str) -> dict` — Build a file-to-file import graph
- `get_changed_files(workspace: str) -> list[str]` — Get list of changed files since last index
- `get_test_files(workspace: str) -> list[str]` — Get list of test files
- `get_config_info(workspace: str) -> dict` — Extract configuration info from project files
- `get_type_info(file_path: str) -> dict` — Get type information for a file
- `_extract_python_ast_symbols(file_path: str) -> list[SymbolInfo]` — Extract symbols using AST
- `_extract_js_types(file_path: str) -> list[TypeInfo]` — Extract type info from JS/TS files

### 3.6 `setup.py` — One-Click Installer

**File:** `E:\coding-assistant\setup.py` (273 lines → ~400 lines)

#### 3.6.1 Enhancements

1. **Add `pip install devmind` support** — make it installable as a package
2. **Add automatic linter installation** — install pylint, flake8, mypy, ruff by default
3. **Add automatic debugpy installation** — install debugpy for debugging support
4. **Add automatic ptyprocess installation** — install ptyprocess for PTY terminal support
5. **Add automatic pytest installation** — install pytest for test running
6. **Add automatic node/npm detection** — for eslint and other JS linters
7. **Add VS Code extension auto-install** — detect and suggest VS Code extensions
8. **Add theme installation** — pre-install built-in themes
9. **Add desktop shortcut creation** — create desktop shortcuts for easy launch
10. **Add system tray integration** — optional system tray icon for quick access

### 3.7 `web\enhanced_ui.html` — Remove Dead Code or Integrate

**File:** `E:\coding-assistant\web\enhanced_ui.html` (553 lines)

**Action:** This file is currently a dead alternate UI not connected to any routes. Options:
1. **Delete it** — Remove the dead file to clean up the codebase
2. **Integrate it** — Add a route `/enhanced` that serves this file, but this is low priority
3. **Extract useful components** — Pull any useful CSS/JS patterns into `index.html`

**Recommendation:** Delete this file and redirect any references to `index.html`.

---

## 4. Web GUI Design

### 4.1 Layout (Enhanced VS Code-style)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Title Bar: [●][●][●] DevMind AI IDE          Model: gemini-2.5-flash │
├──────┬──────────────────────────────────────────────┬──────────────────┤
│      │                                            │                  │
│ 📁   │  📄 main.py  📄 styles.css  📄 index.html │  💬 Chat Panel   │
│ 🔍   │  📄 agent.py   📄 server.py               │                  │
│ 🌿   │  📄 rag_vector_engine.py                  │  ┌──────────────┐│
│ 💬   │  📄 workspace_index.py                    │  │ User: "Run   ││
│ 🐚   │  📄 plugins.py                            │  │ tests"       ││
│ 📈   │  📄 debugger_server.py                    │  │              ││
│ 🧩   │  📄 linter_engine.py                      │  │ DevMind:     ││
│ 🌙   │                                            │  │ "Running..." ││
│ ⚙️   │  [Breadcrumb: Home > src > main.py]       │  │              ││
│      │                                            │  │ ✓ Test 1     ││
│      │  [Editor: Monaco with AST outline]        │  │ ✗ Test 2     ││
│      │                                           │  │   Error: line││
│      │                                           │  │ 42: undefined││
│      │                                           │  │   Variable x ││
│      │                                           │  │   not defined││
│      │                                           │  └──────────────┘│
│      │                                           │                  │
├──────┴──────────────────────────────────────────────┴──────────────────┤
│ 🟢 Ready │ Model: gemini-2.5-flash │ Tokens: 1,234 │ 📁 E:\coding... │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Activity Bar (Left)

| Icon | Tab | Description |
|------|-----|-------------|
| 📁 | Explorer | File tree with type icons and grouping |
| 🔍 | Search | Find/Replace across files |
| 🌿 | Source Control | Git diff, staged changes, commits |
| 💬 | Chat | AI Agent chat panel |
| 🐚 | Terminal | PTY terminal + Test Runner + Debug |
| 📈 | Problems | Linting diagnostics and errors |
| 📋 | Outline | AST-based code outline/symbol tree |
| 🧩 | Extensions | Extension marketplace |
| ⚙️ | Settings | Theme, keybindings, IDE integration |

### 4.3 Editor Features

1. **Monaco Editor** — Already exists, keep it
2. **AST Outline** — Sidebar panel showing classes, functions, variables with line numbers
3. **Go to Definition** — F12 or Ctrl+Click on a symbol
4. **Find References** — Shift+F12 on a symbol
5. **Find & Replace** — Ctrl+F / Ctrl+H overlay
6. **Diagnostics** — Squiggly underlines for linting errors
7. **Breadcrumbs** — Path navigation above the editor
8. **Minimap** — Already in Monaco, keep it
9. **Multiple Tabs** — Already exists, keep it
10. **Split Editor** — Ctrl+\ to split view
11. **Format Document** — Shift+Alt+F
12. **Comment Line** — Ctrl+/
13. **Quick Fix** — Ctrl+. on error lines

### 4.4 Terminal Features (Enhanced)

1. **Persistent PTY Sessions** — Terminal state persists across commands
2. **Multiple Sessions** — Create named terminal sessions
3. **Session Tabs** — Switch between terminal sessions
4. **Command History** — Up/Down arrow to navigate history
5. **Auto-completion** — Basic command auto-completion
6. **Test Runner Integration** — Run tests and see results in terminal
7. **Debug Console** — Debug output and variable inspection
8. **Resize** — Drag to resize terminal panel

### 4.5 Chat Panel Features (Enhanced)

1. **Model Selection** — Already exists, keep it
2. **Agentic Mode Toggle** — Toggle autonomous agent mode
3. **File Context** — Attach current file to chat context
4. **Terminal Output** — Show terminal output in chat
5. **Diff Preview** — Show git diff in chat
6. **Test Results** — Show test results in chat
7. **Prompt Chips** — Quick action buttons (already exist, enhance)
8. **Streaming Responses** — Already exists, keep it
9. **Tool Call Visualization** — Already exists, keep it
10. **Token Usage** — Already exists, keep it

---

## 5. One-Click Installer Design

### 5.1 `setup.py` — Enhanced Installer

The existing `setup.py` should be enhanced to:

1. **Check prerequisites** — Python 3.10+, Git, Node.js (optional)
2. **Install Python dependencies** — From `requirements.txt` plus new ones
3. **Install linters** — `pylint`, `flake8`, `mypy`, `ruff`
4. **Install debugger** — `debugpy`
5. **Install PTY support** — `ptyprocess` (Unix), `pywin32` (Windows)
6. **Install test runner** — `pytest`
7. **Install search dependencies** — `ripgrep` (optional, for fast search)
8. **Create .devmind directory** — For config, cache, and state
9. **Create desktop shortcut** — For easy launch
10. **Verify installation** — Run self-tests to verify everything works
11. **Start server** — Optionally start the DevMind server after install

### 5.2 New `requirements.txt` additions

```
# Existing
fastapi==0.115.0
uvicorn==0.30.0
httpx==0.27.0
rich==13.9.0
prompt_toolkit==3.0.47
pathspec==0.12.1
gitpython==3.1.43
duckduckgo-search==6.3.0
websockets==13.0
python-multipart==0.0.9
SpeechRecognition==3.10.4
selenium==4.21.0
webdriver-manager==4.0.1

# New for DevMind IDE
pylint==3.0.3
flake8==7.0.0
mypy==1.7.1
ruff==0.1.0
debugpy==1.8.0
ptyprocess==0.7.0
pytest==7.4.4
pexpect==4.9.0
```

### 5.3 `pyproject.toml` — New file for pip installable package

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "devmind-ide"
version = "2.0.0"
description = "DevMind — AI-Powered Coding IDE"
requires-python = ">=3.10"
dependencies = [
    "fastapi==0.115.0",
    "uvicorn==0.30.0",
    "httpx==0.27.0",
    "rich==13.9.0",
    "prompt_toolkit==3.0.47",
    "pathspec==0.12.1",
    "gitpython==3.1.43",
    "duckduckgo-search==6.3.0",
    "websockets==13.0",
    "python-multipart==0.0.9",
    "pylint==3.0.3",
    "flake8==7.0.0",
    "mypy==1.7.1",
    "ruff==0.1.0",
    "debugpy==1.8.0",
    "ptyprocess==0.7.0",
    "pytest==7.4.4",
    "pexpect==4.9.0",
]

[project.scripts]
devmind = "server:main"
devmind-cli = "main:main"

[project.optional-dependencies]
dev = ["pytest", "ruff"]
```

### 5.4 Install Script (`install.bat` / `install.sh`)

```batch
@echo off
echo ════════════════════════════════════════
echo   DevMind IDE — One-Click Installer
echo ════════════════════════════════════════
echo.
echo [1/6] Checking Python 3.10+...
python --version
echo [2/6] Installing dependencies...
pip install -r requirements.txt
echo [3/6] Installing linters...
pip install pylint flake8 mypy ruff
echo [4/6] Installing debugger...
pip install debugpy
echo [5/6] Installing PTY support...
pip install ptyprocess
echo [6/6] Installing test runner...
pip install pytest
echo.
echo Creating .devmind directory...
mkdir "%USERPROFILE%\.devmind" 2>nul
echo.
echo ✓ Installation complete!
echo.
echo Start DevMind with: python server.py
echo Or: uvicorn server:app --host 127.0.0.1 --port 7860
echo.
pause
```

---

## 6. IDE Integration for Cursor, Windsurf, OpenCode

### 6.1 Cursor Integration

**File:** `cursor_integration.py` (new, ~100 lines)

**How it works:**
1. Cursor supports `.cursorrules` files that define custom rules and commands
2. Create a `.cursorrules` file in the workspace root with DevMind commands
3. Add a DevMind command to Cursor's command palette via `cursor/settings.json`

**Integration steps:**
1. Generate `.cursorrules` with DevMind commands:
   ```
   # DevMind IDE Commands
   - "Run DevMind AST Analysis" → devmind ast analyze {file}
   - "Run DevMind Lint" → devmind linter run {file}
   - "Run DevMind Tests" → devmind test run {file}
   - "Run DevMind Debug" → devmind debug start {file}
   - "Open DevMind IDE" → devmind open
   ```
2. Add DevMind to Cursor's MCP servers configuration
3. Create a Cursor extension that communicates with DevMind's WebSocket

### 6.2 Windsurf Integration

**File:** `windsurf_integration.py` (new, ~100 lines)

**How it works:**
1. Windsurf supports MCP (Model Context Protocol) servers
2. Register DevMind as an MCP server in Windsurf's config
3. Windsurf can then call DevMind's tools directly

**Integration steps:**
1. Add DevMind MCP server to `~/.config/windsurf/mcp.json`:
   ```json
   {
     "mcpServers": {
       "devmind": {
         "command": "python",
         "args": ["-m", "devmind.mcp_server"],
         "env": {"DEVMIND_PORT": "7860"}
       }
     }
   }
   ```
2. Create a `devmind/mcp_server.py` that exposes DevMind tools as MCP tools
3. Windsurf can then use DevMind for code analysis, linting, debugging, etc.

### 6.3 OpenCode Integration

**File:** `opencode_integration.py` (new, ~100 lines)

**How it works:**
1. OpenCode supports plugins and custom commands
2. Register DevMind as an OpenCode plugin
3. OpenCode can call DevMind's API for enhanced functionality

**Integration steps:**
1. Create a DevMind plugin for OpenCode:
   ```json
   // ~/.config/opencode/plugins/devmind.json
   {
     "name": "devmind",
     "version": "2.0.0",
     "commands": {
       "devmind-analyze": "devmind ast analyze",
       "devmind-lint": "devmind linter run",
       "devmind-test": "devmind test run",
       "devmind-debug": "devmind debug start"
     }
   }
   ```
2. Modify `~/.config/opencode/user/settings.json` to include DevMind plugin
3. OpenCode can then use DevMind's WebSocket API for real-time collaboration

### 6.4 Shared MCP Server Module

**File:** `mcp_server.py` (new, ~150 lines)

```
Purpose: Expose DevMind's tools as an MCP server
         that Cursor, Windsurf, and OpenCode can all use.
```

Key classes and functions:
- `class DevMindMCPServer`
  - `start()` — Start the MCP server
  - `list_tools() -> list[MCPTool]` — List all available tools
  - `call_tool(name: str, args: dict) -> MCPResult` — Call a tool
- `class MCPTool`
  - `name: str`, `description: str`, `input_schema: dict`, `handler: Callable`
- `class MCPResult`
  - `success: bool`, `data: any`, `error: str | None`

---

## 7. RAG/Vector Index Implementation Details

### 7.1 Current State

The existing `rag_vector_engine.py` uses a simple JSON-based approach with token overlap scoring. It's functional but limited.

### 7.2 Enhanced RAG Architecture

```
┌─────────────────────────────────────────────────────┐
│                 RAG Pipeline                        │
│                                                     │
│  1. File Watcher (detect changes)                   │
│     ↓                                               │
│  2. Document Loader (read file content)             │
│     ↓                                               │
│  3. Chunk Splitter (split into 512-token chunks)    │
│     ↓                                               │
│  4. Embedding Generator (TF-IDF → BM25 → Embedding)│
│     ↓                                               │
│  5. Vector Index (inverted index + embeddings)      │
│     ↓                                               │
│  6. Query Processor (user query → tokens)           │
│     ↓                                               │
│  7. Retriever (top-K similar chunks)                │
│     ↓                                               │
│  8. Re-ranker (cross-encoder re-ranking)            │
│     ↓                                               │
│  9. Context Builder (assemble prompt context)       │
│     ↓                                               │
│ 10. LLM Query (send context to model)               │
└─────────────────────────────────────────────────────┘
```

### 7.3 Index Storage

**File:** `~/.devmind/rag_index/`

```
.devmind/rag_index/
├── index.json           # Main index (inverted index + metadata)
├── embeddings/          # Embedding vectors (Phase 2)
│   ├── file1.npy
│   ├── file2.npy
│   └── ...
├── chunks/              # Chunk storage
│   ├── chunk_001.json
│   ├── chunk_002.json
│   └── ...
├── file_hashes.json     # File hash cache for incremental indexing
└── stats.json           # Index statistics
```

### 7.4 Index Format

```json
{
  "version": "2.0",
  "built_at": "2026-08-04T12:00:00Z",
  "workspace": "E:\\coding-assistant",
  "total_files": 150,
  "total_chunks": 2500,
  "total_tokens": 500000,
  "inverted_index": {
    "token": ["chunk_id_1", "chunk_id_2", ...],
    ...
  },
  "chunks": {
    "chunk_id_1": {
      "file_path": "src/main.py",
      "start_line": 1,
      "end_line": 50,
      "text": "...",
      "tokens": ["def", "main", "import", ...],
      "tfidf_score": 0.85,
      "bm25_score": 0.72,
      "file_type": "python",
      "last_modified": "2026-08-04T10:00:00Z"
    }
  },
  "file_hashes": {
    "src/main.py": "abc123...",
    ...
  }
}
```

### 7.5 Search Algorithm

1. **Tokenize query** — Split query into tokens
2. **BM25 scoring** — Score each chunk using BM25 algorithm
3. **TF-IDF re-ranking** — Re-rank using TF-IDF weights
4. **Context window assembly** — Assemble top-K chunks into context
5. **Deduplication** — Remove duplicate chunks from same file
6. **Truncation** — Truncate to fit within context window

### 7.6 Incremental Indexing

- Watch for file changes using file modification timestamps
- Only re-index files that have changed since last index
- Update the inverted index incrementally
- Periodically compact the index (remove stale entries)

---

## 8. AST Parser and Linter Implementation

### 8.1 AST Parser Implementation

#### Python AST (using built-in `ast` module)

```python
import ast
import inspect

class ASTAnalyzer:
    def analyze_file(self, file_path: str) -> ASTResult:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as e:
            return ASTResult(
                file_path=file_path,
                error=str(e),
                symbols=[],
                diagnostics=[Diagnostic(
                    message=f"SyntaxError: {e.msg}",
                    severity="error",
                    line=e.lineno or 1,
                    column=e.offset or 0,
                    source="ast"
                )]
            )
        
        symbols = self._extract_symbols(tree, file_path)
        diagnostics = self._extract_diagnostics(tree, source, file_path)
        imports = self._extract_imports(tree)
        outline = self._build_outline(tree)
        
        return ASTResult(
            file_path=file_path,
            symbols=symbols,
            diagnostics=diagnostics,
            imports=imports,
            outline=outline,
            total_lines=len(source.splitlines())
        )
    
    def _extract_symbols(self, tree: ast.Module, file_path: str) -> list[Symbol]:
        symbols = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                symbols.append(Symbol(
                    name=node.name,
                    kind="class",
                    line=node.lineno,
                    column=node.col_offset,
                    path=file_path,
                    docstring=ast.get_docstring(node)
                ))
            elif isinstance(node, ast.FunctionDef):
                symbols.append(Symbol(
                    name=node.name,
                    kind="function",
                    line=node.lineno,
                    column=node.col_offset,
                    path=file_path,
                    docstring=ast.get_docstring(node),
                    args=[arg.arg for arg in node.args.args],
                    is_async=isinstance(node, ast.AsyncFunctionDef)
                ))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        symbols.append(Symbol(
                            name=target.id,
                            kind="variable",
                            line=node.lineno,
                            column=target.col_offset,
                            path=file_path
                        ))
        return symbols
    
    def find_definition(self, tree: ast.Module, name: str, line: int, col: int) -> Definition | None:
        """Go-to-definition: find where a symbol is defined."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == name and node.lineno == line:
                    return Definition(
                        name=name,
                        kind="function" if isinstance(node, ast.FunctionDef) else "class",
                        path=node.body[0].lineno if node.body else 0,
                        line=node.lineno,
                        column=node.col_offset
                    )
        return None
    
    def find_references(self, tree: ast.Module, name: str) -> list[Reference]:
        """Find all references to a symbol."""
        references = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == name:
                references.append(Reference(
                    name=name,
                    line=node.lineno,
                    column=node.col_offset,
                    path=tree.body[0].lineno if tree.body else 0
                ))
        return references
    
    def get_outline(self, tree: ast.Module) -> list[OutlineItem]:
        """Build a code outline tree."""
        outline = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                item = OutlineItem(name=node.name, kind="class", line=node.lineno, children=[])
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        item.children.append(OutlineItem(
                            name=child.name,
                            kind="method",
                            line=child.lineno
                        ))
                outline.append(item)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                outline.append(OutlineItem(
                    name=node.name,
                    kind="function",
                    line=node.lineno
                ))
        return outline
```

#### JavaScript/TypeScript AST (via subprocess to Node.js)

For JS/TS files, use `@babel/parser` or `typescript` compiler via subprocess:

```python
def analyze_js_file(self, file_path: str) -> ASTResult:
    result = subprocess.run(
        ["node", "-e", f"""
const parser = require('@babel/parser');
const fs = require('fs');
const code = fs.readFileSync('{file_path}', 'utf-8');
const ast = parser.parse(code, {{
  sourceType: 'module',
  plugins: ['typescript', 'jsx', 'decorators-legacy']
}});
console.log(JSON.stringify(ast, null, 2));
"""],
        capture_output=True, text=True, timeout=30
    )
    # Parse the JSON AST output and extract symbols
    ...
```

### 8.2 Linter Implementation

#### Python Linters

```python
class LinterEngine:
    LINTERS = {
        "pylint": {
            "command": "pylint",
            "args": ["--output-format=json", "{file}"],
            "parser": "json",
            "languages": ["python"],
            "severity_map": {
                "C": "convention",
                "R": "refactor",
                "W": "warning",
                "E": "error",
                "F": "fatal"
            }
        },
        "flake8": {
            "command": "flake8",
            "args": ["--format=json", "{file}"],
            "parser": "json",
            "languages": ["python"]
        },
        "mypy": {
            "command": "mypy",
            "args": ["--show-error-codes", "{file}"],
            "parser": "regex",
            "languages": ["python"],
            "regex": r"^(.+?):(\d+):(\d+):\s+(\w+)\s+(.+)$"
        },
        "ruff": {
            "command": "ruff",
            "args": ["check", "--output-format=json", "{file}"],
            "parser": "json",
            "languages": ["python"]
        }
    }
    
    def run_linter(self, file_path: str, linter_name: str = None) -> list[Diagnostic]:
        if linter_name is None:
            linter_name = self._auto_select_linter(file_path)
        
        linter = self.LINTERS.get(linter_name)
        if not linter:
            return []
        
        if not self._is_installed(linter_name):
            return []
        
        cmd = [linter["command"]] + [arg.format(file=file_path) for arg in linter["args"]]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if linter["parser"] == "json":
            return self._parse_json_output(result.stdout, linter)
        elif linter["parser"] == "regex":
            return self._parse_regex_output(result.stdout, linter)
        
        return []
    
    def _auto_select_linter(self, file_path: str) -> str:
        """Auto-select the best linter for a file."""
        # Prefer ruff (fastest), then pylint, then flake8
        for linter in ["ruff", "pylint", "flake8", "mypy"]:
            if self._is_installed(linter):
                return linter
        return "ruff"
```

#### JS/TS Linters (via ESLint)

```python
# ESLint integration
def run_eslint(file_path: str) -> list[Diagnostic]:
    result = subprocess.run(
        ["npx", "eslint", "--format=json", file_path],
        capture_output=True, text=True, timeout=30
    )
    if result.stdout:
        eslint_results = json.loads(result.stdout)
        diagnostics = []
        for file_result in eslint_results:
            for message in file_result.get("messages", []):
                diagnostics.append(Diagnostic(
                    message=message["message"],
                    severity="error" if message["severity"] == 2 else "warning",
                    line=message["line"],
                    column=message["column"],
                    source="eslint",
                    rule=message.get("ruleId", "")
                ))
        return diagnostics
    return []
```

---

## 9. Terminal Execution with PTY Support

### 9.1 Architecture

```
┌─────────────┐     WebSocket      ┌─────────────┐
│  Browser UI │ ◄─────────────────► │ Terminal     │
│             │                     │ Manager      │
│  Terminal   │                     │              │
│  Panel      │                     │  ┌─────────┐│
│             │                     │  │Session 1││
│  $ command  │                     │  │PTY      ││
│  output     │                     │  │         ││
│             │                     │  └─────────┘│
│             │                     │  ┌─────────┐│
│             │                     │  │Session 2││
│             │                     │  │PTY      ││
│             │                     │  │         ││
│             │                     │  └─────────┘│
└─────────────┘                     └─────────────┘
```

### 9.2 Implementation

```python
import ptyprocess
import os
import signal

class TerminalManager:
    def __init__(self):
        self.sessions: dict[str, ptyprocess.PtyProcess] = {}
        self.session_outputs: dict[str, list[str]] = {}
    
    def create_session(self, name: str = "default") -> str:
        session_id = f"term_{len(self.sessions):04d}"
        try:
            # Create PTY process
            pty = ptyprocess.PtyProcess.spawn(
                ["cmd.exe"] if os.name == "nt" else ["/bin/bash"],
                cwd=os.getcwd(),
                env=os.environ.copy()
            )
            self.sessions[session_id] = pty
            self.session_outputs[session_id] = []
            return session_id
        except Exception as e:
            raise RuntimeError(f"Failed to create terminal session: {e}")
    
    def run_command(self, session_id: str, command: str) -> TerminalResult:
        if session_id not in self.sessions:
            return TerminalResult(output="", error="Session not found", exit_code=-1)
        
        pty = self.sessions[session_id]
        try:
            pty.write(command + "\n")
            # Read output with timeout
            output = ""
            try:
                output = pty.read(1024, timeout=5.0)
            except ptyprocess.ptyprocess.TIMEOUT:
                pass
            
            self.session_outputs[session_id].append(output)
            return TerminalResult(output=output, exit_code=0, running=True)
        except Exception as e:
            return TerminalResult(output="", error=str(e), exit_code=-1)
    
    def get_output(self, session_id: str) -> str:
        return "".join(self.session_outputs.get(session_id, []))
    
    def resize(self, session_id: str, cols: int, rows: int) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].setwinsize(rows, cols)
    
    def kill(self, session_id: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].kill()
            del self.sessions[session_id]
            del self.session_outputs[session_id]
    
    def list_sessions(self) -> list[dict]:
        return [
            {"id": sid, "name": f"Session {i}", "running": True}
            for i, sid in enumerate(self.sessions.keys())
        ]
```

### 9.3 Windows PTY Support

On Windows, `ptyprocess` doesn't work. Use `subprocess` with `CREATE_NEW_PROCESS_GROUP` and `PIPE` for stdout/stderr:

```python
import subprocess
import os

class WindowsTerminalManager:
    def create_session(self, name: str = "default") -> str:
        session_id = f"term_{len(self.sessions):04d}"
        proc = subprocess.Popen(
            ["cmd.exe"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            cwd=os.getcwd()
        )
        self.sessions[session_id] = proc
        return session_id
    
    def run_command(self, session_id: str, command: str) -> TerminalResult:
        proc = self.sessions.get(session_id)
        if not proc:
            return TerminalResult(output="", error="Session not found", exit_code=-1)
        
        proc.stdin.write((command + "\n").encode())
        proc.stdin.flush()
        
        try:
            stdout, stderr = proc.communicate(timeout=5)
            return TerminalResult(
                output=stdout.decode(),
                error=stderr.decode(),
                exit_code=proc.returncode
            )
        except subprocess.TimeoutExpired:
            return TerminalResult(output="", error="Timeout", exit_code=-1, running=True)
```

### 9.4 Cross-Platform Terminal Manager

```python
class CrossPlatformTerminalManager:
    def __init__(self):
        if os.name == "nt":
            self._impl = WindowsTerminalManager()
        else:
            self._impl = UnixTerminalManager()
    
    # Delegate all methods to the platform-specific implementation
    def create_session(self, name="default"): return self._impl.create_session(name)
    def run_command(self, session_id, command): return self._impl.run_command(session_id, command)
    def get_output(self, session_id): return self._impl.get_output(session_id)
    def resize(self, session_id, cols, rows): return self._impl.resize(session_id, cols, rows)
    def kill(self, session_id): return self._impl.kill(session_id)
    def list_sessions(self): return self._impl.list_sessions()
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

**Directory:** `tests/unit/`

| Test File | What It Tests |
|-----------|---------------|
| `test_ast_analyzer.py` | AST parsing, symbol extraction, go-to-definition |
| `test_linter_engine.py` | Linter execution, output parsing, diagnostic generation |
| `test_debugger_server.py` | Debug session management, step execution |
| `test_test_runner.py` | Test discovery, execution, result parsing |
| `test_git_diff_viewer.py` | Diff generation, blame, staged diffs |
| `test_terminal_manager.py` | PTY session creation, command execution |
| `test_search_engine.py` | Find/replace across files, regex support |
| `test_theme_manager.py` | Theme loading, application, CSS variable generation |
| `test_keybinding_manager.py` | Keybinding registration, lookup, export/import |
| `test_extension_api.py` | Extension registration, command execution |
| `test_rag_engine.py` | Indexing, search, incremental updates |
| `test_workspace_index.py` | Index building, symbol extraction, caching |

### 10.2 Integration Tests

**Directory:** `tests/integration/`

| Test File | What It Tests |
|-----------|---------------|
| `test_server_api.py` | All REST API endpoints |
| `test_websocket.py` | WebSocket communication |
| `test_ide_integration.py` | Cursor/Windsurf/OpenCode integration |
| `test_full_workflow.py` | End-to-end workflow (edit → lint → debug → test → commit) |

### 10.3 Test Commands

```bash
# Run all unit tests
python -m pytest tests/unit/ -v --tb=short

# Run all integration tests
python -m pytest tests/integration/ -v --tb=short

# Run specific test module
python -m pytest tests/unit/test_ast_analyzer.py -v

# Run with coverage
python -m pytest tests/ --cov=ast_analyzer --cov=linter_engine --cov=debugger_server

# Run linter on the codebase
ruff check .

# Type check
mypy .

# Format code
ruff format .
```

### 10.4 Test Fixtures

**Directory:** `tests/fixtures/`

```
tests/fixtures/
├── sample_project/
│   ├── main.py          # Sample Python file with functions and classes
│   ├── utils.py         # Sample Python file with imports
│   ├── test_main.py     # Sample test file
│   ├── index.html       # Sample HTML file
│   ├── styles.css       # Sample CSS file
│   └── package.json     # Sample config file
├── test_configs/
│   ├── pylintrc
│   ├── .eslintrc.json
│   └── mypy.ini
└── test_assets/
    ├── theme_dark.json
    ├── theme_light.json
    └── keybindings_default.json
```

### 10.5 CI/CD Integration

Add to `.github/workflows/test.yml`:
```yaml
name: DevMind Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install -e .
      - run: python -m pytest tests/ -v
      - run: ruff check .
      - run: mypy .
```

---

## 11. Implementation Phases

### Phase 1: Core IDE Features (Weeks 1-4)
- [ ] AST analyzer for Python
- [ ] Linter integration (pylint, flake8, ruff)
- [ ] Enhanced file explorer with type icons
- [ ] Breadcrumb navigation
- [ ] Find & Replace across files
- [ ] Code outline/symbol tree
- [ ] Git diff viewer in web UI
- [ ] Enhanced terminal with PTY support

### Phase 2: Advanced Features (Weeks 5-8)
- [ ] Debugger integration (debugpy)
- [ ] Test runner (pytest)
- [ ] Theme manager
- [ ] Keybinding system
- [ ] Search engine (find/replace with regex)
- [ ] RAG engine enhancements (BM25, incremental indexing)
- [ ] Workspace indexer enhancements (AST-based symbols)

### Phase 3: IDE Integrations (Weeks 9-10)
- [ ] Cursor integration
- [ ] Windsurf integration
- [ ] OpenCode integration
- [ ] MCP server module
- [ ] Extension API framework

### Phase 4: Polish & Testing (Weeks 11-12)
- [ ] Unit tests for all new modules
- [ ] Integration tests
- [ ] One-click installer enhancements
- [ ] Documentation
- [ ] Performance optimization
- [ ] Bug fixes

---

## 12. File Structure Summary

```
E:\coding-assistant\
├── server.py                  # Modified: +800 lines (new API routes + WS handlers)
├── main.py                    # Modified: +50 lines (new CLI commands)
├── agent.py                   # Modified: +200 lines (new tools)
├── rag_vector_engine.py       # Modified: +150 lines (BM25, incremental indexing)
├── workspace_index.py         # Modified: +100 lines (AST symbols, import graph)
├── plugins.py                 # Modified: +30 lines (extension API support)
├── requirements.txt           # Modified: +8 new dependencies
├── setup.py                   # Modified: +100 lines (enhanced installer)
├── pyproject.toml             # NEW: pip installable package config
├── ast_analyzer.py            # NEW: AST parsing and analysis engine (~400 lines)
├── linter_engine.py           # NEW: Linter integration engine (~350 lines)
├── debugger_server.py         # NEW: Debugger server (~500 lines)
├── test_runner.py             # NEW: Test runner (~300 lines)
├── git_diff_viewer.py         # NEW: Git diff viewer (~200 lines)
├── terminal_manager.py        # NEW: PTY terminal manager (~350 lines)
├── ide_bridge.py              # NEW: IDE integration bridge (~250 lines)
├── theme_manager.py           # NEW: Theme manager (~200 lines)
├── keybinding_manager.py      # NEW: Keybinding system (~200 lines)
├── extension_api.py           # NEW: Extension API framework (~300 lines)
├── search_engine.py           # NEW: Find/replace engine (~250 lines)
├── breadcrumb_nav.py          # NEW: Breadcrumb navigation (~100 lines)
├── project_explorer.py        # NEW: Enhanced file explorer (~200 lines)
├── mcp_server.py              # NEW: MCP server for IDE integrations (~150 lines)
├── cursor_integration.py      # NEW: Cursor IDE integration (~100 lines)
├── windsurf_integration.py    # NEW: Windsurf IDE integration (~100 lines)
├── opencode_integration.py    # NEW: OpenCode IDE integration (~100 lines)
├── web/
│   ├── index.html             # Modified: +900 lines (new UI components)
│   ├── enhanced_ui.html       # DELETE (dead code)
│   └── themes/                # NEW: Theme CSS files
│       ├── dark.css
│       ├── light.css
│       ├── high-contrast.css
│       ├── monokai.css
│       ├── dracula.css
│       ├── solarized-dark.css
│       └── solarized-light.css
├── tests/
│   ├── unit/
│   │   ├── test_ast_analyzer.py
│   │   ├── test_linter_engine.py
│   │   ├── test_debugger_server.py
│   │   ├── test_test_runner.py
│   │   ├── test_git_diff_viewer.py
│   │   ├── test_terminal_manager.py
│   │   ├── test_search_engine.py
│   │   ├── test_theme_manager.py
│   │   ├── test_keybinding_manager.py
│   │   ├── test_extension_api.py
│   │   ├── test_rag_engine.py
│   │   └── test_workspace_index.py
│   ├── integration/
│   │   ├── test_server_api.py
│   │   ├── test_websocket.py
│   │   └── test_ide_integration.py
│   └── fixtures/
│       ├── sample_project/
│       ├── test_configs/
│       └── test_assets/
└── extensions/                # NEW: Extension storage directory
    └── .devmind/
```

---

## 13. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| AST analysis accuracy | >95% | Symbol extraction correctness |
| Linter coverage | All installed linters | Linter execution success rate |
| Terminal session persistence | >1 hour | Session uptime |
| Find/Replace performance | <100ms for 10k files | Search latency |
| Theme switch time | <50ms | CSS variable application time |
| IDE integration success | All 3 IDEs detect DevMind | Integration test pass rate |
| Memory usage | <500MB RAM | Process memory footprint |
| Startup time | <3 seconds | Server startup time |
| Test pass rate | >90% | Unit + integration test pass rate |
| One-click install success | >95% | Install script success rate |
