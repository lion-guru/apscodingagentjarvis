# Implementation Plan

## Phase 1: Core Web GUI + CodeMirror 6
- [x] Create CodeMirror 6-based web/index.html
- [x] Add IDE-style layout (activity bar, sidebar, editor, chat, terminal)
- [x] Add file explorer with type icons
- [x] Add chat with codebase context (RAG)
- [x] Add terminal integration with persistent sessions

## Phase 2: AST Parser & Linter
- [x] Create ast_analyzer.py
- [x] Create linter_engine.py
- [x] Add diagnostics panel to web UI
- [x] Add go-to-definition and find references

## Phase 3: RAG & Indexing
- [x] Enhance rag_vector_engine.py with BM25 scoring
- [x] Add incremental indexing with file hash caching
- [x] Add hybrid search pipeline (BM25 + vector)

## Phase 4: Terminal with PTY
- [x] Create terminal_manager.py with persistent sessions
- [x] Add terminal panel to web UI
- [x] Add command history and output streaming

## Phase 5: Inline Editing & Diff Preview
- [x] Add inline edit tool to agent.py
- [x] Add diff preview before applying (accept/decline)
- [x] Add multi-file editing support

## Phase 6: Knowledge Items, Skills & Artifacts
- [x] Create knowledge_items.py
- [x] Create skills/ directory with skill files
- [x] Create artifacts/ directory structure
- [x] Add context management system

## Phase 7: Agentic Coding & Custom Agents
- [x] Add agent_command_center.py
- [x] Add autonomous agent loop to agent.py
- [x] Agent Command Center (Kanban view) in web UI

## Phase 8: MCP Support & IDE Bridges
- [x] Create mcp_server.py
- [x] Create ide_bridge.py for Cursor/Windsurf/OpenCode integration
- [x] Add .cursor/rules/ generation

## Phase 9: One-Click Installer
- [x] Create setup.py with pyproject.toml
- [x] Create install.bat for Windows

## Phase 10: Polish & Testing
- [x] Verify all files compile correctly
- [x] Run final tests