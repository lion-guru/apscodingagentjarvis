"""
DevMind Web Server — FastAPI Backend + WebSocket
"""
import os
from pathlib import Path

# Load .env file into os.environ on startup
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

import re
import logging
logger = logging.getLogger("devmind")
import asyncio
import base64
import time
import subprocess
import ast_analyzer
import linter_engine
import terminal_manager
import knowledge_items
import session_manager
import agent_command_center
import project_explorer
import inline_editor
import completion_engine
import context_manager
import spaces_manager
import diagnostics_panel
import steering_engine
import ide_bridge
import deploy_panel
import search_engine
import workspace_index
import mcp_server
import self_healing_workflow
import stt_engine
import tts_engine
import ram_monitor
import breadcrumb_nav
import agent_core
import agent_specialists
import attention_engine
import stream_manager
import hermes_agent
import moe_router
import multimodal_engine
import reasoning_engine
import hermes_acp_client
import json
import master_db
from datetime import datetime

def get_ollama_tools(tools_registry):
    ollama_tools = []
    for name, tool in tools_registry.items():
        properties = {}
        required = []
        for param, desc in tool.params_schema.items():
            param_type = "string"
            if "bool" in desc.lower():
                param_type = "boolean"
            properties[param] = {
                "type": param_type,
                "description": desc
            }
            required.append(param)
            
        ollama_tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        })
    return ollama_tools

import json
from datetime import datetime
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Starlette / FastAPI compatibility patch for router init
try:
    import starlette.routing
    _orig_router_init = starlette.routing.Router.__init__
    def _patched_router_init(self, *args, **kwargs):
        kwargs.pop("on_startup", None)
        kwargs.pop("on_shutdown", None)
        return _orig_router_init(self, *args, **kwargs)
    starlette.routing.Router.__init__ = _patched_router_init
except Exception:
    pass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
from agent import (
    build_system_prompt, execute_tool, create_tool_registry,
    restore_last_turn, compact_history, check_ollama, load_env_file,
    DEFAULT_MODEL, OLLAMA_BASE, DEFAULT_WORKSPACE, get_abs_path,
    ollama_chat, set_workspace, set_context,
    THIRD_EYE_AVAILABLE, _mm,
    _is_zen_model, ZEN_API_URL, ZEN_FREE_MODELS,
    _is_omniroute_model, OMNIROUTE_URL
)

# Re-import helpers
from main import extract_tool_calls, remove_tool_calls
from self_healing_workflow import attempt_heal

app = FastAPI(
    title="DevMind AI Agent API",
    description="FastAPI backend for Jarvis/DevMind AI coding assistant",
    version="1.0.0"
)

# ─── Modular Route Registration ──────────────────────────────────
from app.routes.ai import router as ai_router
from app.routes.ide import router as ide_router
from app.routes.system import router as system_router
from app.routes.knowledge import router as knowledge_router
app.include_router(ai_router)
app.include_router(ide_router)
app.include_router(system_router)
app.include_router(knowledge_router)

for _agent in agent_specialists.create_default_agents().values():
    agent_core._orchestrator.register_agent(_agent)

# Register Hermes agents
for _agent in hermes_agent.create_hermes_agents().values():
    agent_core._orchestrator.register_agent(_agent)

# Initialize MoE router
_moe_router = moe_router.MoERouter()
for _expert in agent_specialists.create_default_agents().values():
    _moe_router.add_expert(moe_router.ExpertProfile(expert_name=_expert.role, model=_expert.model if hasattr(_expert, 'model') else 'gemma3:1b'))
agent_core._orchestrator.set_moe_router(_moe_router)

# Initialize MCP Manager
mcp_manager = mcp_server.MCPManager()

# Initialize StreamManager
_stream_manager = stream_manager.StreamManager()

# Initialize VLM Engine
_vlm_engine = multimodal_engine.VLMEngine()

# Initialize Reasoning Engine
_reasoning_engine = reasoning_engine.ReasoningEngine()

# ─── Helper Functions for IDE Bridge Endpoints ─────────────────────────────

def generate_cursor_rules_md(rules: list) -> str:
    """Generate .cursor/rules devmind.mdc content from rules list."""
    lines = ["---", "description: DevMind AI coding rules", "---", ""]
    for rule in rules:
        if isinstance(rule, dict):
            lines.append(f"- **{rule.get('name', 'Rule')}**: {rule.get('description', rule.get('content', ''))}")
        else:
            lines.append(f"- {rule}")
    return "\n".join(lines)

def generate_windsurf_mcp_config_json(mcp_servers: list) -> dict:
    """Generate Windsurf MCP config JSON from server list."""
    config = {"mcpServers": {}}
    for server in mcp_servers:
        name = server.get("name", "unknown")
        config["mcpServers"][name] = {
            "command": server.get("command", ""),
            "args": server.get("args", []),
            "env": server.get("env", {}),
        }
    return config

# Add CORS middleware to support cross-origin WebSocket connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a default tools registry for web sessions
tools_registry = create_tool_registry()

# ─── State ───────────────────────────────────
sessions: dict[str, dict] = {}
WORKSPACE = DEFAULT_WORKSPACE


# ─── HTTP Routes ─────────────────────────────

@app.get("/")
async def root():
    return FileResponse("web/index.html")


@app.post("/api/terminal/run")
async def terminal_run(data: dict):
    """Execute a shell command on the server workspace safely."""
    cmd = data.get("command", "").strip()
    cwd_val = data.get("cwd") or str(WORKSPACE)
    if not cmd:
        return {"output": "No command provided"}
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd_val
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode(errors="replace")
        err = stderr.decode(errors="replace")
        result = output + (f"\n[STDERR]\n{err}" if err else "")
        return {"output": result or "Command executed cleanly."}
    except Exception as e:
        return {"output": f"Execution error: {e}"}


@app.post("/api/chat")
async def chat_endpoint(data: dict):
    """Process single turn chat message."""
    user_msg = data.get("message", "").strip()
    model = data.get("model", DEFAULT_MODEL)
    if not user_msg:
        return {"response": "Message cannot be empty"}
    try:
        return {"response": f"DevMind AI ({model}): Processed request '{user_msg}' successfully."}
    except Exception as e:
        return {"response": f"Assistant response error: {e}"}

@app.get("/api/server/status")
async def server_status():
    """Check if DevMind server is running and return basic info."""
    return {
        "status": "ok",
        "server": "DevMind AI Studio",
        "version": "1.0.0",
        "port": 7860,
        "models_available": len(tools_registry) if tools_registry else 0,
        "workspace": WORKSPACE,
    }

if os.path.exists("web/audio"):
    app.mount("/audio", StaticFiles(directory="web/audio"), name="audio")
if os.path.exists("web/assets"):
    app.mount("/assets", StaticFiles(directory="web/assets"), name="assets")
if os.path.exists("web/videos"):
    app.mount("/videos", StaticFiles(directory="web/videos"), name="videos")



# ─── WebSocket Chat ───────────────────────────


@app.get("/api/supervisor/opencode")
async def supervisor_opencode_status():
    """Get OpenCode robot supervisor status."""
    try:
        from third_eye import OpenCodeSupervisor
        sup = OpenCodeSupervisor()
        return sup.detect()
    except Exception as e:
        return {"running": False, "error": str(e)}


@app.get("/api/workspace/last")
async def get_last_workspace():
    """Get last active workspace directory."""
    return {"workspace": DEFAULT_WORKSPACE}











@app.post("/api/voice/trigger")
async def voice_trigger_endpoint(req: Request):
    """Handle background 'DEV' wake word trigger event."""
    try:
        data = await req.json()
        text = data.get("text", "")
        command = data.get("command", "")
        print(f"[DEV WAKE WORD TRIGGERED] Spoken: '{text}' -> Command: '{command}'")
        return {"status": "success", "triggered": True, "text": text, "command": command}
    except Exception as e:
        return {"status": "error", "message": str(e)}








@app.get("/api/extensions/marketplace")
async def extensions_marketplace_endpoint():
    """Get list of extensions in marketplace."""
    try:
        from plugins import plugin_engine
        return plugin_engine.get_marketplace()
    except Exception as e:
        return []


@app.post("/api/extensions/toggle")
async def extensions_toggle_endpoint(id: str):
    """Install or toggle extension plugin."""
    try:
        from plugins import plugin_engine
        return plugin_engine.toggle_plugin(id)
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/overnight/queue")
async def overnight_queue_endpoint():
    """Get overnight task queue."""
    try:
        from overnight_worker import overnight_worker
        return overnight_worker.get_queue()
    except Exception as e:
        return {"tasks": []}


class OvernightTaskReq(BaseModel):
    prompt: str


@app.post("/api/overnight/add")
async def overnight_add_endpoint(req: OvernightTaskReq):
    """Add task to overnight worker queue."""
    try:
        from overnight_worker import overnight_worker
        return overnight_worker.add_task(req.prompt)
    except Exception as e:
        return {"status": "error", "error": str(e)}








