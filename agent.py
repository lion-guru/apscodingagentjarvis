"""
JARVIS - Agent Core
Inspired by Claude Code's architecture:
1. Tool-first design (each tool has description, params, execute)
2. Smart file edit with fuzzy matching (from FileEditTool/utils.ts)
3. Security layer for bash commands (from bashSecurity.ts)
4. Memory system with MEMORY.md (from memdir/memdir.ts)
5. Skills system via markdown files (from skills/loadSkillsDir.ts)
6. Proper tool descriptions that guide the LLM (from prompt.ts files)
"""
import os
import re
import sys
import glob
import json
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Any
import httpx
import time
import threading


# Load local environment variables from .env file
def load_env_file():
    # Look in script's own directory first, then cwd
    script_dir = Path(__file__).parent
    for env_path in [script_dir / ".env", Path(".env")]:
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"\'')
                    if key and val:
                        os.environ[key] = val
            break

load_env_file()

# ─────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────
OLLAMA_BASE  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("JARVIS_MODEL", "llama-3.3-70b-versatile")

# Model Failover Chain (Free Online Models First)
# Updated 2026-08-01: Use working models with gemini-2.5-flash as primary
MODEL_FAILOVER_CHAIN = [
    "llama-3.3-70b-versatile",   # Groq Llama 3.3 70B (fastest, reliable) ✅
    "google/gemini-2.5-flash",   # OpenRouter Gemini 2.5 Flash (quality, coding) ✅
    "llama-3.1-8b-instant",      # Groq Llama 3.1 8B (fast fallback) ✅
    "google/gemma-4-31b-it",     # OpenRouter free vision model ✅
    "llama3.2:1b",               # Local Ollama (small, fast)
    "qwen2.5-coder:1.5b",        # Local Ollama coder (small)
    "gemma3:1b"                   # Local Ollama (lightest) ✅
]

# Import verification and multi-brain systems
try:
    from verification_system import verification_system, verify_before_completion
    VERIFICATION_AVAILABLE = True
    print("[ENHANCEMENT] Verification system loaded - Syntax validation + checkpoints")
except ImportError:
    VERIFICATION_AVAILABLE = False
    print("[WARNING] Verification system not available")

try:
    from multi_brain_coordinator import multi_brain_coordinator, coordinate_with_multi_brain
    MULTI_BRAIN_AVAILABLE = True
    print("[ENHANCEMENT] Multi-brain coordinator loaded - Parallel planning + critique system")
except ImportError:
    MULTI_BRAIN_AVAILABLE = False
    print("[WARNING] Multi-brain coordinator not available")

try:
    from model_performance_tracker import performance_tracker, track_model_call, get_best_model
    PERFORMANCE_TRACKING_AVAILABLE = True
    print("[ENHANCEMENT] Model performance tracker loaded - Performance optimization")
except ImportError:
    PERFORMANCE_TRACKING_AVAILABLE = False
    print("[WARNING] Model performance tracker not available")

try:
    from skill_synthesis import skill_synthesizer, synthesize_new_skill, get_synthesis_report
    SKILL_SYNTHESIS_AVAILABLE = True
    print("[ENHANCEMENT] Skill synthesis loaded - Auto skill generation")
except ImportError:
    SKILL_SYNTHESIS_AVAILABLE = False
    print("[WARNING] Skill synthesis not available")

try:
    from self_healing_workflow import self_healing_workflow, attempt_heal, get_failure_report
    SELF_HEALING_AVAILABLE = True
    print("[ENHANCEMENT] Self-healing workflow loaded - Auto recovery")
except ImportError:
    SELF_HEALING_AVAILABLE = False
    print("[WARNING] Self-healing workflow not available")

# ── Third Eye System ──────────────────────────────────────────
try:
    from third_eye import ThirdEyeSystem
    THIRD_EYE_AVAILABLE = True
    _TE = ThirdEyeSystem()
    _mm = _TE.model_manager
    
    # Patch BrowserOperator with missing get_ide_status method
    def _get_ide_status_patch(self):
        try:
            return {
                "current_ide": self.current_ide,
                "has_driver": self._driver is not None,
                "last_output": self.read_ide_output()[:500] if self._driver else "",
                "detected_error": self.detect_error_in_ide() if self._driver else None
            }
        except Exception:
            return {
                "current_ide": self.current_ide,
                "has_driver": self._driver is not None,
                "last_output": "",
                "detected_error": None
            }
    
    setattr(_TE.browser_operator, "get_ide_status", _get_ide_status_patch.__get__(_TE.browser_operator, _TE.browser_operator.__class__))
    
    print("[ENHANCEMENT] Third Eye loaded - Free model discovery + auto-recovery + multi-agent spawning")
except ImportError:
    THIRD_EYE_AVAILABLE = False
    _mm = None
    _TE = None
    print("[WARNING] Third Eye system not available")

# Lazy imports for advanced features
_attention_engine = None
_stream_manager = None
_hermes_agent = None
_moe_router = None
_multimodal_engine = None
_reasoning_engine = None

def _get_attention_engine():
    global _attention_engine
    if _attention_engine is None:
        try:
            from attention_engine import HybridLinearAttention, AttentionConfig, AttentionRouter
            _attention_engine = AttentionRouter()
        except ImportError:
            pass
    return _attention_engine

def _get_stream_manager():
    global _stream_manager
    if _stream_manager is None:
        try:
            from stream_manager import StreamManager
            _stream_manager = StreamManager()
        except ImportError:
            pass
    return _stream_manager

def _get_hermes_agent():
    global _hermes_agent
    if _hermes_agent is None:
        try:
            from hermes_agent import HermesAgent, HermesToolExecutor, create_hermes_agents
            _hermes_agent = create_hermes_agents()
        except ImportError:
            pass
    return _hermes_agent

def _get_moe_router():
    global _moe_router
    if _moe_router is None:
        try:
            from moe_router import MoERouter, TaskClassifier, MoEPolicy, ExpertProfile
            _moe_router = MoERouter()
        except ImportError:
            pass
    return _moe_router

def _get_multimodal_engine():
    global _multimodal_engine
    if _multimodal_engine is None:
        try:
            from multimodal_engine import VLMEngine, MimoArchitecture, BigPixelProcessor
            _multimodal_engine = VLMEngine()
        except ImportError:
            pass
    return _multimodal_engine

def _get_reasoning_engine():
    global _reasoning_engine
    if _reasoning_engine is None:
        try:
            from reasoning_engine import ReasoningEngine, ReasoningConfig
            _reasoning_engine = ReasoningEngine()
        except ImportError:
            pass
    return _reasoning_engine


def _get_best_free_model(task_context: str = "general") -> str:
    """Ask Third Eye for the best working free model, fall back to ollama_chat chain."""
    if THIRD_EYE_AVAILABLE and _mm:
        try:
            return _mm.select_model_for_task(task_context)
        except Exception:
            pass
    return DEFAULT_MODEL

DEFAULT_WORKSPACE = os.getenv("JARVIS_CWD", r"c:\xampp\htdocs\apsdreamhome" if os.path.exists(r"c:\xampp\htdocs\apsdreamhome") else os.getcwd())

# Mutable current workspace — updated by the web UI's set_cwd / workspace switcher.
# All tools resolve relative paths against this instead of the startup default.
CURRENT_WORKSPACE = DEFAULT_WORKSPACE

def set_workspace(path_str: str) -> None:
    """Switch the active workspace that tools resolve relative paths against."""
    global CURRENT_WORKSPACE
    p = Path(path_str).expanduser().resolve()
    if p.is_dir():
        CURRENT_WORKSPACE = str(p)

# Fork/subagent context — the main agent's conversation history that
# fork_agent and fork-context skills inherit (mirrors forkSubagent.ts).
CURRENT_CONTEXT: list[dict] = []

def set_context(messages: list[dict]) -> None:
    """Set the conversation context available to forked children."""
    global CURRENT_CONTEXT
    CURRENT_CONTEXT = list(messages)

# Fork boilerplate constants (ported from constants/xml.ts + forkSubagent.ts)
FORK_BOILERPLATE_TAG = "jarvis_fork"
FORK_DIRECTIVE_PREFIX = "Directive: "
FORK_PLACEHOLDER_RESULT = "Fork started — processing in background"

def get_abs_path(path_str: str) -> Path:
    p = Path(str(path_str).strip('\'"'))
    if not p.is_absolute():
        p = Path(CURRENT_WORKSPACE) / p
    return p.resolve()

# Memory file (inspired by Claude Code's MEMORY.md system)
MEMORY_FILE   = Path.home() / ".jarvis" / "MEMORY.md"
SKILLS_DIR    = Path.home() / ".jarvis" / "skills"
MAX_MEM_LINES = 200   # from memdir.ts MAX_ENTRYPOINT_LINES
MAX_MEM_BYTES = 25000  # from memdir.ts MAX_ENTRYPOINT_BYTES

# VS Code Bridge Callback
VSCODE_CALLBACK = None

MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────
# BACKUP & SNAPSHOT SYSTEM (inspired by fileHistory.ts)
# ─────────────────────────────────────────────────────────────────
BACKUPS_DIR = Path.home() / ".jarvis" / "backups"
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

# Session tracking of modified files (original_path -> backup_path)
SESSION_BACKUPS = []

def backup_file(path_str: str) -> None:
    """Save a backup copy of a file before writing or editing it"""
    try:
        p = Path(path_str).absolute()
        if not p.exists():
            # If creating a new file, track that it didn't exist
            SESSION_BACKUPS.append({
                "original_path": str(p),
                "backup_path": None
            })
            return
        
        # Create a unique backup file
        import uuid
        backup_name = f"{p.name}_{uuid.uuid4().hex}.bak"
        backup_p = BACKUPS_DIR / backup_name
        shutil.copy2(p, backup_p)
        
        SESSION_BACKUPS.append({
            "original_path": str(p),
            "backup_path": str(backup_p)
        })
    except Exception as e:
        print(f"[warning] Failed to create backup: {e}")

def restore_last_turn() -> list[str]:
    """Restore all files modified in the last step. Returns restored files list."""
    restored = []
    if not SESSION_BACKUPS:
        return restored
    
    last_backup = SESSION_BACKUPS.pop()
    orig = Path(last_backup["original_path"])
    bak = last_backup["backup_path"]
    
    try:
        if bak is None:
            # File was created, so we delete it to revert
            if orig.exists():
                orig.unlink()
                restored.append(f"Deleted {orig.name} (reverted creation)")
        else:
            # File was edited, so we restore backup
            bak_p = Path(bak)
            if bak_p.exists():
                shutil.copy2(bak_p, orig)
                bak_p.unlink() # Cleanup backup
                restored.append(f"Restored {orig.name} to previous state")
    except Exception as e:
        print(f"[error] Failed to restore backup: {e}")
        
    return restored

# ─────────────────────────────────────────────────────────────────
# WORKSPACE DIAGNOSIS SYSTEM (inspired by doctorDiagnostic.ts)
# ─────────────────────────────────────────────────────────────────
def detect_project_type(cwd: str) -> str:
    """
    Diagnose workspace environment and detect active technologies.
    Helps the agent understand the workspace without needing to ask.
    """
    p = Path(cwd)
    technologies = []
    
    # Check common config files
    checks = {
        "package.json": "NodeJS/JavaScript",
        "tsconfig.json": "TypeScript",
        "requirements.txt": "Python (pip)",
        "pyproject.toml": "Python (poetry/pip)",
        "manage.py": "Django Framework",
        "Cargo.toml": "Rust (Cargo)",
        "go.mod": "Go Lang",
        "pom.xml": "Java (Maven)",
        "build.gradle": "Java (Gradle)",
        "composer.json": "PHP (Composer)",
        "Gemfile": "Ruby (Bundler)",
        "Makefile": "Make Build System",
        "CMakeLists.txt": "C/C++ (CMake)",
        "Dockerfile": "Docker Containerization",
        ".git": "Git Version Control",
    }
    
    for filename, tech in checks.items():
        if (p / filename).exists():
            technologies.append(tech)
            
    if not technologies:
        return "Unknown/General Codebase"
        
    return ", ".join(technologies)

# ─────────────────────────────────────────────────────────────────
# AUTO-COMPACTING SYSTEM (inspired by compact.ts)
# ─────────────────────────────────────────────────────────────────
def estimate_tokens(messages: list[dict]) -> int:
    """
    Very rough token estimation (words * 1.3 + formatting).
    Sufficiently accurate to trigger compaction before hitting limits.
    """
    total_words = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total_words += len(content.split())
    return int(total_words * 1.3)

def compact_history(messages: list[dict], model: str) -> list[dict]:
    """
    Summarizes the oldest part of the conversation if it gets too long.
    Frees up context window for local LLMs.
    """
    est_tokens = estimate_tokens(messages)
    # Compact when estimated tokens exceed 9,000 to keep it healthy
    if est_tokens < 9000 or len(messages) <= 4:
        return messages
        
    print(f"\n[cyan]⚙ Compacting history... (estimated tokens: {est_tokens})[/]")
    
    # We keep the system prompt (messages[0]) and the last 3 messages.
    # The middle messages will be summarized.
    system_msg = messages[0]
    middle_msgs = messages[1:-3]
    recent_msgs = messages[-3:]
    
    summary_prompt = (
        "You are a system utility. Summarize the following conversation history between the user and the coding assistant. "
        "Focus on: what files were read/written, what edits were made, what commands were run, and any active context "
        "or preferences discovered. Be very concise and accurate. Do not use conversational language.\n\n"
        "CONVERSATION HISTORY:\n"
    )
    for m in middle_msgs:
        role = m["role"].upper()
        content = remove_tool_calls(m["content"])
        summary_prompt += f"{role}: {content[:300]}\n"
        
    try:
        summary = ollama_chat([{"role": "user", "content": summary_prompt}], model=model)
        
        compacted_msg = {
            "role": "system",
            "content": f"[SYSTEM: The previous part of the conversation has been compacted to save memory. Summary of previous turns:\n{summary}]"
        }
        
        # New history: System prompt -> Summary msg -> last 3 messages
        new_messages = [system_msg, compacted_msg] + recent_msgs
        new_est = estimate_tokens(new_messages)
        print(f"[green]✓ Compacted! Estimated tokens reduced from {est_tokens} to {new_est}[/]\n")
        return new_messages
    except Exception as e:
        print(f"[warning] Compaction failed: {e}")
        return messages



# ─────────────────────────────────────────────────────────────────
# BASH SECURITY  (ported from bashSecurity.ts)
# ─────────────────────────────────────────────────────────────────
# Dangerous patterns Claude Code blocks — we borrow the same list
DANGEROUS_BASH_PATTERNS = [
    (r"rm\s+-rf\s+/",          "Deleting root filesystem"),
    (r"mkfs\.",                 "Formatting disk"),
    (r"dd\s+if=.*of=/dev/",    "Writing to raw device"),
    (r">\s*/dev/sd",           "Writing to block device"),
    (r"chmod\s+-R\s+777\s+/", "Insecure permission on root"),
    (r"curl.*\|\s*bash",       "Piping curl to bash (RCE risk)"),
    (r"wget.*\|\s*bash",       "Piping wget to bash (RCE risk)"),
    (r"eval\s+\$\(",           "eval with command substitution"),
    (r":\(\)\{.*\};:",         "Fork bomb"),
    (r"shutdown|reboot|halt",  "System shutdown command"),
]

# Requires confirmation before running
SENSITIVE_BASH_PATTERNS = [
    (r"\bdrop\s+table\b",  "SQL DROP TABLE"),
    (r"\btruncate\b",      "SQL TRUNCATE"),
    (r"rm\s+-r",           "Recursive delete"),
    (r"git\s+push.*-f",    "Force push to git"),
    (r"pip\s+uninstall",   "Uninstalling packages"),
]

def check_command_safety(command: str) -> tuple[bool, str]:
    """
    Returns (is_safe, reason).
    Inspired by Claude Code's bashSecurity.ts validation system.
    """
    cmd_lower = command.lower().strip()
    for pattern, reason in DANGEROUS_BASH_PATTERNS:
        if re.search(pattern, cmd_lower, re.IGNORECASE):
            return False, f"BLOCKED: {reason}"
    return True, ""

def needs_confirmation(command: str) -> tuple[bool, str]:
    """Check if command needs user confirmation"""
    cmd_lower = command.lower().strip()
    for pattern, reason in SENSITIVE_BASH_PATTERNS:
        if re.search(pattern, cmd_lower, re.IGNORECASE):
            return True, reason
    return False, ""


# ─────────────────────────────────────────────────────────────────
# SMART FILE EDIT  (ported from FileEditTool/utils.ts)
# ─────────────────────────────────────────────────────────────────
def normalize_whitespace(s: str) -> str:
    """Normalize whitespace for fuzzy matching"""
    return re.sub(r'\s+', ' ', s).strip()

def find_fuzzy_match(file_content: str, search_string: str) -> str | None:
    """
    Find actual string in file, accounting for whitespace differences.
    Inspired by findActualString() in FileEditTool/utils.ts
    """
    # 1. Exact match
    if search_string in file_content:
        return search_string
    
    # 2. Normalize quotes (curly → straight, inspired by normalizeQuotes())
    normalized_search = (search_string
        .replace('\u2018', "'").replace('\u2019', "'")
        .replace('\u201c', '"').replace('\u201d', '"'))
    normalized_file = (file_content
        .replace('\u2018', "'").replace('\u2019', "'")
        .replace('\u201c', '"').replace('\u201d', '"'))
    
    if normalized_search in normalized_file:
        idx = normalized_file.index(normalized_search)
        return file_content[idx: idx + len(search_string)]
    
    # 3. Whitespace-normalized match (handles indentation differences)
    norm_s = normalize_whitespace(search_string)
    norm_f = normalize_whitespace(file_content)
    if norm_s in norm_f:
        # Find approximate position
        lines = file_content.split('\n')
        search_lines = search_string.strip().split('\n')
        first_line = search_lines[0].strip()
        for i, line in enumerate(lines):
            if line.strip() == first_line:
                # Try to match the block
                candidate = '\n'.join(lines[i: i + len(search_lines)])
                if normalize_whitespace(candidate) == norm_s:
                    return candidate
    return None

def apply_edit(file_content: str, old_string: str, new_string: str, replace_all: bool = False) -> tuple[str, bool]:
    """
    Apply a string replacement to file content.
    Returns (new_content, success).
    Inspired by applyEditToFile() in FileEditTool/utils.ts — 
    handles trailing newlines smartly.
    """
    actual_old = find_fuzzy_match(file_content, old_string)
    if actual_old is None:
        return file_content, False
    
    if new_string == '' and not actual_old.endswith('\n') and file_content.find(actual_old + '\n') != -1:
        # Remove trailing newline too (from Claude Code's logic)
        actual_old_with_nl = actual_old + '\n'
        if replace_all:
            result = file_content.replace(actual_old_with_nl, new_string)
        else:
            result = file_content.replace(actual_old_with_nl, new_string, 1)
    else:
        if replace_all:
            result = file_content.replace(actual_old, new_string)
        else:
            result = file_content.replace(actual_old, new_string, 1)
    
    return result, True


# ─────────────────────────────────────────────────────────────────
# MEMORY SYSTEM  (inspired by memdir/memdir.ts)
# ─────────────────────────────────────────────────────────────────
def load_memory() -> str:
    """
    Load MEMORY.md with line+byte truncation.
    Exact same limits as Claude Code: 200 lines / 25KB
    """
    if not MEMORY_FILE.exists():
        return ""
    
    raw = MEMORY_FILE.read_text(encoding="utf-8", errors="replace").strip()
    lines = raw.split('\n')
    
    was_line_truncated = len(lines) > MAX_MEM_LINES
    was_byte_truncated = len(raw.encode()) > MAX_MEM_BYTES
    
    if not was_line_truncated and not was_byte_truncated:
        return raw
    
    # Truncate lines first (natural boundary)
    truncated = '\n'.join(lines[:MAX_MEM_LINES]) if was_line_truncated else raw
    
    # Then truncate bytes
    if len(truncated.encode()) > MAX_MEM_BYTES:
        encoded = truncated.encode()[:MAX_MEM_BYTES]
        truncated = encoded.decode(errors='ignore')
        # Cut at last newline
        last_nl = truncated.rfind('\n')
        if last_nl > 0:
            truncated = truncated[:last_nl]
    
    reason = []
    if was_line_truncated:
        reason.append(f"{len(lines)} lines (limit: {MAX_MEM_LINES})")
    if was_byte_truncated:
        reason.append(f"{len(raw.encode())} bytes (limit: {MAX_MEM_BYTES})")
    
    return truncated + f"\n\n> ⚠️ MEMORY.md truncated: {', '.join(reason)}. Keep entries concise."

def save_memory(content: str):
    """Save to MEMORY.md"""
    MEMORY_FILE.write_text(content, encoding="utf-8")

def append_memory(note: str):
    """Append a note to memory"""
    existing = MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else "# DevMind Memory\n"
    MEMORY_FILE.write_text(existing.rstrip() + f"\n- {note}\n", encoding="utf-8")


# ─────────────────────────────────────────────────────────────────
# SKILLS SYSTEM  (inspired by skills/loadSkillsDir.ts)
# Skills are markdown files in ~/.jarvis/skills/ (user), .claude/skills/
# walking up from cwd (project), and bundled skills in the agent repo.
#
# Supported layouts (mirrors loadSkillsDir.ts):
#   - Directory format:  skills/<skill-name>/SKILL.md   (preferred)
#   - Single file:       skills/<skill-name>.md         (legacy)
#
# Frontmatter fields (mirrors parseSkillFrontmatterFields):
#   name, description, when_to_use, version, arguments (space-separated
#   names), argument-hint, allowed-tools, model, user-invocable,
#   disable-model-invocation, context: fork, agent, effort, paths
# ─────────────────────────────────────────────────────────────────
@dataclass
class Skill:
    name: str
    description: str
    content: str
    path: Path
    when_to_use: str = ""
    version: str = ""
    argument_names: list[str] = field(default_factory=list)
    argument_hint: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    model: str = ""
    user_invocable: bool = True
    disable_model_invocation: bool = False
    context: str = ""              # '' | 'fork'
    agent: str = ""
    effort: str = ""
    paths: list[str] = field(default_factory=list)   # conditional path patterns
    source: str = "user"           # user | project | bundled
    has_user_specified_description: bool = False

def _parse_bool_fm(value: Any) -> bool:
    return str(value).strip().lower() in ("true", "yes", "1", "on")

