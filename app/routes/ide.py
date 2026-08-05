"""
DevMind IDE Routes — Editor, Linting, Completion, Terminal endpoints
"""
from fastapi import APIRouter, Request
import os
import asyncio
from pathlib import Path

router = APIRouter(prefix="/api", tags=["ide"])

# Use the directory containing this routes file's grandparent (app/routes -> app -> coding-assistant)
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


@router.get("/ide/status")
async def ide_status():
    return {"status": "ok", "editor": "active", "features": ["linting", "completion", "diagnostics"]}


@router.get("/files")
async def get_files(cwd: str | None = None):
    """List files and directories in the workspace for the Explorer panel."""
    try:
        base = Path(cwd) if cwd else WORKSPACE_ROOT
        entries = []
        for item in sorted(base.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.name.startswith(".") or item.name in {"__pycache__", "node_modules", ".git"}:
                continue
            try:
                rel = item.relative_to(WORKSPACE_ROOT)
                entries.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "path": str(item),
                    "rel_path": str(rel).replace("\\", "/")
                })
            except ValueError:
                pass
        return {"files": entries}
    except Exception as e:
        return {"files": [], "error": str(e)}


@router.get("/file/read")
async def read_file(path: str):
    """Read file contents from workspace."""
    try:
        target = WORKSPACE_ROOT / path
        if not target.exists() or not target.is_file():
            return {"content": "", "error": "File not found"}
        content = target.read_text(encoding="utf-8", errors="replace")
        return {"content": content, "path": str(target.relative_to(WORKSPACE_ROOT)).replace("\\", "/")}
    except Exception as e:
        return {"content": "", "error": str(e)}


@router.post("/terminal/run")
async def terminal_run_direct(request: Request):
    """Execute a shell command on the server workspace safely."""
    data = await request.json()
    cmd = data.get("command", "").strip()
    cwd_val = data.get("cwd") or str(WORKSPACE_ROOT)
    if not cmd:
        return {"output": "No command provided"}
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd_val
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stdout.decode(errors="replace")
        err = stderr.decode(errors="replace")
        result = output + (f"\n[STDERR]\n{err}" if err else "")
        return {"output": result or "Command executed cleanly."}
    except asyncio.TimeoutError:
        return {"output": "Command timed out after 15 seconds"}
    except Exception as e:
        return {"output": f"Execution error: {e}"}


@router.post("/ide/lint")
async def ide_lint(request: Request):
    try:
        data = await request.json()
        import linter_engine
        results = linter_engine.lint_file(data.get("file_path", ""))
        return {"status": "ok", "diagnostics": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/ide/complete")
async def ide_complete(request: Request):
    try:
        data = await request.json()
        import completion_engine
        results = completion_engine.get_completions(
            data.get("file_path", ""),
            data.get("line", ""),
            data.get("cursor_pos", 0),
            data.get("context", ""),
            data.get("language", "python")
        )
        return {"status": "ok", "completions": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/diagnostics/summary")
async def diagnostics_summary():
    try:
        import diagnostics_panel
        return {"status": "ok", "summary": diagnostics_panel.diagnostics_panel.get_diagnostics_summary()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/terminal/create")
async def terminal_create(request: Request):
    try:
        data = await request.json()
        import terminal_manager
        result = terminal_manager.create_session(data.get("session_id", "default"), data.get("cwd"))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/terminal/execute")
async def terminal_execute(request: Request):
    try:
        data = await request.json()
        import terminal_manager
        result = terminal_manager.execute_command(data.get("session_id", "default"), data.get("command", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/terminal/output")
async def terminal_output(session_id: str = "default"):
    try:
        import terminal_manager
        output = terminal_manager.get_output(session_id)
        return {"status": "ok", "output": output}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/terminal/sessions")
async def terminal_sessions():
    try:
        import terminal_manager
        return {"status": "ok", "sessions": terminal_manager.list_sessions()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/terminal/kill")
async def terminal_kill(request: Request):
    try:
        data = await request.json()
        import terminal_manager
        result = terminal_manager.kill_session(data.get("session_id", "default"))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/explorer/tree")
async def explorer_tree(request: Request):
    try:
        data = await request.json()
        import project_explorer
        tree = project_explorer.get_file_tree(data.get("path", os.getcwd()))
        return {"status": "ok", "tree": tree}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/editor/inline")
async def editor_inline(request: Request):
    try:
        data = await request.json()
        import inline_editor
        result = inline_editor.inline_editor.create_diff(
            data.get("file_path", ""),
            data.get("old_text", ""),
            data.get("new_text", "")
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/steering/rules")
async def steering_rules():
    try:
        import steering_engine
        rules = steering_engine.get_rules() if hasattr(steering_engine, 'get_rules') else []
        return {"status": "ok", "rules": rules}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/spaces/create")
async def spaces_create(request: Request):
    try:
        data = await request.json()
        import spaces_manager
        result = spaces_manager.create_space(data.get("name", ""), data.get("description", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/spaces/list")
async def spaces_list():
    try:
        import spaces_manager
        spaces = spaces_manager.list_spaces() if hasattr(spaces_manager, 'list_spaces') else []
        return {"status": "ok", "spaces": spaces}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/ide/bridge")
async def ide_bridge_config():
    try:
        import ide_bridge
        config = ide_bridge.generate_config() if hasattr(ide_bridge, 'generate_config') else {}
        return {"status": "ok", "config": config}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/deploy/config")
async def deploy_config():
    try:
        import deploy_panel
        config = deploy_panel.get_config() if hasattr(deploy_panel, 'get_config') else {}
        return {"status": "ok", "config": config}
    except Exception as e:
        return {"status": "error", "message": str(e)}
