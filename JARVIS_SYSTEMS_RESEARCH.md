# 🔍 Jarvis/DevMind Systems Research

## 📊 Real Jarvis System Architecture

Based on code analysis of `E:\coding-assistant` (real Jarvis/DevMind agent)

---

## 🏗️ Core Architecture

### 1. **Backend Server (FastAPI + WebSocket)**
**File**: `server.py`

**Components:**
- FastAPI web server
- WebSocket real-time communication
- Session management
- HTTP API endpoints
- Static file serving
- MCP server integration

**Key Features:**
```python
- WebSocket chat engine
- Session state management
- Ollama tools conversion
- HTTP routes for API
- Static file serving for web UI
```

### 2. **Agent Core (Claude Code Inspired)**
**File**: `agent.py`

**Architecture:**
- Tool-first design (like Claude Code)
- Smart file edit with fuzzy matching
- Security layer for bash commands
- Memory system (MEMORY.md)
- Skills system via markdown files
- Proper tool descriptions

**Model Routing:**
```python
- Multi-tier AI failover engine
- Google Gemini 2.0 Flash
- Groq Llama 3.3 70B
- OpenRouter
- Claude 3.5 Sonnet
- Local Ollama (qwen2.5-coder, llama3)
```

### 3. **CLI Interface (Terminal Experience)**
**File**: `main.py`

**Features:**
- Rich console output
- Markdown rendering
- Interactive prompt with history
- Agent loop execution
- Translation support
- Confirmation callbacks for sensitive commands

---

## 🛠️ Tool System (20+ Tools)

### **File Operations**
1. **read_file** - Read files with line numbers
2. **write_file** - Write/create files
3. **edit_file** - Smart file editing with fuzzy matching
4. **list_files** - List directory contents

### **Development Tools**
5. **bash** - Execute shell commands with security layer
6. **search** - Search files with regex
7. **git** - Git operations (status, commit, push, etc.)
8. **diagnose_code** - Code analysis and diagnostics

### **AI/ML Tools**
9. **memory** - Persistent memory system
10. **skills** - Load and execute skills from markdown
11. **spawn_agent** - Create sub-agents for complex tasks
12. **notebook_edit** - Edit Jupyter notebooks

### **Web/Browser Tools**
13. **web_search** - Web search functionality
14. **browser** - Browser automation (Puppeteer)
15. **analyze_env** - Environment analysis

### **Advanced Tools**
16. **index_project** - Project indexing
17. **semantic_search** - Semantic code search
18. **mcp_tool** - MCP tool integration
19. **restore_last_turn** - Undo last operation
20. **compact_history** - Context management

---

## 🧠 AI Model System

### **Multi-Tier Failover Engine**
```python
MODEL_FAILOVER_CHAIN = [
    "gemini-2.0-flash",      # Primary (Google)
    "gpt-4o-mini",           # Backup 1 (OpenAI)
    "claude-3.5-sonnet",     # Backup 2 (Anthropic)
    "llama3.2:3b",           # Local (Ollama)
    "qwen2.5:3b-instruct"    # Local (Ollama)
]
```

### **Model Dispatch System**
- **Google Gemini API** - Primary choice
- **OpenAI GPT** - Backup option
- **Anthropic Claude** - High-quality backup
- **Groq Llama** - Fast inference
- **OpenRouter** - Multiple model access
- **Local Ollama** - Free, offline option

### **Auto-Switching Logic**
- Detect rate limits/quota errors
- Automatic model switching
- Context preservation during switch
- Error handling and retry logic

---

## 💾 Memory & Context System

### **Memory File System**
```python
MEMORY_FILE = Path.home() / ".devmind" / "MEMORY.md"
MAX_MEM_LINES = 200
MAX_MEM_BYTES = 25000
```

**Features:**
- Persistent cross-session knowledge
- Project-specific memories
- Automatic compaction
- Line and byte limits

### **Skills System**
```python
SKILLS_DIR = Path.home() / ".devmind" / "skills"
```

**Features:**
- Load skills from markdown files
- Execute custom procedures
- Project-specific skills
- Dynamic skill loading

### **Context Management**
- History compaction
- Token usage optimization
- Session-based context
- Memory-backed context

---

## 🔒 Security System

### **Bash Security Layer**
```python
DANGEROUS_BASH_PATTERNS = [
    (r"rm\s+-rf\s+/",          "Deleting root filesystem"),
    (r"mkfs\.",                 "Formatting disk"),
    (r"dd\s+if=.*of=/dev/",    "Writing to raw device"),
    (r">\s*/dev/sd",           "Writing to block device"),
    (r"chmod\s+-R\s+777\s+/", "Insecure permission on root"),
    (r"curl.*\|\s*bash",       "Piping curl to bash (RCE risk)"),
    (r"wget.*\|\s*bash",       "Piping wget to bash (RCE risk)"),
    (r"eval\s+\$\(",           "eval with command substitution"),
    (r":\(\){.*\};:",         "Fork bomb"),
    (r"shutdown|reboot|halt",  "System shutdown command"),
]
```

### **Confirmation System**
- Sensitive command detection
- User confirmation prompts
- Risk explanation
- Safe command execution

---

## 🗄️ Backup & Snapshots

### **File Backup System**
```python
BACKUPS_DIR = Path.home() / ".devmind" / "backups"
SESSION_BACKUPS = []
```

**Features:**
- Automatic file backup before edits
- Session tracking of modifications
- One-click restore (undo)
- Unique backup naming with UUID