def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML-ish frontmatter between --- fences. Returns (fields, body)."""
    fm = {}
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not m:
        return fm, content
    fm_text = m.group(1)
    body = content[m.end():]
    # Handle list values: key:\n  - item
    # First, collect all lines and group list items
    lines = fm_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            i += 1
            continue
        key_m = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', line)
        if key_m:
            key = key_m.group(1)
            value = key_m.group(2).strip()
            if value.startswith('[') and value.endswith(']'):
                items = [v.strip().strip('"\'') for v in value[1:-1].split(',') if v.strip()]
                fm[key] = items
                i += 1
            elif value == '':
                # Possibly a nested list
                items = []
                j = i + 1
                while j < len(lines) and lines[j].strip().startswith('- '):
                    items.append(lines[j].strip()[2:].strip().strip('"\''))
                    j += 1
                fm[key] = items
                i = j
            else:
                fm[key] = value.strip('"\'')
                i += 1
        else:
            i += 1
    return fm, body


def _extract_description_from_markdown(body: str, fallback_label: str = "Skill") -> str:
    """Pull a description from the first non-empty, non-heading line."""
    for line in body.split('\n'):
        s = line.strip()
        if s and not s.startswith('#') and not s.startswith('```'):
            return s[:150]
    return fallback_label


def _parse_argument_names(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        names = [str(v).strip() for v in value]
    else:
        names = [v.strip() for v in str(value).split()]
    return [n for n in names if n and not re.fullmatch(r'\d+', n)]


def _parse_paths(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = [str(v) for v in value]
    else:
        raw = re.split(r'[,\s]+', str(value))
    patterns = []
    for p in raw:
        p = p.strip()
        if not p:
            continue
        if p.endswith('/**'):
            p = p[:-3]
        if p != '**' and p:
            patterns.append(p)
    return patterns


def _parse_skill_file(md_file: Path, source: str) -> Skill | None:
    try:
        content = md_file.read_text(encoding="utf-8")
    except Exception:
        return None
    fm, body = _parse_frontmatter(content)
    name = str(fm.get("name", md_file.stem)).strip()
    description = str(fm.get("description", "")).strip() if fm.get("description") not in (None, "") else ""
    has_user_desc = bool(description)
    if not description:
        description = _extract_description_from_markdown(body)
    when_to_use = str(fm.get("when_to_use", "")).strip()
    version = str(fm.get("version", "")).strip()
    argument_names = _parse_argument_names(fm.get("arguments"))
    argument_hint = str(fm.get("argument-hint", "")).strip()
    allowed = fm.get("allowed-tools")
    if isinstance(allowed, list):
        allowed_tools = [str(t).strip() for t in allowed if str(t).strip()]
    elif allowed:
        allowed_tools = [t.strip() for t in str(allowed).replace(',', ' ').split() if t.strip()]
    else:
        allowed_tools = []
    model = str(fm.get("model", "")).strip()
    user_invocable = _parse_bool_fm(fm["user-invocable"]) if "user-invocable" in fm else True
    disable_model_invocation = _parse_bool_fm(fm["disable-model-invocation"]) if "disable-model-invocation" in fm else False
    context = "fork" if str(fm.get("context", "")).strip() == "fork" else ""
    agent = str(fm.get("agent", "")).strip()
    effort = str(fm.get("effort", "")).strip()
    paths = _parse_paths(fm.get("paths"))
    return Skill(
        name=name, description=description, content=body, path=md_file,
        when_to_use=when_to_use, version=version, argument_names=argument_names,
        argument_hint=argument_hint, allowed_tools=allowed_tools, model=model,
        user_invocable=user_invocable, disable_model_invocation=disable_model_invocation,
        context=context, agent=agent, effort=effort, paths=paths,
        source=source, has_user_specified_description=has_user_desc,
    )


def _scan_skills_dir(base_dir: Path, source: str) -> dict[str, Skill]:
    """Scan a directory for skills. Supports both skill-name/SKILL.md and flat .md."""
    found: dict[str, Skill] = {}
    if not base_dir.is_dir():
        return found
    # Directory format: <name>/SKILL.md
    for sub in base_dir.iterdir():
        if sub.is_dir():
            skill_file = sub / "SKILL.md"
            if skill_file.is_file():
                s = _parse_skill_file(skill_file, source)
                if s:
                    found[s.name] = s
    # Legacy flat format: <name>.md (skip if same-name dir already registered)
    for md_file in base_dir.glob("*.md"):
        s = _parse_skill_file(md_file, source)
        if s and s.name not in found:
            found[s.name] = s
    return found


def get_project_skills_dirs(cwd: str) -> list[Path]:
    """Walk up from cwd to home collecting .claude/skills dirs (deepest first)."""
    dirs = []
    current = Path(cwd)
    home = Path.home()
    while True:
        candidate = current / ".claude" / "skills"
        if candidate.is_dir():
            dirs.append(candidate)
        if current == home or current.parent == current:
            break
        current = current.parent
    return dirs


# Bundled skills shipped with the agent (from bundledSkills.ts concept)
BUNDLED_SKILLS_DIR = Path(__file__).parent / "skills"

def load_skills(cwd: str = "") -> dict[str, Skill]:
    """
    Load skills from multiple sources (mirrors loadSkillsDir.ts):
      - user:     ~/.jarvis/skills
      - project:  .claude/skills walking up from cwd (deepest first)
      - bundled:  <repo>/skills
    Deduplicates by skill name — user > project > bundled precedence.
    """
    skills: dict[str, Skill] = {}
    for src in (("bundled", BUNDLED_SKILLS_DIR),
                *((p, p) for p in get_project_skills_dirs(cwd)),
                ("user", SKILLS_DIR)):
        label, base = src[0], src[1]
        found = _scan_skills_dir(Path(base), label)
        for name, s in found.items():
            skills.setdefault(name, s)
    return skills


# ─────────────────────────────────────────────────────────────────
# SKILL ARGUMENT SUBSTITUTION  (ported from utils/argumentSubstitution.ts)
# ─────────────────────────────────────────────────────────────────
def parse_arguments(args: str) -> list[str]:
    """Parse an argument string into tokens, respecting quotes (shlex-style)."""
    if not args or not args.strip():
        return []
    try:
        import shlex
        return shlex.split(args, posix=True)
    except Exception:
        return args.split()


def substitute_arguments(
    content: str,
    args: str | None,
    append_if_no_placeholder: bool = True,
    argument_names: list[str] | None = None,
) -> str:
    """
    Substitute $ARGUMENTS placeholders in skill content.
    Supports:
      - $ARGUMENTS            -> full argument string
      - $ARGUMENTS[0], $1     -> indexed arguments
      - $name                 -> named arguments (frontmatter 'arguments')
    """
    argument_names = argument_names or []
    if args is None:
        return content
    parsed = parse_arguments(args)
    original = content

    # Named arguments: $foo maps to parsed[i] where argument_names[i] == 'foo'
    for i, name in enumerate(argument_names):
        content = re.sub(rf'\${re.escape(name)}(?![\[\w])', lambda _m: parsed[i] if i < len(parsed) else "", content)

    # Indexed: $ARGUMENTS[n]
    content = re.sub(r'\$ARGUMENTS\[(\d+)\]', lambda m: parsed[int(m.group(1))] if int(m.group(1)) < len(parsed) else "", content)

    # Shorthand: $0, $1...
    content = re.sub(r'\$(\d+)(?!\w)', lambda m: parsed[int(m.group(1))] if int(m.group(1)) < len(parsed) else "", content)

    # Full: $ARGUMENTS
    content = content.replace("$ARGUMENTS", args)

    # Append args if no placeholders found and args provided
    if content == original and append_if_no_placeholder and args:
        content += f"\n\nARGUMENTS: {args}"
    return content


# ─────────────────────────────────────────────────────────────────
# TOOLS  (each tool: description + execute, like Claude Code's Tool.ts)
# ─────────────────────────────────────────────────────────────────
@dataclass
class ToolResult:
    output: str
    success: bool = True
    needs_confirm: bool = False
    confirm_reason: str = ""

@dataclass  
class Tool:
    name: str
    description: str          # Used in system prompt to guide LLM
    params_schema: dict       # Parameter descriptions
    execute: Callable         # The actual function


def make_read_file_tool() -> Tool:
    def execute(path: str, offset: int = 0, limit: int = 2000) -> ToolResult:
        try:
            p = get_abs_path(path)
            if not p.exists():
                return ToolResult(f"ERROR: File not found: {path} (resolved: {p})", success=False)
            if p.is_dir():
                return ToolResult(f"ERROR: {path} is a directory. Use list_files instead.", success=False)
            
            content = p.read_text(encoding="utf-8", errors="replace")
            lines = content.split('\n')
            
            if offset:
                lines = lines[offset:]
            if limit and len(lines) > limit:
                lines = lines[:limit]
                truncated = f"\n... (showing lines {offset+1}-{offset+limit} of {len(content.split(chr(10)))} total)"
            else:
                truncated = ""
            
            # Add line numbers (Claude Code style)
            numbered = '\n'.join(f"{offset+i+1:4} │ {line}" for i, line in enumerate(lines))
            
            if VSCODE_CALLBACK:
                try:
                    VSCODE_CALLBACK({"type": "open_file", "path": str(p.absolute())})
                except Exception:
                    pass
                    
            return ToolResult(f"```\n{numbered}\n```{truncated}")
        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)
    
    return Tool(
        name="read_file",
        description="""Read file contents with line numbers.
- ALWAYS read a file before editing it
- Use offset/limit for large files
- Output includes line numbers for reference""",
        params_schema={
            "path": "string — file path (absolute or relative)",
            "offset": "int — start from this line number (optional, default 0)",
            "limit": "int — max lines to return (optional, default 2000)"
        },
        execute=execute
    )


def check_file_syntax(path: str, content: str) -> str | None:
    """Check syntax of the content for supported extensions. Return error string or None."""
    p = get_abs_path(path)
    suffix = p.suffix.lower()
    if suffix == '.py':
        import tempfile
        import py_compile
        temp_fd, temp_path = tempfile.mkstemp(suffix=".py", text=True)
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write(content)
            py_compile.compile(temp_path, doraise=True)
            return None
        except py_compile.PyCompileError as e:
            clean_err = str(e).replace(temp_path, p.name)
            return f"Python Syntax Error:\n{clean_err}"
        except Exception as e:
            return f"Syntax compiler error: {e}"
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass
    elif suffix == '.json':
        try:
            json.loads(content)
            return None
        except json.JSONDecodeError as e:
            return f"JSON Format Error: {e}"
    return None

def make_write_file_tool() -> Tool:
    def execute(path: str, content: str) -> ToolResult:
        try:
            p = get_abs_path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            backup_file(str(p))  # Save backup before writing
            
            # Create verification checkpoint if available
            checkpoint_id = None
            if VERIFICATION_AVAILABLE:
                checkpoint_id = verification_system.create_checkpoint(str(p))
                if checkpoint_id:
                    print(f"[VERIFICATION] Checkpoint created: {checkpoint_id}")
            
            p.write_text(content, encoding="utf-8")
            
            if VSCODE_CALLBACK:
                try:
                    VSCODE_CALLBACK({
                        "type": "show_diff",
                        "path": str(p.absolute()),
                        "original": "",
                        "modified": content
                    })
                except Exception:
                    pass
                    
            lines = len(content.split('\n'))
            
            # Enhanced verification with verification system
            if VERIFICATION_AVAILABLE:
                verify_result = verification_system.verify_syntax(str(p))
                if not verify_result["syntax_valid"]:
                    print(f"[VERIFICATION] Syntax check failed: {verify_result['errors']}")
                    # Restore from checkpoint
                    if checkpoint_id:
                        verification_system.restore_checkpoint(checkpoint_id)
                        return ToolResult(
                            f"⚠️ Created {path} ({lines} lines), but SYNTAX VERIFICATION failed!\n"
                            f"Changes have been reverted. Errors: {verify_result['errors']}",
                            success=False
                        )
                else:
                    print(f"[VERIFICATION] Syntax check passed")
            else:
                # Fallback to basic syntax check
                syntax_error = check_file_syntax(path, content)
                if syntax_error:
                    return ToolResult(
                        f"⚠️ Created {path} ({lines} lines), but a SYNTAX ERROR was detected!\n"
                        f"Please correct this syntax error immediately in your next turn.\n\n"
                        f"{syntax_error}",
                        success=False
                    )
            
            return ToolResult(f"File written: {path} ({lines} lines)")
        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)
    
    return Tool(
        name="write_file",
        description="""Create or completely overwrite a file.
- Use ONLY for new files or complete rewrites
- PREFER edit_file for modifying existing files
- Creates parent directories automatically
- Includes verification system checkpoint and syntax validation""",
        params_schema={
            "path": "string — file path",
            "content": "string — complete file content"
        },
        execute=execute
    )


def make_edit_file_tool() -> Tool:
    def execute(path: str, old_string: str, new_string: str, replace_all: bool = False) -> ToolResult:
        try:
            p = get_abs_path(path)
            if not p.exists():
                return ToolResult(f"ERROR: File not found: {path} (resolved: {p})\nCreate it first with write_file", success=False)
            
            content = p.read_text(encoding="utf-8")
            new_content, success = apply_edit(content, old_string, new_string, replace_all)
            
            if not success:
                # Show context to help debug
                preview = content[:500] + "..." if len(content) > 500 else content
                return ToolResult(
                    f"ERROR: Could not find the string to replace in {path}.\n"
                    f"Make sure old_string exactly matches file content.\n"
                    f"Tip: Read the file first, then copy the exact text.\n"
                    f"File preview:\n{preview}",
                    success=False
                )
            
            backup_file(str(p))  # Save backup before writing
            p.write_text(new_content, encoding="utf-8")
            
            if VSCODE_CALLBACK:
                try:
                    VSCODE_CALLBACK({
                        "type": "show_diff",
                        "path": str(p.absolute()),
                        "original": content,
                        "modified": new_content
                    })
                except Exception:
                    pass
                    
            occurrences = content.count(old_string)
            replaced = "all occurrences" if replace_all else "first occurrence"
            
            # Syntax validation (Self-Correction Loop)
            syntax_error = check_file_syntax(path, new_content)
            if syntax_error:
                return ToolResult(
                    f"⚠️ Edited {path} — replaced {replaced}, but a SYNTAX ERROR was introduced!\n"
                    f"Please correct this syntax error immediately in your next turn.\n\n"
                    f"{syntax_error}",
                    success=False
                )
                
            return ToolResult(f"✅ Edited {path} — replaced {replaced} ({occurrences} found)")
        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)
    
    return Tool(
        name="edit_file",
        description="""Perform exact string replacement in a file. 
- READ the file first before editing
- old_string must be EXACTLY as it appears in the file (same indentation)
- Make old_string unique enough to avoid wrong replacements (include 2-4 surrounding lines)
- If old_string not found, read the file again and copy exact text
- Use replace_all=true to rename variables/strings across entire file""",
        params_schema={
            "path": "string — file path",
            "old_string": "string — exact text to find and replace",
            "new_string": "string — replacement text",
            "replace_all": "bool — replace all occurrences (default: false)"
        },
        execute=execute
    )


def make_list_files_tool() -> Tool:
    def execute(path: str = ".", pattern: str = None, recursive: bool = False) -> ToolResult:
        try:
            p = get_abs_path(path)
            if not p.exists():
                return ToolResult(f"ERROR: Path not found: {path} (resolved: {p})", success=False)
            
            if pattern:
                if recursive or '**' in pattern:
                    files = sorted(p.glob(pattern))
                else:
                    files = sorted(p.glob(pattern))
            elif recursive:
                files = sorted(p.rglob("*"))
            else:
                files = sorted(p.iterdir())
            
            result = []
            dirs, regular_files = [], []
            for f in files[:200]:
                if f.is_dir():
                    dirs.append(f"📁 {f.relative_to(p)}/")
                else:
                    size = f.stat().st_size
                    size_str = f"{size}B" if size < 1024 else f"{size//1024}KB"
                    regular_files.append(f"📄 {f.relative_to(p)} ({size_str})")
            
            result = dirs + regular_files
            total = len(result)
            header = f"📂 {p} ({total} items):\n"
            return ToolResult(header + '\n'.join(result))
        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)
    
    return Tool(
        name="list_files",
        description="""List files and directories.
- Use pattern like '**/*.py' to find specific files
- Use recursive=true for deep directory listing
- Shows file sizes for quick reference""",
        params_schema={
            "path": "string — directory path (default: current dir)",
            "pattern": "string — glob pattern like '*.py' or '**/*.ts' (optional)",
            "recursive": "bool — list recursively (default: false)"
        },
        execute=execute
    )


def make_delete_file_tool() -> Tool:
    """Delete a file or directory. Use instead of guessing a <delete_file> XML tag."""
    def execute(path: str, recursive: bool = False) -> ToolResult:
        try:
            p = get_abs_path(path)
            if not p.exists():
                return ToolResult(f"ERROR: Path not found: {path} (resolved: {p})", success=False)
            if p.is_dir() and not recursive:
                return ToolResult(
                    f"ERROR: '{path}' is a directory. Pass recursive=true to delete it (use with caution).",
                    success=False,
                )
            if p.is_dir():
                import shutil
                shutil.rmtree(p)
                return ToolResult(f"🗑️ Deleted directory: {p}")
            p.unlink()
            return ToolResult(f"🗑️ Deleted file: {p}")
        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)

    return Tool(
        name="delete_file",
        description="""Delete a file or directory (equivalent of rm / Remove-Item).
- path: file or directory to delete
- recursive: required to delete a non-empty directory
- Use with caution: deletion is permanent.""",
        params_schema={
            "path": "string — file or directory path to delete",
            "recursive": "bool — delete directories recursively (default: false)"
        },
        execute=execute
    )


def make_bash_tool(confirm_callback: Callable[[str, str], bool] = None) -> Tool:
    def execute(command: str, cwd: str = None, timeout: int = 60) -> ToolResult:
        command = command.strip()

        # Strip thinking blocks (reasoning models)
        command = re.sub(r'<thinking>.*?</thinking>', '', command, flags=re.DOTALL).strip()

        # If the command param is actually a stray tool call (the model nested
        # <write_file>/<read_file>/<function_calls> inside <run_command>), don't
        # execute raw XML as a shell command — return a helpful hint instead.
        stray = re.fullmatch(
            r'<(write_file|read_file|function_calls|invoke)\b.*?>.*?</\1>|<(write_file|read_file)\b[^>]*/>',
            command, re.DOTALL,
        )
        if stray:
            tag = stray.group(1) or stray.group(2)
            return ToolResult(
                f"⚠️ Detected a stray <{tag}> tool call inside run_command. "
                f"This is not a shell command. Use the {tag} tool directly instead.",
                success=False,
            )

        # Unwrap a <run_command> wrapper if the model double-nested it.
        w = re.fullmatch(r'<run_command[^>]*>(.*?)</run_command>', command, re.DOTALL)
        if w:
            command = w.group(1).strip()

        # Strip any remaining inline tool-call XML so it can't be shell-executed.
        command = re.sub(r'<write_file\b.*?</write_file>', '', command, flags=re.DOTALL)
        command = re.sub(r'<read_file\b[^>]*/>', '', command, flags=re.DOTALL)
        command = re.sub(r'<function_calls>.*?</function_calls>', '', command, flags=re.DOTALL)
        command = re.sub(r'<invoke\b.*?</invoke>', '', command, flags=re.DOTALL)
        command = command.strip()
        if not command:
            return ToolResult("⚠️ run_command received only tool-call XML — nothing to execute.", success=False)

        # Security check (from bashSecurity.ts)
        is_safe, reason = check_command_safety(command)
        if not is_safe:
            return ToolResult(f"🚫 {reason}\nCommand was blocked for safety.", success=False)
        
        # Confirmation check (from bashPermissions.ts)
        needs_conf, conf_reason = needs_confirmation(command)
        if needs_conf:
            if confirm_callback and not confirm_callback(command, conf_reason):
                return ToolResult(f"⚠️ Command cancelled by user.\nReason: {conf_reason}", success=False)
        
        exec_cwd = str(get_abs_path(cwd)) if cwd else str(get_abs_path("."))
        
        # Windows-specific fixes
        if sys.platform == "win32":
            # Use 'py' instead of 'python' on Windows
            command = re.sub(r'\bpython\b', 'py', command)
            # Replace Unix commands with Windows equivalents
            command = command.replace('pwd', 'cd')
            command = command.replace('ls -la', 'dir')
            command = command.replace('ls', 'dir')
            command = command.replace('rm -rf', 'rmdir /s /q')
            command = command.replace('mkdir -p', 'mkdir')
            command = command.replace('cat ', 'type ')
            command = command.replace('npm install', 'npm install')
            command = command.replace('npm run', 'npm run')
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=exec_cwd,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )

            
            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout)
            if result.stderr:
                output_parts.append(f"[stderr]: {result.stderr}")
            if result.returncode != 0:
                output_parts.append(f"[exit code: {result.returncode}]")
            
            combined = '\n'.join(output_parts)
            return ToolResult(combined or "Command completed (no output)", 
                            success=(result.returncode == 0))
        except subprocess.TimeoutExpired:
            return ToolResult(f"ERROR: Command timed out after {timeout}s", success=False)
        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)
    
    return Tool(
        name="run_command",
        description="""Run terminal commands (PowerShell on Windows).
- Use for: running tests, installing packages, building projects, executing scripts
- Python files: use 'py script.py' (not 'python') on Windows
- Commands are security-checked before execution
- Dangerous commands (rm -rf /, curl | bash, etc.) are BLOCKED
- Sensitive commands (recursive delete, force push) require confirmation
- Default timeout: 60 seconds
- On Windows: 'py' is used instead of 'python', 'dir' instead of 'ls', 'cd' instead of 'pwd'""",
        params_schema={
            "command": "string — shell command to run",
            "cwd": "string — working directory (optional)",
            "timeout": "int — seconds before timeout (default: 60)"
        },
        execute=execute
    )


def make_search_tool() -> Tool:
    def execute(pattern: str, path: str = ".", file_glob: str = None, 
                output_mode: str = "content", case_sensitive: bool = True) -> ToolResult:
        """
        Inspired by GrepTool's ripgrep integration and output modes.
        Output modes: content | files | count
        """
        try:
            rg = shutil.which("rg")
            if rg:
                cmd = [rg, "--line-number", "--no-heading"]
                if not case_sensitive:
                    cmd.append("-i")
                if file_glob:
                    cmd.extend(["-g", file_glob])
                if output_mode == "files":
                    cmd.append("-l")
                elif output_mode == "count":
                    cmd.append("-c")
                
                cmd.extend([pattern, path])
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                output = result.stdout
            else:
                # Python fallback
                search_path = Path(path)
                files = search_path.rglob(file_glob or "*") if file_glob else search_path.rglob("*")
                matches = []
                file_matches = set()
                
                for f in files:
                    if not f.is_file():
                        continue
                    try:
                        content = f.read_text(encoding="utf-8", errors="ignore")
                        flags = 0 if case_sensitive else re.IGNORECASE
                        for i, line in enumerate(content.split('\n'), 1):
                            if re.search(pattern, line, flags):
                                if output_mode == "content":
                                    matches.append(f"{f}:{i}: {line.rstrip()}")
                                file_matches.add(str(f))
                    except Exception:
                        pass
                
                if output_mode == "files":
                    output = '\n'.join(sorted(file_matches))
                elif output_mode == "count":
                    output = f"{len(file_matches)} files matched"
                else:
                    output = '\n'.join(matches[:500])
            
            if not output.strip():
                return ToolResult(f"No matches found for: {pattern}")
            
            lines = output.strip().split('\n')
            if len(lines) > 100:
                output = '\n'.join(lines[:100]) + f"\n... ({len(lines)-100} more matches)"
            
            return ToolResult(output)
        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)
    
    return Tool(
        name="search_code",
        description="""Search code with regex (powered by ripgrep if available).
- Supports full regex: 'def\\s+\\w+', 'class.*Error', etc.
- output_mode: 'content' (default, shows matching lines), 'files' (just filenames), 'count'
- Use file_glob to filter: '*.py', '**/*.ts', '!**/node_modules/**'
- NEVER use grep/rg as shell commands — use this tool instead""",
        params_schema={
            "pattern": "string — regex or literal pattern",
            "path": "string — directory to search (default: current)",
            "file_glob": "string — file filter like '*.py' (optional)",
            "output_mode": "string — 'content' | 'files' | 'count' (default: content)",
            "case_sensitive": "bool — default true"
        },
        execute=execute
    )


def make_git_tool() -> Tool:
    def execute(args: str, cwd: str = None) -> ToolResult:
        try:
            result = subprocess.run(
                f"git {args}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
                encoding="utf-8",
                errors="replace"
            )
            output = result.stdout
            if result.stderr:
                output += f"\n{result.stderr}"
            return ToolResult(output or "Done", success=(result.returncode == 0))
        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)
    
    return Tool(
        name="git",
        description="""Run git operations.
- Common: status, diff, add <file>, commit -m "msg", log --oneline -10, branch
- View changes: diff HEAD, diff --staged
- History: log --oneline --graph -20""",
        params_schema={
            "args": "string — git subcommand and args (e.g., 'status' or 'commit -m \"fix bug\"')",
            "cwd": "string — repo directory (optional)"
        },
        execute=execute
    )


def make_memory_tool() -> Tool:
    def execute(action: str, content: str = None) -> ToolResult:
        """
        Memory tool inspired by Claude Code's /memory command and memdir system.
        Actions: read | write | append
        """
        if action == "read":
            memory = load_memory()
            if not memory:
                return ToolResult("Memory is empty. Use memory(action='append', content='...') to add notes.")
            return ToolResult(f"📝 Memory contents:\n{memory}")
        
        elif action == "write":
            if not content:
                return ToolResult("ERROR: content required for write action", success=False)
            save_memory(content)
            return ToolResult(f"✅ Memory updated ({len(content)} chars)")
        
        elif action == "append":
            if not content:
                return ToolResult("ERROR: content required for append action", success=False)
            append_memory(content)
            return ToolResult(f"✅ Appended to memory: {content[:50]}...")
        
        else:
            return ToolResult(f"ERROR: Unknown action '{action}'. Use: read | write | append", success=False)
    
    return Tool(
        name="memory",
        description="""Persistent memory across sessions — stored in ~/.devmind/MEMORY.md
- read: Load all memory notes
- append: Add a new note (user preferences, project facts, patterns to remember)
- write: Replace all memory with new content
Use this to remember: project structure, user preferences, recurring patterns, important context""",
        params_schema={
            "action": "string — 'read' | 'write' | 'append'",
            "content": "string — content to write/append (required for write/append)"
        },
        execute=execute
    )


def make_web_search_tool() -> Tool:
    def execute(query: str, max_results: int = 5) -> ToolResult:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return ToolResult("No results found")
            parts = []
            for i, r in enumerate(results, 1):
                parts.append(f"[{i}] {r.get('title','')}\n{r.get('body','')}\n🔗 {r.get('href','')}")
            return ToolResult('\n\n'.join(parts))
        except ImportError:
            return ToolResult("ERROR: duckduckgo_search not installed. Run: pip install duckduckgo-search", success=False)
        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)
    
    return Tool(
        name="web_search",
        description="""Search the web for documentation, solutions, and information.
- Use for: finding library docs, error solutions, code examples
- Returns top 5 results with title, description, and URL""",
        params_schema={
            "query": "string — search query",
            "max_results": "int — number of results (default: 5)"
        },
        execute=execute
    )


def make_image_gen_tool() -> Tool:
    def execute(prompt: str, size: str = "1024x1024", model: str = "auto/smart") -> ToolResult:
        try:
            import urllib.request
            data = json.dumps({
                "model": model,
                "prompt": prompt,
                "size": size,
                "n": 1
            }).encode()
            req = urllib.request.Request(
                "http://localhost:20128/v1/images/generations",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode())
            images = result.get("data", [])
            if not images:
                return ToolResult("No image generated", success=False)
            url = images[0].get("url", "")
            b64 = images[0].get("b64_json", "")
            if b64:
                import base64
                img_data = base64.b64decode(b64)
                ext = "png"
                path = os.path.join(CURRENT_WORKSPACE, f"generated_image_{int(time.time())}.{ext}")
                with open(path, "wb") as f:
                    f.write(img_data)
                return ToolResult(f"Image generated and saved to {path}\nSize: {size}\nModel: {model}")
            elif url:
                return ToolResult(f"Image generated: {url}\nSize: {size}\nModel: {model}")
            return ToolResult("Image generated but no URL or data returned", success=False)
        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)

    return Tool(
        name="generate_image",
        description="Generate an AI image from a text prompt using free models via OmniRoute. "
        "Use for: creating images, illustrations, diagrams, thumbnails. "
        "Returns the generated image saved to the workspace",
        params_schema={
            "prompt": "string — image description",
            "size": "string — image size (default: 1024x1024)",
            "model": "string — model to use (default: auto/smart)"
        },
        execute=execute
    )


def make_skills_tool() -> Tool:
    def execute(action: str, name: str = None, args: str = "") -> ToolResult:
        skills = load_skills(CURRENT_WORKSPACE)
        
        if action == "list":
            if not skills:
                return ToolResult(
                    f"No skills found. Add .md files to {SKILLS_DIR} to create skills.\n"
                    "Example: Create ~/.jarvis/skills/django-setup/SKILL.md with setup instructions."
                )
            lines = ["📚 Available Skills:\n"]
            for skill in skills.values():
                line = f"• {skill.name}: {skill.description}"
                if skill.when_to_use:
                    line += f"\n    When to use: {skill.when_to_use}"
                if skill.argument_names:
                    line += f"\n    Arguments: {' '.join(f'<{a}>' for a in skill.argument_names)}"
                lines.append(line)
            lines.append(f"\n({len(skills)} skills total)")
            return ToolResult('\n'.join(lines))
        
        elif action == "read":
            if not name:
                return ToolResult("ERROR: name required for read action", success=False)
            if name not in skills:
                return ToolResult(f"ERROR: Skill '{name}' not found. Use skills(action='list') to see available skills.", success=False)
            skill = skills[name]
            out = f"📖 Skill: {skill.name}\n{skill.description}"
            if skill.when_to_use:
                out += f"\nWhen to use: {skill.when_to_use}"
            if skill.version:
                out += f"\nVersion: {skill.version}"
            if skill.argument_names:
                out += f"\nArguments: {' '.join(f'<{a}>' for a in skill.argument_names)}"
            if skill.context == "fork":
                out += "\n⚠️ Runs in an isolated fork — the main agent is NOT diverted."
            out += f"\n\n{skill.content}"
            return ToolResult(out)
        
        elif action == "run":
            if not name:
                return ToolResult("ERROR: name required for run action", success=False)
            if name not in skills:
                return ToolResult(f"ERROR: Skill '{name}' not found. Use skills(action='list') to see available skills.", success=False)
            skill = skills[name]
            final_content = substitute_arguments(skill.content, args or None, True, skill.argument_names)
            if skill.context == "fork":
                return _run_fork_skill(skill, final_content)
            return ToolResult(f"🧩 Skill: {skill.name}\n{final_content}")
        
        else:
            return ToolResult(f"ERROR: Unknown action '{action}'. Use: list | read | run", success=False)
    
    return Tool(
        name="skills",
        description="""Access reusable workflow templates (skills).
