"""
DevMind System Routes — Memory, Failover, Vector, Usage, Mesh, Autonomy endpoints
"""
from fastapi import APIRouter, Request
import os

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/memory/search")
async def memory_search(query: str = "", limit: int = 10):
    try:
        from memory_engine import memory_engine
        results = memory_engine.find_relevant_memories(query, top_k=limit)
        return {"status": "ok", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/memory/stats")
async def memory_stats():
    try:
        from master_db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM master_memory")
        row = cursor.fetchone()
        conn.close()
        return {"status": "ok", "stats": {"total_memories": row["total"] if row else 0}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/memory/add")
async def memory_add(request: Request):
    try:
        data = await request.json()
        from memory_engine import memory_engine
        result = memory_engine.add_memory(
            data.get("insight", ""),
            data.get("category", "general"),
            data.get("project_path", "")
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/model/failover-status")
async def model_failover_status():
    try:
        from model_failover import failover_manager
        return {"status": "ok", "failover_chain": failover_manager.get_model_status()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/model/failover/test")
async def model_failover_test(request: Request):
    try:
        from model_failover import failover_manager
        model = failover_manager.get_available_model()
        return {"status": "ok", "result": {"current_model": model["name"], "provider": model["provider"]}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/model/usage")
async def model_usage():
    try:
        from model_usage_tracker import UsageTracker
        tracker = UsageTracker()
        return {"status": "ok", "usage": tracker.get_usage() if hasattr(tracker, 'get_usage') else {}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/model/quota")
async def model_quota():
    try:
        from model_usage_tracker import UsageTracker
        tracker = UsageTracker()
        return {"status": "ok", "quota": tracker.get_quota_status() if hasattr(tracker, 'get_quota_status') else {}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/vector/embed")
async def vector_embed(request: Request):
    try:
        data = await request.json()
        from vector_db import get_embedding
        embedding = get_embedding(data.get("text", ""))
        return {"status": "ok", "result": {"embedding": embedding[:10], "dimension": len(embedding)}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/vector/search")
async def vector_search(request: Request):
    try:
        data = await request.json()
        from vector_db import query_database
        results = query_database(data.get("cwd", os.getcwd()), data.get("query", ""), data.get("limit", 5))
        return {"status": "ok", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/vector/store")
async def vector_store(request: Request):
    try:
        data = await request.json()
        from vector_db import index_directory
        result = index_directory(data.get("cwd", os.getcwd()))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/session/compress")
async def session_compress(request: Request):
    try:
        data = await request.json()
        from trajectory_compressor import compress_trajectory, CompressionConfig
        messages = data.get("messages", [])
        config = CompressionConfig(
            target_max_tokens=data.get("target_max_tokens", 8000),
            protect_last_n_turns=data.get("protect_last_n_turns", 4),
            summarization_model=data.get("summarization_model", "gemini-2.5-flash"),
        )
        compressed, metrics = compress_trajectory(messages, config)
        return {
            "status": "ok",
            "original_count": metrics.original_turns,
            "compressed_count": metrics.compressed_turns,
            "tokens_saved": metrics.tokens_saved,
            "compression_ratio": round(metrics.compression_ratio, 4),
            "was_compressed": metrics.was_compressed,
            "messages": compressed,
            "metrics": metrics.to_dict(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/system/metrics")
async def system_metrics():
    try:
        from jarvis_autonomy import autonomy_engine
        metrics = autonomy_engine.get_system_metrics()
        return {"status": "ok", "metrics": metrics}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/system/ensure-services")
async def system_ensure_services():
    try:
        from jarvis_autonomy import autonomy_engine
        result = autonomy_engine.ensure_services_running()
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/system/learn-pattern")
async def system_learn_pattern(request: Request):
    try:
        data = await request.json()
        from jarvis_autonomy import autonomy_engine
        result = autonomy_engine.learn_user_pattern(data.get("file", ""), data.get("edit_type", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/mesh/status")
async def mesh_status():
    try:
        from devmind_mesh import mesh_engine
        return {"status": "ok", "mesh": mesh_engine.get_status()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/mesh/sync")
async def mesh_sync(request: Request):
    try:
        data = await request.json()
        from devmind_mesh import mesh_engine
        result = mesh_engine.sync(data.get("workspace_path", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/offline/status")
async def offline_status():
    try:
        from offline_llm import offline_accelerator
        status = offline_accelerator.check_availability()
        return {"status": "ok", "offline": status}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/offline/chat")
async def offline_chat(request: Request):
    try:
        data = await request.json()
        from offline_llm import offline_accelerator
        result = offline_accelerator.generate_offline(data.get("prompt", ""), data.get("model", "qwen-2.5-coder-32b"))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/attention/compress")
async def attention_compress_info():
    return {"status": "ok", "endpoint": "POST /api/attention/compress"}


@router.post("/attention/compress")
async def attention_compress(request: Request):
    try:
        data = await request.json()
        from attention_engine import HybridLinearAttention
        engine = HybridLinearAttention()
        result = engine.compress(data.get("tokens", []), data.get("window_size", 128)) if hasattr(engine, 'compress') else {"status": "not_implemented"}
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/ram/status")
async def ram_status_route():
    try:
        import ram_monitor
        return ram_monitor.get_status()
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/ram/check")
async def ram_check_route():
    try:
        import ram_monitor
        result = ram_monitor.check_and_swap()
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/stt/status")
async def stt_status_route():
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


@router.get("/tts/status")
async def tts_status_route():
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


@router.get("/tts/voices")
async def tts_voices_route():
    try:
        from tts_engine import list_voices
        voices = list_voices()
        return {"status": "ok", "voices": voices}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/vision/status")
async def vision_status_route():
    try:
        from local_vision import smart_vision
        import psutil
        ram = psutil.virtual_memory()
        return {
            "status": "ok",
            "local_tools": {
                "tesseract_ocr": smart_vision.ocr.available if hasattr(smart_vision, 'ocr') else False,
                "pdf_engine": smart_vision.pdf_reader.engine if hasattr(smart_vision, 'pdf_reader') else "none",
                "screenshot_backend": smart_vision.screenshot.backend if hasattr(smart_vision, 'screenshot') else "none",
            },
            "ram": {
                "total_gb": round(ram.total / (1024**3), 2),
                "available_gb": round(ram.available / (1024**3), 2),
                "percent": ram.percent,
            },
            "recommendation": "Use local tools for text extraction, AI only for understanding"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/git/status")
async def git_status():
    """Get current git status (changed files)."""
    import subprocess, os
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=10
        )
        changes = []
        for line in result.stdout.splitlines():
            if line.strip():
                status = line[:2].strip()
                filepath = line[3:].strip()
                changes.append({"status": status, "file": filepath})
        return {"status": "ok", "changes": changes, "branch": _get_git_branch()}
    except Exception as e:
        return {"status": "ok", "changes": [], "branch": "main", "error": str(e)}


def _get_git_branch():
    import subprocess
    try:
        r = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "main"
    except Exception:
        return "main"


@router.post("/github/commit-and-push")
async def git_commit_and_push(request: Request):
    """Stage all changes, commit with message, and push."""
    import subprocess, os
    try:
        data = await request.json()
        msg = data.get("message", "DevMind: auto commit")
        cwd = os.getcwd()
        subprocess.run(["git", "add", "-A"], cwd=cwd, timeout=10)
        r = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True, cwd=cwd, timeout=15)
        push_r = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=cwd, timeout=30)
        return {
            "success": True,
            "commit_output": r.stdout + r.stderr,
            "push_output": push_r.stdout + push_r.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/extensions/detect")
async def extensions_detect():
    """Return list of recommended extensions for the DevMind IDE."""
    extensions = [
        {"name": "Python", "id": "ms-python.python", "installed": True},
        {"name": "ESLint", "id": "dbaeumer.vscode-eslint", "installed": False},
        {"name": "Prettier", "id": "esbenp.prettier-vscode", "installed": False},
        {"name": "GitLens", "id": "eamodio.gitlens", "installed": True},
        {"name": "Pylance", "id": "ms-python.vscode-pylance", "installed": True},
        {"name": "DevMind AI", "id": "devmind.ai-assistant", "installed": True},
    ]
    return {"status": "ok", "extensions": extensions}