### **Snapshot System**
- Pre-edit snapshots
- Rollback capability
- Change tracking
- Recovery from errors

---

## 🌐 MCP Integration

### **MCP Manager**
```python
MCP_CONFIG_FILE = Path.home() / ".devmind" / "mcp_config.json"
```

**Features:**
- Load MCP servers from config
- Start MCP processes
- Register MCP tools
- RPC communication
- Tool execution

### **Supported MCP Servers**
- filesystem (file operations)
- memory (persistent memory)
- sequential-thinking (deep reasoning)
- git (version control)
- sqlite (database)
- ollama (local AI)
- puppeteer (browser automation)
- github (GitHub integration)
- brave-search (web search)

---

## 🌙 Autonomous Task System

### **Task Queue Runner**
**File**: `task_queue_runner.py`

**Features:**
- Scheduled task execution
- Time window enforcement (1 AM - 6 AM)
- Task status tracking
- Retry logic
- Logging and monitoring

### **Task Configuration**
**File**: `tasks.json`

**Current Tasks:**
1. Database Schema Validation
2. Security Audit - SQL Injection
3. Error Log Analysis
4. Code Quality - Dead Code
5. API Endpoint Testing
6. Performance - Database Indexes
7. Documentation Update
8. Dependency Check

---

## 🎨 Web Interface (Control Panel)

### **Frontend Features**
- Monaco Code Editor integration
- Live code diff viewer
- Multi-tab support
- Syntax highlighting
- Inline autocompletion

### **Git Integration**
- Real-time Git status
- File status badges (M, A, D)
- 1-click staging & committing
- Commit history viewer
- Branch management

### **Terminal Integration**
- Interactive terminal
- Colorized output
- Error diagnostics
- Quick action shortcuts
- Command history

---

## 🎙️ Voice Feedback System

### **Voice Narration**
- Real-time voice feedback
- Agent step narration
- File write announcements
- Task completion notifications
- Error voice alerts

---

## 🚀 Setup & Diagnostics

### **1-Click Setup**
**File**: `install.bat`

**Features:**
- Virtual environment creation
- Dependency installation
- API key scanning
- Connectivity verification
- Server startup

### **Setup Wizard**
**File**: `setup_wizard.py`

**Features:**
- System diagnostics
- API key validation
- Environment check
- Configuration testing
- Issue detection

---

## 📊 Project Structure

```
apscodingagentjarvis/
├── server.py              # FastAPI Backend + WebSocket
├── agent.py               # Core Agent Loop + Tool Registry
├── main.py                # CLI Interface
├── task_queue_runner.py   # Autonomous Task Execution
├── setup_wizard.py        # System Diagnostics
├── install.bat            # 1-Click Setup
├── model_failover.py      # Model Switching Logic
├── requirements.txt       # Python Dependencies
├── .env                   # API Keys
├── .devmind/              # User Data Directory
│   ├── MEMORY.md          # Persistent Memory
│   ├── skills/            # Custom Skills
│   ├── backups/           # File Backups
│   ├── mcp_config.json    # MCP Configuration
│   └── history/           # Command History
├── web/
│   └── index.html         # Web UI (Monaco Editor)
└── tasks.json             # Autonomous Task Queue
```

---

## 🎯 Key Capabilities Summary

### **Core Capabilities**
✅ 20+ Built-in Tools
✅ Multi-Model AI Support
✅ Automatic Model Failover
✅ Persistent Memory System
✅ Skills & Custom Procedures
✅ Security Layer
✅ Backup & Restore
✅ MCP Integration
✅ Autonomous Task Execution
✅ Web Interface with Code Editor
✅ Git Integration
✅ Terminal Integration
✅ Voice Feedback
✅ 1-Click Setup

### **Advanced Features**
✅ File Operation Security
✅ Context Management
✅ Translation Support
✅ Sub-agent Spawning
✅ Notebook Editing
✅ Browser Automation
✅ Semantic Search
✅ Project Indexing
✅ Environment Analysis
✅ Nighttime Automation

---

## 🔧 Integration Points

### **OpenCode IDE Integration Potential**
- **MCP Tools**: Already configured for OpenCode
- **Model Management**: Can enhance OpenCode's AI
- **Task Automation**: Can work alongside OpenCode
- **File Operations**: Complementary to OpenCode's editor
- **Git Integration**: Can enhance OpenCode's Git features

### **Current Status**
- ✅ Standalone web interface (localhost:7860)
- ✅ CLI interface (terminal-based)
- ✅ MCP servers configured
- ✅ Model failover system
- ✅ Autonomous task system
- 🔄 OpenCode-specific integration (potential)

---

## 📝 Notes for OpenCode-Focused Strategy

**What Jarvis Already Has:**
- Complete tool ecosystem (20+ tools)
- Multi-model failover
- Autonomous execution
- Memory and skills system
- Security and backup systems

**What Should Be OpenCode-Focused:**
- Use OpenCode as primary IDE
- Jarvis supports OpenCode workflows
- Model management for OpenCode AI
- Task automation around OpenCode
- MCP integration with OpenCode

**Key Insight:**
Jarvis is a complete standalone system. For OpenCode-focused strategy, Jarvis should:
1. Complement OpenCode (not compete)
2. Handle background tasks
3. Manage model switching for OpenCode
4. Provide autonomous coding support
5. Focus on OpenCode workflow optimization

---

**Research Complete**: Real Jarvis has comprehensive systems for autonomous coding with 20+ tools, multi-model support, and advanced features like memory, skills, and security.