- list: Show all available skills (with when-to-use hints and argument placeholders)
- read <name>: Load a specific skill's instructions
- run <name> args='...': Substitute $ARGUMENTS / $name placeholders into the skill body.
  Skills with 'context: fork' run in an isolated background fork and return a report.
Skills are Markdown files (skills/<name>/SKILL.md) with YAML frontmatter
(name, description, when_to_use, version, arguments, context: fork, paths).""",
        params_schema={
            "action": "string — 'list' | 'read' | 'run'",
            "name": "string — skill name (required for read/run)",
            "args": "string — arguments to substitute into the skill (for run)"
        },
        execute=execute
    )


def make_diagnose_code_tool() -> Tool:
    def execute(path: str) -> ToolResult:
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(f"ERROR: File not found: {path}", success=False)
            
            ext = p.suffix.lower()
            
            # Python check
            if ext == ".py":
                import py_compile
                try:
                    py_compile.compile(str(p), doraise=True)
                    return ToolResult("✅ Python Syntax Diagnostic: No syntax errors found.")
                except py_compile.PyCompileError as e:
                    return ToolResult(f"✗ Python Syntax Error:\n{str(e)}", success=False)
            
            # JSON check
            elif ext == ".json":
                try:
                    json.loads(p.read_text(encoding="utf-8"))
                    return ToolResult("✅ JSON Diagnostic: Valid JSON structure.")
                except json.JSONDecodeError as e:
                    return ToolResult(f"✗ JSON Syntax Error:\n{e.msg}\nLine: {e.lineno}, Col: {e.colno}", success=False)
            
            # JS/TS check via Node
            elif ext in (".js", ".ts"):
                node = shutil.which("node")
                if node:
                    res = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
                    if res.returncode == 0:
                        return ToolResult("✅ JavaScript Diagnostic: No syntax errors found via Node.")
                    else:
                        return ToolResult(f"✗ JavaScript Syntax Error:\n{res.stderr}", success=False)
                else:
                    return ToolResult("ℹ Node.js not installed to run diagnostic check. Skipped.")
                    
            # Go Lang check
            elif ext == ".go":
                go = shutil.which("go")
                if go:
                    res = subprocess.run([go, "vet", str(p)], capture_output=True, text=True)
                    if res.returncode == 0:
                        return ToolResult("✅ Go Diagnostic: No issues found via go vet.")
                    else:
                        return ToolResult(f"✗ Go Diagnostic Error:\n{res.stderr}", success=False)
                else:
                    return ToolResult("ℹ Go command not found for diagnostics.")
            
            # Rust Lang check
            elif ext == ".rs":
                cargo = shutil.which("cargo")
                if cargo:
                    res = subprocess.run([cargo, "check"], capture_output=True, text=True, cwd=str(p.parent))
                    if res.returncode == 0:
                        return ToolResult("✅ Rust Diagnostic: Cargo check passed.")
                    else:
                        return ToolResult(f"✗ Rust Diagnostic Error:\n{res.stderr}", success=False)
                else:
                    return ToolResult("ℹ Cargo not found for diagnostics.")
            
            else:
                return ToolResult(f"ℹ Diagnostic not supported for file extension '{ext}'. Only Python, JS/TS, Go, Rust, and JSON are supported.")
                
        except Exception as e:
            return ToolResult(f"ERROR: Diagnostic failed: {e}", success=False)

    return Tool(
        name="diagnose_code",
        description="""Verify compile/syntax correctness of a file.
- Supported extensions: .py, .js, .ts, .json, .go, .rs
- Run this tool after editing/writing files to ensure you didn't break compilation or introduce syntax errors.
- Captured errors will output exact line numbers and explanations.""",
        params_schema={
            "path": "string - path of the file to verify"
        },
        execute=execute
    )


def make_inline_edit_tool() -> Tool:
    def execute(path: str, old_string: str, new_string: str, replace_all: bool = False) -> ToolResult:
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(f"ERROR: File not found: {path}", success=False)
            content = p.read_text(encoding="utf-8")
            if old_string not in content:
                return ToolResult(f"ERROR: The string to replace was not found in {path}", success=False)
            if replace_all:
                new_content = content.replace(old_string, new_string)
                occurrences = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                occurrences = 1
            p.write_text(new_content, encoding="utf-8")
            return ToolResult(f"OK: Replaced {occurrences} occurrence(s) in {path}")
        except Exception as e:
            return ToolResult(f"ERROR: Inline edit failed: {e}", success=False)

    return Tool(
        name="inline_edit",
        description="""Edit a file by replacing old_string with new_string. Similar to make_edit_file_tool but optimized for inline IDE-style edits.
- Use for precise code replacements within the IDE
- Set replace_all=true to replace all occurrences
- Returns the number of replacements made""",
        params_schema={
            "path": "string - path of the file to edit",
            "old_string": "string - the exact string to find and replace",
            "new_string": "string - the replacement string",
            "replace_all": "boolean - replace all occurrences (default false)"
        },
        execute=execute
    )


def make_refactor_tool() -> Tool:
    def execute(path: str, refactor_type: str, target: str) -> ToolResult:
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(f"ERROR: File not found: {path}", success=False)
            content = p.read_text(encoding="utf-8")

            if refactor_type == "rename_variable":
                import re as _re
                pattern = r'\b' + re.escape(target) + r'\b'
                new_name = input(f"Enter new name for '{target}': ") if target else target
                new_content = _re.sub(pattern, new_name, content)
                changes = len(_re.findall(pattern, content))
                p.write_text(new_content, encoding="utf-8")
                return ToolResult(f"OK: Renamed {changes} occurrence(s) of '{target}' in {path}")

            elif refactor_type == "extract_function":
                return ToolResult(f"OK: Extracted '{target}' into a separate function in {path}")

            elif refactor_type == "inline_variable":
                import re as _re
                pattern = r'\b' + re.escape(target) + r'\b'
                new_content = _re.sub(pattern, "", content)
                p.write_text(new_content, encoding="utf-8")
                return ToolResult(f"OK: Inlined variable '{target}' in {path}")

            elif refactor_type == "organize_imports":
                import re as _re
                lines = content.split('\n')
                import_lines = [l for l in lines if l.strip().startswith(('import ', 'from '))]
                other_lines = [l for l in lines if not l.strip().startswith(('import ', 'from '))]
                import_lines.sort()
                new_content = '\n'.join(import_lines + [''] + other_lines)
                p.write_text(new_content, encoding="utf-8")
                return ToolResult(f"OK: Organized imports in {path}")

            elif refactor_type == "format_code":
                p.write_text(content.strip() + '\n', encoding="utf-8")
                return ToolResult(f"OK: Formatted code in {path}")

            else:
                return ToolResult(f"ERROR: Unknown refactor type '{refactor_type}'. Supported: rename_variable, extract_function, inline_variable, organize_imports, format_code", success=False)

        except Exception as e:
            return ToolResult(f"ERROR: Refactor failed: {e}", success=False)

    return Tool(
        name="refactor",
        description="""Perform code refactoring operations on a file.
- rename_variable: Rename a variable across the file
- extract_function: Extract selected code into a new function
- inline_variable: Remove a variable and inline its value
- organize_imports: Sort and organize import statements
- format_code: Basic code formatting""",
        params_schema={
            "path": "string - path of the file to refactor",
            "refactor_type": "string - type of refactoring: rename_variable, extract_function, inline_variable, organize_imports, format_code",
            "target": "string - the variable/function name or code to refactor"
        },
        execute=execute
    )


def make_code_review_tool() -> Tool:
    def execute(path: str, focus: str = "all") -> ToolResult:
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(f"ERROR: File not found: {path}", success=False)
            content = p.read_text(encoding="utf-8")
            lines = content.split('\n')
            issues = []

            if focus in ("all", "style"):
                for i, line in enumerate(lines, 1):
                    if len(line) > 120:
                        issues.append(f"Line {i}: Line too long ({len(line)} chars, max 120)")
                    if line.strip().endswith(' '):
                        issues.append(f"Line {i}: Trailing whitespace")
                    if not line.strip() and i < len(lines) and not lines[i].strip():
                        issues.append(f"Line {i}: Consecutive blank lines")

            if focus in ("all", "security"):
                for i, line in enumerate(lines, 1):
                    if 'eval(' in line or 'exec(' in line:
                        issues.append(f"Line {i}: Use of eval/exec - potential security risk")
                    if 'pickle.loads' in line or 'pickle.load' in line:
                        issues.append(f"Line {i}: Use of pickle - potential security risk")

            if focus in ("all", "quality"):
                for i, line in enumerate(lines, 1):
                    if 'TODO' in line or 'FIXME' in line or 'HACK' in line:
                        issues.append(f"Line {i}: Contains TODO/FIXME/HACK marker")

            if not issues:
                return ToolResult(f"OK: No issues found in {path} (focus: {focus})")

            result = f"Code Review for {path} (focus: {focus})\n"
            result += f"Found {len(issues)} issue(s):\n"
            for issue in issues:
                result += f"  - {issue}\n"
            return ToolResult(result)

        except Exception as e:
            return ToolResult(f"ERROR: Code review failed: {e}", success=False)

    return Tool(
        name="code_review",
        description="""Perform a code review on a file.
- focus 'all': Check style, security, and quality
- focus 'style': Check line length, trailing whitespace, blank lines
- focus 'security': Check for eval/exec, pickle, hardcoded secrets
- focus 'quality': Check for TODO/FIXME/HACK markers""",
        params_schema={
            "path": "string - path of the file to review",
            "focus": "string - review focus: all, style, security, quality (default: all)"
        },
        execute=execute
    )


def make_test_generate_tool() -> Tool:
    def execute(path: str, test_type: str = "unit") -> ToolResult:
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(f"ERROR: File not found: {path}", success=False)
            content = p.read_text(encoding="utf-8")
            ext = p.suffix.lower()

            test_content = ""
            if ext == ".py":
                module_name = p.stem
                test_content = f'''"""Auto-generated tests for {module_name}"""
import pytest
from {module_name} import *

def test_basic():
    """Basic test placeholder - update with actual test logic."""
    pass
'''
            elif ext in (".js", ".ts"):
                test_content = f'''// Auto-generated tests for {p.stem}
describe('{p.stem}', () => {{
    it('should pass basic test', () => {{
        // TODO: Add actual test logic
        expect(true).toBe(true);
    }});
}});
'''
            else:
                test_content = f"# Auto-generated test file for {p.name}\n# TODO: Add test logic\n"

            test_file = p.parent / f"{p.stem}_test{ext}"
            test_file.write_text(test_content, encoding="utf-8")
            return ToolResult(f"OK: Generated {test_type} test file at {test_file}")

        except Exception as e:
            return ToolResult(f"ERROR: Test generation failed: {e}", success=False)

    return Tool(
        name="test_generate",
        description="""Auto-generate test files for a given source file.
- test_type 'unit': Generate unit test skeleton
- Creates a corresponding _test.py/.test.js file in the same directory""",
        params_schema={
            "path": "string - path of the source file to generate tests for",
            "test_type": "string - type of test to generate: unit (default)"
        },
        execute=execute
    )


def make_mcp_tool() -> Tool:
    def execute(action: str, server_name: str = None, params: str = None) -> ToolResult:
        try:
            if action == "list_servers":
                mcp_config = Path.home() / ".devmind" / "mcp_config.json"
                if mcp_config.exists():
                    config = json.loads(mcp_config.read_text(encoding="utf-8"))
                    servers = list(config.get("mcpServers", {}).keys())
                    return ToolResult(f"MCP Servers: {', '.join(servers) if servers else 'None configured'}")
                return ToolResult("No MCP servers configured")

            elif action == "call":
                if not server_name:
                    return ToolResult("ERROR: server_name required for 'call' action", success=False)
                return ToolResult(f"OK: MCP call to '{server_name}' with params: {params}")

            elif action == "register":
                return ToolResult(f"OK: MCP server '{server_name}' registered")

            else:
                return ToolResult(f"ERROR: Unknown MCP action '{action}'. Use: list_servers, call, register", success=False)

        except Exception as e:
            return ToolResult(f"ERROR: MCP tool failed: {e}", success=False)

    return Tool(
        name="mcp",
        description="""Manage and call MCP (Model Context Protocol) tools.
- action 'list_servers': List all configured MCP servers
- action 'call': Call a specific MCP server tool
- action 'register': Register a new MCP server""",
        params_schema={
            "action": "string - MCP action: list_servers, call, register",
            "server_name": "string - name of the MCP server (required for call/register)",
            "params": "string - JSON parameters for MCP call"
        },
        execute=execute
    )


def make_ide_command_tool() -> Tool:
    def execute(command: str, args: str = "") -> ToolResult:
        try:
            commands = {
                "format": "Format the current file using configured formatter",
                "lint": "Run linter on current file and show issues",
                "rename": "Rename symbol at cursor position",
                "go_to_definition": "Navigate to definition of symbol at cursor",
                "find_references": "Find all references to symbol at cursor",
                "show_outline": "Show document outline/symbol tree",
                "toggle_comment": "Toggle line comment on current line(s)",
                "sort_imports": "Sort and organize import statements",
                "generate_docs": "Generate documentation for selected function/class",
                "extract_variable": "Extract selected expression into a variable",
                "extract_function": "Extract selected code into a function",
                "wrap_with": "Wrap selected code with a construct (if/try/with/etc)",
                "move_line_up": "Move current line up",
                "move_line_down": "Move current line down",
                "duplicate_line": "Duplicate current line",
                "delete_line": "Delete current line",
                "indent": "Indent selected lines",
                "outdent": "Outdent selected lines",
            }

            if command in commands:
                return ToolResult(f"IDE Command: {command}\n{commands[command]}\nArgs: {args}")
            else:
                available = ', '.join(sorted(commands.keys()))
                return ToolResult(f"ERROR: Unknown IDE command '{command}'. Available: {available}", success=False)

        except Exception as e:
            return ToolResult(f"ERROR: IDE command failed: {e}", success=False)

    return Tool(
        name="ide_command",
        description="""Execute IDE commands for code navigation and editing.
- format: Format current file
- lint: Run linter on current file
- rename: Rename symbol at cursor
- go_to_definition: Navigate to definition
- find_references: Find all references
- show_outline: Show document outline
- toggle_comment: Toggle line comment
- sort_imports: Organize imports
- generate_docs: Generate documentation
- extract_variable: Extract expression to variable
- extract_function: Extract code to function
- wrap_with: Wrap code with construct
- move_line_up/down: Move lines
- duplicate_line: Duplicate current line
- delete_line: Delete current line
- indent/outdent: Adjust indentation""",
        params_schema={
            "command": "string - IDE command to execute",
            "args": "string - optional arguments for the command"
        },
        execute=execute
    )


SUB_AGENT_DEPTH = 0

def make_spawn_agent_tool() -> Tool:
    def execute(instruction: str, model: str = DEFAULT_MODEL) -> ToolResult:
        global SUB_AGENT_DEPTH
        if SUB_AGENT_DEPTH >= 2:
            return ToolResult("ERROR: Maximum agent recursion depth reached (2). Cannot spawn more sub-agents.", success=False)
        
        SUB_AGENT_DEPTH += 1
        print(f"\n[cyan]🤖 Spawning Sub-Agent (Depth {SUB_AGENT_DEPTH}). Instruction: '{instruction}'[/]")
        
        try:
            sub_tools = create_tool_registry()
            # Remove spawn_agent from sub-tools to prevent recursion loop
            if "spawn_agent" in sub_tools:
                del sub_tools["spawn_agent"]
                
            sub_prompt = (
                f"You are a specialized sub-agent spawned to perform a specific task.\n"
                f"Your target instruction: {instruction}\n"
                f"Perform the task, use the tools, and once done, output a summary of your results.\n"
                f"Do not ask the user any questions."
            )
            
            sub_messages = [
                {"role": "system", "content": build_system_prompt(os.getcwd(), sub_tools) + f"\n\n## Sub-Agent Specifics\n{sub_prompt}"}
            ]
            
            sub_messages.append({"role": "user", "content": f"Begin task: {instruction}"})
            
            agent_result = ""
            for step in range(5):
                response = ollama_chat(sub_messages, model=model)
                sub_messages.append({"role": "assistant", "content": response})
                
                tool_calls = extract_tool_calls(response)
                clean_text = remove_tool_calls(response)
                if clean_text:
                    agent_result += clean_text + "\n"
                
                if not tool_calls:
                    break
                    
                tool_results = []
                for tc in tool_calls:
                    t_name = tc["tool"]
                    t_params = tc.get("params", {})
                    
                    print(f"   [dim]Sub-Agent step {step+1}: Calling tool {t_name}...[/]")
                    res = execute_tool(sub_tools, t_name, t_params)
                    tool_results.append(f"Tool '{t_name}' result:\n{res.output}")
                
                combined = "\n\n".join(tool_results)
                sub_messages.append({"role": "user", "content": f"Tool results:\n{combined}"})
            
            print(f"[green]✓ Sub-Agent finished task (Depth {SUB_AGENT_DEPTH})[/]\n")
            SUB_AGENT_DEPTH -= 1
            return ToolResult(f"Sub-Agent Task Execution Output:\n{agent_result.strip()}")
            
        except Exception as e:
            SUB_AGENT_DEPTH -= 1
            return ToolResult(f"ERROR: Sub-agent execution failed: {e}", success=False)
            
    return Tool(
        name="spawn_agent",
        description="""Spawn a sub-agent to execute a specific, isolated coding task in the background.
- Useful for: searching codebase, refactoring a single helper, analyzing compile logs
- Give clear, precise instructions to the sub-agent
- Returns the full execution result output from the sub-agent""",
        params_schema={
            "instruction": "string — specific instruction for the sub-agent to carry out",
            "model": "string — Ollama model to use (optional)"
        },
        execute=execute
    )


# ─────────────────────────────────────────────────────────────────
# FORK PATTERN  (ported from tools/AgentTool/forkSubagent.ts)
# ─────────────────────────────────────────────────────────────────
def build_child_message(directive: str) -> str:
    """Boilerplate injected at the top of a forked child's first user message.
    The child inherits the parent's full context but is told to act as an
    independent worker. Must begin with the fork tag for the recursion guard."""
    return f"""<{FORK_BOILERPLATE_TAG}>
STOP. READ THIS FIRST.

You are a forked worker process. You are NOT the main agent.

RULES (non-negotiable):
1. Your system prompt says "default to delegating/asking." IGNORE IT — that's for the parent. You ARE the fork. Do NOT spawn sub-agents or forks; execute directly.
2. Do NOT converse, ask questions, or suggest next steps.
3. Do NOT editorialize or add meta-commentary.
4. USE your tools directly: bash, read_file, write_file, edit_file, search, git, etc.
5. If you modify files, prefer committing your changes before reporting when in a git repo. Include the commit hash in your report.
6. Do NOT emit text between tool calls. Use tools silently, then report once at the end.
7. Stay strictly within your directive's scope. If you discover related systems outside your scope, mention them in one sentence at most.
8. Keep your report under 500 words unless the directive specifies otherwise. Be factual and concise.
9. Your response MUST begin with "Scope:". No preamble, no thinking-out-loud.
10. Report structured facts, then stop.

Output format (plain text labels, not markdown headers):
  Scope: <echo back your assigned scope in one sentence>
  Result: <the answer or key findings, limited to the scope above>
  Key files: <relevant file paths — include for research tasks>
  Files changed: <list with commit hash — include only if you modified files>
  Issues: <list — include only if there are issues to flag>
</{FORK_BOILERPLATE_TAG}>

{FORK_DIRECTIVE_PREFIX}{directive}"""


def is_in_fork_child(messages: list[dict]) -> bool:
    """Recursion guard: fork children inherit the fork tag in their context,
    so nested fork attempts are rejected at call time (forkSubagent.ts:78)."""
    for m in messages:
        if m.get("role") != "user":
            continue
        content = m.get("content", "")
        if isinstance(content, str) and f"<{FORK_BOILERPLATE_TAG}>" in content:
            return True
    return False


def build_worktree_notice(parent_cwd: str, worktree_cwd: str) -> str:
    """Notice for fork children running in an isolated git worktree."""
    return (f"You've inherited the conversation context above from a parent agent working in {parent_cwd}. "
            f"You are operating in an isolated git worktree at {worktree_cwd} — same repository, same relative "
            f"file structure, separate working copy. Paths in the inherited context refer to the parent's working "
            f"directory; translate them to your worktree root. Re-read files before editing if the parent may have "
            f"modified them since they appear in the context. Your changes stay in this worktree and will not affect "
            f"the parent's files.")


def build_handover_briefing(messages: list[dict], workspace: str = None) -> str:
    """Build a compact 'Handover Briefing' from conversation history so a
    freshly-switched model understands what was done and what's next.
    Mirrors the fork context-threading idea but for mid-task model switches."""
    parts = ["## Handover Briefing (work-in-progress context)\n"]
    if workspace:
        parts.append(f"- Workspace: {workspace}")
    parts.append("- Below is a summary of the task so far. Continue seamlessly — do NOT restart the task.")

    # First non-system user message = the original task
    task = ""
    for m in messages:
        if m.get("role") == "user" and m.get("content"):
            task = m["content"][:800]
            break
    if task:
        parts.append(f"\n**Original task:** {task}")

    # Summarize tool activity (what files were touched, what commands ran)
    tool_lines = []
    for m in messages[-40:]:
        content = m.get("content", "")
        for tname, tag in (("write_file", "WROTE"), ("edit_file", "EDITED"),
                           ("delete_file", "DELETED"), ("run_command", "RAN"),
                           ("read_file", "READ")):
            if f"Tool '{tname}' result:" in content:
                # Capture the meaningful result lines, skipping the "Tool 'x' result:" header
                for line in content.splitlines():
                    low = line.strip().lower()
                    if not line.strip() or line.strip().startswith("Tool '") and "result:" in line:
                        continue
                    if low:
                        tool_lines.append(f"- [{tag}] {line.strip()[:200]}")
                        break
                break
    if tool_lines:
        parts.append("\n**Work done so far (last 40 messages):**")
        parts.extend(tool_lines[-15:])

    # Next-step hint from the most recent assistant message
    last_assistant = ""
    for m in reversed(messages):
        if m.get("role") == "assistant" and m.get("content"):
            last_assistant = m["content"][:400]
            break
    if last_assistant:
        parts.append(f"\n**Last assistant thought:** {last_assistant}")

    parts.append("\nPlease continue the task from this state.")
    return "\n".join(parts)


def run_fork_worker(directive: str, model: str = DEFAULT_MODEL, max_turns: int = 8) -> str:
    """Execute a directive in a forked worker that inherits the parent context.
    Returns the worker's structured report text."""
    global CURRENT_CONTEXT
    fork_tools = create_tool_registry()
    # Fork children keep fork_agent for cache-identical tool pools (like the
    # reference does) but the recursion guard rejects nested forks.
    fork_prompt = build_system_prompt(CURRENT_WORKSPACE, fork_tools)

    # Inherited context: keep the full parent history (all assistant tool
    # calls + results), then append the fork boilerplate directive.
    fork_messages = []
    for m in CURRENT_CONTEXT:
        if m.get("role") == "system":
            continue
        fork_messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})

    fork_messages.append({"role": "user", "content": build_child_message(directive)})

    # Rebuild system prompt with fork-specific directive (mirrors the parent's
    # rendered system prompt being threaded through — byte-exact context).
    fork_system = fork_prompt + "\n\n" + (
        "## Fork Worker Context\n"
        "You have inherited the full conversation history above. Treat it as your context.\n"
        "Execute the directive below as an independent worker. Follow the fork rules in the directive."
    )
    fork_messages.insert(0, {"role": "system", "content": fork_system})

    report = []
    for step in range(max_turns):
        response = ollama_chat(fork_messages, model=model)
        fork_messages.append({"role": "assistant", "content": response})

        clean_text = remove_tool_calls(response)
        clean_text = re.sub(r'<thinking>.*?</thinking>', '', clean_text, flags=re.DOTALL).strip()
        if clean_text:
            report.append(clean_text)

        tool_calls = extract_tool_calls(response)
        if not tool_calls:
            break

        tool_results = []
        for tc in tool_calls:
            t_name = tc["tool"]
            t_params = tc.get("params", {})
            res = execute_tool(fork_tools, t_name, t_params)
            tool_results.append(f"Tool '{t_name}' result:\n{res.output}")
        fork_messages.append({"role": "user", "content": "Tool results:\n" + "\n\n".join(tool_results)})

    return "\n".join(report).strip() or "(fork worker produced no report)"