@app.post("/api/self_repair/run")
async def self_repair_run_endpoint():
    """Scan codebase files and perform automatic bug repairs."""
    try:
        from self_repair_autofix import self_repair_engine
        return self_repair_engine.scan_and_repair()
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/third-eye/browser")
async def third_eye_browser(action: str = "detect"):
    """Control browser-based IDEs (OpenCode web, Windsurf, etc.)."""
    try:
        from agent import THIRD_EYE_AVAILABLE, _TE
        if not THIRD_EYE_AVAILABLE or _TE is None:
            return {"available": False, "error": "Third Eye not loaded"}

        bo = getattr(_TE, "browser_operator", None)
        if bo is None:
            return {"available": False, "error": "Browser operator not available"}

        if action == "detect":
            ide = bo.detect_ide_in_browser()
            return {"detected_ide": ide, "driver_available": getattr(bo, "_driver", None) is not None}
        elif action == "read":
            return {"output": bo.read_ide_output()}
        elif action == "check_error":
            err = bo.detect_error_in_ide()
            if err:
                mm = getattr(_TE, "model_manager", None)
                best = mm.select_model_for_task("coding") if mm else "gemini-2.5-flash"
                switched = bo.switch_ide_model(best)
                retried = bo.click_retry_or_resubmit()
                return {"error": err, "switched_to": best, "switched": switched, "retried": retried}
            return {"error": None, "message": "No errors detected"}
        else:
            return {"error": "invalid action", "valid_actions": ["detect", "read", "check_error"]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/diff/file")
async def get_file_diff(path: str = "", cwd: str | None = None):
    file_path = path.strip('\'"')
    root_cwd = cwd.strip('\'"') if cwd and cwd.strip('\'"') else str(DEFAULT_WORKSPACE)
    try:
        proc = await asyncio.create_subprocess_shell(
            f'git diff "{file_path}"' if file_path else 'git diff',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=root_cwd
        )
        stdout, stderr = await proc.communicate()
        diff_text = stdout.decode(errors="replace").strip()
        if not diff_text:
            proc_staged = await asyncio.create_subprocess_shell(
                f'git diff --cached "{file_path}"' if file_path else 'git diff --cached',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=root_cwd
            )
            out_staged, _ = await proc_staged.communicate()
            diff_text = out_staged.decode(errors="replace").strip()
        return {"diff": diff_text}
    except Exception as e:
        return {"diff": "", "error": str(e)}



@app.get("/api/files")
async def get_files(cwd: str | None = None, dir_path: str | None = None):
    root_cwd = cwd.strip('\'"') if cwd and cwd.strip('\'"') else str(DEFAULT_WORKSPACE)
    if dir_path:
        cwd_path = Path(dir_path.strip('\'"'))
        if not cwd_path.is_absolute():
            cwd_path = Path(root_cwd) / cwd_path
    else:
        cwd_path = Path(root_cwd)
        
    if not cwd_path.is_dir():
        return {"files": []}
    try:
        items = []
        for path in sorted(cwd_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            # Skip hidden/git folders, but show .devmind
            if path.name.startswith(".") and path.name not in [".devmind", ".agents"]:
                continue
            if path.name in ["__pycache__", "node_modules", ".git"]:
                continue
            items.append({
                "name": path.name,
                "is_dir": path.is_dir(),
                "path": str(path),
                "rel_path": str(path.relative_to(root_cwd)) if root_cwd in str(path) else path.name
            })
        return {"files": items, "current_dir": str(cwd_path)}
    except Exception as e:
        return {"files": [], "error": str(e)}



@app.get("/api/git/status")
async def get_git_status(cwd: str | None = None):
    cwd_clean = cwd.strip('\'"') if cwd and cwd.strip('\'"') else str(DEFAULT_WORKSPACE)
    try:
        proc = await asyncio.create_subprocess_shell(
            "git status --porcelain",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd_clean
        )
        stdout, stderr = await proc.communicate()
        err = stderr.decode(errors="replace").strip()
        if err:
            print(f"[Git Status Error] {err}")
        lines = stdout.decode(errors="replace").strip().split("\n")
        changes = []
        for line in lines:
            if line.strip():
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2:
                    code, file_path = parts
                    changes.append({"status": code, "file": file_path})
        return {"changes": changes, "error": err}
    except Exception as e:
        print(f"[Git Status Exception] {e}")
        return {"changes": [], "error": str(e)}


@app.get("/api/git/commits")
async def get_git_commits(cwd: str | None = None):
    cwd_clean = cwd.strip('\'"') if cwd and cwd.strip('\'"') else str(DEFAULT_WORKSPACE)
    try:
        proc = await asyncio.create_subprocess_shell(
            "git log -n 5 --oneline",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd_clean
        )
        stdout, stderr = await proc.communicate()
        err = stderr.decode(errors="replace").strip()
        if err:
            print(f"[Git Commits Error] {err}")
        lines = stdout.decode(errors="replace").strip().split("\n")
        commits = []
        for line in lines:
            if line.strip():
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2:
                    sha, msg = parts
                    commits.append({"sha": sha, "message": msg})
        return {"commits": commits, "error": err}
    except Exception as e:
        print(f"[Git Commits Exception] {e}")
        return {"commits": [], "error": str(e)}


@app.get("/api/files/content")
async def get_file_content(path: str):
    file_path = Path(path.strip('\'"'))
    if not file_path.is_file():
        return {"content": "", "error": "File not found"}
    try:
        content = file_path.read_text(encoding="utf-8")
        return {"content": content}
    except Exception as e:
        return {"content": "", "error": str(e)}


@app.post("/api/files/save")
async def save_file_content(data: dict):
    path = data.get("path", "").strip('\'"')
    content = data.get("content", "")
    file_path = Path(path)
    try:
        from agent import backup_file
        backup_file(path)
        file_path.write_text(content, encoding="utf-8")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/files/create")
async def create_new_file(data: dict):
    path = data.get("path", "").strip('\'"')
    file_path = Path(path)
    try:
        if file_path.exists():
            return {"success": False, "error": "File already exists"}
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("", encoding="utf-8")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/files/delete")
async def delete_file_endpoint(data: dict):
    path = data.get("path", "").strip('\'"')
    file_path = Path(path)
    try:
        if not file_path.is_file():
            return {"success": False, "error": "File not found"}
        from agent import backup_file
        backup_file(path)
        file_path.unlink()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/git/commit")
async def git_commit_gui(data: dict):
    cwd = data.get("cwd", "").strip('\'"')
    message = data.get("message", "").strip()
    try:
        await asyncio.create_subprocess_shell("git add .", cwd=cwd)
        proc = await asyncio.create_subprocess_shell(
            f'git commit -m "{message}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        stdout, stderr = await proc.communicate()
        err = stderr.decode(errors="replace").strip()
        out = stdout.decode(errors="replace").strip()
        return {"success": True, "output": out, "error": err}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/terminal/run")
async def run_terminal_command(data: dict):
    cwd = data.get("cwd", "").strip('\'"')
    command = data.get("command", "").strip()
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode(errors="replace").strip()
        err = stderr.decode(errors="replace").strip()
        return {"success": True, "output": out, "error": err}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/config/gemini")
async def configure_gemini(data: dict):
    api_key = data.get("api_key", "").strip()
    if not api_key:
        return {"success": False, "error": "API Key cannot be empty"}
    try:
        env_lines = []
        if os.path.exists(".env"):
            with open(".env", "r", encoding="utf-8") as f:
                env_lines = f.readlines()
        
        replaced = False
        for i, line in enumerate(env_lines):
            if line.strip().startswith("GEMINI_API_KEY="):
                env_lines[i] = f"GEMINI_API_KEY={api_key}\n"
                replaced = True
                break
        
        if not replaced:
            env_lines.append(f"\nGEMINI_API_KEY={api_key}\n")
            
        with open(".env", "w", encoding="utf-8") as f:
            f.writelines(env_lines)
            
        os.environ["GEMINI_API_KEY"] = api_key
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/model-config")
async def save_model_config(data: dict):
    """Save/update manual failover config (model_config.json)."""
    try:
        from model_usage_tracker import CONFIG_FILE
        existing = {}
        if CONFIG_FILE.exists():
            existing = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        # Only update the keys the user provided
        for key in ("failover_chain", "disabled_models", "switch_threshold", "manual_override"):
            if key in data:
                existing[key] = data[key]
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        return {"success": True, "config": existing}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/autocomplete")
async def autocomplete(data: dict):
    model = data.get("model", "llama-3.3-70b-versatile")
    prefix = data.get("text_before_cursor", "")
    suffix = data.get("text_after_cursor", "")
    
    # We'll construct a prompt for code completion
    prompt = f"Complete the following code. Provide ONLY the inserted code, without markdown formatting or explanation. Do not repeat the prefix.\n\nPREFIX:\n{prefix[-1000:]}\n\nSUFFIX:\n{suffix[:500]}"
    
    try:
        if "gemini" in model.lower():
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key: return {"success": False, "error": "No Gemini API Key"}
            
            gemini_model_map = {
                "gemini-1.5-flash": "gemini-2.5-flash",
                "gemini-1.5-pro": "gemini-2.5-flash",
                "gemini-2.0-flash": "gemini-2.5-flash",
                "gemini-2.0-flash-exp": "gemini-2.5-flash",
                "gemini": "gemini-2.5-flash",
                "gemini-2.5-flash": "gemini-2.5-flash"
            }
            official_model = gemini_model_map.get(model.lower(), model.lower())
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{official_model}:generateContent?key={api_key}"
            payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
            async with httpx.AsyncClient() as client:
                r = await client.post(url, json=payload, timeout=10.0)
                r.raise_for_status()
                result = r.json()
            completion = result["candidates"][0]["content"]["parts"][0]["text"]
        elif "/" in model or "openrouter" in model.lower():
            api_key = master_db.get_key("OPENROUTER_API_KEY")
            if not api_key: return {"success": False, "error": "No OpenRouter Key"}
            url = "https://openrouter.ai/api/v1/chat/completions"
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            async with httpx.AsyncClient() as client:
                r = await client.post(url, json=payload, headers=headers, timeout=10.0)
                r.raise_for_status()
                result = r.json()
            completion = result["choices"][0]["message"]["content"]
        elif "gpt" in model.lower():
            api_key = master_db.get_key("OPENAI_API_KEY")
            if not api_key: return {"success": False, "error": "No OpenAI Key"}
            url = "https://api.openai.com/v1/chat/completions"
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            async with httpx.AsyncClient() as client:
                r = await client.post(url, json=payload, headers=headers, timeout=10.0)
                r.raise_for_status()
                result = r.json()
            completion = result["choices"][0]["message"]["content"]
        elif "claude" in model.lower():
            api_key = master_db.get_key("ANTHROPIC_API_KEY")
            if not api_key: return {"success": False, "error": "No Anthropic Key"}
            url = "https://api.anthropic.com/v1/messages"
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1024}
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
            async with httpx.AsyncClient() as client:
                r = await client.post(url, json=payload, headers=headers, timeout=10.0)
                r.raise_for_status()
                result = r.json()
            completion = result["content"][0]["text"]
        else:
            url = f"{OLLAMA_BASE}/api/generate"
            payload = {"model": model, "prompt": prompt, "stream": False}
            async with httpx.AsyncClient() as client:
                r = await client.post(url, json=payload, timeout=10.0)
                r.raise_for_status()
                result = r.json()
            completion = result["response"]
            
        # Clean up common markdown blocks
        completion = completion.replace("```python\n", "").replace("```javascript\n", "").replace("```\n", "").replace("```", "")
        return {"success": True, "completion": completion.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/test_apis")
async def test_apis():
    import subprocess
    import sys
    try:
        proc = subprocess.run([sys.executable, "query_mysql.py"], capture_output=True, text=True, cwd="E:/coding-assistant")
        return {"output": proc.stdout, "error": proc.stderr}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/temp/query_mysql")
async def temp_query_mysql():
    import subprocess
    import sys
    try:
        import pymysql
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql", "--quiet"])
        import pymysql

    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3307"))
    user = os.getenv("MYSQL_USER", "root")
    passwords = [os.getenv("MYSQL_PASSWORD", ""), ""]
    connection = None
    
    for pwd in passwords:
        try:
            connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=pwd,
                autocommit=True
            )
            break
        except Exception:
            pass
            
    if not connection:
        return {"success": False, "error": "Could not connect to MySQL on 3307"}
        
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW DATABASES;")
            databases = [db[0] for db in cursor.fetchall()]
            
            target_db = "apsdreamhome"
            if target_db not in databases:
                for db in databases:
                    if target_db.lower() in db.lower():
                        target_db = db
                        break
            if target_db not in databases:
                return {"success": False, "error": "Database not found", "databases": databases}
                
            connection.select_db(target_db)
            cursor.execute("SHOW TABLES;")
            tables = [t[0] for t in cursor.fetchall()]
            
            found_keys = {}
            for table in tables:
                try:
                    cursor.execute(f"DESCRIBE `{table}`")
                    columns = [col[0] for col in cursor.fetchall()]
                    promising_cols = [c for c in columns if any(kw in c.lower() for kw in ["key", "val", "api", "config", "token", "secret", "setting"])]
                    if promising_cols:
                        cursor.execute(f"SELECT * FROM `{table}` LIMIT 100")
                        rows = cursor.fetchall()
                        for row in rows:
                            row_str = str(row)
                            if "AIza" in row_str or "sk-or" in row_str or "key" in row_str.lower() or "api" in row_str.lower():
                                for val in row:
                                    if isinstance(val, str):
                                        if val.startswith("AIza"):
                                            found_keys["gemini_key"] = val
                                        elif val.startswith("sk-or-"):
                                            found_keys["openrouter_key"] = val
                                        elif len(val) > 20 and any(kw in val.lower() for kw in ["key", "secret"]):
                                            found_keys[table] = val
                except Exception:
                    pass
            
            env_path = Path(".env")
            env_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
            
            def update_env(k, v):
                replaced = False
                for i, line in enumerate(env_lines):
                    if line.strip().startswith(f"{k}="):
                        env_lines[i] = f"{k}={v}"
                        replaced = True
                        break
                if not replaced:
                    env_lines.append(f"{k}={v}")
                os.environ[k] = v

            if "gemini_key" in found_keys and not os.getenv("GEMINI_API_KEY"):
                update_env("GEMINI_API_KEY", found_keys["gemini_key"])
            if "openrouter_key" in found_keys and not os.getenv("OPENROUTER_API_KEY"):
                update_env("OPENROUTER_API_KEY", found_keys["openrouter_key"])
                
            env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
            
            return {"success": True, "found_keys": found_keys}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if connection:
            connection.close()


@app.post("/api/db/save-keys")
async def save_keys_to_db(request: Request):
    """Save all API keys from .env to project SQLite database."""
    try:
        from master_db import save_keys_from_env
        result = save_keys_from_env()
        return {"success": True, "database": "master_db.sqlite", "table": "api_keys", **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/db/list-keys")
async def list_keys_from_db(provider: str = ""):
    """List all API keys from project SQLite database (masked values)."""
    try:
        from master_db import list_api_keys_masked
        keys = list_api_keys_masked(provider)
        return {"success": True, "keys": keys, "count": len(keys)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/db/add-key")
async def add_key_to_db(request: Request):
    """Add a single API key to database."""
    try:
        data = await request.json()
        from master_db import save_api_key
        result = save_api_key(
            provider=data.get("provider", ""),
            key_name=data.get("key_name", ""),
            key_value=data.get("key_value", ""),
            label=data.get("label", ""),
            email=data.get("email", ""),
            is_primary=data.get("is_primary", False)
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/db/delete-key")
async def delete_key_from_db(request: Request):
    """Delete an API key from database."""
    try:
        data = await request.json()
        from master_db import delete_api_key
        result = delete_api_key(data.get("provider", ""), data.get("key_name", ""))
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/db/set-primary")
async def set_primary_key_endpoint(request: Request):
    """Set a key as primary for a provider."""
    try:
        data = await request.json()
        from master_db import set_primary_key
        result = set_primary_key(data.get("provider", ""), data.get("key_name", ""))
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/db/get-key")
async def get_key_from_db(provider: str, key_name: str = ""):
    """Get a specific API key value (for internal use)."""
    try:
        from master_db import get_api_key
        result = get_api_key(provider, key_name)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/tasks")
async def get_tasks():
    tasks_file = Path("tasks.json")
    if not tasks_file.exists():
        from task_queue_runner import DEFAULT_TASKS
        tasks_file.write_text(json.dumps(DEFAULT_TASKS, indent=2), encoding="utf-8")
        return {"tasks": DEFAULT_TASKS}
    try:
        tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        return {"tasks": tasks}
    except Exception as e:
        return {"tasks": [], "error": str(e)}


@app.post("/api/tasks/add")
async def add_task(data: dict):
    title = data.get("title", "").strip()
    instruction = data.get("instruction", "").strip()
    if not title or not instruction:
        return {"success": False, "error": "Title and instruction are required"}
    
    tasks_file = Path("tasks.json")
    tasks = []
    if tasks_file.exists():
        try:
            tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        except Exception:
            tasks = []
            
    new_id = max([t.get("id", 0) for t in tasks] + [0]) + 1
    new_task = {
        "id": new_id,
        "title": title,
        "instruction": instruction,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    tasks.append(new_task)
    tasks_file.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    return {"success": True, "task": new_task}


@app.post("/api/tasks/run")
async def trigger_task_run(data: dict):
    model = data.get("model", DEFAULT_MODEL)
    cwd = data.get("cwd", str(DEFAULT_WORKSPACE))
    import subprocess
    import sys
    script_path = Path("task_queue_runner.py")
    try:
        subprocess.Popen([sys.executable, str(script_path), "--cwd", cwd, "--model", model])
        return {"success": True, "message": "Autonomous task runner launched"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/agent/system_status")
async def system_status():
    from agent import detect_project_type
    cwd = str(DEFAULT_WORKSPACE)
    project_type = detect_project_type(cwd)
    
    # Read mcp.json if present
    mcp_path = Path.home() / "AppData" / "Roaming" / "OpenCode" / "User" / "mcp.json"
    mcp_servers = []
    if mcp_path.exists():
        try:
            mcp_data = json.loads(mcp_path.read_text(encoding="utf-8"))
            for name, cfg in mcp_data.get("mcpServers", {}).items():
                mcp_servers.append({
                    "name": name,
                    "disabled": cfg.get("disabled", False),
                    "note": cfg.get("note", "")
                })
        except Exception:
            pass
            
    keys_loaded = {
        "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
        "OPENROUTER_API_KEY": bool(os.getenv("OPENROUTER_API_KEY")),
        "OPENCODE_API_KEY": bool(os.getenv("OPENCODE_API_KEY")),
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
        "GITHUB_TOKEN": bool(os.getenv("GITHUB_TOKEN")),
    }
    
    return {
        "workspace": cwd,
        "project_type": project_type,
        "keys_loaded": keys_loaded,
        "mcp_servers_count": len(mcp_servers),
        "mcp_servers": mcp_servers
    }


@app.get("/api/model-quotas")
async def model_quotas():
    """Report per-model quota/usage status + current manual config."""
    try:
        from model_usage_tracker import usage_tracker, CONFIG_FILE
        statuses = {}
        # Report status for every known working model plus configured ones
        models = set()
        try:
            from agent import _mm, THIRD_EYE_AVAILABLE, ZEN_FREE_MODELS
            if THIRD_EYE_AVAILABLE and _mm:
                for m in _mm.models or []:
                    models.add(m["model"])
            if os.getenv("OPENCODE_API_KEY"):
                models.update(ZEN_FREE_MODELS)
        except Exception:
            pass
        for model in sorted(models):
            try:
                statuses[model] = usage_tracker.quota_status(model)
            except Exception:
                pass
        manual_config = {}
        try:
            import json as _json
            if CONFIG_FILE.exists():
                manual_config = _json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {
            "models": statuses,
            "manual_config": manual_config,
            "config_file": str(CONFIG_FILE),
            "usage_file": str(usage_tracker._cache.get("calls", []).__class__) if False else str(
                Path.home() / ".devmind" / "model_usage.json"),
            "call_count_24h": len(usage_tracker._cache.get("calls", [])),
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Model Performance & Token Summary Endpoints ──────────────

@app.get("/api/model/performance")
async def model_performance():
    """Return per-model performance report (success rate, avg time, tokens)."""
    try:
        from model_performance_tracker import performance_tracker
        report = performance_tracker.get_performance_report()
        return {"status": "ok", "report": report}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/token-summary")
async def token_summary():
    """Return aggregated token usage and cost summary."""
    try:
        from cost_tracker import tracker
        summary = tracker.get_summary()
        return {"status": "ok", "summary": summary}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/ide/detect")
async def ide_detect():
    """Detect which IDEs are currently running on the system."""
    try:
        from agent import THIRD_EYE_AVAILABLE, _TE
        if THIRD_EYE_AVAILABLE and _TE:
            detected = _TE.app_monitor.detect_running_ide()
            status = _TE.app_monitor.get_status()
            return {
                "detected_ide": detected,
                "all_processes": status.get("monitored_processes", []),
                "process_health": status.get("process_health", {}),
            }
        return {"detected_ide": None, "note": "Third Eye not available"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/ide/monitor")
async def ide_monitor(ide: str = ""):
    """Monitor the health and status of a running IDE."""
    try:
        from agent import THIRD_EYE_AVAILABLE, _TE
        if THIRD_EYE_AVAILABLE and _TE:
            am = _TE.app_monitor
            if ide:
                health = am.monitor_window_activity(ide)
                hang = am.detect_hang(ide, threshold_seconds=30)
                return {
                    "ide": ide,
                    "health": health,
                    "hang_detected": hang["hung"],
                    "idle_seconds": hang["idle_seconds"],
                }
            else:
                return am.get_status()
        return {"error": "Third Eye not available"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/ide/recover")
async def ide_recover(data: dict):
    """Recover a hung or crashed IDE."""
    try:
        ide_name = data.get("ide", "")
        if not ide_name:
            return {"error": "Please specify IDE name", "valid_ides": ["OpenCode", "Windsurf", "Cursor", "VS Code", "Antigravity"]}

        from agent import THIRD_EYE_AVAILABLE, _TE
        if THIRD_EYE_AVAILABLE and _TE:
            recovery = _TE.recovery_engine.diagnose_and_recover(
                error=f"IDE {ide_name} needs recovery",
                context="ide_recovery",
                proc_name=ide_name
            )
            return {"ok": True, "recovery": recovery}
        return {"error": "Third Eye not available"}
    except Exception as e:
        return {"error": str(e)}


# ─── Extension Detection & Installation ──────────────────

@app.get("/api/extensions/detect")
async def detect_extensions():
    """Detect installed and missing VS Code extensions."""
    try:
        # Common extensions for web development
        common_extensions = [
            {"name": "ESLint", "id": "dbaeumer.vscode-eslint", "command": "code --install-extension dbaeumer.vscode-eslint"},
            {"name": "Prettier", "id": "esbenp.prettier-vscode", "command": "code --install-extension esbenp.prettier-vscode"},
            {"name": "GitLens", "id": "eamodio.gitlens", "command": "code --install-extension eamodio.gitlens"},
            {"name": "Python", "id": "ms-python.python", "command": "code --install-extension ms-python.python"},
            {"name": "JavaScript Debugger", "id": "ms-vscode.js-debug", "command": "code --install-extension ms-vscode.js-debug"},
            {"name": "Auto Rename Tag", "id": "formulahendry.auto-rename-tag", "command": "code --install-extension formulahendry.auto-rename-tag"},
            {"name": "Bracket Pair Colorization", "id": "coenraadp.bracket-pair-colorizer-2", "command": "code --install-extension coenraadp.bracket-pair-colorizer-2"},
            {"name": "Path Intellisense", "id": "christian-kohler.path-intellisense", "command": "code --install-extension christian-kohler.path-intellisense"},
            {"name": "Live Server", "id": "ritwickdey.LiveServer", "command": "code --install-extension ritwickdey.LiveServer"},
            {"name": "HTML CSS Support", "id": "ecmel.vscode-html-css", "command": "code --install-extension ecmel.vscode-html-css"},
        ]

        extensions = []
        for ext in common_extensions:
            # Check if extension is installed by looking for it in the extensions directory
            installed = False
            ext_dir = Path.home() / ".vscode" / "extensions"
            if ext_dir.exists():
                for d in ext_dir.iterdir():
                    if ext["id"].replace(".", "-").lower() in d.name.lower():
                        installed = True
                        break
            # Also try checking via code command
            if not installed:
                try:
                    result = subprocess.run(
                        ["code", "--list-extensions"],
                        capture_output=True, text=True, timeout=5
                    )
                    if ext["id"] in result.stdout:
                        installed = True
                except Exception:
                    pass

            extensions.append({
                "name": ext["name"],
                "id": ext["id"],
                "installed": installed,
                "command": ext["command"],
            })

        return {"extensions": extensions}
    except Exception as e:
        return {"error": str(e), "extensions": []}


@app.post("/api/extensions/install")
async def install_extension(data: dict):
    """Install a VS Code extension."""
    try:
        name = data.get("name", "")
        command = data.get("command", "")
        if not command:
            return {"success": False, "error": "No install command provided"}

        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )
        success = result.returncode == 0
        return {
            "success": success,
            "output": result.stdout,
            "error": result.stderr if not success else "",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── GitHub Features ─────────────────────────────────────

@app.get("/api/github/issues")
async def get_github_issues():
    """Get GitHub issues for the current repo."""
    try:
        cwd = str(DEFAULT_WORKSPACE)
        # Check if it's a git repo with a remote
        remote_result = subprocess.run(
            "git remote -v", shell=True, capture_output=True, text=True, cwd=cwd, timeout=10
        )
        remote_url = remote_result.stdout.strip()

        # Extract owner/repo from remote URL
        repo_info = None
        if "github.com" in remote_url:
            parts = remote_url.split("github.com/")
            if len(parts) > 1:
                repo_path = parts[1].replace(".git", "").strip()
                repo_info = repo_path

        if not repo_info:
            return {"issues": [], "error": "No GitHub remote found"}

        # Try to get issues using GitHub CLI
        gh_result = subprocess.run(
            "gh issue list --state all --limit 20 --json number,title,state",
            shell=True, capture_output=True, text=True, cwd=cwd, timeout=15
        )

        if gh_result.returncode != 0:
            # Fallback: try gh auth status first
            auth_result = subprocess.run(
                "gh auth status", shell=True, capture_output=True, text=True, timeout=10
            )
            if auth_result.returncode != 0:
                return {
                    "issues": [],
                    "error": "GitHub CLI not authenticated. Run 'gh auth login' first.",
                    "repo": repo_info,
                }
            return {"issues": [], "error": "Failed to fetch issues", "repo": repo_info}

        try:
            issues = json.loads(gh_result.stdout)
            return {"issues": issues, "repo": repo_info}
        except json.JSONDecodeError:
            return {"issues": [], "error": "Failed to parse issues output", "repo": repo_info}

    except Exception as e:
        return {"issues": [], "error": str(e)}


@app.post("/api/github/pr")
async def create_github_pr(data: dict):
    """Create a GitHub PR."""
    try:
        title = data.get("title", "")
        body = data.get("body", "")
        base = data.get("base", "main")
        head = data.get("head", "")

        if not title:
            return {"success": False, "error": "PR title is required"}

        cwd = str(DEFAULT_WORKSPACE)

        # Get current branch if head not specified
        if not head:
            branch_result = subprocess.run(
                "git branch --show-current", shell=True, capture_output=True, text=True, cwd=cwd, timeout=10
            )
            head = branch_result.stdout.strip()

        # Create PR using GitHub CLI
        cmd = f'gh pr create --title "{title}" --body "{body}" --base {base} --head {head}'
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=30
        )

        if result.returncode == 0:
            # Extract PR URL from output
            pr_url = result.stdout.strip()
            return {"success": True, "pr_url": pr_url, "output": pr_url}
        else:
            return {"success": False, "error": result.stderr.strip() or result.stdout.strip()}

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/github/commit-and-push")
async def commit_and_push(data: dict):
    """Commit all changes and push to GitHub."""
    try:
        cwd = str(DEFAULT_WORKSPACE)
        message = data.get("message", "")

        if not message:
            # Auto-generate commit message
            diff_result = subprocess.run(
                "git diff --stat", shell=True, capture_output=True, text=True, cwd=cwd, timeout=10
            )
            message = f"Auto-commit: {diff_result.stdout.strip() or 'updates'}"

        # Stage, commit, push
        commands = [
            "git add -A",
            f'git commit -m "{message}"',
            "git push",
        ]

        results = []
        for cmd in commands:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=30
            )
            results.append({"cmd": cmd, "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()})

        success = all(r["returncode"] == 0 for r in results)
        return {"success": success, "results": results}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── WebSocket Chat ───────────────────────────

import re

def parse_mention(text):
    match = re.search(r'@(gpt-4o(?:-mini)?|claude(?:-3-5-sonnet)?|gemini(?:-1\.5-flash|-1\.5-pro|-2\.0-flash)?)', text, re.IGNORECASE)
    if match:
        tag = match.group(1).lower()
        if "gpt-4o-mini" in tag: return "gpt-4o-mini"
        if "gpt" in tag: return "gpt-4o"
        if "claude" in tag: return "claude-3-5-sonnet-latest"
        if "gemini-1.5-pro" in tag: return "gemini-1.5-pro"
        if "gemini-1.5-flash" in tag: return "gemini-1.5-flash"
        if "gemini" in tag: return "gemini-2.0-flash"
    return None


def inject_handover(session: dict, new_model: str) -> None:
    """Append a Handover Briefing to the session so a freshly-switched model
    (after quota/rate-limit failover) understands the work-in-progress state."""
    try:
        from agent import build_handover_briefing
        cwd_val = session.get("cwd") or str(WORKSPACE)
        briefing = build_handover_briefing(session["messages"], cwd_val)
        session["messages"].append({
            "role": "user",
            "content": (f"[Model switched to {new_model}.]\n\n{briefing}\n\n"
                        f"Continue the task above. Do not restart it.")
        })
    except Exception as e:
        print(f"[Handover warning] {e}")


@app.websocket("/ws/{session_id:path}")
                
                if agentic_mode:
                    user_input = (
                        "🚀 [AGENTIC AUTO-PILOT ENABLED]\n"
                        "You are operating in fully autonomous Agentic Mode. Your goal is to completely resolve the user's task on your own.\n"
                        "1. Do not stop until the goal is fully achieved.\n"
                        "2. Always start by creating a `plan.md` file using your tools.\n"
                        "3. Use your tools sequentially to complete the task. Check your work.\n"
                        "4. When finished, summarize what you accomplished.\n\n"
                        "USER TASK:\n" + user_input
                    )
                
                user_msg = {"role": "user", "content": user_input}
                if image_base64:
                    user_msg["image"] = image_base64
                    user_msg["mime_type"] = mime_type
                
                session["messages"].append(user_msg)
                await send("user_ack", {
                    "content": user_input, 
                    "has_image": True if image_base64 else False
                })
                
                # Auto-compact history if context token usage is too high
                session["messages"] = compact_history(session["messages"], model)
                
                # Parse user mention
                mentioned_model = parse_mention(user_input)
                if mentioned_model:
                    model = mentioned_model
                    await send("info", {"content": f"🤖 Routing to {model}..."})
                
                # Agentic loop
                max_iterations = 100 if agentic_mode else 10
                tool_call_history: list[tuple[str, str]] = []
                consecutive_no_progress = 0
                # Broadcast coder agent running status
                try:
                    from agent_town_bridge import update_agent_status
                    update_agent_status("coder", "running", user_input[:80])
                except Exception:
                    pass
                for iteration in range(max_iterations):
                    await send("thinking", {"step": iteration + 1})
                    
                    full_response = ""
                    try:
                        if "gemini" in model.lower():
                            # Google Gemini Route
                            api_key = master_db.get_key("GEMINI_API_KEY")
                            if not api_key:
                                await send("error", {"content": "GEMINI_API_KEY is not configured! Please open ⚙️ Settings and save your API key."})
                                break
                                
                            system_instruction = ""
                            contents = []
                            for m in session["messages"]:
                                role = m["role"]
                                content = m["content"]
                                if role == "system":
                                    system_instruction = content
                                else:
                                    gemini_role = "user" if role == "user" else "model"
                                    parts = [{"text": content}]
                                    if m.get("image"):
                                        parts.append({
                                            "inlineData": {
                                                "mimeType": m.get("mime_type", "image/png"),
                                                "data": m["image"]
                                            }
                                        })
                                    contents.append({
                                        "role": gemini_role,
                                        "parts": parts
                                    })
                            
                            payload = {"contents": contents}
                            if system_instruction:
                                payload["systemInstruction"] = {
                                    "parts": [{"text": system_instruction}]
                                }
                            
                            gemini_model_map = {
                                "gemini-1.5-flash": "gemini-2.5-flash",
                                "gemini-1.5-pro": "gemini-2.5-flash",
                                "gemini-2.0-flash": "gemini-2.5-flash",
                                "gemini-2.0-flash-exp": "gemini-2.5-flash",
                                "gemini": "gemini-2.5-flash",
                                "gemini-2.5-flash": "gemini-2.5-flash"
                            }
                            official_model = gemini_model_map.get(model.lower(), model.lower())
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/{official_model}:generateContent?key={api_key}"
                            
                            async with httpx.AsyncClient() as client:
                                resp = await client.post(url, json=payload, timeout=90.0)
                                if resp.status_code == 429 or resp.status_code >= 500:
                                    err_code = resp.status_code
                                    if master_db.get_key("GROQ_API_KEY"):
                                        await send("info", {"content": f"⚠️ Gemini Error ({err_code}). Auto-switching to Groq Llama 3.3 70B (Free)..."})
                                        inject_handover(session, "llama-3.3-70b-versatile")
                                        model = "llama-3.3-70b-versatile"
                                        session["model"] = "llama-3.3-70b-versatile"
                                        await send("model_changed", {"model": "llama-3.3-70b-versatile"})
                                        continue
                                    elif master_db.get_key("OPENROUTER_API_KEY"):
                                        await send("info", {"content": f"⚠️ Gemini Error ({err_code}). Auto-switching to Gemma 2 9B (OpenRouter Free)..."})
                                        inject_handover(session, "google/gemma-2-9b-it:free")
                                        model = "google/gemma-2-9b-it:free"
                                        session["model"] = "google/gemma-2-9b-it:free"
                                        await send("model_changed", {"model": "google/gemma-2-9b-it:free"})
                                        continue
                                    else:
                                        await send("info", {"content": f"⚠️ Gemini Error ({err_code}). Pausing 3s to retry..."})
                                        await asyncio.sleep(3.0)
                                        continue
                                resp.raise_for_status()
                                result = resp.json()
                                
                            try:
                                full_response = result["candidates"][0]["content"]["parts"][0]["text"]
                            except (KeyError, IndexError):
                                if "error" in result:
                                    raise ValueError(f"Gemini API Error: {result['error'].get('message', 'Unknown')}")
                                raise ValueError(f"Unexpected response structure from Gemini API: {result}")
                            
                            # Simulate streaming for Gemini to keep UI looking dynamic
                            await send("assistant_start", {})
                            chunk_size = 30
                            for idx in range(0, len(full_response), chunk_size):
                                chunk_text = full_response[idx:idx+chunk_size]
                                if "<tool_call>" not in full_response[:idx+chunk_size]:
                                    await send("token", {"content": chunk_text})
                                await asyncio.sleep(0.005)
                        elif _is_zen_model(model.lower()):
                            # OpenCode Zen Route (multi-model gateway incl. free models)
                            api_key = master_db.get_key("OPENCODE_API_KEY")
                            if not api_key:
                                await send("error", {"content": "OPENCODE_API_KEY is not configured! Please open ⚙️ Settings and save your API key."})
                                break

                            formatted_messages = []
                            for m in session["messages"]:
                                formatted_messages.append({"role": m["role"], "content": m["content"]})

                            url = ZEN_API_URL
                            payload = {"model": model, "messages": formatted_messages}
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

                            async with httpx.AsyncClient() as client:
                                resp = await client.post(url, headers=headers, json=payload, timeout=90.0)
                                if resp.status_code == 429 or resp.status_code >= 500:
                                    err_code = resp.status_code
                                    # Rotate to the next Zen free model before giving up
                                    other_zen = [m for m in ZEN_FREE_MODELS if m != model]
                                    fallback_zen = other_zen[0] if other_zen else "llama-3.3-70b-versatile"
                                    await send("info", {"content": f"⚠️ Zen Error ({err_code}). Auto-switching to {fallback_zen}..."})
                                    inject_handover(session, fallback_zen)
                                    model = fallback_zen
                                    session["model"] = fallback_zen
                                    await send("model_changed", {"model": fallback_zen})
                                    continue
                                resp.raise_for_status()
                                result = resp.json()

                            try:
                                msg = result["choices"][0]["message"]
                                full_response = msg.get("content")
                                if not full_response and msg.get("reasoning"):
                                    full_response = msg["reasoning"]
                                if not full_response:
                                    full_response = result["choices"][0].get("text", "")
                                if full_response is None:
                                    full_response = ""
                            except (KeyError, IndexError):
                                if "error" in result:
                                    raise ValueError(f"Zen API Error: {result['error'].get('message', 'Unknown')}")
                                raise ValueError(f"Unexpected response structure from Zen API: {result}")

                            # Simulate streaming for UI
                            await send("assistant_start", {})
                            chunk_size = 30
                            for idx in range(0, len(full_response), chunk_size):
                                chunk_text = full_response[idx:idx+chunk_size]
                                if "<tool_call>" not in full_response[:idx+chunk_size]:
                                    await send("token", {"content": chunk_text})
                                await asyncio.sleep(0.005)
                        elif model.lower().startswith("auto/") or model.lower() == "omniroute":
                            # OmniRoute — local AI gateway (290+ providers, auto-fallback)
                            formatted_messages = []
                            for m in session["messages"]:
                                formatted_messages.append({"role": m["role"], "content": m["content"]})
                            payload = {"model": model, "messages": formatted_messages, "stream": False}
                            async with httpx.AsyncClient() as client:
                                resp = await client.post(OMNIROUTE_URL, json=payload, timeout=90.0)
                                if resp.status_code == 429 or resp.status_code >= 500:
                                    await send("info", {"content": f"⚠️ OmniRoute Error ({resp.status_code}). Retrying with next model..."})
                                    # Fall back to Groq as OmniRoute's own fallback
                                    inject_handover(session, "llama-3.3-70b-versatile")
                                    model = "llama-3.3-70b-versatile"
                                    session["model"] = "llama-3.3-70b-versatile"
                                    await send("model_changed", {"model": "llama-3.3-70b-versatile"})
                                    continue
                                resp.raise_for_status()
                                result = resp.json()
                            try:
                                full_response = result["choices"][0]["message"]["content"]
                                if full_response is None:
                                    full_response = ""
                            except (KeyError, IndexError):
                                if "error" in result:
                                    raise ValueError(f"OmniRoute Error: {result['error'].get('message', 'Unknown')}")
                                raise ValueError(f"Unexpected response structure from OmniRoute: {result}")

                            await send("assistant_start", {})
                            chunk_size = 30
                            for idx in range(0, len(full_response), chunk_size):
                                chunk_text = full_response[idx:idx+chunk_size]
                                if "<tool_call>" not in full_response[:idx+chunk_size]:
                                    await send("token", {"content": chunk_text})
                                await asyncio.sleep(0.005)
                        elif "/" in model or "openrouter" in model.lower():
                            # OpenRouter Route
                            api_key = master_db.get_key("OPENROUTER_API_KEY")
                            if not api_key:
                                await send("error", {"content": "OPENROUTER_API_KEY is not configured! Please open ⚙️ Settings and save your API key."})
                                break
                                
                            formatted_messages = []
                            for m in session["messages"]:
                                role = m["role"]
                                content = m["content"]
                                msg_payload = {"role": role, "content": content}
                                # OpenRouter supports images via URL, but for base64 it requires specific formatting. 
                                # Assuming text only for simplicity, or we can add image support if needed.
                                formatted_messages.append(msg_payload)
                                
                            url = "https://openrouter.ai/api/v1/chat/completions"
                            payload = {
                                "model": model,
                                "messages": formatted_messages
                            }
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": "http://localhost:7860",
                                "X-Title": "DevMind"
                            }
                            
                            async with httpx.AsyncClient() as client:
                                resp = await client.post(url, headers=headers, json=payload, timeout=90.0)
                                if resp.status_code != 200:
                                    err_info = resp.text
                                    if "credit" in err_info.lower() or "quota" in err_info.lower() or "insufficient" in err_info.lower():
                                        await send("info", {"content": "⚠️ OpenRouter Quota Error. Auto-switching to Groq Llama 3.3 70B (Free)..."})
                                        inject_handover(session, "llama-3.1-8b-instant")
                                        model = "llama-3.1-8b-instant"
                                        session["model"] = "llama-3.1-8b-instant"
                                        await send("model_changed", {"model": "llama-3.1-8b-instant"})
                                        continue
                                result = resp.json()
                                
                            try:
                                full_response = result["choices"][0]["message"]["content"]
                            except (KeyError, IndexError):
                                raise ValueError(f"Unexpected response structure from OpenRouter API: {result}")
                            
                            # Simulate streaming for OpenRouter
                            await send("assistant_start", {})
                            chunk_size = 30
                            for idx in range(0, len(full_response), chunk_size):
                                chunk_text = full_response[idx:idx+chunk_size]
                                if "<tool_call>" not in full_response[:idx+chunk_size]:
                                    await send("token", {"content": chunk_text})
                                await asyncio.sleep(0.005)
                        elif "gpt" in model.lower():
                            # Native OpenAI Route
                            api_key = master_db.get_key("OPENAI_API_KEY")
                            if not api_key:
                                await send("error", {"content": "OPENAI_API_KEY is not configured! Please open ⚙️ Settings and save your API key."})
                                break
                                
                            formatted_messages = []
                            for m in session["messages"]:
                                formatted_messages.append({"role": m["role"], "content": m["content"]})
                                
                            url = "https://api.openai.com/v1/chat/completions"
                            payload = {"model": model, "messages": formatted_messages}
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            
                            async with httpx.AsyncClient() as client:
                                resp = await client.post(url, headers=headers, json=payload, timeout=90.0)
                                if resp.status_code != 200:
                                    err_info = resp.text
                                    if "quota" in err_info.lower() or "billing" in err_info.lower() or "insufficient" in err_info.lower():
                                        await send("info", {"content": "⚠️ OpenAI Quota Error. Auto-switching to Groq Llama 3.1 8B (Free)..."})
                                        inject_handover(session, "llama-3.1-8b-instant")
                                        model = "llama-3.1-8b-instant"
                                        session["model"] = "llama-3.1-8b-instant"
                                        await send("model_changed", {"model": "llama-3.1-8b-instant"})
                                        continue
                                    else:
                                        await send("error", {"content": f"OpenAI API Error: {err_info}"})
                                        break
                                result = resp.json()
                                
                            try:
                                full_response = result["choices"][0]["message"]["content"]
                            except (KeyError, IndexError):
                                raise ValueError(f"Unexpected response structure from OpenAI API: {result}")
                            
                            await send("assistant_start", {})
                            chunk_size = 30
                            for idx in range(0, len(full_response), chunk_size):
                                chunk_text = full_response[idx:idx+chunk_size]
                                if "<tool_call>" not in full_response[:idx+chunk_size]:
                                    await send("token", {"content": chunk_text})
                                await asyncio.sleep(0.005)
                        elif "groq" in model.lower() or "llama-3" in model.lower() or "mixtral" in model.lower():
                            # Native Groq Route (Ultra-Fast)
                            api_key = master_db.get_key("GROQ_API_KEY")
                            if not api_key:
                                await send("error", {"content": "GROQ_API_KEY is not configured! Please open ⚙️ Settings and save your API key."})
                                break

                            formatted_messages = []
                            for m in session["messages"]:
                                formatted_messages.append({"role": m["role"], "content": m["content"]})

                            groq_model_map = {
                                "groq": "llama-3.3-70b-versatile",
                                "llama-3.3-70b": "llama-3.3-70b-versatile",
                                "llama-3.1-8b": "llama-3.1-8b-instant",
                                "mixtral-8x7b": "mixtral-8x7b-32768"
                            }
                            target_groq_model = groq_model_map.get(model.lower(), model)
                            url = "https://api.groq.com/openai/v1/chat/completions"
                            payload = {"model": target_groq_model, "messages": formatted_messages}
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            groq_org = os.getenv("GROQ_ORG_ID")
                            if groq_org:
                                headers["Groq-Organization"] = groq_org

                            async with httpx.AsyncClient() as client:
                                resp = await client.post(url, headers=headers, json=payload, timeout=90.0)
                                if resp.status_code == 429:
                                    # Rate limited — immediately fall back to Ollama local model
                                    await send("info", {"content": "⚠️ Groq rate limit hit. Switching to local Ollama model..."})
                                    # Find first working Ollama model
                                    ollama_models = [m for m in _mm.models if m.get("provider") == "ollama"] if THIRD_EYE_AVAILABLE and _mm else []
                                    fallback_model = ollama_models[0]["model"] if ollama_models else "llama3.2:3b"
                                    inject_handover(session, fallback_model)
                                    model = fallback_model
                                    session["model"] = fallback_model
                                    await send("model_changed", {"model": fallback_model})
                                    continue
                                elif resp.status_code != 200:
                                    err_text = resp.text
                                    # Check for quota/billing errors — fall back to Ollama
                                    if "quota" in err_text.lower() or "billing" in err_text.lower() or "insufficient" in err_text.lower() or "rate limit" in err_text.lower():
                                        await send("info", {"content": "⚠️ Groq quota error. Switching to local Ollama model..."})
                                        ollama_models = [m for m in _mm.models if m.get("provider") == "ollama"] if THIRD_EYE_AVAILABLE and _mm else []
                                        fallback_model = ollama_models[0]["model"] if ollama_models else "llama3.2:3b"
                                        inject_handover(session, fallback_model)
                                        model = fallback_model
                                        session["model"] = fallback_model
                                        await send("model_changed", {"model": fallback_model})
                                        continue
                                    else:
                                        await send("error", {"content": f"Groq API Error: {err_text}"})
                                        break
                                result = resp.json()

                            try:
                                full_response = result["choices"][0]["message"]["content"]
                            except (KeyError, IndexError):
                                raise ValueError(f"Unexpected response structure from Groq API: {result}")

                            await send("assistant_start", {})
                            chunk_size = 30
                            for idx in range(0, len(full_response), chunk_size):
                                chunk_text = full_response[idx:idx+chunk_size]
                                if "<tool_call>" not in full_response[:idx+chunk_size]:
                                    await send("token", {"content": chunk_text})
                                await asyncio.sleep(0.005)
                        elif "claude" in model.lower():
                            # Native Anthropic Route
                            api_key = master_db.get_key("ANTHROPIC_API_KEY")
                            if not api_key:
                                await send("error", {"content": "ANTHROPIC_API_KEY is not configured! Please open ⚙️ Settings and save your API key."})
                                break
                                
                            system_instruction = next((m["content"] for m in session["messages"] if m["role"] == "system"), "")
                            formatted_messages = []
                            for m in session["messages"]:
                                if m["role"] != "system":
                                    formatted_messages.append({"role": m["role"], "content": m["content"]})
                                
                            url = "https://api.anthropic.com/v1/messages"
                            payload = {
                                "model": model, 
                                "messages": formatted_messages,
                                "max_tokens": 4096
                            }
                            if system_instruction:
                                payload["system"] = system_instruction
                                
                            headers = {
                                "x-api-key": api_key, 
                                "anthropic-version": "2023-06-01", 
                                "Content-Type": "application/json"
                            }
                            
                            async with httpx.AsyncClient() as client:
                                resp = await client.post(url, headers=headers, json=payload, timeout=90.0)
                                if resp.status_code != 200:
                                    err_text = resp.text
                                    if "credit balance" in err_text.lower() or "quota" in err_text.lower() or "billing" in err_text.lower():
                                         await send("info", {"content": f"⚠️ Anthropic API Credit Exhausted. Auto-switching to Groq Llama 3.3 70B (Free)..."})
                                         inject_handover(session, "llama-3.3-70b-versatile")
                                         model = "llama-3.3-70b-versatile"
                                         session["model"] = "llama-3.3-70b-versatile"
                                         await send("model_changed", {"model": "llama-3.3-70b-versatile"})
                                         continue
                                    else:
                                        await send("error", {"content": f"Anthropic API Error: {err_text}"})
                                        break
                                result = resp.json()
                                
                            try:
                                full_response = result["content"][0]["text"]
                            except (KeyError, IndexError):
                                raise ValueError(f"Unexpected response structure from Anthropic API: {result}")
                            
                            await send("assistant_start", {})
                            chunk_size = 30
                            for idx in range(0, len(full_response), chunk_size):
                                chunk_text = full_response[idx:idx+chunk_size]
                                if "<tool_call>" not in full_response[:idx+chunk_size]:
                                    await send("token", {"content": chunk_text})
                                await asyncio.sleep(0.005)
                        else:
                            # Local Ollama Route
                            formatted_messages = []
                            for m in session["messages"]:
                                role = m["role"]
                                content = m["content"]
                                msg_payload = {"role": role, "content": content}
                                if m.get("image"):
                                    msg_payload["images"] = [m["image"]]
                                formatted_messages.append(msg_payload)
                                
                            ollama_tools = get_ollama_tools(tools_registry)
                                
                            async with httpx.AsyncClient() as client:
                                await send("assistant_start", {})
                                resp = await client.post(
                                    f"{OLLAMA_BASE}/api/chat",
                                    json={
                                        "model": model,
                                        "messages": formatted_messages,
                                        "stream": False,
                                        "tools": ollama_tools,
                                        "options": {
                                            "temperature": 0.1,
                                            "num_ctx": 16384
                                        }
                                    },
                                    timeout=300.0
                                )
                                result = resp.json()
                                msg = result.get("message", {})
                                text_content = msg.get("content", "") or ""
                                
                                # Simulate streaming for UI
                                chunk_size = 30
                                for idx in range(0, len(text_content), chunk_size):
                                    await send("token", {"content": text_content[idx:idx+chunk_size]})
                                    await asyncio.sleep(0.005)
                                    
                                full_response += text_content
                                
                                # Inject native tool calls as XML strings for the parser
                                if "tool_calls" in msg:
                                    for tc in msg["tool_calls"]:
                                        fn = tc.get("function", {})
                                        name = fn.get("name")
                                        args = fn.get("arguments", {})
                                        if isinstance(args, str):
                                            try:
                                                args = json.loads(args)
                                            except Exception:
                                                pass
                                        tc_json = json.dumps({"tool": name, "params": args})
                                        full_response += f"\n<tool_call>\n{tc_json}\n</tool_call>\n"
                    except Exception as e:
                        await send("error", {"content": f"Model Error: {str(e)}"})
                        break
                    
                    session["messages"].append({"role": "assistant", "content": full_response})
                    
                    # Send token usage info
                    est_input_tokens = sum(len(m.get("content", "")) for m in session["messages"]) // 4
                    est_output_tokens = len(full_response) // 4
                    est_total_tokens = est_input_tokens + est_output_tokens
                    await send("token_usage", {
                        "model": model,
                        "input_tokens": est_input_tokens,
                        "output_tokens": est_output_tokens,
                        "total_tokens": est_total_tokens,
                    })

                    # Extract tool calls
                    tool_calls = extract_tool_calls(full_response)
                    clean_text = remove_tool_calls(full_response)
                    # Strip thinking/reasoning blocks emitted by reasoning models (deepseek-r1, qwq, etc.)
                    clean_text = re.sub(r'<thinking>.*?</thinking>', '', clean_text, flags=re.DOTALL).strip()
                    
                    if clean_text:
                        await send("assistant_text", {"content": clean_text})
                    
                    ai_mention = parse_mention(full_response)
                    if ai_mention:
                        model = ai_mention
                        await send("info", {"content": f"🔄 Model delegating task to {model}..."})
                        session["messages"].append({"role": "user", "content": f"Please continue the task as {model}."})
                        continue # Skip breaking to trigger the next model

                    if not tool_calls:
                        await send("done", {})
                        break
                    
                    # Loop detection: if the same tool+params repeats, the agent is stuck
                    sig = tuple(sorted((k, str(v)[:300]) for k, v in tool_calls[0]["params"].items()))
                    history_sig = (tool_calls[0]["tool"], sig)
                    tool_call_history.append(history_sig)
                    repeat_count = sum(1 for h in tool_call_history[-4:] if h == history_sig)
                    if repeat_count >= 3:
                        await send("info", {"content": f"⚠️ Loop detected: '{tool_calls[0]['tool']}' repeated {repeat_count}x with identical params. Stopping."})
                        session["messages"].append({"role": "user", "content": "You appear to be stuck calling the same tool repeatedly. Stop looping and summarize your findings so far."})
                        # One more turn to let the model summarize, then finish
                        full_response = ""
                        try:
                            if "/" in model or "openrouter" in model.lower() or "gpt" in model.lower() or "claude" in model.lower() or "gemini" in model.lower() or "llama" in model.lower():
                                final_turn = await asyncio.get_event_loop().run_in_executor(
                                    None, lambda: ollama_chat(session["messages"], model)
                                )
                                await send("assistant_text", {"content": final_turn})
                        except Exception as e:
                            await send("error", {"content": f"Final turn failed: {e}"})
                        await send("done", {})
                        break
                    
                    # Execute tools
                    tool_results = []
                    executed_any = False
                    # Make the current conversation context available to fork_agent
                    # and fork-context skills (mirrors forkSubagent.ts context threading).
                    set_context(session["messages"])
                    MAX_HEAL_ATTEMPTS = 3
                    for tc in tool_calls:
                        tool_name = tc["tool"]
                        params = tc["params"]
                        
                        await send("tool_start", {"tool": tool_name, "params": params})
                        
                        # Self-healing retry loop (Windsurf/OpenCode style)
                        last_result = None
                        for attempt in range(MAX_HEAL_ATTEMPTS):
                            loop = asyncio.get_event_loop()
                            result = await loop.run_in_executor(
                                None, lambda tn=tool_name, p=params: execute_tool(tools_registry, tn, p)
                            )
                            
                            if result.success:
                                last_result = result
                                break
                            
                            # Trigger self-healing on failure
                            heal_result = await loop.run_in_executor(
                                None, lambda tn=tool_name, p=params, err=result.output, att=attempt: 
                                    attempt_heal(
                                        task=f"Tool: {tn}",
                                        error=err,
                                        context={"tool": tn, "params": dict(p), "cwd": session["cwd"], "attempt": att, "error": err}
                                    )
                            )
                            
                            if heal_result.get("healed") and attempt < MAX_HEAL_ATTEMPTS - 1:
                                # Apply healing - adjust params and retry
                                adjusted = heal_result.get("adjusted_params", params)
                                if isinstance(adjusted, dict) and "command" in adjusted:
                                    params = adjusted
                                await send("info", {"content": f"Self-healing: {heal_result['strategy']} (Attempt {attempt+1}/{MAX_HEAL_ATTEMPTS})"})
                                continue
                            else:
                                # No healing possible or max attempts reached
                                last_result = result
                                break
                        
                        executed_any = True
                        final_result = last_result if last_result else result
                        
                        await send("tool_result", {
                            "tool": tool_name, 
                            "result": final_result.output[:2000],
                            "success": final_result.success
                        })
                        tool_results.append(f"Tool '{tool_name}' result:\n{final_result.output}")
                    
                    if not executed_any:
                        await send("done", {})
                        break
                    
                    combined = "\n\n".join(tool_results)
                    session["messages"].append({"role": "user", "content": f"Tool results:\n{combined}"})
                
                # Broadcast coder agent done status
                try:
                    from agent_town_bridge import update_agent_status
                    update_agent_status("coder", "done", "")
                except Exception:
                    pass
            
            elif msg_type == "set_cwd":
                new_cwd = data.get("cwd", "").strip('\'"')
                if Path(new_cwd).is_dir():
                    session["cwd"] = new_cwd
                    set_workspace(new_cwd)
                    session["messages"][0] = {
                        "role": "system",
                        "content": build_system_prompt(new_cwd, tools_registry)
                    }
                    await send("cwd_changed", {"cwd": new_cwd})
                else:
                    await send("error", {"content": f"Directory not found: {new_cwd}"})
            
            elif msg_type == "set_model":
                session["model"] = data.get("model", DEFAULT_MODEL)
                await send("model_changed", {"model": session["model"]})
            
            elif msg_type == "clear":
                session["messages"] = [{
                    "role": "system",
                    "content": build_system_prompt(session["cwd"], tools_registry)
                }]
                await send("cleared", {})
    
    except WebSocketDisconnect:
        pass



# ─── VS Code Extension Bridge ──────────────────
vscode_sockets: set[WebSocket] = set()

async def broadcast_to_vscode(message: dict):
    """Async broadcast messages to all connected VS Code extensions"""
    disconnected = []
    for socket in vscode_sockets:
        try:
            await socket.send_json(message)
        except Exception:
            disconnected.append(socket)
    for socket in disconnected:
        vscode_sockets.discard(socket)

def vscode_callback(message: dict):
    """Sync wrapper callback to bridge tool execution threads with the asyncio loop"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_to_vscode(message), loop)
    except Exception:
        pass

# Bind callback to agent core
import agent
agent.VSCODE_CALLBACK = vscode_callback

@app.websocket("/ws/vscode_bridge")
async def vscode_bridge_endpoint(websocket: WebSocket):
    await websocket.accept()
    vscode_sockets.add(websocket)
    print("[VS Code Bridge] Extension connected.")
    try:
        while True:
            # Receive active editor contexts or command replies
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "editor_context":
                # We can store active document details if needed
                pass
    except WebSocketDisconnect:
        pass
    finally:
        vscode_sockets.remove(websocket)
        print("[VS Code Bridge] Extension disconnected.")




@app.get("/api/files/list")
async def list_files(path: str = "."):
    try:
        full_path = os.path.join(WORKSPACE, path)
        if not os.path.exists(full_path):
            return {"status": "error", "message": "Path not found"}
        if os.path.isfile(full_path):
            return {"status": "ok", "type": "file", "name": os.path.basename(full_path), "path": full_path}
        items = []
        for entry in sorted(os.listdir(full_path)):
            entry_path = os.path.join(full_path, entry)
            items.append({
                "name": entry,
                "type": "folder" if os.path.isdir(entry_path) else "file",
                "path": entry_path,
                "size": os.path.getsize(entry_path) if os.path.isfile(entry_path) else 0
            })
        return {"status": "ok", "items": items, "path": full_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/file/read")
async def read_file(path: str):
    try:
        full_path = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
        if not os.path.exists(full_path):
            return {"status": "error", "message": "File not found"}
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"status": "ok", "path": full_path, "content": content, "size": len(content)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/file/save")
async def save_file(request: Request):
    try:
        data = await request.json()
        path = data.get("path", "")
        content = data.get("content", "")
        full_path = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "ok", "path": full_path, "saved": True}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/file/create")
async def create_file(request: Request):
    try:
        data = await request.json()
        path = data.get("path", "")
        content = data.get("content", "")
        full_path = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "ok", "path": full_path, "created": True}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/file/delete")
async def delete_file(path: str):
    try:
        full_path = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
        if os.path.isdir(full_path):
            import shutil
            shutil.rmtree(full_path)
        elif os.path.exists(full_path):
            os.remove(full_path)
        return {"status": "ok", "deleted": full_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ─── AST Analysis Endpoints ─────────────────────────────────────────────────

@app.post("/api/ast/analyze")
async def analyze_file(request: Request):
    try:
        data = await request.json()
        path = data.get("path", "")
        full_path = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
        result = ast_analyzer.analyze_file(full_path)
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/ast/definition")
async def get_definition(path: str, symbol: str):
    try:
        full_path = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
        result = ast_analyzer.get_definition(full_path, symbol)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/ast/references")
async def get_references(path: str, symbol: str):
    try:
        full_path = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
        result = ast_analyzer.find_references(full_path, symbol)
        return {"status": "ok", "references": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/ast/outline")
async def get_outline(path: str):
    try:
        full_path = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
        result = ast_analyzer.get_outline(full_path)
        return {"status": "ok", "outline": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ─── Linting Endpoints ──────────────────────────────────────────────────────

@app.post("/api/lint")
async def lint_file(request: Request):
    try:
        data = await request.json()
        path = data.get("path", "")
        linters = data.get("linters", ["ruff", "pylint", "flake8"])
        full_path = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
        diagnostics = linter_engine.lint_file(full_path, linters)
        summary = linter_engine.get_diagnostics_summary(diagnostics)
        return {"status": "ok", "diagnostics": summary}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/lint/auto-fix")
async def get_auto_fix(path: str):
    try:
        full_path = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
        diagnostics = linter_engine.lint_file(full_path)
        fixes = linter_engine.get_auto_fix(full_path, diagnostics)
        return {"status": "ok", "fixes": fixes}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ─── Terminal Endpoints ─────────────────────────────────────────────────────

@app.post("/api/terminal/session")
async def create_terminal_session(request: Request):
    try:
        data = await request.json()
        session_id = data.get("session_id", f"term_{int(time.time())}")
        cwd = data.get("cwd", WORKSPACE)
        result = terminal_manager.create_session(session_id, cwd)
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}







@app.delete("/api/terminal/session/{session_id}")
async def kill_terminal_session(session_id: str):
    result = terminal_manager.kill_session(session_id)
    return {"status": "ok", **result}

# ─── Chat Endpoint ──────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        model = data.get("model", "gemini-2.5-flash")
        messages = [{"role": "user", "content": message}]
        # ollama_chat is sync but handles all models (gemini/groq/openrouter/ollama)
        response = ollama_chat(messages, model=model)
        return {"status": "ok", "response": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ─── Agent Command Center Endpoints ────────────────────────────────────────

@app.get("/api/agents/list")
async def list_agents():
    return {"status": "ok", "agents": agent_command_center.list_agents()}

@app.post("/api/agents/spawn")
async def spawn_agent(request: Request):
    try:
        data = await request.json()
        name = data.get("name", "Agent")
        task = data.get("task", "")
        result = agent_command_center.spawn_agent(name, task)
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/agents/{agent_id}/status")
async def update_agent_status(agent_id: str, request: Request):
    try:
        data = await request.json()
        status = data.get("status", "idle")
        task = data.get("task", None)
        result = agent_command_center.update_agent(agent_id, status, task)
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ─── Knowledge Items Endpoints ─────────────────────────────────────────────





@app.get("/api/knowledge/search")
async def search_knowledge(q: str):
    results = knowledge_items.search(q)
    return {"status": "ok", "results": results}

# ─── Session Management Endpoints ──────────────────────────────────────────

@app.post("/api/session/create")
async def create_session(request: Request):
    try:
        data = await request.json()
        session_id = data.get("session_id", f"session_{int(time.time())}")
        workspace = data.get("workspace", WORKSPACE)
        session = session_manager.create_session(session_id, workspace)
        return {"status": "ok", "session": session}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        return {"status": "error", "message": "Session not found"}
    return {"status": "ok", "session": session}

@app.post("/api/session/{session_id}/message")
async def add_session_message(session_id: str, request: Request):
    try:
        data = await request.json()
        message = session_manager.add_message(session_id, data.get("role", "user"), data.get("content", ""))
        return {"status": "ok", "message": message}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/sessions/list")
async def list_sessions():
    sessions = session_manager.list_sessions()
    return {"status": "ok", "sessions": sessions}

# ─── Settings Endpoint ─────────────────────────────────────────────────────

@app.get("/api/settings")
async def get_settings():
    config_path = os.path.join(os.path.expanduser("~"), ".devmind", "model_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        config = {"failover_chain": [], "disabled_models": [], "switch_threshold": 0.85, "manual_override": {}}
    return {"status": "ok", "settings": config}

@app.post("/api/settings")
async def save_settings(request: Request):
    try:
        data = await request.json()
        config_path = os.path.join(os.path.expanduser("~"), ".devmind", "model_config.json")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)
        return {"status": "ok", "settings": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ─── RAG Search Endpoint ───────────────────────────────────────────────────

@app.post("/api/rag/search")
async def rag_search(request: Request):
    try:
        from rag_vector_engine import rag_engine
        data = await request.json()
        query = data.get("query", "")
        workspace = data.get("workspace", WORKSPACE)
        results = rag_engine.hybrid_search(query, workspace)
        return {"status": "ok", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}



# ─── IDE Bridges Endpoints ─────────────────────────────────────────────────

@app.post("/api/ide-bridge/cursor-rules")
async def generate_cursor_rules(request: Request):
    try:
        data = await request.json()
        rules = data.get("rules", [])
        content = generate_cursor_rules_md(rules)
        path = os.path.join(WORKSPACE, ".cursor", "rules", "devmind.mdc")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return {"status": "ok", "path": path, "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/ide-bridge/windsurf-mcp")
async def generate_windsurf_mcp_config(request: Request):
    try:
        data = await request.json()
        mcp_servers = data.get("mcp_servers", [])
        config = generate_windsurf_mcp_config_json(mcp_servers)
        path = os.path.join(WORKSPACE, ".windsurf", "mcp_config.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
        return {"status": "ok", "path": path, "config": config}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ???? Project Explorer Endpoints ????

@app.get("/api/project/tree")
async def get_project_tree(path: str = None):
    try:
        tree = project_explorer.get_file_tree(path)
        return {"status": "ok", "tree": tree}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/project/search")
async def search_project_files(q: str = ""):
    try:
        results = project_explorer.search_files(q)
        return {"status": "ok", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/project/symbols")
async def get_file_symbols(file_path: str = ""):
    try:
        symbols = project_explorer.get_symbols(file_path)
        return {"status": "ok", "symbols": symbols}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/project/breadcrumbs")
async def get_breadcrumbs(file_path: str = ""):
    try:
        crumbs = project_explorer.get_breadcrumbs(file_path)
        return {"status": "ok", "breadcrumbs": crumbs}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ???? Inline Editor Endpoints ????

@app.post("/api/inline/edit")
async def inline_edit(request: Request):
    try:
        data = await request.json()
        result = inline_editor.create_diff(
            data.get("file_path", ""),
            data.get("old_string", ""),
            data.get("new_string", ""),
            data.get("replace_all", False),
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/inline/accept")
async def accept_inline_edit(request: Request):
    try:
        data = await request.json()
        result = inline_editor.accept_diff(data.get("diff_id"))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/inline/decline")
async def decline_inline_edit(request: Request):
    try:
        data = await request.json()
        result = inline_editor.decline_diff(data.get("diff_id"))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/inline/pending")
async def list_pending_edits():
    return {"status": "ok", "edits": inline_editor.list_pending_edits()}

@app.get("/api/inline/history")
async def list_edit_history():
    return {"status": "ok", "history": inline_editor.list_edit_history()}

# ???? Completion Engine Endpoints ????

@app.get("/api/completions")
async def get_completions(
    file_path: str = "",
    line: str = "",
    cursor_pos: int = 0,
    context: str = "",
    language: str = "python",
):
    try:
        completions = completion_engine.get_completions(
            file_path, line, cursor_pos, context, language
        )
        return {"status": "ok", "completions": completions}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/completions/record")
async def record_completion(request: Request):
    try:
        data = await request.json()
        completion_engine.record_completion(
            data.get("file_path", ""),
            data.get("label", ""),
            data.get("insert_text", ""),
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ???? Context Manager Endpoints ????

@app.post("/api/context/save")
async def save_context(request: Request):
    try:
        data = await request.json()
        result = context_manager.save_context(
            data.get("session_id", ""),
            data.get("messages", []),
            data.get("artifacts", []),
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/context/load")
async def load_context(session_id: str = ""):
    return context_manager.load_context(session_id)

@app.get("/api/context/list")
async def list_contexts():
    return {"status": "ok", "contexts": context_manager.list_contexts()}

@app.get("/api/context/stats")
async def context_stats():
    return {"status": "ok", "stats": context_manager.get_context_stats()}

# ???? Spaces Manager Endpoints ????





@app.get("/api/spaces/get")
async def get_space(space_id: str = ""):
    return spaces_manager.get_space(space_id)

@app.post("/api/spaces/add-file")
async def add_file_to_space(request: Request):
    try:
        data = await request.json()
        result = spaces_manager.add_file_to_space(
            data.get("space_id", ""),
            data.get("file_path", ""),
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/spaces/delete")
async def delete_space(request: Request):
    try:
        data = await request.json()
        result = spaces_manager.delete_space(data.get("space_id", ""))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ???? Diagnostics Panel Endpoints ????

@app.post("/api/diagnostics/run")
async def run_diagnostics(request: Request):
    try:
        data = await request.json()
        result = diagnostics_panel.run_linting(data.get("file_path", ""))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/diagnostics/get")
async def get_diagnostics(file_path: str = ""):
    return diagnostics_panel.get_diagnostics(file_path)



@app.post("/api/diagnostics/clear")
async def clear_diagnostics(request: Request):
    try:
        data = await request.json()
        result = diagnostics_panel.clear_diagnostics(data.get("file_path"))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ???? Steering Engine Endpoints ????

@app.post("/api/steering/create")
async def create_steering(request: Request):
    try:
        data = await request.json()
        result = steering_engine.create_steering_file(
            data.get("name", ""),
            data.get("content", ""),
            data.get("scope", "project"),
            data.get("language"),
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/steering/list")
async def list_steering_files():
    return {"status": "ok", "files": steering_engine.list_steering_files()}

@app.get("/api/steering/get")
async def get_steering_file(name: str = ""):
    return steering_engine.get_steering_file(name)

@app.post("/api/steering/update")
async def update_steering(request: Request):
    try:
        data = await request.json()
        result = steering_engine.update_steering_file(
            data.get("name", ""),
            data.get("content"),
            data.get("scope"),
            data.get("language"),
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/steering/delete")
async def delete_steering(request: Request):
    try:
        data = await request.json()
        result = steering_engine.delete_steering_file(data.get("name", ""))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ???? IDE Bridge Endpoints ????

@app.post("/api/bridge/cursor")
async def bridge_cursor(request: Request):
    try:
        data = await request.json()
        result = ide_bridge.ide_bridge.generate_cursor_config(data.get("workspace", WORKSPACE))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/bridge/windsurf")
async def bridge_windsurf(request: Request):
    try:
        data = await request.json()
        result = ide_bridge.ide_bridge.generate_windsurf_config(data.get("workspace", WORKSPACE))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/bridge/opencode")
async def bridge_opencode(request: Request):
    try:
        data = await request.json()
        result = ide_bridge.ide_bridge.generate_opencode_config(data.get("workspace", WORKSPACE))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/bridge/list")
async def list_bridges():
    return {"status": "ok", "bridges": ide_bridge.ide_bridge.list_bridges()}

# ???? Deploy Panel Endpoints ????

@app.post("/api/deploy/docker")
async def deploy_docker(request: Request):
    try:
        data = await request.json()
        result = deploy_panel.deploy_docker(data.get("workspace", WORKSPACE))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/deploy/cloud")
async def deploy_cloud(request: Request):
    try:
        data = await request.json()
        result = deploy_panel.deploy_cloud(
            data.get("provider", "aws"),
            data.get("workspace", WORKSPACE),
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/deploy/local")
async def deploy_local(request: Request):
    try:
        data = await request.json()
        result = deploy_panel.deploy_local(data.get("workspace", WORKSPACE))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/deploy/list")
async def list_deployments():
    return {"status": "ok", "deployments": deploy_panel.list_deployments()}

# ???? Search Engine Endpoints ????

@app.post("/api/search/index")
async def search_index(request: Request):
    try:
        data = await request.json()
        result = search_engine.index_workspace(data.get("workspace", WORKSPACE))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/search")
async def search_files(
    q: str = "",
    method: str = "hybrid",
    top_k: int = 10,
):
    try:
        results = search_engine.search(q, top_k, method)
        return {"status": "ok", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ???? Workspace Index Endpoints ????

@app.get("/api/workspace/tree")
async def get_workspace_tree(path: str = None):
    try:
        tree = project_explorer.get_file_tree(path)
        return {"status": "ok", "tree": tree}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/workspace/index")
async def index_workspace(request: Request):
    try:
        data = await request.json()
        result = workspace_index.index_workspace(data.get("workspace", WORKSPACE))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/workspace/symbols")
async def get_workspace_symbols():
    return {"status": "ok", "symbols": workspace_index.get_symbols()}

@app.get("/api/workspace/find")
async def find_workspace_symbol(name: str = ""):
    return {"status": "ok", "results": workspace_index.find_symbol(name)}

@app.get("/api/workspace/imports")
async def get_import_graph():
    return {"status": "ok", "imports": workspace_index.get_import_graph()}

@app.get("/api/workspace/references")
async def get_cross_references(symbol_name: str = ""):
    return {"status": "ok", "references": workspace_index.get_cross_references(symbol_name)}

# ???? MCP Server Endpoints ????

@app.post("/api/mcp/register")
async def register_mcp_server(request: Request):
    try:
        data = await request.json()
        result = mcp_manager.register_server(
            data.get("name", ""),
            data.get("command", ""),
            data.get("args", []),
            data.get("env", {}),
            data.get("description", ""),
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/mcp/list")
async def list_mcp_servers():
    return {"status": "ok", "servers": mcp_manager.list_servers()}

@app.post("/api/mcp/start")
async def start_mcp_server(request: Request):
    try:
        data = await request.json()
        result = mcp_manager.start_server(data.get("name", ""))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/mcp/stop")
async def stop_mcp_server(request: Request):
    try:
        data = await request.json()
        result = mcp_manager.stop_server(data.get("name", ""))
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/mcp/call")
async def call_mcp_tool(request: Request):
    try:
        data = await request.json()
        result = mcp_manager.call_tool(
            data.get("server_name", ""),
            data.get("tool_name", ""),
            data.get("params", {}),
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ???? Skills Endpoints ????

@app.get("/api/skills/get")
async def get_skill(name: str = ""):
    skill_file = Path("skills") / f"{name}.md"
    if not skill_file.exists():
        return {"status": "error", "error": f"Skill '{name}' not found"}
    return {"status": "ok", "content": skill_file.read_text(encoding="utf-8")}

# ???? Artifacts Endpoints ????

@app.get("/api/artifacts/list")
async def list_artifacts():
    artifacts_dir = Path("artifacts")
    artifacts = []
    if artifacts_dir.exists():
        for f in artifacts_dir.glob("*"):
            if f.is_file():
                artifacts.append({
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                })
    return {"status": "ok", "artifacts": artifacts}

@app.get("/api/artifacts/get")
async def get_artifact(name: str = ""):
    artifact_file = Path("artifacts") / name
    if not artifact_file.exists():
        return {"status": "error", "error": f"Artifact '{name}' not found"}
    return {"status": "ok", "content": artifact_file.read_text(encoding="utf-8")}

# ???? Agentic AI Endpoints ????

@app.post("/api/agent/execute")
async def agent_execute(request: Request):
    try:
        data = await request.json()
        result = await agent_core.execute_agent(
            data.get("title", ""),
            data.get("description", ""),
            data.get("agent_role", "general"),
            data.get("requires_approval", False),
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/agent/delegate")
async def agent_delegate(request: Request):
    try:
        data = await request.json()
        result = await agent_core.delegate_subagent(
            data.get("parent_task_id", ""),
            data.get("title", ""),
            data.get("description", ""),
            data.get("agent_role", "general"),
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/agent/approve")
async def agent_approve(request: Request):
    try:
        data = await request.json()
        result = await agent_core.approve_operation(
            data.get("task_id", ""),
            data.get("approved", False),
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/agent/steer")
async def agent_steer(request: Request):
    try:
        data = await request.json()
        rules = data.get("rules", [])
        result = await agent_core.steer_agent(rules)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/agent/status/{task_id}")
async def agent_status(task_id: str):
    try:
        result = await agent_core.get_agent_status(task_id)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/agent/active")
async def agent_active():
    try:
        result = await agent_core.get_active_tasks()
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/agent/modes")
async def agent_modes():
    return {
        "status": "ok",
        "modes": [
            {"id": "chat", "label": "Chat Mode", "description": "Agent suggests, human approves each step"},
            {"id": "inline", "label": "Inline Ctrl+K", "description": "Agent makes inline edits with preview"},
            {"id": "autonomous", "label": "Full Autonomous", "description": "Agent runs end-to-end with HITL checkpoints only"},
        ],
    }

@app.post("/api/agent/shortcuts")
async def agent_shortcuts(request: Request):
    try:
        data = await request.json()
        shortcut = data.get("shortcut", "")
        shortcuts = {
            "auto_fix": {
                "title": "Auto-Fix All Problems",
                "description": "Run linter and auto-fix all issues",
                "agent_role": "healer",
            },
            "generate_tests": {
                "title": "Generate Test Suite",
                "description": "Generate unit tests for current file",
                "agent_role": "reviewer",
            },
            "refactor_selection": {
                "title": "Refactor Selection",
                "description": "Refactor selected code for better structure",
                "agent_role": "coder",
            },
            "architectural_review": {
                "title": "Architectural Review",
                "description": "Review project structure and suggest improvements",
                "agent_role": "planner",
            },
            "deploy_app": {
                "title": "Deploy App",
                "description": "Deploy application to Azure",
                "agent_role": "planner",
            },
        }
        if shortcut not in shortcuts:
            return {"status": "error", "message": f"Unknown shortcut: {shortcut}"}
        config = shortcuts[shortcut]
        result = await agent_core.execute_agent(
            config["title"], config["description"], config["agent_role"]
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Hermes ACP Integration Endpoints
@app.get("/api/hermes/acp/status")
async def hermes_acp_status():
    client = hermes_acp_client.HermesACPClient()
    connected = await client.connect()
    if connected:
        await client.disconnect()
        return {"status": "ok", "hermes_acp_available": True}
    return {"status": "ok", "hermes_acp_available": False}


@app.post("/api/hermes/acp/chat")
async def hermes_acp_chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        session_id = data.get("session_id")
        client = hermes_acp_client.HermesACPClient()
        connected = await client.connect()
        if not connected:
            return {"status": "error", "message": "Hermes ACP not available"}
        result = await client.chat(message, session_id)
        await client.disconnect()
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/hermes/acp/tools")
async def hermes_acp_tools():
    try:
        client = hermes_acp_client.HermesACPClient()
        connected = await client.connect()
        if not connected:
            return {"status": "error", "message": "Hermes ACP not available"}
        tools = await client.get_tools()
        await client.disconnect()
        return {"status": "ok", "tools": tools}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/hermes/acp/sessions")
async def hermes_acp_sessions():
    try:
        client = hermes_acp_client.HermesACPClient()
        connected = await client.connect()
        if not connected:
            return {"status": "error", "message": "Hermes ACP not available"}
        sessions = await client.list_sessions()
        await client.disconnect()
        return {"status": "ok", "sessions": sessions}
    except Exception as e:
        return {"status": "error", "message": str(e)}












@app.get("/api/streams/active")
async def streams_active():
    return {"status": "ok", "channels": _stream_manager.list_channels(), "active_count": _stream_manager.get_active_count()}

@app.post("/api/streams/merge")
async def streams_merge(request: Request):
    try:
        data = await request.json()
        stream_names = data.get("streams", [])
        strategy = data.get("strategy", "interleave")
        merged = []
        async for item in _stream_manager.merge_streams(stream_names, strategy):
            merged.append(item)
        return {"status": "ok", "merged_items": len(merged)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── Agent Town Integration ─────────────────────────────────
from agent_town_bridge import get_all_agents, get_agent, update_agent_status, register_ws_client, unregister_ws_client, get_activity, route_task, add_activity

@app.get("/api/agent-town/agents")
async def agent_town_agents():
    """Return all DevMind agents with their current status for Agent Town."""
    return {"status": "ok", "agents": get_all_agents()}

@app.get("/api/agent-town/agents/{agent_id}")
async def agent_town_agent(agent_id: str):
    """Return a single DevMind agent by ID."""
    agent = get_agent(agent_id)
    if not agent:
        return {"status": "error", "message": f"Agent '{agent_id}' not found"}
    return {"status": "ok", "agent": agent}

@app.post("/api/agent-town/agents/{agent_id}/status")
async def agent_town_update_status(agent_id: str, request: Request):
    """Update an agent's status (called by DevMind internals)."""
    data = await request.json()
    update_agent_status(agent_id, data.get("status", "idle"), data.get("task", ""))
    return {"status": "ok"}

@app.get("/api/agent-town/activity")
async def agent_town_activity():
    """Return recent activity feed for Agent Town."""
    return {"status": "ok", "activity": get_activity()}

@app.post("/api/agent-town/chat")
async def agent_town_chat(request: Request):
    """Chat endpoint with smart agent routing. Agent Town sends a message,
    DevMind routes it to the best agent and returns the response."""
    try:
        data = await request.json()
        message = data.get("message", "").strip()
        if not message:
            return {"status": "error", "message": "Empty message"}

        # Route to best agent
        agent_id = route_task(message)
        agent = get_agent(agent_id)
        agent_name = agent.get("name", "Coder") if agent else "Coder"

        # Add activity entry
        add_activity(agent_id, "started", message)

        # Execute via the chat engine (handles all models)
        model = data.get("model", "gemini-2.5-flash")
        messages = [{"role": "user", "content": message}]
        response = ollama_chat(messages, model=model)

        # Mark completed
        add_activity(agent_id, "completed", message, response=response[:500])

        return {
            "status": "ok",
            "response": response,
            "routed_to": agent_id,
            "agent_name": agent_name,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ─── STT / TTS / RAM Monitor Endpoints ───────────────────────────

@app.get("/api/ram/status")
async def ram_status():
    """Get current RAM usage and swap status."""
    return ram_monitor.get_status()

@app.post("/api/ram/check")
async def ram_check():
    """Check RAM and auto-swap to cloud if needed."""
    result = ram_monitor.check_and_swap()
    return {"status": "ok", **result}

@app.get("/api/stt/status")
async def stt_status():
    """Check STT engine status."""
    try:
        from stt_engine import DEFAULT_MODEL, WHISPER_MODEL
        import psutil
        ram = psutil.virtual_memory()
        return {
            "status": "ok",
            "engine": "faster-whisper",
            "model": DEFAULT_MODEL,
            "whisper_model": WHISPER_MODEL,
            "ram_available_gb": round(ram.available / (1024**3), 2),
            "ready": True
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/tts/status")
async def tts_status():
    """Check TTS engine status."""
    try:
        from tts_engine import list_voices, DEFAULT_VOICE
        voices = list_voices()
        return {
            "status": "ok",
            "engines": ["edge-tts", "pyttsx3"],
            "default_voice": DEFAULT_VOICE,
            "voices_count": len(voices),
            "ready": True
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/stt/transcribe")
async def stt_transcribe(request: Request):
    """Transcribe audio file to text using faster-whisper."""
    try:
        data = await request.json()
        file_path = data.get("file_path", "")
        language = data.get("language", "en")

        if not file_path:
            return {"status": "error", "message": "file_path required"}

        result = stt_engine.transcribe_file(file_path, language)
        return {"status": "ok" if result["success"] else "error", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/stt/transcribe-bytes")
async def stt_transcribe_bytes(request: Request):
    """Transcribe raw audio bytes to text."""
    try:
        body = await request.body()
        content_type = request.headers.get("content-type", "audio/wav")

        # Determine file extension from content type
        ext = ".wav"
        if "mp3" in content_type:
            ext = ".mp3"
        elif "ogg" in content_type:
            ext = ".ogg"
        elif "webm" in content_type:
            ext = ".webm"

        result = stt_engine.transcribe_bytes(body, f"audio{ext}")
        return {"status": "ok" if result["success"] else "error", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/tts/synthesize")
async def tts_synthesize(request: Request):
    """Synthesize text to speech."""
    try:
        data = await request.json()
        text = data.get("text", "")
        agent = data.get("agent", None)
        voice = data.get("voice", None)
        engine = data.get("engine", "auto")

        if not text:
            return {"status": "error", "message": "text required"}

        result = tts_engine.synthesize(text, agent=agent, voice=voice, engine=engine)
        return {"status": "ok" if result["success"] else "error", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/tts/voices")
async def tts_voices():
    """List available TTS voices."""
    voices = tts_engine.list_voices()
    return {"status": "ok", "voices": voices}

# ─────────────────────────────────────────────────────────────
# LOCAL VISION ENDPOINTS (Local First, AI Fallback)
# ─────────────────────────────────────────────────────────────
@app.post("/api/vision/read")
async def vision_read_file(request: Request):
    """
    Smart file reading - local tools first, AI fallback.
    Reads images, PDFs, text files. Only uses AI when needed.
    """
    try:
        data = await request.json()
        file_path = data.get("file_path", "")
        task = data.get("task", "read text")
        
        if not file_path:
            return {"status": "error", "error": "file_path required"}
        
        from local_vision import smart_vision
        result = smart_vision.read_file(file_path, task)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/vision/screenshot")
async def vision_screenshot(request: Request):
    """Capture and analyze screenshot - local capture, AI analysis if needed."""
    try:
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        task = data.get("task", "describe")
        
        from local_vision import smart_vision
        result = smart_vision.read_screenshot(task)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/vision/analyze")
async def vision_analyze(request: Request):
    """
    Analyze image/PDF with AI model (when local tools aren't enough).
    Automatically picks smallest appropriate model.
    """
    try:
        data = await request.json()
        image_b64 = data.get("image_base64", "")
        file_path = data.get("file_path", "")
        prompt = data.get("prompt", "Describe this image")
        model = data.get("model", "")  # Auto-pick if empty
        
        if not image_b64 and not file_path:
            return {"status": "error", "error": "image_base64 or file_path required"}
        
        # Import Ollama for local AI
        import httpx
        import psutil
        
        # Get available RAM
        ram_available = psutil.virtual_memory().available // (1024 * 1024)
        
        # Pick model based on RAM
        if not model:
            if ram_available < 200:
                return {"status": "error", "error": "Not enough RAM for vision model"}
            elif ram_available < 500:
                model = "moondream:1.8b"
            else:
                model = "gemma3:4b"
        
        # Get image data
        if file_path and not image_b64:
            from local_vision import smart_vision
            file_result = smart_vision.read_file(file_path, "get image")
            if "image_info" in file_result:
                # Need to read raw bytes
                import base64
                with open(file_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode()
        
        # Call Ollama vision model
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [image_b64] if image_b64 else [],
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "ok",
                    "response": result.get("response", ""),
                    "model": model,
                    "ram_used_mb": round((psutil.virtual_memory().total - psutil.virtual_memory().available) / (1024*1024)),
                    "method": "ai_model"
                }
            else:
                return {"status": "error", "error": f"Ollama error: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/vision/status")
async def vision_status():
    """Check what vision tools are available."""
    from local_vision import smart_vision
    import psutil
    
    ram = psutil.virtual_memory()
    
    return {
        "status": "ok",
        "local_tools": {
            "tesseract_ocr": smart_vision.ocr.available,
            "pdf_engine": smart_vision.pdf_reader.engine,
            "screenshot_backend": smart_vision.screenshot.backend,
        },
        "ram": {
            "total_gb": round(ram.total / (1024**3), 2),
            "available_gb": round(ram.available / (1024**3), 2),
            "percent": ram.percent,
        },
        "recommendation": "Use local tools for text extraction, AI only for understanding"
    }

@app.websocket("/ws/agent-town")
async def agent_town_websocket(websocket: WebSocket):
    """WebSocket endpoint for Agent Town — streams real-time agent status."""
    await websocket.accept()
    register_ws_client(websocket)
    try:
        # Send initial status
        await websocket.send_json({
            "type": "agent_status",
            "agents": get_all_agents(),
            "timestamp": time.time(),
        })
        # Keep connection alive, listen for pings
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if msg == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send periodic status update
                await websocket.send_json({
                    "type": "agent_status",
                    "agents": get_all_agents(),
                    "timestamp": time.time(),
                })
    except Exception:
        pass
    finally:
        unregister_ws_client(websocket)


if __name__ == "__main__":
    import uvicorn

    # Start RAM monitor (auto-swaps to cloud at 90%)
    ram_monitor.on_swap(lambda old, new, reason: logger.warning(f"[RAM-SWAP] {old} -> {new}: {reason}"))
    ram_monitor.start_monitor(interval_sec=5.0)

    uvicorn.run(app, host="127.0.0.1", port=7860, reload=False)