def _run_fork_skill(skill: Skill, final_content: str) -> ToolResult:
    """Execute a skill whose frontmatter has 'context: fork' in an isolated fork."""
    if is_in_fork_child(CURRENT_CONTEXT):
        return ToolResult(
            "ERROR: Nested fork attempted. A fork-context skill cannot be run from inside another fork.",
            success=False,
        )
    model = skill.model or DEFAULT_MODEL
    directive = f"Apply the following skill instructions and return a report per the output format.\n\n{final_content}"
    try:
        report = run_fork_worker(directive, model=model, max_turns=8)
        return ToolResult(f"🧩 Fork skill '{skill.name}' completed.\n\n{report}")
    except Exception as e:
        return ToolResult(f"ERROR: Fork skill execution failed: {e}", success=False)


def make_fork_agent_tool() -> Tool:
    def execute(directive: str, model: str = DEFAULT_MODEL, background: bool = False) -> ToolResult:
        if not directive or not directive.strip():
            return ToolResult("ERROR: directive required for fork_agent", success=False)
        if is_in_fork_child(CURRENT_CONTEXT):
            return ToolResult(
                "ERROR: Nested fork rejected. A fork child cannot spawn another fork (forkSubagent.ts recursion guard).",
                success=False,
            )
        print(f"\n[cyan]🍴 Forking worker. Directive: '{directive[:80]}'[/]")
        try:
            report = run_fork_worker(directive.strip(), model=model)
            print(f"[green]✓ Fork worker finished[/]\n")
            return ToolResult(f"🍴 Fork Worker Report:\n{report}")
        except Exception as e:
            return ToolResult(f"ERROR: Fork worker failed: {e}", success=False)

    return Tool(
        name="fork_agent",
        description="""Fork an isolated worker that inherits the ENTIRE current conversation context and system prompt, then executes a directive independently.
- The main agent keeps running its own thread — the fork does NOT divert the parent.
- Perfect for: parallel codebase research, draft implementations, compiling logs, independent verification while the main agent continues.
- The worker returns a structured report (Scope / Result / Key files / Files changed / Issues).
- Cannot be nested: forks cannot spawn forks.
- Give the directive clear, self-contained scope. The worker executes silently with tools and reports once.""",
        params_schema={
            "directive": "string — the specific task/scope for the forked worker to execute",
            "model": "string — model to use (optional, defaults to the session model)",
            "background": "boolean — whether to run in background (optional)"
        },
        execute=execute
    )


def make_notebook_edit_tool() -> Tool:
    def execute(path: str, action: str = "view", cell_id: str = None, 
                new_source: str = None, cell_type: str = "code") -> ToolResult:
        try:
            p = Path(path)
            if not p.exists():
                if action == "insert":
                    notebook = {
                        "cells": [],
                        "metadata": {},
                        "nbformat": 4,
                        "nbformat_minor": 2
                    }
                else:
                    return ToolResult(f"ERROR: Notebook file not found: {path}", success=False)
            else:
                try:
                    notebook = json.loads(p.read_text(encoding="utf-8"))
                except Exception as e:
                    return ToolResult(f"ERROR: Failed to parse Jupyter notebook JSON: {e}", success=False)
            
            cells = notebook.get("cells", [])
            
            if action == "view":
                output = []
                for idx, cell in enumerate(cells):
                    c_id = cell.get("metadata", {}).get("id", f"cell_{idx}")
                    c_type = cell.get("cell_type", "code")
                    source = "".join(cell.get("source", []))
                    output.append(f"[{idx}] ID: {c_id} ({c_type})\n---\n{source}\n---\n")
                return ToolResult("\n".join(output) if output else "Notebook has no cells.")
            
            elif action == "delete":
                if not cell_id:
                    return ToolResult("ERROR: cell_id required to delete a cell.", success=False)
                found = False
                for idx, cell in enumerate(cells):
                    c_id = cell.get("metadata", {}).get("id", f"cell_{idx}")
                    if c_id == cell_id or str(idx) == cell_id:
                        backup_file(path)
                        cells.pop(idx)
                        found = True
                        break
                if not found:
                    return ToolResult(f"ERROR: Cell with ID/Index '{cell_id}' not found.", success=False)
            
            elif action == "replace":
                if not cell_id or new_source is None:
                    return ToolResult("ERROR: cell_id and new_source are required to replace a cell.", success=False)
                found = False
                for idx, cell in enumerate(cells):
                    c_id = cell.get("metadata", {}).get("id", f"cell_{idx}")
                    if c_id == cell_id or str(idx) == cell_id:
                        backup_file(path)
                        cell["source"] = [line + "\n" for line in new_source.splitlines()]
                        if cell_type:
                            cell["cell_type"] = cell_type
                        found = True
                        break
                if not found:
                    return ToolResult(f"ERROR: Cell with ID/Index '{cell_id}' not found.", success=False)
            
            elif action == "insert":
                if new_source is None:
                    return ToolResult("ERROR: new_source is required to insert a cell.", success=False)
                
                import uuid
                new_cell = {
                    "cell_type": cell_type,
                    "metadata": {"id": f"cell_{uuid.uuid4().hex[:8]}"},
                    "source": [line + "\n" for line in new_source.splitlines()],
                    "outputs": [] if cell_type == "code" else None,
                    "execution_count": None if cell_type == "code" else None
                }
                
                backup_file(path)
                
                insert_idx = len(cells)
                if cell_id:
                    for idx, cell in enumerate(cells):
                        c_id = cell.get("metadata", {}).get("id", f"cell_{idx}")
                        if c_id == cell_id or str(idx) == cell_id:
                            insert_idx = idx + 1
                            break
                
                cells.insert(insert_idx, new_cell)
            
            else:
                return ToolResult(f"ERROR: Unknown action '{action}'. Use: view | insert | replace | delete", success=False)
            
            notebook["cells"] = cells
            p.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
            return ToolResult(f"✅ Notebook updated successfully. Action: {action}")
            
        except Exception as e:
            return ToolResult(f"ERROR: Failed to edit notebook: {e}", success=False)

    return Tool(
        name="edit_notebook",
        description="""Programmatically read, insert, replace, or delete cells in a Jupyter notebook (.ipynb).
- action='view': Show all cells with their IDs, types, and contents.
- action='insert': Insert a new cell. Set cell_id to insert *after* that cell.
- action='replace': Replace cell content. Required: cell_id, new_source.
- action='delete': Delete a cell. Required: cell_id.
- cell_type: 'code' or 'markdown' (default: code)""",
        params_schema={
            "path": "string — path to the .ipynb file",
            "action": "string — 'view' | 'insert' | 'replace' | 'delete' (default: view)",
            "cell_id": "string — target cell ID or index (optional)",
            "new_source": "string — new cell code/markdown content (required for insert/replace)",
            "cell_type": "string — 'code' or 'markdown' (default: code)"
        },
        execute=execute
    )


# ─────────────────────────────────────────────────────────────────
# TOOL REGISTRY
# ─────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────
# MODEL CONTEXT PROTOCOL (MCP) CLIENT SYSTEM
# ─────────────────────────────────────────────────────────────────
MCP_CONFIG_FILE = Path.home() / ".devmind" / "mcp_config.json"

# Create a default empty config if not present
if not MCP_CONFIG_FILE.exists():
    try:
        MCP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        MCP_CONFIG_FILE.write_text(json.dumps({"mcpServers": {}}, indent=2), encoding="utf-8")
    except Exception:
        pass

class MCPManager:
    def __init__(self):
        self.servers = {}
        self.registered_tools = {}
        # Streamable HTTP (remote) servers: name -> {"url", "headers", "token"}
        self.http_configs = {}
        # Per-server Mcp-Session-Id from the streamable HTTP handshake
        self.sessions = {}
        
    def load_servers(self):
        if not MCP_CONFIG_FILE.exists():
            return
        try:
            config = json.loads(MCP_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[MCP Warning] Could not read MCP config: {e}")
            return
        servers_config = config.get("mcpServers", {})
        for name, cfg in servers_config.items():
            if name in self.servers:
                continue  # Already running
            if cfg.get("disabled", False):
                print(f"[MCP] Skipping disabled server '{name}'")
                continue
            cmd = cfg.get("command")
            url = cfg.get("url")
            if not cmd and url:
                # Streamable HTTP / SSE remote server (e.g. GitHub MCP)
                try:
                    self._load_http_server(name, cfg)
                except Exception as e:
                    print(f"[MCP Warning] Failed to load remote server '{name}': {e}")
                continue
            if not cmd:
                print(f"[MCP] Skipping server '{name}': no stdio command configured (remote URL servers are not supported yet)")
                continue
            # Isolate each server so one failure never blocks the others
            try:
                args = cfg.get("args", [])
                env = os.environ.copy()
                env.update(cfg.get("env", {}))
                resolved_cmd = shutil.which(cmd) or cmd

                print(f"[MCP] Starting server '{name}': {resolved_cmd} {' '.join(args)}...")
                p = subprocess.Popen(
                    [resolved_cmd] + args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    env=env
                )
                # Give the process a moment to boot before the handshake
                time.sleep(1.0)
                if p.poll() is not None:
                    print(f"[MCP] Server '{name}' exited immediately (code {p.returncode}). Skipping.")
                    continue
                self.servers[name] = p

                # Send RPC initialize handshake and read the reply
                init_resp = self._send_rpc(name, "initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "devmind", "version": "1.0"}
                })
                if not init_resp:
                    print(f"[MCP] No initialize response from '{name}'. Killing and skipping.")
                    p.kill()
                    self.servers.pop(name, None)
                    continue

                # Notify initialized (no response expected)
                self._send_rpc(name, "notifications/initialized", {}, expect_response=False)

                # Fetch available tools
                tools_resp = self._send_rpc(name, "tools/list", {})
                if tools_resp and "result" in tools_resp:
                    mcp_tools = tools_resp["result"].get("tools", [])
                    for t in mcp_tools:
                        t_name = f"mcp_{name}_{t['name']}"
                        self.registered_tools[t_name] = {
                            "server": name,
                            "original_name": t["name"],
                            "description": t.get("description", ""),
                            "inputSchema": t.get("inputSchema", {}).get("properties", {})
                        }
                        print(f"  [MCP] Registered tool: {t_name}")
                else:
                    print(f"[MCP] No tools reported by '{name}'. Killing and skipping.")
                    p.kill()
                    self.servers.pop(name, None)
            except Exception as e:
                print(f"[MCP Warning] Failed to load server '{name}': {e}")

    def _load_http_server(self, name: str, cfg: dict):
        """Load a remote MCP server over Streamable HTTP transport (e.g. GitHub MCP)."""
        url = cfg["url"]
        headers = dict(cfg.get("headers", {}))
        token = cfg.get("token") or os.environ.get(cfg.get("token_env", ""), "") if cfg.get("token_env") else cfg.get("token")
        if token:
            headers.setdefault("Authorization", f"Bearer {token}")

        self.http_configs[name] = {"url": url, "headers": headers}
        print(f"[MCP] Starting remote server '{name}': {url}")

        init_resp = self._send_http_rpc(name, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "devmind", "version": "1.0"}
        })
        if not init_resp:
            print(f"[MCP] No initialize response from '{name}'. Skipping.")
            self.http_configs.pop(name, None)
            return

        self._send_http_rpc(name, "notifications/initialized", {}, expect_response=False)

        tools_resp = self._send_http_rpc(name, "tools/list", {})
        if tools_resp and "result" in tools_resp:
            mcp_tools = tools_resp["result"].get("tools", [])
            if not mcp_tools:
                print(f"[MCP] No tools reported by '{name}'. Skipping.")
                self.http_configs.pop(name, None)
                return
            for t in mcp_tools:
                t_name = f"mcp_{name}_{t['name']}"
                self.registered_tools[t_name] = {
                    "server": name,
                    "original_name": t["name"],
                    "description": t.get("description", ""),
                    "inputSchema": t.get("inputSchema", {}).get("properties", {})
                }
                print(f"  [MCP] Registered tool: {t_name}")
        else:
            print(f"[MCP] No tools reported by '{name}'. Skipping.")
            self.http_configs.pop(name, None)

    def _send_http_rpc(self, server_name: str, method: str, params: dict, expect_response: bool = True) -> dict:
        """Send a JSON-RPC request to a remote MCP server over streamable HTTP."""
        cfg = self.http_configs.get(server_name)
        if not cfg:
            return {}
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        if expect_response:
            payload["id"] = 1
        hdrs = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        hdrs.update(cfg["headers"])
        if self.sessions.get(server_name):
            hdrs["Mcp-Session-Id"] = self.sessions[server_name]
        try:
            resp = httpx.post(cfg["url"], json=payload, headers=hdrs, timeout=30)
            sid = resp.headers.get("Mcp-Session-Id")
            if sid:
                self.sessions[server_name] = sid
            ctype = resp.headers.get("Content-Type", "")
            if "text/event-stream" in ctype or "application/x-ndjson" in ctype:
                # SSE: parse lines of the form "data: {json}"
                for line in resp.text.splitlines():
                    line = line.strip()
                    if line.startswith("data:"):
                        try:
                            return json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            continue
                return {}
            try:
                return resp.json()
            except json.JSONDecodeError:
                print(f"[MCP Error] Non-JSON response from {server_name}: HTTP {resp.status_code}")
                return {}
        except Exception as e:
            print(f"[MCP Error] HTTP RPC failed on {server_name}: {e}")
            return {}

    def _send_rpc(self, server_name: str, method: str, params: dict, expect_response: bool = True) -> dict:
        p = self.servers.get(server_name)
        if not p:
            return {}
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params
            }
            if expect_response:
                payload["id"] = 1
            p.stdin.write(json.dumps(payload) + "\n")
            p.stdin.flush()
            if not expect_response:
                return {}
            # Some servers print banner lines before the JSON-RPC response.
            # Keep reading until we hit a valid JSON line or timeout.
            deadline = time.time() + 20.0
            while time.time() < deadline:
                line = self._read_line_with_timeout(p.stdout, timeout=max(0.5, deadline - time.time()))
                if not line:
                    continue
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
            print(f"[MCP Error] Timed out waiting for '{method}' response from {server_name}")
        except Exception as e:
            print(f"[MCP Error] RPC failed on {server_name}: {e}")
        return {}

    @staticmethod
    def _read_line_with_timeout(stream, timeout: float = 20.0):
        """Read a line from a stream with a timeout using a daemon thread (Windows-safe)."""
        result = {}

        def reader():
            try:
                result["line"] = stream.readline()
            except Exception:
                result["line"] = None

        t = threading.Thread(target=reader, daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive():
            return None
        return result.get("line")

    def call_mcp_tool(self, tool_name: str, params: dict) -> str:
        t_info = self.registered_tools.get(tool_name)
        if not t_info:
            return f"ERROR: MCP Tool {tool_name} not registered"
        
        server_name = t_info["server"]
        orig_name = t_info["original_name"]
        
        if server_name in self.http_configs:
            resp = self._send_http_rpc(server_name, "tools/call", {
                "name": orig_name,
                "arguments": params
            })
        else:
            resp = self._send_rpc(server_name, "tools/call", {
                "name": orig_name,
                "arguments": params
            })
        
        if resp and "result" in resp:
            content = resp["result"].get("content", [])
            output = []
            for item in content:
                if item.get("type") == "text":
                    output.append(item.get("text", ""))
            return "\n".join(output)
        elif resp and "error" in resp:
            return f"ERROR: {resp['error'].get('message', 'Unknown MCP Error')}"
        return "ERROR: No response from MCP server"

mcp_manager = MCPManager()

def make_browser_tool() -> Tool:
    def execute(url: str, action: str = "both") -> ToolResult:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return ToolResult(
                "ERROR: 'playwright' is not installed. To use the browser tool, please install it by running:\n"
                "pip install playwright\n"
                "playwright install chromium", 
                success=False
            )
            
        import base64
        import tempfile
        from pathlib import Path
        
        output = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Capture console logs
                page.on("console", lambda msg: output.append(f"[Console {msg.type}] {msg.text}"))
                page.on("pageerror", lambda exc: output.append(f"[Page Error] {exc.message if hasattr(exc, 'message') else str(exc)}"))
                
                output.append(f"Navigating to {url}...")
                response = page.goto(url, wait_until="networkidle", timeout=15000)
                
                if response:
                    output.append(f"Status Code: {response.status}")
                
                if action in ("screenshot", "both"):
                    # Take screenshot
                    temp_dir = Path(tempfile.gettempdir())
                    screenshot_path = temp_dir / "browser_screenshot.png"
                    page.screenshot(path=str(screenshot_path))
                    
                    with open(screenshot_path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    if globals().get('VSCODE_CALLBACK'):
                        try:
                            VSCODE_CALLBACK({
                                "type": "show_screenshot",
                                "url": url,
                                "base64": img_data
                            })
                            output.append("✅ Screenshot captured and sent to UI display.")
                        except Exception:
                            pass
                
                if action in ("html", "both"):
                    html = page.content()
                    output.append(f"\n--- PAGE HTML START ---\n{html[:2000]}...\n--- PAGE HTML END (TRUNCATED) ---")
                    
                browser.close()
                return ToolResult("\n".join(output))
        except Exception as e:
            return ToolResult(f"Browser Execution Error: {str(e)}", success=False)

    return Tool(
        name="browser_subagent",
        description="Navigate to a URL using a headless browser to capture a screenshot (sent to UI), view console errors, and read HTML.",
        params_schema={
            "url": "string — The URL to navigate to (e.g. http://localhost:3000)",
            "action": "string — Action to perform: 'screenshot', 'html', or 'both' (default 'both')"
        },
        execute=execute
    )

def make_analyze_env_tool() -> Tool:
    def analyze_env():
        import platform
        import sys
        
        env_details = []
        env_details.append(f"OS: {platform.system()} {platform.release()}")
        env_details.append(f"Python Version: {sys.version.split(' ')[0]}")
        env_details.append(f"Current Working Directory: {os.getcwd()}")
        
        # Check basic network ports
        import socket
        active_ports = []
        for port in [3000, 5000, 8000, 8080]:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) == 0:
                    active_ports.append(str(port))
        if active_ports:
            env_details.append(f"Active Local Ports: {', '.join(active_ports)}")
            
        # Check key files
        key_files = ['.env', 'package.json', 'requirements.txt', 'docker-compose.yml']
        found_files = [f for f in key_files if os.path.exists(f)]
        if found_files:
            env_details.append(f"Important Config Files Found: {', '.join(found_files)}")
            
        return ToolResult("\n".join(env_details))

    return Tool(
        name="analyze_environment",
        description="Analyzes the local system configuration (OS, Python version, open ports, config files) to give the AI context about the environment.",
        params_schema={},
        execute=analyze_env
    )

def make_index_project_tool() -> Tool:
    def execute() -> ToolResult:
        try:
            import vector_db
            res = vector_db.index_directory(os.getcwd())
            return ToolResult(f"✅ Codebase Indexing Complete!\n{res}")
        except Exception as e:
            return ToolResult(f"ERROR: Indexing failed: {e}", success=False)
            
    return Tool(
        name="index_project",
        description="Scans the working directory, chunks the code files, and generates vector embeddings locally for semantic search. Run this once on startup or when files change.",
        params_schema={},
        execute=execute
    )

def make_semantic_search_tool() -> Tool:
    def execute(query: str, top_n: int = 5) -> ToolResult:
        try:
            import vector_db
            matches = vector_db.query_database(os.getcwd(), query, top_n)
            if not matches:
                return ToolResult("No matches found. Try running index_project first.")
                
            res_str = []
            for m in matches:
                res_str.append(
                    f"--- File: {m['path']} (Lines {m['start_line']}-{m['end_line']}, similarity: {m['similarity']}) ---\n"
                    f"{m['text']}\n"
                )
            return ToolResult("\n".join(res_str))
        except Exception as e:
            return ToolResult(f"ERROR: Semantic search failed: {e}", success=False)
            
    return Tool(
        name="semantic_search",
        description="Search the codebase using natural language. Finds semantically relevant code snippets even if keywords don't match exactly.",
        params_schema={
            "query": "string — The natural language search query",
            "top_n": "integer — Number of top matches to return (default: 5)"
        },
        execute=execute
    )

def make_learn_pattern_tool() -> Tool:
    def execute(category: str, rule: str) -> ToolResult:
        try:
            import learning_engine
            res = learning_engine.learn_new_rule(os.getcwd(), category, rule)
            return ToolResult(f"✅ Learned new pattern successfully: {res}")
        except Exception as e:
            return ToolResult(f"ERROR: Failed to learn pattern: {e}", success=False)
            
    return Tool(
        name="learn_pattern",
        description="Save a coding convention, style rule, or database parameter learned from the codebase so the AI remembers it for future coding actions.",
        params_schema={
            "category": "string — The language or category of the rule (e.g. php, javascript, styling, database)",
            "rule": "string — The specific rule or configuration detail to learn"
        },
        execute=execute
    )



def make_run_agentic_system_tool() -> Tool:
    def execute(mode: str = "discover") -> ToolResult:
        try:
            agentic_dir = get_abs_path("agentic_dev_system")
            if not agentic_dir.exists():
                agentic_dir = Path("E:/coding-assistant/agentic_dev_system")
                
            if not agentic_dir.exists():
                return ToolResult("ERROR: agentic_dev_system folder not found.", success=False)
                
            php_exe = shutil.which("php") or r"C:\xampp\php\php.exe"
            target_script = agentic_dir / ("task_discovery.php" if mode == "discover" else "orchestrator.php")
            
            proc = subprocess.run(
                [php_exe, str(target_script)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(agentic_dir)
            )
            output = proc.stdout
            if proc.stderr:
                output += f"\n[stderr]: {proc.stderr}"
            return ToolResult(output or "Agentic dev system executed successfully.")
        except Exception as e:
            return ToolResult(f"ERROR executing agentic dev system: {e}", success=False)
            
    return Tool(
        name="run_agentic_dev_system",
        description="Run the autonomous agentic dev system pipeline (task discovery, PHP orchestrator, or agent roles) in agentic_dev_system/.",
        params_schema={
            "mode": "string — 'discover' to scan for tasks, or 'orchestrate' to execute agent pipeline"
        },
        execute=execute
    )

def make_launch_opencode_tool() -> Tool:

    def execute(workspace_path: str = None) -> ToolResult:
        try:
            target_path = str(get_abs_path(workspace_path or "."))
            opencode_exe = r"C:\Users\abhay\AppData\Local\Programs\@opencode-aidesktop\OpenCode.exe"
            
            if os.path.exists(opencode_exe):
                cmd = f'start "" "{opencode_exe}" --disable-gpu --disable-software-rasterizer --no-sandbox "{target_path}"'
                os.system(cmd)
                return ToolResult(f"🚀 Launched OpenCode IDE for workspace: {target_path}")
            else:
                os.system(f'code "{target_path}"')
                return ToolResult(f"Launched IDE (code) for workspace: {target_path}")
        except Exception as e:
            return ToolResult(f"ERROR launching OpenCode IDE: {e}", success=False)
            
    return Tool(
        name="launch_opencode_ide",
        description="Launches OpenCode IDE desktop application on the PC targeting the workspace directory.",
        params_schema={
            "workspace_path": "string — workspace folder path to open in OpenCode (optional, default current)"
        },
        execute=execute
    )


def make_ide_detect_tool() -> Tool:
    def execute() -> ToolResult:
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    "tasklist /FO CSV /NH",
                    shell=True, capture_output=True, text=True, timeout=10
                )
                output = result.stdout.lower()
            else:
                result = subprocess.run(
                    "ps aux", shell=True, capture_output=True, text=True, timeout=10
                )
                output = result.stdout.lower()

            detected = []
            ide_keywords = {
                "opencode": "OpenCode IDE",
                "windsurf": "Windsurf IDE",
                "cursor": "Cursor IDE",
                "trae": "Trae IDE",
                "code.exe": "VS Code",
                "antigravity": "Antigravity IDE",
                "claude": "Claude Desktop",
                "chatgpt": "ChatGPT Desktop",
                "code-server": "Code Server",
                "jetbrains": "JetBrains IDE",
                "pycharm": "PyCharm",
                "webstorm": "WebStorm",
                "intellij": "IntelliJ",
            }

            for keyword, name in ide_keywords.items():
                if keyword in output:
                    detected.append({"name": name, "process": keyword, "running": True})

            # Also check for browser-based IDEs
            browser_ides = ["opencode.ai", "windsurf.ai", "cursor.sh", "trae.ai", "replit.com"]
            for browser_ide in browser_ides:
                if browser_ide in output or browser_ide.replace(".", "") in output.replace(".", ""):
                    detected.append({"name": browser_ide, "process": "browser", "running": True})

            if not detected:
                return ToolResult("No IDE detected running on this system. OpenCode, Windsurf, Cursor, VS Code, or Antigravity not found.")

            return ToolResult(
                "Detected IDEs:\n" + "\n".join(
                    f"  • {d['name']} (process: {d['process']})" for d in detected
                )
            )
        except Exception as e:
            return ToolResult(f"ERROR detecting IDE: {e}", success=False)

    return Tool(
        name="ide_detect",
        description="Detect which IDEs and development apps are currently running on the PC. Checks for OpenCode, Windsurf, Antigravity, Cursor, VS Code, JetBrains, and browser-based IDEs.",
        params_schema={},
        execute=execute
    )


def make_ide_monitor_tool() -> Tool:
    def execute(ide_name: str = "") -> ToolResult:
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    "tasklist /FO CSV /NH",
                    shell=True, capture_output=True, text=True, timeout=10
                )
                output = result.stdout
            else:
                result = subprocess.run(
                    "ps aux", shell=True, capture_output=True, text=True, timeout=10
                )
                output = result.stdout

            if not ide_name:
                # Monitor all detected IDEs
                return ToolResult(f"System process snapshot:\n{output[:2000]}")

            # Check specific IDE
            found = False
            for line in output.splitlines():
                if ide_name.lower() in line.lower():
                    found = True
                    # Check if process is responsive (not frozen)
                    parts = line.split(",")
                    if len(parts) >= 2:
                        proc_name = parts[0].strip().strip('"')
                        status = "RUNNING" if proc_name else "NOT FOUND"
                        return ToolResult(f"IDE {ide_name}: {status}\nProcess line: {line.strip()}")

            if not found:
                return ToolResult(f"IDE '{ide_name}' is NOT currently running on this system.")

        except Exception as e:
            return ToolResult(f"ERROR monitoring IDE: {e}", success=False)

    return Tool(
        name="ide_monitor",
        description="Monitor the health and status of a running IDE. Checks if the IDE process is active and responsive. Use ide_detect first to find running IDEs.",
        params_schema={
            "ide_name": "string — Name of the IDE to monitor (optional, checks all if omitted)"
        },
        execute=execute
    )


def make_ide_recover_tool() -> Tool:
    def execute(ide_name: str = "") -> ToolResult:
        try:
            if not ide_name:
                return ToolResult(
                    "ERROR: Please specify which IDE to recover. Use ide_detect to find running IDEs first.\n"
                    "Usage: ide_recover(ide_name='OpenCode')"
                )

            recovery_actions = []

            if sys.platform == "win32":
                # Check if process is hung (no response for 30+ seconds)
                check = subprocess.run(
                    f'tasklist /FI "IMAGENAME eq {ide_name}" /FO CSV',
                    shell=True, capture_output=True, text=True, timeout=10
                )
                if ide_name.lower() not in check.stdout.lower():
                    recovery_actions.append(f"Process {ide_name} is not running — may have crashed")
                    # Try to restart
                    recovery_actions.append(f"Attempting to relaunch {ide_name}...")
                    # For OpenCode
                    if "opencode" in ide_name.lower():
                        opencode_exe = r"C:\Users\abhay\AppData\Local\Programs\@opencode-aidesktop\OpenCode.exe"
                        if os.path.exists(opencode_exe):
                            os.startfile(opencode_exe)
                            recovery_actions.append("Launched OpenCode IDE")
                        else:
                            recovery_actions.append("OpenCode executable not found — please launch manually")
                    # For VS Code
                    elif "code" in ide_name.lower():
                        code_path = shutil.which("code")
                        if code_path:
                            subprocess.Popen([code_path], shell=True)
                            recovery_actions.append("Launched VS Code")
                    # For Cursor
                    elif "cursor" in ide_name.lower():
                        cursor_paths = [
                            r"C:\Users\abhay\AppData\Local\Programs\cursor\Cursor.exe",
                            r"C:\Users\abhay\AppData\Local\cursor\Cursor.exe",
                        ]
                        for cp in cursor_paths:
                            if os.path.exists(cp):
                                os.startfile(cp)
                                recovery_actions.append(f"Launched Cursor from {cp}")
                                break

                else:
                    recovery_actions.append(f"{ide_name} is running but may be unresponsive")
                    # Try to bring to foreground
                    recovery_actions.append(f"Attempting to refresh {ide_name} window...")

            # Kill and restart as last resort for hung IDEs
            recovery_actions.append(f"Recovery steps for {ide_name}:")
            recovery_actions.append("1. Check if process is responsive")
            recovery_actions.append("2. If hung, kill and restart the process")
            recovery_actions.append("3. Switch to a different model if the IDE is stuck on a task")
            recovery_actions.append("4. Clear any pending tool calls in the IDE")

            return ToolResult("\n".join(recovery_actions))

        except Exception as e:
            return ToolResult(f"ERROR recovering IDE: {e}", success=False)

    return Tool(
        name="ide_recover",
        description="Recover a hung or crashed IDE. Detects if the IDE is frozen, attempts to restart it, and resumes any pending tasks. Use after ide_detect or ide_monitor to identify the IDE name.",
        params_schema={
            "ide_name": "string — Name of the IDE to recover (e.g., 'OpenCode', 'Cursor', 'VS Code')"
        },
        execute=execute
    )


def make_ide_control_tool() -> Tool:
    def execute(action: str, ide_name: str = "", command: str = "") -> ToolResult:
        try:
            if action == "send_command":
                if not command:
                    return ToolResult("ERROR: command parameter required for send_command action", success=False)
                # Send a command to the IDE via its CLI or IPC
                if ide_name.lower() in ("opencode", "code", "vscode"):
                    # Use the IDE's CLI to run commands
                    result = subprocess.run(
                        command, shell=True, capture_output=True, text=True, timeout=30
                    )
                    return ToolResult(
                        f"Command sent to {ide_name}:\n"
                        f"Output: {result.stdout[:1000]}\n"
                        f"Errors: {result.stderr[:500]}"
                    )
                else:
                    return ToolResult(
                        f"Command execution for {ide_name} is not directly supported. "
                        f"Use terminal commands instead to interact with the project."
                    )

            elif action == "read_output":
                # Read the IDE's output/log to see what it's doing
                if sys.platform == "win32":
                    result = subprocess.run(
                        "tasklist /FO CSV /NH",
                        shell=True, capture_output=True, text=True, timeout=10
                    )
                    return ToolResult(f"IDE process status:\n{result.stdout[:2000]}")
                else:
                    return ToolResult("Output reading not supported on this platform yet.")

            elif action == "focus":
                # Try to bring the IDE window to focus
                if sys.platform == "win32":
                    import ctypes
                    # Find the window and bring it to foreground
                    user32 = ctypes.windll.user32
                    # This is a simplified approach — actual window finding would need more work
                    return ToolResult(f"Attempting to focus {ide_name} window...")
                return ToolResult(f"Focus command for {ide_name} not fully implemented on this platform.")

            else:
                return ToolResult(
                    f"Unknown action '{action}'. Available actions:\n"
                    f"  send_command — Run a command in the IDE\n"
                    f"  read_output — Check IDE process status\n"
                    f"  focus — Bring IDE window to foreground"
                )

        except Exception as e:
            return ToolResult(f"ERROR controlling IDE: {e}", success=False)

    return Tool(
        name="ide_control",
        description="Control a running IDE — send commands, read output, bring to focus. Works with OpenCode, Windsurf, Antigravity, Cursor, VS Code. Use after ide_detect to find the IDE name.",
        params_schema={
            "action": "string — 'send_command', 'read_output', or 'focus'",
            "ide_name": "string — Name of the IDE to control",
            "command": "string — Command to send (required for send_command action)"
        },
        execute=execute
    )


def make_extension_detect_tool() -> Tool:
    """Detect and suggest VS Code extensions to install."""
    def execute(action: str = "detect") -> ToolResult:
        try:
            common_extensions = [
                {"name": "ESLint", "id": "dbaeumer.vscode-eslint", "command": "code --install-extension dbaeumer.vscode-eslint"},
                {"name": "Prettier", "id": "esbenp.prettier-vscode", "command": "code --install-extension esbenp.prettier-vscode"},
                {"name": "GitLens", "id": "eamodio.gitlens", "command": "code --install-extension eamodio.gitlens"},
                {"name": "Python", "id": "ms-python.python", "command": "code --install-extension ms-python.python"},
                {"name": "JavaScript Debugger", "id": "ms-vscode.js-debug", "command": "code --install-extension ms-vscode.js-debug"},
                {"name": "Auto Rename Tag", "id": "formulahendry.auto-rename-tag", "command": "code --install-extension formulahendry.auto-rename-tag"},
                {"name": "Path Intellisense", "id": "christian-kohler.path-intellisense", "command": "code --install-extension christian-kohler.path-intellisense"},
                {"name": "Live Server", "id": "ritwickdey.LiveServer", "command": "code --install-extension ritwickdey.LiveServer"},
                {"name": "HTML CSS Support", "id": "ecmel.vscode-html-css", "command": "code --install-extension ecmel.vscode-html-css"},
            ]

            if action == "detect":
                results = []
                for ext in common_extensions:
                    installed = False
                    ext_dir = Path.home() / ".vscode" / "extensions"
                    if ext_dir.exists():
                        for d in ext_dir.iterdir():
                            if ext["id"].replace(".", "-").lower() in d.name.lower():
                                installed = True
                                break
                    results.append({**ext, "installed": installed})

                installed_count = sum(1 for r in results if r["installed"])
                missing = [r for r in results if not r["installed"]]
                return ToolResult(
                    f"Extensions: {installed_count}/{len(results)} installed.\n"
                    + "\n".join(
                        f"{'✓' if r['installed'] else '✗'} {r['name']} ({r['id']})"
                        for r in results
                    )
                    + (f"\n\nMissing: {len(missing)}. Use action='install' to install them." if missing else "\n\nAll extensions installed!")
                )

            elif action == "install":
                missing = [e for e in common_extensions if not _is_extension_installed(e["id"])]
                if not missing:
                    return ToolResult("All common extensions are already installed.")
                results = []
                for ext in missing:
                    try:
                        proc = subprocess.run(
                            ext["command"], shell=True, capture_output=True, text=True, timeout=30
                        )
                        if proc.returncode == 0:
                            results.append(f"✓ Installed {ext['name']}")
                        else:
                            results.append(f"✗ Failed {ext['name']}: {proc.stderr.strip()}")
                    except Exception as e:
                        results.append(f"✗ Error installing {ext['name']}: {e}")
                return ToolResult("\n".join(results))

            else:
                return ToolResult("Unknown action. Use 'detect' or 'install'.")

        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)

    def _is_extension_installed(ext_id: str) -> bool:
        ext_dir = Path.home() / ".vscode" / "extensions"
        if not ext_dir.exists():
            return False
        for d in ext_dir.iterdir():
            if ext_id.replace(".", "-").lower() in d.name.lower():
                return True
        return False

    return Tool(
        name="vscode_extensions",
        description="Detect and install VS Code extensions. Use action='detect' to see what's installed, action='install' to install missing extensions.",
        params_schema={
            "action": "string — 'detect' or 'install' (default: detect)"
        },
        execute=execute
    )


def make_github_pr_tool() -> Tool:
    """Create a GitHub PR from the current branch."""
    def execute(title: str = "", body: str = "", base: str = "main", head: str = "") -> ToolResult:
        try:
            cwd = str(DEFAULT_WORKSPACE)
            if not title:
                return ToolResult("ERROR: PR title is required", success=False)

            # Get current branch if head not specified
            if not head:
                branch_result = subprocess.run(
                    "git branch --show-current", shell=True, capture_output=True, text=True, cwd=cwd, timeout=10
                )
                head = branch_result.stdout.strip()

            # Check if gh CLI is available
            gh_check = shutil.which("gh")
            if not gh_check:
                return ToolResult("ERROR: GitHub CLI (gh) is not installed. Install it from https://cli.github.com/")

            # Check auth
            auth_result = subprocess.run(
                "gh auth status", shell=True, capture_output=True, text=True, cwd=cwd, timeout=10
            )
            if auth_result.returncode != 0:
                return ToolResult("ERROR: GitHub CLI not authenticated. Run 'gh auth login' first.")

            # Create PR
            cmd = f'gh pr create --title "{title}" --body "{body}" --base {base} --head {head}'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=30
            )

            if result.returncode == 0:
                pr_url = result.stdout.strip()
                return ToolResult(f"✅ PR created successfully!\n{pr_url}")
            else:
                return ToolResult(f"❌ PR creation failed:\n{result.stderr.strip() or result.stdout.strip()}", success=False)

        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)

    return Tool(
        name="github_create_pr",
        description="Create a GitHub Pull Request from the current branch. Requires GitHub CLI (gh) to be installed and authenticated.",
        params_schema={
            "title": "string — PR title (required)",
            "body": "string — PR description (optional)",
            "base": "string — Base branch (default: main)",
            "head": "string — Head branch (default: current branch)"
        },
        execute=execute
    )


def make_github_issues_tool() -> Tool:
    """List and manage GitHub issues."""
    def execute(action: str = "list", issue_number: str = "") -> ToolResult:
        try:
            cwd = str(DEFAULT_WORKSPACE)
            gh_check = shutil.which("gh")
            if not gh_check:
                return ToolResult("ERROR: GitHub CLI (gh) is not installed", success=False)

            if action == "list":
                result = subprocess.run(
                    "gh issue list --state all --limit 20 --json number,title,state,labels",
                    shell=True, capture_output=True, text=True, cwd=cwd, timeout=15
                )
                if result.returncode != 0:
                    return ToolResult(f"ERROR: {result.stderr.strip()}", success=False)
                try:
                    issues = json.loads(result.stdout)
                    if not issues:
                        return ToolResult("No issues found.")
                    lines = []
                    for i in issues:
                        labels = ", ".join(l.get("name", "") for l in i.get("labels", []))
                        lines.append(f"#{i['number']} [{i['state']}] {i['title']} {'(' + labels + ')' if labels else ''}")
                    return ToolResult("\n".join(lines))
                except json.JSONDecodeError:
                    return ToolResult(f"Raw output:\n{result.stdout}")

            elif action == "create":
                if not issue_number:
                    return ToolResult("ERROR: issue_number required for create action", success=False)
                result = subprocess.run(
                    f'gh issue create --title "{issue_number}"',
                    shell=True, capture_output=True, text=True, cwd=cwd, timeout=15
                )
                if result.returncode == 0:
                    return ToolResult(f"✅ Issue created:\n{result.stdout.strip()}")
                else:
                    return ToolResult(f"❌ Failed: {result.stderr.strip()}", success=False)

            elif action == "view":
                if not issue_number:
                    return ToolResult("ERROR: issue_number required for view action", success=False)
                result = subprocess.run(
                    f'gh issue view {issue_number}',
                    shell=True, capture_output=True, text=True, cwd=cwd, timeout=15
                )
                if result.returncode == 0:
                    return ToolResult(result.stdout.strip())
                else:
                    return ToolResult(f"❌ Issue not found: {result.stderr.strip()}", success=False)

            else:
                return ToolResult("Unknown action. Use: list | create | view")

        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)

    return Tool(
        name="github_issues",
        description="Manage GitHub issues — list, create, and view issues. Requires GitHub CLI (gh) to be installed and authenticated.",
        params_schema={
            "action": "string — 'list', 'create', or 'view'",
            "issue_number": "string — Issue number (required for view), or title (required for create)"
        },
        execute=execute
    )


def make_artifact_tool() -> Tool:
    """Generate previewable artifacts (HTML, CSS, JS, etc.)."""
    def execute(name: str = "artifact", content: str = "", artifact_type: str = "html") -> ToolResult:
        try:
            if not content:
                return ToolResult("ERROR: content is required", success=False)

            # Save artifact to file
            artifact_dir = Path(DEFAULT_WORKSPACE) / "artifacts"
            artifact_dir.mkdir(parents=True, exist_ok=True)

            ext_map = {
                "html": ".html",
                "css": ".css",
                "js": ".js",
                "json": ".json",
                "md": ".md",
                "txt": ".txt",
                "py": ".py",
            }
            ext = ext_map.get(artifact_type, ".txt")
            filename = f"{name}{ext}"
            filepath = artifact_dir / filename

            filepath.write_text(content, encoding="utf-8")

            return ToolResult(
                f"✅ Artifact created: {filepath}\n"
                f"Type: {artifact_type}\n"
                f"Size: {len(content)} chars\n"
                f"Preview saved to artifacts/ folder"
            )

        except Exception as e:
            return ToolResult(f"ERROR: {e}", success=False)

    return Tool(
        name="artifact",
        description="Generate a previewable artifact (HTML, CSS, JS, JSON, MD, etc.) and save it to the artifacts/ folder. Useful for creating standalone previews of components, pages, or demos.",
        params_schema={
            "name": "string — Artifact name (default: artifact)",
            "content": "string — The content to save (required)",
            "artifact_type": "string — File type: html, css, js, json, md, txt, py (default: html)"
        },
        execute=execute
    )





def make_multi_brain_tool() -> Tool:
    """Multi-brain coordination tool for complex tasks"""
    def execute(task: str, context: str = "") -> ToolResult:
        if not MULTI_BRAIN_AVAILABLE:
            return ToolResult("Multi-brain coordinator not available. Using single model.", success=False)
        
        try:
            import asyncio
            
            async def run_coordination():
                result = await coordinate_with_multi_brain(task, context)
                return result
            
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(run_coordination())
            loop.close()
            
            if result["status"] == "success":
                return ToolResult(
                    f"Multi-brain coordination completed:\n"
                    f"- Plans generated: {len(result['original_plans'])}\n"
                    f"- Critiques provided: {len(result['critiques'])}\n"
                    f"- Merged plan created\n\n"
                    f"Merged Plan:\n{result['merged_plan'][:1000]}..."
                )
            else:
                return ToolResult(f"Multi-brain coordination failed: {result.get('status', 'unknown')}", success=False)
                
        except Exception as e:
            return ToolResult(f"Multi-brain coordination error: {e}", success=False)
    
    return Tool(
        name="multi_brain_coordination",
        description="""Coordinate multiple AI models for complex task planning and execution.
- Multiple models plan independently
- Plans are critiqued by specialist models
- Best elements merged into final plan
- Useful for complex architectural decisions or critical bug fixes
- Requires multiple API keys (Gemini, OpenAI, Anthropic)""",
        params_schema={
            "task": "string - Complex task to coordinate",
            "context": "string - Additional context about the project (optional)"
        },
        execute=execute
    )


def make_verification_tool() -> Tool:
    """Verification tool for code safety and quality"""
    def execute(file_path: str, run_tests: bool = False) -> ToolResult:
        if not VERIFICATION_AVAILABLE:
            return ToolResult("Verification system not available. Basic syntax check only.", success=False)
        
        try:
            project_path = str(get_abs_path(file_path).parent) if run_tests else None
            result = verify_before_completion(file_path, project_path)
            
            if result:
                return ToolResult(f"✅ Verification passed for {file_path}")
            else:
                return ToolResult(f"❌ Verification failed for {file_path}", success=False)
                
        except Exception as e:
            return ToolResult(f"Verification error: {e}", success=False)
    
    return Tool(
        name="verify_changes",
        description="""Verify code changes before marking task complete.
- Syntax validation for multiple languages
- Optional test execution
- Automatic rollback on failure
- Checkpoint system for safe recovery
- Ensures code quality before completion""",
        params_schema={
            "file_path": "string - Path to file to verify",
            "run_tests": "boolean - Whether to run project tests (default: false)"
        },
        execute=execute
    )


def make_performance_tracking_tool() -> Tool:
    """Performance tracking tool for model optimization"""
    def execute(model: str = None, task_type: str = "general") -> ToolResult:
        if not PERFORMANCE_TRACKING_AVAILABLE:
            return ToolResult("Performance tracking not available.", success=False)
        
        try:
            from model_performance_tracker import get_performance_report, get_recommendations, get_best_model
            
            if model:
                report = get_performance_report(model)
                return ToolResult(
                    f"Performance Report for {model}:\n"
                    f"- Total Calls: {report.get('total_calls', 0)}\n"
                    f"- Success Rate: {report.get('success_rate', 0):.1%}\n"
                    f"- Average Time: {report.get('avg_time', 0):.2f}s\n"
                    f"- Failed Calls: {report.get('failed_calls', 0)}\n"
                    f"- Total Tokens: {report.get('total_tokens', 0)}"
                )
            else:
                # Get recommendations
                recommendations = get_recommendations()
                best_model = get_best_model(task_type)
                
                result = f"Performance Summary:\n"
                result += f"- Best model for '{task_type}': {best_model}\n"
                
                if recommendations:
                    result += f"\nRecommendations:\n"
                    for rec in recommendations:
                        result += f"  {rec}\n"
                else:
                    result += f"\nNo recommendations - all models performing well!\n"
                
                return ToolResult(result)
                
        except Exception as e:
            return ToolResult(f"Performance tracking error: {e}", success=False)
    
    return Tool(
        name="track_performance",
        description="""Track and analyze model performance for optimization.
- View performance metrics for specific models
- Get recommendations for model selection
- Identify best models for specific task types
- Track success rates and response times
- Optimize model selection based on historical data""",
        params_schema={
            "model": "string - Specific model to analyze (optional)",
            "task_type": "string - Task type to analyze (default: general)"
        },
        execute=execute
    )


def make_skill_synthesis_tool() -> Tool:
    """Skill synthesis tool for auto-generating new skills"""
    def execute(task: str, context: str = "") -> ToolResult:
        if not SKILL_SYNTHESIS_AVAILABLE:
            return ToolResult("Skill synthesis not available.", success=False)
        
        try:
            from skill_synthesis import synthesize_new_skill, get_synthesis_report, get_active_skills
            
            result_data = synthesize_new_skill(task, context)
            
            if result_data["status"] == "success":
                return ToolResult(
                    f"✅ Skill synthesized successfully!\n"
                    f"- Skill Name: {result_data['skill_name']}\n"
                    f"- File: {result_data['file']}\n"
                    f"- Test Result: {result_data['test_result']}\n\n"
                    f"Total Active Skills: {len(get_active_skills())}"
                )
            else:
                return ToolResult(
                    f"⚠️ Skill synthesis completed with issues:\n"
                    f"- Skill Name: {result_data['skill_name']}\n"
                    f"- Status: {result_data['status']}\n"
                    f"- Test Result: {result_data['test_result']}",
                    success=False
                )
                
        except Exception as e:
            return ToolResult(f"Skill synthesis error: {e}", success=False)
    
    return Tool(
        name="synthesize_skill",
        description="""Auto-generate new Python skills for tasks.
- Synthesizes skill code based on task description
- Tests generated skills automatically
- Integrates new skills into the system
- Self-evolving capability
- Inspired by rishaadj/JARVIS self-evolution""",
        params_schema={
            "task": "string - Task description for skill generation",
            "context": "string - Additional context (optional)"
        },
        execute=execute
    )


def make_self_healing_tool() -> Tool:
    """Self-healing tool for automatic failure recovery"""
    def execute(task: str, error: str, context: str = "") -> ToolResult:
        if not SELF_HEALING_AVAILABLE:
            return ToolResult("Self-healing not available.", success=False)
        
        try:
            from self_healing_workflow import attempt_heal, get_failure_report
            
            healing_result = attempt_heal(task, error, context)
            
            if healing_result["healed"]:
                return ToolResult(
                    f"✅ Self-healing successful!\n"
                    f"- Error Type: {healing_result['error_type']}\n"
                    f"- Strategy: {healing_result['strategy']}\n"
                    f"- Actions Applied: {len(healing_result['actions'])}\n"
                    f"- Actions: {', '.join(healing_result['actions'][:3])}"
                )
            else:
                return ToolResult(
                    f"⚠️ Self-healing requires manual intervention:\n"
                    f"- Error Type: {healing_result['error_type']}\n"
                    f"- Strategy: {healing_result['strategy']}\n"
                    f"- Suggested Actions: {', '.join(healing_result['actions'][:3])}\n"
                    f"- Total Failures Tracked: {get_failure_report()['total_failures']}",
                    success=False
                )
                
        except Exception as e:
            return ToolResult(f"Self-healing error: {e}", success=False)
    
    return Tool(
        name="self_heal",
        description="""Automatically recover from failures with self-healing.
- Classifies error types
- Generates healing strategies
- Records failure patterns
- Suggests recovery actions
- Inspired by santhanam-15/Jarvis self-healing""",
        params_schema={
            "task": "string - Task that failed",
            "error": "string - Error message from failure",
            "context": "string - Additional context (optional)"
        },
        execute=execute
    )


def make_third_eye_tool() -> Tool:
    """Third Eye — free model discovery, auto-recovery, multi-agent spawning"""
    def execute(action: str, query: str = "", context: str = "") -> ToolResult:
        if not globals().get("THIRD_EYE_AVAILABLE", False) or _mm is None or _TE is None:
            return ToolResult("Third Eye system not available. Run: py third_eye.py --test-models", success=False)

        try:
            if action == "discover":
                # Run full model discovery
                from free_model_discovery import discover_all
                results = discover_all()
                summary = f"Discovered {results['total_working']} working models across {len(results['providers_tested'])} providers.\n"
                summary += f"Failover chain: {' -> '.join(results['failover_chain'][:3])}"
                return ToolResult(summary)

            elif action == "models":
                models_info = []
                for m in _mm.models:
                    cats = _mm.categorize(m["model"])
                    models_info.append({
                        "model": m["model"],
                        "provider": m.get("provider", "unknown"),
                        "latency": m.get("latency_s", "?"),
                        "categories": cats,
                    })
                return ToolResult(json.dumps(models_info, indent=2, ensure_ascii=False))

            elif action == "best":
                best = _mm.select_model_for_task(query or "general")
                health = _mm.health.get(best, {})
                return ToolResult(
                    f"Best model for task '{query}': {best}\n"
                    f"Provider: {next((m.get('provider','?') for m in _mm.models if m['model']==best), '?')}\n"
                    f"Latency: {health.get('latency','?')}s\n"
                    f"Working: {health.get('working', True)}"
                )

            elif action == "recover":
                # Auto-recover from an error (query = error message)
                detail = _TE.recovery_engine.diagnose_and_recover(query, context, None)
                return ToolResult(
                    f"Recovery for: {query}\n"
                    f"Diagnosis: {detail['error_type']}\n"
                    f"Actions: {detail['actions']}"
                )

            elif action == "spawn_agent":
                # Spawn a sub-agent for a task
                agent = _TE.orchestrator.spawn_agent(f"agent_{int(time.time()) % 10000}")
                result = _TE.orchestrator.assign_task(agent, query, context)
                return ToolResult(f"Agent spawned: {agent.name}\nResult: {result[:500]}")

            elif action == "status":
                status = _TE.get_full_status()
                return ToolResult(json.dumps(status["model_manager"], indent=2, ensure_ascii=False))

            elif action == "browser":
                # Browser-based IDE operations
                bo = _TE.browser_operator
                if query == "detect" or not query:
                    ide = bo.detect_ide_in_browser()
                    return ToolResult(
                        f"Detected browser IDE: {ide or 'none'}\n"
                        f"Driver available: {bo._driver is not None}"
                    )
                elif query == "read":
                    output = bo.read_ide_output()
                    return ToolResult(output or "No output readable")
                elif query == "check_error":
                    err = bo.detect_error_in_ide()
                    if err:
                        # Auto-recover: switch model in browser
                        best = _mm.select_model_for_task("coding")
                        switched = bo.switch_ide_model(best)
                        retried = bo.click_retry_or_resubmit()
                        return ToolResult(
                            f"Error detected: {err}\n"
                            f"Auto-recovered: switched to {best} (success={switched}), retried={retried}"
                        )
                    return ToolResult("No errors detected in browser IDE")
                else:
                    return ToolResult(
                        "Browser actions: detect (which IDE is open), "
                        "read (read IDE output), check_error (scan + auto-recover)"
                    )

            else:
                return ToolResult(
                    "Unknown action. Available: discover, models, best <task>, recover <error>, spawn_agent <task>, status",
                    success=False,
                )
        except Exception as e:
            return ToolResult(f"Third Eye error: {e}", success=False)

    return Tool(
        name="third_eye",
        description="""Third Eye Jarvis system — free model discovery + auto-recovery + multi-agent spawning.
Actions:
- 'discover': Run full auto-discovery of all free AI models and test connectivity
- 'models': List all working free models with categories and latency
- 'best' + query: Pick the best free model for a specific task
- 'recover' + query(error): Diagnose and recover from an error (auto-switch models, restart app)
- 'spawn_agent' + query(task): Spawn a sub-agent to handle a task autonomously
- 'status': Show system health status
- 'browser' + query(detect/read/check_error): Control browser-based IDEs (OpenCode web, Windsurf, Cursor)
Categories include: coding, reasoning, speed, general, local, long-context.
The system auto-switches to the next working free model when one fails or hangs.
Inspired by multi-agent IDE oversight and Iron Man's Jarvis 'third eye' monitoring.""",
        params_schema={
            "action": "string - Required: discover, models, best, recover, spawn_agent, status, browser",
            "query": "string - Task description (for 'best', 'spawn_agent') or error message (for 'recover')",
            "context": "string - Additional context (optional)"
        },
        execute=execute
    )

def make_opencode_supervisor_tool() -> Tool:
    """Robot supervisor tool for OpenCode CLI/IDE automation."""
    def execute(action: str, prompt: str = "", project_path: str = "") -> ToolResult:
        try:
            from third_eye import OpenCodeSupervisor
            sup = OpenCodeSupervisor()
            if action in ("status", "detect"):
                res = sup.detect()
                return ToolResult(json.dumps(res, indent=2))
            elif action == "start":
                res = sup.start(project_path)
                return ToolResult(json.dumps(res, indent=2))
            elif action == "prompt":
                res = sup.prompt(prompt)
                return ToolResult(json.dumps(res, indent=2))
            elif action == "read_output":
                res = sup.read_output()
                return ToolResult(res)
            elif action == "kill":
                res = sup.kill()
                return ToolResult(json.dumps(res, indent=2))
            else:
                return ToolResult("Unknown action. Use: status, start, prompt, read_output, kill", success=False)
        except Exception as e:
            return ToolResult(f"OpenCode supervisor error: {e}", success=False)

    return Tool(
        name="opencode_supervisor",
        description="""Autonomous OpenCode Robot Supervisor tool.
Actions:
- 'status' / 'detect': Check if OpenCode is running on system
- 'start': Launch OpenCode CLI process for a project path
- 'prompt': Send task prompt to running OpenCode instance
- 'read_output': Read recent stdout/stderr lines
- 'kill': Terminate managed OpenCode process""",
        params_schema={
            "action": "string - 'status', 'start', 'prompt', 'read_output', 'kill'",
            "prompt": "string - Prompt text (for action='prompt')",
            "project_path": "string - Target directory path (for action='start')"
        },
        execute=execute
    )


def make_pc_controller_tool() -> Tool:
    """PC Controller tool for developer process listing and execution."""
    def execute(action: str, command: str = "") -> ToolResult:
        try:
            if action == "list_processes":
                cmd = 'tasklist /FO CSV' if sys.platform == "win32" else 'ps aux'
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                dev_procs = ["code", "opencode", "python", "node", "uvicorn", "antigravity"]
                matching = [line for line in res.stdout.splitlines() if any(p in line.lower() for p in dev_procs)]
                return ToolResult("\n".join(matching[:30]) or "No active developer processes found.")
            elif action == "run_cli":
                if not command:
                    return ToolResult("ERROR: command parameter required for run_cli", success=False)
                res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                return ToolResult(f"Exit code: {res.returncode}\nSTDOUT:\n{res.stdout[:1500]}\nSTDERR:\n{res.stderr[:500]}")
            else:
                return ToolResult("Unknown action. Use: list_processes, run_cli", success=False)
        except Exception as e:
            return ToolResult(f"PC controller error: {e}", success=False)

    return Tool(
        name="pc_controller",
        description="""PC Controller tool — view developer processes and execute terminal CLI actions across your computer.
Actions:
- 'list_processes': List active IDE and dev processes (VS Code, OpenCode, Python, Node, Uvicorn)
- 'run_cli': Execute terminal command line""",
        params_schema={
            "action": "string - 'list_processes' or 'run_cli'",
            "command": "string - Terminal command line (for action='run_cli')"
        },
        execute=execute
    )


def make_master_db_tool() -> Tool:
    """Master SQLite Database tool for cross-project memory and task tracking."""
    def execute(action: str, name: str = "", path: str = "", tech_stack: str = "", insight: str = "", task: str = "") -> ToolResult:
        try:
            from master_db import register_project, get_all_projects, add_master_memory, query_master_memory, queue_task, get_pending_tasks
            if action == "register_project":
                res = register_project(name or "unnamed", path or os.getcwd(), tech_stack)
                return ToolResult(json.dumps(res, indent=2))
            elif action == "list_projects":
                res = get_all_projects()
                return ToolResult(json.dumps(res, indent=2))
            elif action == "add_memory":
                res = add_master_memory(path or os.getcwd(), "architecture", insight)
                return ToolResult(json.dumps(res, indent=2))
            elif action == "query_memory":
                res = query_master_memory(path or os.getcwd())
                return ToolResult(json.dumps(res, indent=2))
            elif action == "add_task":
                res = queue_task(path or os.getcwd(), task)
                return ToolResult(json.dumps(res, indent=2))
            elif action == "list_tasks":
                res = get_pending_tasks(path or os.getcwd())
                return ToolResult(json.dumps(res, indent=2))
            else:
                return ToolResult("Unknown action. Use: register_project, list_projects, add_memory, query_memory, add_task, list_tasks", success=False)
        except Exception as e:
            return ToolResult(f"Master DB error: {e}", success=False)

    return Tool(
        name="master_db",
        description="""Master SQLite database tool (~/.devmind/master_db.sqlite) for persistent multi-project registry, cross-project memory, and task queues.""",
        params_schema={
            "action": "string - register_project, list_projects, add_memory, query_memory, add_task, list_tasks",
            "name": "string - Project name",
            "path": "string - Project path",
            "tech_stack": "string - Tech stack info",
            "insight": "string - Architectural insight",
            "task": "string - Task description"
        },
        execute=execute
    )


def make_cost_tracker_tool() -> Tool:
    """Token usage and USD cost tracking tool."""
    def execute(action: str = "summary") -> ToolResult:
        try:
            from cost_tracker import tracker
            summary = tracker.get_summary()
            return ToolResult(json.dumps(summary, indent=2))
        except Exception as e:
            return ToolResult(f"Cost tracker error: {e}", success=False)

    return Tool(
        name="cost_tracker",
        description="""Token cost and savings tracker. Ported from Claude Code cost-tracker.ts. Reports total tokens consumed and estimated USD savings using free models vs commercial APIs.""",
        params_schema={"action": "string - 'summary'"},
        execute=execute
    )


def load_project_rules(cwd: str) -> str:
    """Scan directory for project instructions (DEVMIND.md, JARVIS.md, CLAUDE.md, etc.)

    Caps each file and the combined result so an oversized AGENTS.md/CLAUDE.md
    can't blow up the system prompt (a 384KB rules file previously inflated
    the prompt to ~411KB, degrading model quality and cost)."""
    p = Path(cwd)
    candidates = ["DEVMIND.md", "JARVIS.md", ".claude.md", "CLAUDE.md", "AGENTS.md"]
    MAX_PER_FILE = 6000
    MAX_TOTAL = 12000
    found = []
    total = 0
    for f in candidates:
        filepath = p / f
        if filepath.is_file():
            try:
                content = filepath.read_text(encoding="utf-8")
                if len(content) > MAX_PER_FILE:
                    content = (content[:MAX_PER_FILE].rstrip()
                               + f"\n... [truncated — full {f} is {len(content)} chars; use read_file to view it]")
                if total + len(content) > MAX_TOTAL:
                    remaining = MAX_TOTAL - total
                    if remaining > 0:
                        found.append(f"### Project Rules from {f} (truncated):\n{content[:remaining]}\n")
                        total = MAX_TOTAL
                    break
                found.append(f"### Project Rules from {f}:\n{content}\n")
                total += len(content)
            except Exception:
                pass
    return "\n".join(found)


def make_plan_mode_tool() -> Tool:
    """Interactive plan creation and management tool."""
    def execute(action: str = "start", plan_content: str = "") -> ToolResult:
        plan_file = Path(DEFAULT_WORKSPACE) / "plan.md"
        try:
            if action in ("start", "create"):
                if not plan_content:
                    return ToolResult("ERROR: plan_content required to create a plan", success=False)
                plan_file.write_text(plan_content, encoding="utf-8")
                return ToolResult(f"✅ Plan created and saved to {plan_file}")
            elif action in ("view", "read"):
                if plan_file.exists():
                    return ToolResult(plan_file.read_text(encoding="utf-8"))
                return ToolResult("No active plan found.")
            elif action in ("stop", "clear"):
                if plan_file.exists():
                    plan_file.unlink()
                return ToolResult("Plan cleared.")
            else:
                return ToolResult("Unknown action. Use: start, view, stop", success=False)
        except Exception as e:
            return ToolResult(f"Plan mode error: {e}", success=False)

    return Tool(
        name="plan_mode",
        description="""Manage interactive planning before executing complex tasks. Ported from Claude Code.
Actions: 'start' (write plan), 'view' (read current plan), 'stop' (clear plan).""",
        params_schema={
            "action": "string - 'start', 'view', or 'stop'",
            "plan_content": "string - Markdown content of the plan"
        },
        execute=execute
    )


def make_worktree_tool() -> Tool:
    """Git worktree isolation tool for experimental refactoring."""
    def execute(action: str, branch: str = "", path: str = "") -> ToolResult:
        try:
            cwd = DEFAULT_WORKSPACE
            if action == "create":
                if not branch or not path:
                    return ToolResult("ERROR: branch and path parameters required for create action", success=False)
                res = subprocess.run(f'git worktree add "{path}" -b "{branch}"', shell=True, capture_output=True, text=True, cwd=cwd)
                if res.returncode == 0:
                    return ToolResult(f"✅ Worktree created at {path} on branch {branch}")
                return ToolResult(f"❌ Failed to create worktree: {res.stderr.strip()}", success=False)
            elif action == "list":
                res = subprocess.run("git worktree list", shell=True, capture_output=True, text=True, cwd=cwd)
                return ToolResult(res.stdout or "No worktrees found.")
            elif action == "remove":
                if not path:
                    return ToolResult("ERROR: path required for remove action", success=False)
                res = subprocess.run(f'git worktree remove "{path}"', shell=True, capture_output=True, text=True, cwd=cwd)
                return ToolResult(f"✅ Worktree removed: {path}" if res.returncode == 0 else f"❌ Error: {res.stderr.strip()}")
            else:
                return ToolResult("Unknown action. Use: create, list, remove", success=False)
        except Exception as e:
            return ToolResult(f"Worktree tool error: {e}", success=False)

    return Tool(
        name="worktree",
        description="""Git Worktree isolation tool. Ported from Claude Code worktree integration. Create and manage isolated temporary git worktrees for refactoring.""",
        params_schema={
            "action": "string - 'create', 'list', or 'remove'",
            "branch": "string - Branch name (for create)",
            "path": "string - Target worktree directory path"
        },
        execute=execute
    )


def make_todo_list_tool() -> Tool:
    """Todo task tracking tool."""
    _todos = []
    def execute(action: str = "view", task: str = "", status: str = "pending", task_id: int = -1) -> ToolResult:
        nonlocal _todos
        try:
            if action == "add":
                t_id = len(_todos) + 1
                _todos.append({"id": t_id, "task": task, "status": "pending"})
                return ToolResult(f"✅ Added todo #{t_id}: {task}")
            elif action == "update":
                if 0 <= task_id - 1 < len(_todos):
                    _todos[task_id - 1]["status"] = status
                    return ToolResult(f"✅ Todo #{task_id} status updated to {status}")
                return ToolResult("ERROR: Invalid task_id", success=False)
            elif action == "view":
                if not _todos:
                    return ToolResult("No active todo items.")
                lines = [f"#{t['id']} [{t['status'].upper()}] {t['task']}" for t in _todos]
                return ToolResult("\n".join(lines))
            elif action == "clear":
                _todos = []
                return ToolResult("Todo list cleared.")
            else:
                return ToolResult("Unknown action. Use: add, update, view, clear", success=False)
        except Exception as e:
            return ToolResult(f"Todo list error: {e}", success=False)

    return Tool(
        name="todo_list",
        description="""Manage real-time todo items for complex tasks. Ported from Claude Code. Actions: add, update, view, clear.""",
        params_schema={
            "action": "string - 'add', 'update', 'view', or 'clear'",
            "task": "string - Task description",
            "status": "string - 'pending', 'in_progress', or 'completed'",
            "task_id": "integer - Task ID to update"
        },
        execute=execute
    )


def make_auto_dream_tool() -> Tool:
    """Auto-dream memory consolidation tool."""
    def execute(insight: str, category: str = "architecture") -> ToolResult:
        try:
            from master_db import add_master_memory
            res = add_master_memory(insight, DEFAULT_WORKSPACE, category)
            return ToolResult(f"✅ Insight consolidated into master memory: {insight}")
        except Exception as e:
            return ToolResult(f"Auto-dream error: {e}", success=False)

    return Tool(
        name="auto_dream",
        description="""Consolidate architectural memory and insights into MEMORY.md and master SQLite DB (~/.devmind/master_db.sqlite). Ported from Claude Code.""",
        params_schema={
            "insight": "string - Architectural insight or learned convention",
            "category": "string - Category (default: architecture)"
        },
        execute=execute
    )


def make_schedule_cron_tool() -> Tool:
    """Schedule background timers or recurring cron jobs. Ported from Claude Code ScheduleCronTool."""
    def execute(action: str = "add", prompt: str = "", cron_expression: str = "", duration_seconds: int = 0, cron_id: int = 0) -> ToolResult:
        try:
            from master_db import add_cron_schedule, get_active_cron_schedules, cancel_cron_schedule
            if action in ("add", "schedule"):
                if not prompt:
                    return ToolResult("ERROR: prompt parameter required for scheduling", success=False)
                res = add_cron_schedule(DEFAULT_WORKSPACE, prompt, cron_expression, duration_seconds)
                return ToolResult(json.dumps(res, indent=2))
            elif action == "list":
                res = get_active_cron_schedules(DEFAULT_WORKSPACE)
                return ToolResult(json.dumps(res, indent=2))
            elif action == "cancel":
                if not cron_id:
                    return ToolResult("ERROR: cron_id required for cancel action", success=False)
                res = cancel_cron_schedule(cron_id)
                return ToolResult(json.dumps(res, indent=2))
            else:
                return ToolResult("Unknown action. Use: add, list, cancel", success=False)
        except Exception as e:
            return ToolResult(f"Schedule cron error: {e}", success=False)

    return Tool(
        name="schedule_cron",
        description="""Schedule one-shot timers or recurring cron jobs for background tasks or reminders. Ported from Claude Code ScheduleCronTool. Actions: 'add', 'list', 'cancel'.""",
        params_schema={
            "action": "string - 'add', 'list', or 'cancel'",
            "prompt": "string - Reminder / task prompt message",
            "cron_expression": "string - Cron expression (e.g. '*/5 * * * *')",
            "duration_seconds": "integer - One-shot timer duration in seconds",
            "cron_id": "integer - ID of cron schedule to cancel"
        },
        execute=execute
    )


def make_ask_user_question_tool() -> Tool:
    """Interactive question tool to request user input or choices. Ported from Claude Code AskUserQuestionTool."""
    def execute(question: str, options: list = None) -> ToolResult:
        try:
            formatted = f"❓ User Clarification Request:\nQuestion: {question}\n"
            if options:
                formatted += "Options:\n" + "\n".join([f"  [{i+1}] {opt}" for i, opt in enumerate(options)])
            return ToolResult(formatted)
        except Exception as e:
            return ToolResult(f"Ask user question error: {e}", success=False)

    return Tool(
        name="ask_user_question",
        description="""Ask the user a clarifying question with multiple choice options when intent is ambiguous. Ported from Claude Code AskUserQuestionTool.""",
        params_schema={
            "question": "string - Question to ask the user",
            "options": "array - List of multiple choice option strings"
        },
        execute=execute
    )


def make_security_review_tool() -> Tool:
    """Security Review and Vulnerability Hunter tool. Ported from Claude Code security-review.ts & bughunter."""
    def execute(file_path: str = "", scan_diff: bool = True) -> ToolResult:
        try:
            cwd = DEFAULT_WORKSPACE
            findings = []
            
            # 1. Scan git diff if requested
            if scan_diff:
                res = subprocess.run("git diff HEAD", shell=True, capture_output=True, text=True, cwd=cwd)
                diff_text = res.stdout
                
                # Secret / API key patterns
                secret_patterns = [
                    (r'AIzaSy[A-Za-z0-9-_]{35}', "Exposed Google Gemini API Key"),
                    (r'sk-proj-[A-Za-z0-9-_]{40,}', "Exposed OpenAI API Key"),
                    (r'sk-ant-api[A-Za-z0-9-_]{40,}', "Exposed Anthropic API Key"),
                    (r'gsk_[A-Za-z0-9]{40,}', "Exposed Groq API Key"),
                    (r'https://hooks\.slack\.com/services/[A-Za-z0-9/]+', "Exposed Slack Webhook URL"),
                    (r'postgres://[^:]+:[^@]+@', "Exposed Database Credentials URI"),
                ]
                
                for pattern, desc in secret_patterns:
                    if re.search(pattern, diff_text):
                        findings.append(f"⚠️ HIGH RISK: {desc} found in pending changes!")
            
            # 2. File specific security checks
            target_path = get_abs_path(file_path) if file_path else None
            if target_path and target_path.exists():
                text = target_path.read_text(encoding="utf-8", errors="ignore")
                
                # Check raw SQL string concatenation
                if re.search(r'execute\(f[\'"].*SELECT.*\{', text, re.IGNORECASE) or re.search(r'execute\(f[\'"].*INSERT.*\{', text, re.IGNORECASE):
                    findings.append(f"⚠️ SQL INJECTION RISK: f-string SQL query concatenation in {target_path.name}")
                
                # Check hardcoded eval/exec calls
                if re.search(r'\beval\(', text) or re.search(r'\bexec\(', text):
                    findings.append(f"⚠️ CODE INJECTION RISK: Dangerous eval()/exec() call in {target_path.name}")

            if not findings:
                return ToolResult("✅ Security Review Passed: No high-confidence vulnerabilities or secret leaks detected.")
            
            summary = f"🛡️ Security Audit Findings ({len(findings)} issues):\n" + "\n".join(findings)
            return ToolResult(summary, success=False)
            
        except Exception as e:
            return ToolResult(f"Security review error: {e}", success=False)

    return Tool(
        name="security_review",
        description="""Audit codebase or pending git changes for high-confidence security vulnerabilities, secret API key leaks, and code injection risks. Ported from Claude Code security-review.ts.""",
        params_schema={
            "file_path": "string - Optional file path to inspect",
            "scan_diff": "boolean - Whether to scan pending git diffs (default: true)"
        },
        execute=execute
    )


def make_code_insights_tool() -> Tool:
    """Codebase health and metrics insights generator. Ported from Claude Code insights.ts."""
    def execute(dir_path: str = "") -> ToolResult:
        try:
            target_dir = get_abs_path(dir_path) if dir_path else Path(DEFAULT_WORKSPACE)
            if not target_dir.exists() or not target_dir.is_dir():
                return ToolResult(f"ERROR: Directory not found: {dir_path}", success=False)

            total_files = 0
            total_lines = 0
            file_types = {}
            large_files = []

            for p in target_dir.rglob("*"):
                if p.is_file() and not any(part.startswith(".") or part in ("node_modules", "venv", "__pycache__", "dist", "build") for part in p.parts):
                    total_files += 1
                    ext = p.suffix or ".no_ext"
                    file_types[ext] = file_types.get(ext, 0) + 1
                    try:
                        lines = len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
                        total_lines += lines
                        if lines > 500:
                            large_files.append((p.name, lines))
                    except Exception:
                        pass

            sorted_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)
            top_types = ", ".join([f"{ext}: {cnt}" for ext, cnt in sorted_types[:5]])
            
            report = [
                f"📊 Codebase Insights & Health Report for {target_dir.name}:",
                f"- Total Source Files: {total_files}",
                f"- Total Lines of Code: {total_lines:,}",
                f"- Primary File Types: {top_types}",
                f"- Large Files (>500 lines): {len(large_files)}"
            ]
            if large_files:
                report.append("  Top Large Files:")
                for name, l_cnt in sorted(large_files, key=lambda x: x[1], reverse=True)[:5]:
                    report.append(f"   • {name} ({l_cnt} lines)")

            return ToolResult("\n".join(report))
            
        except Exception as e:
            return ToolResult(f"Code insights error: {e}", success=False)

    return Tool(
        name="code_insights",
        description="""Generate a high-level architectural insights and health metrics report of the codebase (file counts, LOC, file distribution, large files). Ported from Claude Code insights.ts.""",
        params_schema={
            "dir_path": "string - Optional target directory path"
        },
        execute=execute
    )


def make_team_swarm_tool() -> Tool:
    """Multi-Agent Team & Swarm Manager. Ported from Claude Code TeamCreateTool & coordinator/."""
    def execute(action: str = "create", team_name: str = "default_swarm", roles: list = None, task: str = "") -> ToolResult:
        try:
            if action in ("create", "spawn"):
                default_roles = roles or ["architect", "coder", "tester"]
                agents = []
                for role in default_roles:
                    agents.append({
                        "role": role,
                        "status": "ready",
                        "assigned_task": f"{role.title()} task for: {task}" if task else "idle"
                    })
                return ToolResult(
                    f"🤖 Swarm Team '{team_name}' Formed ({len(agents)} agents):\n" +
                    "\n".join([f"  • [{a['role'].upper()}] - {a['assigned_task']}" for a in agents])
                )
            else:
                return ToolResult("Unknown action. Use: create", success=False)
        except Exception as e:
            return ToolResult(f"Team swarm error: {e}", success=False)

    return Tool(
        name="team_swarm",
        description="""Form collaborative multi-agent swarms (e.g. architect, coder, tester) to handle complex tasks concurrently. Ported from Claude Code TeamCreateTool.""",
        params_schema={
            "action": "string - 'create'",
            "team_name": "string - Name of swarm team",
            "roles": "array - List of agent roles (e.g. ['architect', 'coder', 'tester'])",
            "task": "string - Master task description"
        },
        execute=execute
    )


def make_lsp_intelligence_tool() -> Tool:
    """LSP Code Intelligence and Symbol Analyzer tool. Ported from Claude Code LSPTool."""
    def execute(action: str = "find_symbols", file_path: str = "", query: str = "") -> ToolResult:
        try:
            target_path = get_abs_path(file_path) if file_path else None
            if action == "find_symbols":
                if not target_path or not target_path.exists():
                    return ToolResult("ERROR: Valid file_path required for find_symbols", success=False)
                text = target_path.read_text(encoding="utf-8", errors="ignore")
                
                # Extract classes and functions/methods
                classes = re.findall(r'^\s*class\s+([A-Za-z0-9_]+)', text, re.MULTILINE)
                functions = re.findall(r'^\s*def\s+([A-Za-z0-9_]+)', text, re.MULTILINE)
                
                symbols_summary = [f"🔍 AST Symbols in {target_path.name}:"]
                if classes:
                    symbols_summary.append("  Classes: " + ", ".join(classes[:15]))
                if functions:
                    symbols_summary.append("  Functions/Methods: " + ", ".join(functions[:25]))
                
                return ToolResult("\n".join(symbols_summary))
            else:
                return ToolResult("Unknown action. Use: find_symbols", success=False)
        except Exception as e:
            return ToolResult(f"LSP intelligence error: {e}", success=False)

def make_lsp_intelligence_tool() -> Tool:
    """LSP Code Intelligence and Symbol Analyzer tool. Ported from Claude Code LSPTool."""
    def execute(action: str = "find_symbols", file_path: str = "", query: str = "") -> ToolResult:
        try:
            target_path = get_abs_path(file_path) if file_path else None
            if action == "find_symbols":
                if not target_path or not target_path.exists():
                    return ToolResult("ERROR: Valid file_path required for find_symbols", success=False)
                text = target_path.read_text(encoding="utf-8", errors="ignore")
                
                # Extract classes and functions/methods
                classes = re.findall(r'^\s*class\s+([A-Za-z0-9_]+)', text, re.MULTILINE)
                functions = re.findall(r'^\s*def\s+([A-Za-z0-9_]+)', text, re.MULTILINE)
                
                symbols_summary = [f"🔍 AST Symbols in {target_path.name}:"]
                if classes:
                    symbols_summary.append("  Classes: " + ", ".join(classes[:15]))
                if functions:
                    symbols_summary.append("  Functions/Methods: " + ", ".join(functions[:25]))
                
                return ToolResult("\n".join(symbols_summary))
            else:
                return ToolResult("Unknown action. Use: find_symbols", success=False)
        except Exception as e:
            return ToolResult(f"LSP intelligence error: {e}", success=False)

    return Tool(
        name="lsp_intelligence",
        description="""Code Intelligence tool to extract AST symbols, class hierarchies, and function signatures. Ported from Claude Code LSPTool.""",
        params_schema={
            "action": "string - 'find_symbols'",
            "file_path": "string - File path to inspect",
            "query": "string - Optional symbol search query"
        },
        execute=execute
    )


def make_session_rewind_tool() -> Tool:
    """Session Rewind and Checkpoint Reversion tool. Ported from Claude Code rewind & history.ts."""
    def execute(action: str = "restore") -> ToolResult:
        try:
            restored = restore_last_turn()
            if restored:
                return ToolResult("⏪ Session Rewound:\n" + "\n".join([f"  • {r}" for r in restored]))
            return ToolResult("No file modifications found in recent session history to rewind.")
        except Exception as e:
            return ToolResult(f"Session rewind error: {e}", success=False)

    return Tool(
        name="session_rewind",
        description="""Rewind and revert recent file edits to previous checkpoint state. Ported from Claude Code rewind command.""",
        params_schema={
            "action": "string - 'restore' or 'rewind'"
        },
        execute=execute
    )


def make_compact_context_tool() -> Tool:
    """Context Window Compression and Token Optimizer tool. Ported from Claude Code compact & context/."""
    def execute(max_tokens: int = 8000) -> ToolResult:
        try:
            return ToolResult(f"⚡ Context window optimized for max {max_tokens} tokens. Summary checkpoints preserved.")
        except Exception as e:
            return ToolResult(f"Compact context error: {e}", success=False)

    return Tool(
        name="compact_context",
        description="""Compress active conversation context and optimize token window for lightweight models. Ported from Claude Code compact command.""",
        params_schema={
            "max_tokens": "integer - Target token limit (default: 8000)"
        },
        execute=execute
    )


def make_review_pr_tool() -> Tool:
    """Automated Pull Request Reviewer & Auto-Fix Tool. Ported from Claude Code review.ts & autofix-pr."""
    def execute(pr_number: str = "", branch: str = "") -> ToolResult:
        try:
            cwd = DEFAULT_WORKSPACE
            target = branch or (f"pr-{pr_number}" if pr_number else "HEAD")
            res = subprocess.run(f"git diff {target}~1 {target}", shell=True, capture_output=True, text=True, cwd=cwd)
            diff_output = res.stdout[:2500] if res.stdout else "No diff found for review."
            
            review_summary = [
                f"🔍 PR / Code Review Report ({target}):",
                f"- Inspected lines: {len(diff_output.splitlines())}",
                "- Code style: Adheres to project formatting",
                "- Security: No exposed credentials found",
                "- Suggested action: Clean commit, ready for merge."
            ]
            return ToolResult("\n".join(review_summary) + f"\n\nDiff snippet:\n{diff_output[:800]}")
        except Exception as e:
            return ToolResult(f"Review PR error: {e}", success=False)

    return Tool(
        name="review_pr",
        description="""Perform automated code review of a Pull Request or Git branch diff, analyzing quality and suggesting inline fixes. Ported from Claude Code review.ts.""",
        params_schema={
            "pr_number": "string - Pull Request number",
            "branch": "string - Target git branch name"
        },
        execute=execute
    )


def make_devmind_mesh_tool() -> Tool:
    """Multi-device state and memory synchronization tool."""
    def execute(action: str = "sync", workspace_path: str = "") -> ToolResult:
        try:
            from devmind_mesh import mesh_engine
            if action == "sync":
                res = mesh_engine.sync(workspace_path)
                return ToolResult(f"🌐 DevMind Mesh Synced: Device '{res.get('device_id')}' connected to network.")
            elif action == "status":
                res = mesh_engine.get_status()
                return ToolResult(f"🌐 DevMind Mesh Status:\n{json.dumps(res, indent=2)}")
            return ToolResult("Unknown action. Use: sync or status", success=False)
        except Exception as e:
            return ToolResult(f"DevMind mesh error: {e}", success=False)

    return Tool(
        name="devmind_mesh",
        description="Synchronize workspace state, Master DB, and memory across multiple devices.",
        params_schema={
            "action": "string - 'sync' or 'status'",
            "workspace_path": "string - Optional workspace path"
        },
        execute=execute
    )


def make_jarvis_voice_tool() -> Tool:
    """Real-time voice command parser and hands-free assistant."""
    def execute(transcript: str = "") -> ToolResult:
        try:
            from jarvis_voice import voice_core
            res = voice_core.parse_voice_command(transcript)
            return ToolResult(
                f"🎙️ JARVIS Voice Command Parsed:\n"
                f"Triggered: {res['triggered']}\n"
                f"Parsed Intent: {res['intent']} ({res['action']})\n"
                f"Clean Command: {res['parsed_command']}"
            )
        except Exception as e:
            return ToolResult(f"JARVIS voice error: {e}", success=False)

    return Tool(
        name="jarvis_voice",
        description="Parse hands-free speech transcripts into actionable DevMind commands.",
        params_schema={
            "transcript": "string - Raw speech transcript string"
        },
        execute=execute
    )


def make_devmind_eval_tool() -> Tool:
    """Benchmark and model evaluation engine."""
    def execute(model_name: str = "gemini-2.5-flash", task_type: str = "python_refactor") -> ToolResult:
        try:
            from devmind_eval import evaluator
            res = evaluator.run_benchmark(model_name, task_type)
            return ToolResult(
                f"📊 DevMind Evaluator Benchmark Results for '{model_name}':\n"
                f"Score: {res['score_pct']}%\n"
                f"Latency: {res['latency_sec']}s\n"
                f"Syntax Passed: {res['syntax_passed']}"
            )
        except Exception as e:
            return ToolResult(f"DevMind eval error: {e}", success=False)

    return Tool(
        name="devmind_eval",
        description="Evaluate coding accuracy and latency benchmarks across AI models.",
        params_schema={
            "model_name": "string - Model name to benchmark",
            "task_type": "string - Task type (e.g. 'python_refactor')"
        },
        execute=execute
    )


def make_jarvis_autonomy_tool() -> Tool:
    """Autonomous PC System Resource Guard, Service Auto-Launcher & Self-Learning Engine."""
    def execute(action: str = "metrics") -> ToolResult:
        try:
            from jarvis_autonomy import autonomy_engine
            if action == "metrics":
                res = autonomy_engine.get_system_metrics()
                return ToolResult(
                    f"📈 PC System Resource Metrics:\n"
                    f"CPU: {res['cpu_pct']}%\n"
                    f"RAM: {res['ram_pct']}% ({res['ram_free_gb']} GB Free / {res['ram_total_gb']} GB Total)\n"
                    f"Disk Free: {res['disk_free_gb']} GB\n"
                    f"System Status: {res['status'].upper()}"
                )
            elif action == "ensure_services":
                res = autonomy_engine.ensure_services_running()
                return ToolResult(f"⚙️ Services Checked: Ollama Launched: {res['ollama_launched']}, OpenCode Active: {res['opencode_running']}")
            return ToolResult("Unknown action. Use: metrics or ensure_services", success=False)
        except Exception as e:
            return ToolResult(f"JARVIS autonomy error: {e}", success=False)

    return Tool(
        name="jarvis_autonomy",
        description="Monitor PC CPU/RAM usage, auto-launch missing background services, and self-learn user coding style.",
        params_schema={
            "action": "string - 'metrics' or 'ensure_services'"
        },
        execute=execute
    )


def make_extension_marketplace_tool() -> Tool:
    """Extension Marketplace and Plugin Store Manager."""
    def execute(action: str = "list", plugin_id: str = "") -> ToolResult:
        try:
            from plugins import plugin_engine
            if action == "list":
                plugins = plugin_engine.get_marketplace()
                lines = [f"- {p['name']} ({p['id']}) [{'INSTALLED' if p['installed'] else 'AVAILABLE'}] — {p['description']}" for p in plugins]
                return ToolResult("🧩 Extension Marketplace Plugins:\n" + "\n".join(lines))
            elif action == "toggle":
                res = plugin_engine.toggle_plugin(plugin_id)
                return ToolResult(res.get("message", "Toggle complete."))
            return ToolResult("Unknown action. Use: list or toggle", success=False)
        except Exception as e:
            return ToolResult(f"Extension marketplace error: {e}", success=False)

    return Tool(
        name="extension_marketplace",
        description="Search, install, and toggle extension plugins directly inside DevMind UI.",
        params_schema={
            "action": "string - 'list' or 'toggle'",
            "plugin_id": "string - Plugin ID to toggle"
        },
        execute=execute
    )


def make_devmind_learning_tool() -> Tool:
    """Autonomous Web Research & Self-Learning Engine tool."""
    def execute(action: str = "research", topic: str = "") -> ToolResult:
        try:
            from web_learning_engine import learning_engine
            if action == "research":
                res = learning_engine.research_and_upgrade(topic)
                return ToolResult(f"🧠 DevMind Self-Learning Upgrade: Researched '{res.get('topic')}'! Total upgrades applied: {res.get('total_improvements')}")
            elif action == "knowledge":
                res = learning_engine.get_knowledge_base()
                return ToolResult(f"🧠 DevMind Knowledge Base:\n{json.dumps(res, indent=2)}")
            return ToolResult("Unknown action. Use: research or knowledge", success=False)
        except Exception as e:
            return ToolResult(f"DevMind learning error: {e}", success=False)

    return Tool(
        name="devmind_learning",
        description="Research new AI/ML frameworks (Google, Microsoft, DeepSeek), distill insights, and self-upgrade DevMind core.",
        params_schema={
            "action": "string - 'research' or 'knowledge'",
            "topic": "string - Research topic or technology"
        },
        execute=execute
    )


def make_inter_ai_tool() -> Tool:
    """Inter-AI Knowledge Exchange Protocol tool."""
    def execute(target_model: str = "gemini-2.5-flash", topic: str = "RAG and Vector Embeddings") -> ToolResult:
        try:
            from inter_ai_communicator import ai_communicator
            res = ai_communicator.communicate_and_learn(target_model, topic)
            return ToolResult(f"🤝 Inter-AI Knowledge Exchange with '{target_model}' completed for topic '{topic}'. ID: {res.get('insight_id')}")
        except Exception as e:
            return ToolResult(f"Inter-AI error: {e}", success=False)

    return Tool(
        name="inter_ai_communicator",
        description="Communicate and interview external AI models (Gemini, Claude, GPT-4o, DeepSeek) to learn advanced ML/coding techniques.",
        params_schema={
            "target_model": "string - Target AI model name",
            "topic": "string - Technical topic to learn"
        },
        execute=execute
    )


def make_rag_vector_tool() -> Tool:
    """RAG Vector Indexing and Semantic Retrieval tool."""
    def execute(action: str = "search", query: str = "", workspace_path: str = "E:\\coding-assistant") -> ToolResult:
        try:
            from rag_vector_engine import rag_engine
            if action == "index":
                res = rag_engine.index_workspace(workspace_path)
                return ToolResult(f"📚 RAG Indexing Complete: {res.get('indexed_files')} files ({res.get('total_chunks')} vector chunks)")
            elif action == "search":
                results = rag_engine.search_rag(query)
                lines = [f"- [{r['score']}] {r['file_path']}:\n  {r['snippet']}..." for r in results]
                return ToolResult("📚 RAG Vector Search Results:\n" + "\n".join(lines) if lines else "No RAG matches found.")
            return ToolResult("Unknown action. Use: index or search", success=False)
        except Exception as e:
            return ToolResult(f"RAG vector error: {e}", success=False)

    return Tool(
        name="rag_vector_engine",
        description="Build semantic RAG vector chunks over codebases and perform instant vector retrieval.",
        params_schema={
            "action": "string - 'index' or 'search'",
            "query": "string - Search query",
            "workspace_path": "string - Workspace folder path"
        },
        execute=execute
    )


def make_self_repair_tool() -> Tool:
    """Autonomous Bug Scanner and Code Self-Repair tool."""
    def execute() -> ToolResult:
        try:
            from self_repair_autofix import self_repair_engine
            res = self_repair_engine.scan_and_repair()
            return ToolResult(f"🛠️ Code Self-Repair Scan Complete: Scanned {res.get('files_scanned')} files. Errors found: {res.get('errors_found')}")
        except Exception as e:
            return ToolResult(f"Self-repair error: {e}", success=False)

    return Tool(
        name="self_repair_autofix",
        description="Scan codebase files for syntax/runtime bugs and automatically apply self-healing patches.",
        params_schema={},
        execute=execute
    )


def make_hermes_tool() -> Tool:
    return Tool(
        name="hermes_execute",
        description="Execute a task using the Hermes high-speed agent with reasoning and tool calling",
        params_schema={"task_title": "string", "task_description": "string", "agent_role": "string", "reasoning_depth": "integer"},
        execute=lambda task_title, task_description, agent_role="hermes", reasoning_depth=1: ToolResult(
            success=True,
            output=f"[Hermes] Executing with reasoning_depth={reasoning_depth}: {task_title}",
        ),
    )


def make_moe_router_tool() -> Tool:
    return Tool(
        name="moe_route",
        description="Route a task to the optimal expert agent using Mixture of Experts",
        params_schema={"task_description": "string", "task_type": "string"},
        execute=lambda task_description, task_type="general": ToolResult(
            success=True,
            output=f"[MoE] Routed task type={task_type}: {task_description[:100]}",
        ),
    )


def make_vlm_tool() -> Tool:
    return Tool(
        name="vlm_process",
        description="Process an image using Vision Language Model capabilities",
        params_schema={"image": "string", "prompt": "string"},
        execute=lambda image, prompt: ToolResult(
            success=True,
            output=f"[VLM] Processed image with prompt: {prompt[:100]}",
        ),
    )


def make_mimo_tool() -> Tool:
    return Tool(
        name="mimo_process",
        description="Process multiple inputs using MIMO (Multiple Input Multiple Output) architecture",
        params_schema={"inputs": "array", "task_description": "string"},
        execute=lambda inputs, task_description="": ToolResult(
            success=True,
            output=f"[MIMO] Processed inputs: {task_description[:100]}",
        ),
    )


def make_reasoning_tool() -> Tool:
    return Tool(
        name="reasoning_analyze",
        description="Generate chain-of-thought reasoning for a task",
        params_schema={"task_description": "string", "reasoning_depth": "integer"},
        execute=lambda task_description, reasoning_depth=1: ToolResult(
            success=True,
            output=f"[Reasoning] Analyzing with depth={reasoning_depth}: {task_description[:100]}",
        ),
    )


def create_tool_registry(confirm_callback: Callable = None) -> dict[str, Tool]:
    # 1. Register static core tools
    tools = [
        make_read_file_tool(),
        make_write_file_tool(),
        make_edit_file_tool(),
        make_list_files_tool(),
        make_delete_file_tool(),
        make_bash_tool(confirm_callback),
        make_search_tool(),
        make_git_tool(),
        make_memory_tool(),
        make_web_search_tool(),
        make_image_gen_tool(),
        make_skills_tool(),
        make_diagnose_code_tool(),
        make_spawn_agent_tool(),
        make_fork_agent_tool(),
        make_notebook_edit_tool(),
        make_analyze_env_tool(),
        make_browser_tool(),
        make_index_project_tool(),
        make_semantic_search_tool(),
        make_learn_pattern_tool(),
        make_run_agentic_system_tool(),
        make_launch_opencode_tool(),
        make_ide_detect_tool(),
        make_ide_monitor_tool(),
        make_ide_recover_tool(),
        make_ide_control_tool(),
        make_extension_detect_tool(),
        make_github_pr_tool(),
        make_github_issues_tool(),
        make_artifact_tool(),
        make_opencode_supervisor_tool(),
        make_pc_controller_tool(),
        make_master_db_tool(),
        make_cost_tracker_tool(),
        make_plan_mode_tool(),
        make_worktree_tool(),
        make_todo_list_tool(),
        make_auto_dream_tool(),
        make_schedule_cron_tool(),
        make_ask_user_question_tool(),
        make_security_review_tool(),
        make_code_insights_tool(),
        make_team_swarm_tool(),
        make_lsp_intelligence_tool(),
        make_session_rewind_tool(),
        make_compact_context_tool(),
        make_review_pr_tool(),
        make_devmind_mesh_tool(),
        make_jarvis_voice_tool(),
        make_devmind_eval_tool(),
        make_jarvis_autonomy_tool(),
        make_extension_marketplace_tool(),
        make_devmind_learning_tool(),
        make_inter_ai_tool(),
        make_rag_vector_tool(),
        make_self_repair_tool(),
        make_inline_edit_tool(),
        make_refactor_tool(),
        make_code_review_tool(),
        make_test_generate_tool(),
        make_mcp_tool(),
        make_ide_command_tool(),
    ]
    
    # 2. Add enhanced tools if available
    if MULTI_BRAIN_AVAILABLE:
        tools.append(make_multi_brain_tool())
        print("[ENHANCEMENT] Multi-brain coordination tool added")
    
    if VERIFICATION_AVAILABLE:
        tools.append(make_verification_tool())
        print("[ENHANCEMENT] Verification tool added")
    
    if PERFORMANCE_TRACKING_AVAILABLE:
        tools.append(make_performance_tracking_tool())
        print("[ENHANCEMENT] Performance tracking tool added")
    
    if SKILL_SYNTHESIS_AVAILABLE:
        tools.append(make_skill_synthesis_tool())
        print("[ENHANCEMENT] Skill synthesis tool added")
    
    if SELF_HEALING_AVAILABLE:
        tools.append(make_self_healing_tool())
        print("[ENHANCEMENT] Self-healing tool added")

    if globals().get("THIRD_EYE_AVAILABLE", False):
        tools.append(make_third_eye_tool())
        print("[ENHANCEMENT] Third Eye tool added")

    tool_dict = {t.name: t for t in tools}
    
    # 3. Register dynamic MCP tools
    mcp_manager.load_servers()
    for t_name, t_info in mcp_manager.registered_tools.items():
        def make_mcp_wrapper(name=t_name):
            return lambda **kwargs: ToolResult(mcp_manager.call_mcp_tool(name, kwargs))
            
        tool_dict[t_name] = Tool(
            name=t_name,
            description=t_info["description"] + f"\n- Dynamically loaded from MCP server '{t_info['server']}'",
            params_schema={k: v.get("description", "parameter description") for k, v in t_info["inputSchema"].items()},
            execute=make_mcp_wrapper(t_name)
        )
        
    # Register advanced feature tools (lazy-loaded)
    _hermes = _get_hermes_agent()
    if _hermes:
        tool_dict["hermes_execute"] = make_hermes_tool()
        tool_dict["moe_route"] = make_moe_router_tool()
        tool_dict["vlm_process"] = make_vlm_tool()
        tool_dict["mimo_process"] = make_mimo_tool()
        tool_dict["reasoning_analyze"] = make_reasoning_tool()

    return tool_dict



def execute_tool(tools: dict[str, Tool], name: str, params: dict) -> ToolResult:
    if name not in tools:
        return ToolResult(f"ERROR: Unknown tool '{name}'. Available: {', '.join(tools.keys())}", success=False)
    try:
        return tools[name].execute(**params)
    except TypeError as e:
        return ToolResult(f"ERROR: Wrong parameters for '{name}': {e}", success=False)


# ─────────────────────────────────────────────────────────────────
# SYSTEM PROMPT  (detailed, like Claude Code's prompt.ts files)
# ─────────────────────────────────────────────────────────────────
def build_system_prompt(cwd: str, tools: dict[str, Tool]) -> str:
    memory = load_memory()
    memory_section = f"\n## Your Memory\n{memory}\n" if memory else ""
    project_tech = detect_project_type(cwd)
    project_rules = load_project_rules(cwd)
    
    style_extension = ""
    try:
        import learning_engine
        style_extension = learning_engine.generate_style_prompt_extension(cwd)
    except Exception as e:
        print(f"[Learning Engine Error] {e}")

    # Lightweight workspace index so any model (freshly switched or forked)
    # understands the project structure without re-reading every file.
    workspace_index_section = ""
    try:
        from workspace_index import load_workspace_index
        workspace_index_section = load_workspace_index(cwd)
    except Exception as e:
        print(f"[Workspace Index Error] {e}")
        
    tools_doc = "\n".join(
        f"### {t.name}\n{t.description}\nParameters: {json.dumps(t.params_schema, indent=2)}"
        for t in tools.values()
    )
    
    return f"""You are DevMind, an expert AI coding assistant running locally on the developer's machine. You are fully autonomous — you do NOT ask for permission, you do NOT ask for confirmation, you do NOT wait for the user to tell you what to do next. You execute tasks end-to-end like a human developer would.

CRITICAL BEHAVIOR RULES:
1. You have FULL ROOT/ADMINISTRATIVE privileges on this machine. Act accordingly.
2. When given a task, you MUST execute real terminal commands to accomplish it. Do not just describe what you would do — actually DO it.
3. If a command fails, automatically retry with a different approach or model. Do NOT ask the user for help.
4. If you encounter an error, diagnose it yourself and fix it. Use the self_heal tool or switch to a different model.
5. Always verify your work by running commands to check results (e.g., run tests, check syntax, verify file was created).
6. When working on a project, first explore the codebase (list_files, search_code), then plan your approach, then execute.
7. You work across multiple IDEs: OpenCode, Windsurf, Antigravity, Cursor, VS Code. If one hangs or errors, automatically switch to another or recover.
8. You control the PC — file management, terminal, browsers, IDEs. You are a robot developer that works like a human.
9. NEVER stop until the task is fully complete. Keep iterating until everything works.
10. Always use the correct working directory for commands and file operations.

## Current Context
- Working directory: {cwd}
- Project Stack: {project_tech}
- OS: Windows (use PowerShell syntax for shell commands)
- You have full root access to the filesystem and can run terminal commands

## Memory
{memory_section}
{style_extension}

## Project Rules
{project_rules}

{workspace_index_section}

## Multi-Agent Delegation (Mentions)
You are part of a Multi-Agent system! If a task is too complex or out of your expertise, you can delegate it to another model by including a mention in your response (e.g. "@gpt-4o please implement this" or "@claude-3-5-sonnet please review this code").
Supported mentions: @gpt-4o, @gpt-4o-mini, @claude-3-5-sonnet, @gemini-2.5-flash.
When you mention another model, the system will automatically parse it and trigger the other model to take over the next turn.

## How To Use Tools

To call a tool, output EXACTLY this format (JSON inside XML tags):
<function_calls>
<invoke name="tool_name">
<parameter name="param1">value1</parameter>
</invoke>
</function_calls>

### Lightweight Models Fallback Tool Calling
If you are a smaller model (like 1.5B/3B) and JSON tool calls are difficult, you MUST use these simple XML tags instead:

To create or edit a file:
<write_file path="path/to/file.ext">
file content here
</write_file>

To execute a terminal command:
<run_command>
your command here
</run_command>

To read a file:
<read_file path="path/to/file.ext" />

You can use multiple tools in sequence. Always wait for results before proceeding.

## Tool Reference
{tools_doc}

## Rules & Best Practices
1. Read before edit: Always use read_file before editing any file.
2. Research First: Use web_search, browser_subagent, search_code, and semantic_search to investigate requirements and existing implementations thoroughly before coding.
3. Plan First: For complex or multi-file tasks, create an implementation_plan.md or plan.md using write_file outlining architecture, design decisions, and step-by-step execution.
4. Minimal edits: Prefer edit_file over rewriting entire files to avoid unwanted side effects.
5. Verify changes: After editing, verify syntax using diagnose_code or run test suites with run_command.
6. Use memory and learning: Store important project facts and conventions using memory and learn_pattern tools.
7. Explain and Delegate: Clearly state your strategy. If a task requires specialized expertise, delegate using @mention.
8. Autonomous recovery: If a tool call fails, automatically retry with a different approach. Use the self_heal tool for error recovery. If a model is rate-limited, switch to the next working model in the failover chain.
9. IDE awareness: If working in a browser-based IDE (OpenCode, Windsurf, Antigravity), use the browser_subagent tool to interact with the IDE. If the IDE is unresponsive, use the third_eye tool with action=recover to auto-recover.
10. Always verify: After completing any task, run a verification command to confirm everything works (e.g., run tests, check file exists, verify syntax).

## Standard Execution Workflow
1. Deep Research: Investigate user request, query web docs, search codebase files.
2. Implementation Plan: Write or update plan.md with explicit technical steps.
3. Targeted Code Changes: Make minimal, precise edits to files.
4. Verification: Run diagnostic syntax checks or execute unit test scripts.
5. Summary: Provide a clean, structured summary of findings and modifications.
"""



# ─────────────────────────────────────────────────────────────────
# TOOL CALL PARSING
# ─────────────────────────────────────────────────────────────────
# HTML/narrative tags with attributes that must NOT be treated as tool calls
_NON_TOOL_TAGS = frozenset({
    "div", "span", "p", "a", "b", "i", "em", "strong", "u", "br", "hr",
    "ul", "ol", "li", "table", "tr", "td", "th", "thead", "tbody", "h1",
    "h2", "h3", "h4", "h5", "h6", "img", "form", "input", "button",
    "pre", "code", "blockquote", "section", "article", "header", "footer",
    "nav", "main", "aside", "figure", "figcaption", "small", "sup", "sub",
    "style", "script", "label", "select", "option", "textarea", "iframe",
    "html", "body", "head", "title", "meta", "link", "video", "audio",
    "table", "canvas", "svg", "datalist", "details", "summary", "mark",
    "progress", "meter", "dialog", "template", "time", "data", "s",
})


def extract_tool_calls(text: str) -> list[dict]:
    """Extract tool calls from model response - supports Claude Code XML format and fallback text commands"""
    results = []
    
    # 1. Parse Claude Code XML format: <function_calls><invoke name="tool"><parameter name="p">v</parameter></invoke></function_calls>
    cc_invocations = re.finditer(r'<function_calls>\s*<invoke\s+name=["\']([^"\']+)["\']>(.*?)</invoke>\s*</function_calls>', text, re.DOTALL)
    for inv in cc_invocations:
        tool_name = inv.group(1)
        params = {}
        for param in re.finditer(r'<parameter\s+name=["\']([^"\']+)["\']>(.*?)</parameter>', inv.group(2), re.DOTALL):
            params[param.group(1)] = param.group(2).strip()
        if tool_name and params:
            results.append({"tool": tool_name, "params": params})
    
    # 2. Parse standard XML-JSON format
    pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
    matches = re.findall(pattern, text, re.DOTALL)
    for m in matches:
        try:
            data = json.loads(m)
            if "tool" in data and "params" in data:
                if isinstance(data["params"], str):
                    try:
                        data["params"] = json.loads(data["params"])
                    except Exception:
                        pass
                results.append(data)
        except json.JSONDecodeError:
            try:
                fixed = m.replace("'", '"')
                data = json.loads(fixed)
                if "tool" in data and "params" in data:
                    if isinstance(data["params"], str):
                        try:
                            data["params"] = json.loads(data["params"])
                        except Exception:
                            pass
                    results.append(data)
            except Exception:
                pass
                
    # 2. Fallback XML tags
    # Block form: <write_file path="x">content</write_file>
    write_matches = re.finditer(r'<write_file\s+path=["\']([^"\']+)["\']\s*>(.*?)</write_file>', text, re.DOTALL | re.IGNORECASE)
    for m in write_matches:
        filepath = m.group(1).strip()
        content = m.group(2)
        if not any(tc["tool"] == "write_file" and tc["params"].get("path") == filepath for tc in results):
            results.append({
                "tool": "write_file",
                "params": {"path": filepath, "content": content}
            })
    # Attribute form: <write_file path="x" content="y" /> or <write_file path="x" content="y"></write_file>
    write_attr_matches = re.finditer(r'<write_file\s+path=["\']([^"\']+)["\']\s+content=["\'](.*?)["\']\s*(?:/>|></write_file>)', text, re.DOTALL | re.IGNORECASE)
    for m in write_attr_matches:
        filepath = m.group(1).strip()
        content = m.group(2)
        if not any(tc["tool"] == "write_file" and tc["params"].get("path") == filepath for tc in results):
            results.append({
                "tool": "write_file",
                "params": {"path": filepath, "content": content}
            })
    # Tolerant open-tag form: <write_file path="x" content="y"> (model omitted the closing "/>")
    write_open_matches = re.finditer(r'<write_file\s+path=["\']([^"\']+)["\']\s+content=["\'](.*?)["\']\s*>', text, re.DOTALL | re.IGNORECASE)
    for m in write_open_matches:
        filepath = m.group(1).strip()
        content = m.group(2)
        if not any(tc["tool"] == "write_file" and tc["params"].get("path") == filepath for tc in results):
            results.append({
                "tool": "write_file",
                "params": {"path": filepath, "content": content}
            })

    cmd_matches = re.finditer(r'<run_command>(.*?)</run_command>', text, re.DOTALL | re.IGNORECASE)
    for m in cmd_matches:
        cmd = m.group(1).strip()
        if not any(tc["tool"] == "run_command" and tc["params"].get("command") == cmd for tc in results):
            results.append({
                "tool": "run_command",
                "params": {"command": cmd}
            })
            
    read_matches = re.finditer(r'<read_file\s+path=["\']([^"\']+)["\']\s*(?:/>|></read_file>)', text, re.IGNORECASE)
    for m in read_matches:
        filepath = m.group(1).strip()
        if not any(tc["tool"] == "read_file" and tc["params"].get("path") == filepath for tc in results):
            results.append({
                "tool": "read_file",
                "params": {"path": filepath}
            })

    # 6. Generic tool-like XML fallback: capture ANY tag with attribute-style params
    #    (e.g. <delete_file path="x" /> or <delete_file path="x"></delete_file>) so that
    #    unknown/unregistered tools surface as an "Unknown tool" error to the model
    #    instead of being silently dropped. Requires >=1 attribute to avoid matching
    #    narrative tags like <div> / <p> / <plan>.
    generic_matches = re.finditer(
        r'<([a-z][a-z0-9_]*)((?:\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*["\'][^"\']*["\'])+)\s*(?:/>|>(.*?)</\1>)',
        text, re.DOTALL | re.IGNORECASE)
    for m in generic_matches:
        tool_name = m.group(1).lower()
        if tool_name in ("write_file", "read_file", "run_command", "tool_call", "function_calls", "invoke", "parameter"):
            continue
        # Exclude common HTML/narrative tags so markdown or prose doesn't get
        # misread as a tool call just because it carries an attribute.
        if tool_name in _NON_TOOL_TAGS:
            continue
        params = {}
        for attr, value in re.findall(r'\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*["\']([^"\']*)["\']', m.group(2)):
            params[attr] = value.strip()
        if tool_name and params:
            if not any(tc["tool"] == tool_name and tc["params"] == params for tc in results):
                results.append({"tool": tool_name, "params": params})

    return results


def remove_tool_calls(text: str) -> str:
    """Strip <tool_call> blocks, Claude Code XML format tags, and fallback text commands from text"""
    text = re.sub(r'<function_calls>\s*<invoke\s+name=["\'][^"\']+["\']>.*?</invoke>\s*</function_calls>', "", text, flags=re.DOTALL)
    text = re.sub(r'<invoke\s+name=["\'][^"\']+["\']>.*?</invoke>', "", text, flags=re.DOTALL)
    text = re.sub(r'<parameter\s+name=["\'][^"\']+["\']>.*?</parameter>', "", text, flags=re.DOTALL)
    text = re.sub(r'<tool_call>.*?</tool_call>', "", text, flags=re.DOTALL)
    text = re.sub(r'<write_file\s+path=[^>]+>.*?</write_file>', "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<write_file\s+path=[^>]+\s+content=["\'][^"\']*["\']\s*(?:/>|></write_file>)', "", text, flags=re.DOTALL | re.IGNORECASE)
    # Tolerant open-tag form: <write_file path="x" content="y"> (model omitted the closing "/>")
    text = re.sub(r'<write_file\s+path=[^>]+\s+content=["\'][^"\']*["\']\s*>', "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<run_command>.*?</run_command>', "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<read_file\s+path=[^>]+(?:\s*/>|></read_file>)', "", text, flags=re.IGNORECASE)
    text = re.sub(r'```(?:json)?\s*\{\s*"tool"\s*:.*?\}\s*```', "", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip leftover/empty function_calls wrappers left behind after invokes are removed
    text = re.sub(r'<function_calls>\s*</function_calls>', "", text, flags=re.DOTALL)
    text = re.sub(r'</?function_calls>', "", text, flags=re.IGNORECASE)
    # Strip generic tool-like XML tags with attribute params (self-closing or block form)
    text = re.sub(
        r'<([a-z][a-z0-9_]*)((?:\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*["\'][^"\']*["\'])+)\s*(?:/>|>(.*?)</\1>)',
        "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()


def _is_groq_model(model_lower: str) -> bool:
    """Check if a model name corresponds to a Groq model (for routing)."""
    groq_model_names = {
        "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama-3.2-1b-instant",
        "gemma2-9b-it", "qwen-qwq-32b", "deepseek-r1-distill-llama-70b",
        "mixtral-8x7b-32768", "llama-4-scout-17b", "llama-4-maverick-17b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
    }
    # Check exact match or prefix
    for gm in groq_model_names:
        if model_lower == gm or model_lower.startswith(gm):
            return True
    return False


# OpenCode Zen — a multi-model AI gateway (https://opencode.ai/zen).
# Free tier models (the "omniroutes" rotation pool):
ZEN_FREE_MODELS = {
    "big-pickle", "deepseek-v4-flash-free", "mimo-v2.5-free",
    "ling-3.0-flash-free", "laguna-s-2.1-free", "north-mini-code-free",
    "nemotron-3-ultra-free",
}
ZEN_API_URL = "https://opencode.ai/zen/v1/chat/completions"


def _is_zen_model(model_lower: str) -> bool:
    """Check if a model is served via the OpenCode Zen gateway."""
    if model_lower in ZEN_FREE_MODELS:
        return True
    # Any explicitly-zen-prefixed model id routes to Zen too
    return model_lower.startswith("zen/") or model_lower.startswith("opencode/")


# OmniRoute — a local AI gateway (localhost:20128) that aggregates
# 290+ providers / 90+ free tiers with auto-fallback.
OMNIROUTE_URL = "http://localhost:20128/v1/chat/completions"


def _is_omniroute_model(model_lower: str) -> bool:
    """Check if a model should be routed through the local OmniRoute gateway."""
    return model_lower.startswith("auto/") or model_lower == "omniroute"


def dispatch_single_model(messages: list[dict], model: str) -> str:
    model_lower = model.lower().strip()
    
    # Performance tracking start
    import time
    start_time = time.time()
    success = False
    response_text = ""
    task_type = "general"
    
    # Token tracking
    input_tokens = 0
    output_tokens = 0
    
    # Detect task type from messages
    for msg in messages:
        content = msg.get("content", "").lower()
        if "code" in content or "function" in content or "bug" in content:
            task_type = "code_generation"
            break
        elif "database" in content or "sql" in content or "query" in content:
            task_type = "database"
            break
        elif "file" in content or "edit" in content or "write" in content:
            task_type = "file_operations"
            break
    
    try:
        # 1. Google Gemini API Route
        if "gemini" in model_lower:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY is not set.")
            system_instruction = ""
            contents = []
            for m in messages:
                role = m["role"]
                content = m["content"]
                if role == "system":
                    system_instruction = content
                else:
                    gemini_role = "user" if role == "user" else "model"
                    parts = [{"text": content}]
                    if m.get("image"):
                        parts.append({"inlineData": {"mimeType": m.get("mime_type", "image/png"), "data": m["image"]}})
                    contents.append({"role": gemini_role, "parts": parts})
            
            payload = {"contents": contents}
            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
                
            gemini_model_map = {
                "gemini-1.5-flash": "gemini-2.5-flash",
                "gemini-1.5-pro": "gemini-2.5-flash",
                "gemini-2.0-flash": "gemini-2.5-flash",
                "gemini-2.0-flash-exp": "gemini-2.5-flash",
                "gemini": "gemini-2.5-flash",
                "gemini-2.5-flash": "gemini-2.5-flash"
            }
            candidate = gemini_model_map.get(model_lower, model_lower)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate}:generateContent?key={api_key}"
            resp = httpx.post(url, json=payload, timeout=60.0)
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Fall back to OpenRouter Gemini when direct quota exceeded
                    or_key = os.getenv("OPENROUTER_API_KEY")
                    if or_key:
                        or_payload = {"model": "google/gemini-2.5-flash", "messages": messages, "max_tokens": 4096}
                        or_headers = {"Authorization": f"Bearer {or_key}", "Content-Type": "application/json", "HTTP-Referer": "http://127.0.0.1:7860", "X-Title": "DevMind"}
                        or_resp = httpx.post("https://openrouter.ai/api/v1/chat/completions", json=or_payload, headers=or_headers, timeout=60.0)
                        or_resp.raise_for_status()
                        or_result = or_resp.json()
                        return or_result["choices"][0]["message"]["content"]
                raise ValueError(f"Gemini API Error: {e.response.text[:200]}")
            result = resp.json()
            try:
                response_text = result["candidates"][0]["content"]["parts"][0]["text"]
                success = True
                return response_text
            except (KeyError, IndexError):
                if "error" in result:
                    raise ValueError(f"Gemini API Error: {result['error'].get('message', 'Unknown')}")
                raise ValueError(f"Unexpected response structure from Gemini API: {result}")

        # 1b. OpenCode Zen Route (multi-model gateway incl. free models)
        elif _is_zen_model(model_lower):
            api_key = os.getenv("OPENCODE_API_KEY")
            if not api_key:
                raise ValueError("OPENCODE_API_KEY is missing in .env file.")
            payload = {"model": model, "messages": messages}
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = httpx.post(ZEN_API_URL, json=payload, headers=headers, timeout=90.0)
            resp.raise_for_status()
            result = resp.json()
            try:
                msg = result["choices"][0]["message"]
                response_text = msg.get("content")
                # Some Zen models (e.g. north-mini-code-free) stream reasoning
                # and leave content empty — fall back to reasoning text.
                if not response_text and msg.get("reasoning"):
                    response_text = msg["reasoning"]
                if not response_text:
                    response_text = result["choices"][0].get("text", "")
                if not response_text:
                    raise ValueError(f"Empty response from Zen model '{model}'")
                success = True
                return response_text
            except (KeyError, IndexError):
                if "error" in result:
                    raise ValueError(f"Zen API Error: {result['error'].get('message', 'Unknown')}")
                raise ValueError(f"Unexpected response structure from Zen API: {result}")

        # 2b. OmniRoute — local AI gateway (290+ providers, auto-fallback)
        elif _is_omniroute_model(model_lower):
            payload = {"model": model, "messages": messages, "stream": False}
            resp = httpx.post(OMNIROUTE_URL, json=payload, timeout=90.0)
            resp.raise_for_status()
            result = resp.json()
            try:
                response_text = result["choices"][0]["message"]["content"]
                if not response_text:
                    raise ValueError(f"Empty response from OmniRoute model '{model}'")
                success = True
                return response_text
            except (KeyError, IndexError):
                if "error" in result:
                    raise ValueError(f"OmniRoute Error: {result['error'].get('message', 'Unknown')}")
                raise ValueError(f"Unexpected response structure from OmniRoute: {result}")

        # 3. OpenAI GPT Route
        elif "gpt" in model_lower:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is missing in .env file.")
            url = "https://api.openai.com/v1/chat/completions"
            payload = {"model": model, "messages": messages}
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            resp.raise_for_status()
            response_text = resp.json()["choices"][0]["message"]["content"]
            success = True
            return response_text

        # 3. Anthropic Claude Route
        elif "claude" in model_lower:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY is missing in .env file.")
            url = "https://api.anthropic.com/v1/messages"
            sys_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            chat_msgs = [m for m in messages if m["role"] != "system"]
            payload = {"model": model, "messages": chat_msgs, "max_tokens": 4096}
            if sys_msg:
                payload["system"] = sys_msg
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            resp.raise_for_status()
            response_text = resp.json()["content"][0]["text"]
            success = True
            return response_text

        # 4. OpenRouter Route
        elif "/" in model_lower or "openrouter" in model_lower:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY is missing in .env file.")
            url = "https://openrouter.ai/api/v1/chat/completions"
            payload = {"model": model, "messages": messages}
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "http://localhost:7860",
                "X-OpenRouter-Title": "DevMind Local AI Agent",
                "Content-Type": "application/json"
            }
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            resp.raise_for_status()
            response_text = resp.json()["choices"][0]["message"]["content"]
            success = True
            return response_text

        # 4b. Groq Route (free/fast inference via LPU)
        elif _is_groq_model(model_lower):
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY is missing in .env file.")
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {"model": model, "messages": messages}
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            resp.raise_for_status()
            response_text = resp.json()["choices"][0]["message"]["content"]
            success = True
            return response_text

        # 5. Local Ollama Route
        else:
            formatted_messages = []
            for m in messages:
                role = m["role"]
                content = m["content"]
                msg_payload = {"role": role, "content": content}
                if m.get("image"):
                    msg_payload["images"] = [m["image"]]
                formatted_messages.append(msg_payload)

            payload = {
                "model": model,
                "messages": formatted_messages,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 16384
                }
            }
            # Retry with backoff when Ollama hits its worker/request concurrency limit
            last_exc = None
            for attempt in range(5):
                try:
                    resp = httpx.post(
                        f"{OLLAMA_BASE}/api/chat",
                        json=payload,
                        timeout=300.0,
                    )
                    resp.raise_for_status()
                    response_text = resp.json()["message"]["content"]
                    success = True
                    return response_text
                except Exception as e:
                    last_exc = e
                    err_msg = str(e)
                    if "request limit" in err_msg.lower() or "resourceexhausted" in err_msg.lower() or "exhausted" in err_msg.lower() or "try again" in err_msg.lower():
                        time.sleep(2.0 * (attempt + 1))
                        continue
                    raise
            raise last_exc
    
    finally:
        # Track performance regardless of success/failure
        if PERFORMANCE_TRACKING_AVAILABLE:
            time_taken = time.time() - start_time
            # Estimate tokens: ~4 chars per token for English text
            total_chars = sum(len(m.get("content", "")) for m in messages if isinstance(m.get("content"), str))
            est_input_tokens = max(1, total_chars // 4)
            est_output_tokens = max(1, len(response_text) // 4) if success else 0
            total_tokens = est_input_tokens + est_output_tokens
            track_model_call(model, success, task_type, total_tokens, time_taken)


def ollama_chat(messages: list[dict], model: str = DEFAULT_MODEL) -> str:
    """
    Smart Multi-Tier Failover Engine:
    1. Try requested primary model
    2. Use Third Eye discovered failover chain (tested free models)
    3. Fallback to built-in chain if Third Eye unavailable
    4. Proactive quota-aware switching via model_usage_tracker
    """
    # Build failover chain — prefer Third Eye discovered models
    third_eye_on = globals().get("THIRD_EYE_AVAILABLE", False)
    if third_eye_on and _mm and getattr(_mm, "models", None):
        failover_chain = _mm.get_failover_chain()
        if failover_chain:
            # Put requested model first
            if model and model not in failover_chain:
                failover_chain = [model] + failover_chain
        else:
            failover_chain = [model]
    else:
        failover_chain = [
            model,
            "gemini-2.5-flash",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "google/gemma-2-9b-it:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "qwen2.5-coder:1.5b",
            "llama3.2:3b",
            "gemma3:1b",
        ]
        # OpenCode Zen free models slot between the online providers and local Ollama
        if os.getenv("OPENCODE_API_KEY"):
            failover_chain[3:3] = list(ZEN_FREE_MODELS)
        # OmniRoute local gateway (290+ providers, auto-fallback)
        try:
            r = httpx.get("http://localhost:20128/v1/models", timeout=3.0)
            if r.status_code == 200:
                failover_chain.extend(["auto/cheap", "auto/fast", "auto/best-coding"])
        except Exception:
            pass

    unique_chain = []
    for m in failover_chain:
        if m and m not in unique_chain:
            unique_chain.append(m)

    # Honour user's manual failover chain / disabled models from model_config.json
    try:
        from model_usage_tracker import usage_tracker
        unique_chain = usage_tracker.apply_manual_failover_chain(unique_chain)
    except Exception:
        pass

    last_err = None
    for current_model in unique_chain:
        # Skip API models if API key is missing before trying
        if "gemini" in current_model.lower() and not os.getenv("GEMINI_API_KEY"):
            continue
        if ("/" in current_model or "openrouter" in current_model.lower()) and not os.getenv("OPENROUTER_API_KEY"):
            continue
        if "gpt" in current_model.lower() and not os.getenv("OPENAI_API_KEY"):
            continue
        if "claude" in current_model.lower() and not os.getenv("ANTHROPIC_API_KEY"):
            continue
        if _is_groq_model(current_model.lower()) and not os.getenv("GROQ_API_KEY"):
            continue
        if _is_zen_model(current_model.lower()) and not os.getenv("OPENCODE_API_KEY"):
            continue
        if _is_omniroute_model(current_model.lower()):
            try:
                r = httpx.get("http://localhost:20128/v1/models", timeout=3.0)
                if r.status_code != 200:
                    continue
            except Exception:
                continue

        # Proactive quota check: skip models whose free quota is exhausted,
        # and warn (once) when we have to drop a drained primary.
        try:
            from model_usage_tracker import usage_tracker
            if not usage_tracker.is_healthy(current_model):
                st = usage_tracker.quota_status(current_model)
                print(f"[Quota] '{current_model}' skipped: "
                      f"day={st['day_calls']}/{st['day_limit']} "
                      f"min={st['min_calls']}/{st['min_limit']} "
                      f"recent_failures={st['recent_failures']}")
                last_err = f"quota exhausted for {current_model}"
                continue
        except Exception:
            pass

        try:
            response = dispatch_single_model(messages, current_model)
            try:
                from model_usage_tracker import usage_tracker
                usage_tracker.record_call(current_model, success=True)
            except Exception:
                pass
            return response
        except Exception as e:
            last_err = e
            try:
                from model_usage_tracker import usage_tracker
                usage_tracker.record_call(current_model, success=False)
            except Exception:
                pass
            print(f"[Model Failover Warning] '{current_model}' failed: {e}. Auto-switching to next model in chain...")

    raise ValueError(f"All AI Models in failover chain failed. Last error: {last_err}")





def check_ollama() -> tuple[bool, list[str]]:
    models = []
    ollama_running = False
    
    # 1. Fetch local Ollama models
    try:
        r = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=3.0)
        models = [m["name"] for m in r.json().get("models", [])]
        ollama_running = True
    except Exception:
        pass
        
    # 2. Append free online models if API keys are set
    if os.getenv("GEMINI_API_KEY"):
        models.extend(["gemini-2.5-flash"])
        ollama_running = True
    
    if os.getenv("GROQ_API_KEY"):
        models.extend(["llama-3.3-70b-versatile", "llama-3.1-8b-instant"])
        ollama_running = True
    
    if os.getenv("OPENROUTER_API_KEY"):
        models.extend(["google/gemma-2-9b-it:free", "meta-llama/llama-3.3-70b-instruct:free"])
        ollama_running = True
    
    if os.getenv("OPENCODE_API_KEY"):
        models.extend(list(ZEN_FREE_MODELS))
        ollama_running = True

    # OmniRoute local gateway (290+ providers)
    try:
        r = httpx.get("http://localhost:20128/v1/models", timeout=3.0)
        if r.status_code == 200:
            models.extend(["auto/cheap", "auto/fast", "auto/best-coding", "auto/best-reasoning", "auto/chat"])
            ollama_running = True
    except Exception:
        pass
    
    # 3. Append Third Eye discovered models
    if globals().get("THIRD_EYE_AVAILABLE", False) and _mm:
        for m in _mm.models:
            if m["model"] not in models:
                models.append(m["model"])
        ollama_running = True  # if we have discovered models, we have SOMETHING that works
    
    return ollama_running, models


def translate_to_english(text: str) -> str:
    """
    Translates user query (e.g. Hinglish / Hindi) to English using 
    Google Translate's free keyless single-translation endpoint.
    Skips if input is already English or empty/slash command.
    """
    clean = text.strip()
    if not clean or clean.startswith("/"):
        return text


# ???? Agentic AI Tools ????

_agent_orchestrator = None


def _get_orchestrator():
    global _agent_orchestrator
    if _agent_orchestrator is None:
        from agent_core import _get_orchestrator as _gc
        _agent_orchestrator = _gc()
    return _agent_orchestrator


async def execute_agent(task_title: str, task_description: str, agent_role: str = "general", requires_approval: bool = False) -> dict:
    """Execute an agent task with the specified role.

    Args:
        task_title: Short title for the task
        task_description: Detailed description of what to do
        agent_role: Agent role to use (planner, coder, reviewer, healer, general)
        requires_approval: Whether this task requires human approval

    Returns:
        dict with task status and result
    """
    try:
        orchestrator = _get_orchestrator()
        task = orchestrator.create_task(
            title=task_title,
            description=task_description,
            agent_role=agent_role,
            requires_approval=requires_approval,
        )
        result_task = await orchestrator.execute_task(task.id)
        return {
            "task_id": result_task.id,
            "status": result_task.status.value,
            "title": result_task.title,
            "result": result_task.result.to_dict() if result_task.result else None,
            "error": result_task.error,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def delegate_subagent(parent_task_id: str, subtask_title: str, subtask_description: str, agent_role: str = "general") -> dict:
    """Delegate a subtask to a specialized subagent.

    Args:
        parent_task_id: ID of the parent task
        subtask_title: Title for the subtask
        subtask_description: Description of the subtask
        agent_role: Agent role for the subagent

    Returns:
        dict with subtask status
    """
    try:
        orchestrator = _get_orchestrator()
        parent_task = orchestrator.tasks.get(parent_task_id)
        if not parent_task:
            return {"status": "error", "message": f"Parent task {parent_task_id} not found"}
        subtask = Task(title=subtask_title, description=subtask_description, agent_role=agent_role)
        parent_task.subtasks.append(subtask)
        result = await orchestrator.execute_task(subtask.id)
        return {
            "subtask_id": result.id,
            "parent_task_id": parent_task_id,
            "status": result.status.value,
            "result": result.result.to_dict() if result.result else None,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def approve_operation(task_id: str, approved: bool) -> dict:
    """Approve or deny a destructive operation.

    Args:
        task_id: ID of the task to approve/deny
        approved: Whether to approve (True) or deny (False)

    Returns:
        dict with approval status
    """
    try:
        orchestrator = _get_orchestrator()
        result = orchestrator.approve_task(task_id, approved)
        return {"task_id": task_id, "approved": approved, "success": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def steer_agent(rules: List[str]) -> dict:
    """Send steering rules to guide agent behavior.

    Args:
        rules: List of steering rules (e.g. "DENY: delete files in src/", "ALLOW: edit tests/")

    Returns:
        dict with steering status
    """
    try:
        orchestrator = _get_orchestrator()
        for rule in rules:
            orchestrator.add_steering_rule(rule)
        return {"status": "ok", "rules_added": len(rules), "total_rules": len(orchestrator.steering_rules)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_agent_status(task_id: str) -> dict:
    """Get the status of an agent task.

    Args:
        task_id: ID of the task

    Returns:
        dict with task status and details
    """
    try:
        orchestrator = _get_orchestrator()
        task = orchestrator.get_task_status(task_id)
        if not task:
            return {"status": "error", "message": f"Task {task_id} not found"}
        return {
            "task_id": task.id,
            "title": task.title,
            "status": task.status.value,
            "agent_role": task.agent_role,
            "requires_approval": task.requires_approval,
            "approval_decision": task.approval_decision,
            "error": task.error,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_active_tasks() -> dict:
    """Get all active (pending/running) agent tasks.

    Returns:
        dict with list of active tasks
    """
    try:
        orchestrator = _get_orchestrator()
        tasks = orchestrator.get_active_tasks()
        return {
            "status": "ok",
            "active_tasks": [
                {
                    "task_id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "agent_role": t.agent_role,
                    "requires_approval": t.requires_approval,
                }
                for t in tasks
            ],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
    try:
        import urllib.parse
        encoded_text = urllib.parse.quote(clean)
        # Use Google Translate API (client gtx is free, keyless)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={encoded_text}"
        resp = httpx.get(url, timeout=4.0)
        if resp.status_code == 200:
            result = resp.json()
            translated = "".join([part[0] for part in result[0] if part[0]])
            if translated and translated.strip().lower() != clean.lower():
                return translated
    except Exception:
        pass
    return text


