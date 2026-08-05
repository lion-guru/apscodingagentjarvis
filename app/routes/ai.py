"""
DevMind AI Routes — Agent, Model, Reasoning endpoints
"""
from fastapi import APIRouter, Request
import os

router = APIRouter(prefix="/api", tags=["ai"])


@router.get("/models")
async def get_models():
    try:
        from agent import check_ollama, DEFAULT_MODEL
        _, models = check_ollama()
        online_models = [
            "gemini-2.5-flash", "gpt-4o", "gpt-4o-mini",
            "claude-3-5-sonnet-latest", "llama-3.3-70b-versatile",
            "qwen/qwen-2.5-coder-32b-instruct:free",
        ]
        for m in online_models:
            if m not in models:
                models.append(m)
        try:
            from agent import THIRD_EYE_AVAILABLE, _mm
            if THIRD_EYE_AVAILABLE and _mm:
                for m in _mm.models:
                    if m["model"] not in models:
                        models.append(m["model"])
        except ImportError:
            pass
        return {"models": models, "default": DEFAULT_MODEL}
    except Exception as e:
        return {"models": [], "error": str(e)}


@router.get("/health")
async def health():
    import httpx
    from agent import OLLAMA_BASE
    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{OLLAMA_BASE}/api/tags", timeout=3.0)
        return {"status": "ok", "ollama": "connected"}
    except Exception:
        return {"status": "error", "ollama": "disconnected"}


@router.get("/model/status")
async def model_status():
    try:
        from agent import check_ollama, DEFAULT_MODEL
        is_ok, models = check_ollama()
        failover_chain = []
        try:
            from agent import THIRD_EYE_AVAILABLE, _mm
            if THIRD_EYE_AVAILABLE and _mm:
                failover_chain = _mm.get_failover_chain()
        except Exception:
            pass
        return {
            "status": "ok",
            "active_model": DEFAULT_MODEL,
            "ollama_running": is_ok,
            "available_models_count": len(models),
            "models": models,
            "failover_chain": failover_chain,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/server/status")
async def server_status_route():
    try:
        from agent import DEFAULT_MODEL, DEFAULT_WORKSPACE
        return {
            "status": "ok",
            "server": "DevMind AI Studio",
            "version": "1.0.0",
            "port": 7860,
            "active_model": DEFAULT_MODEL,
            "workspace": DEFAULT_WORKSPACE,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}



@router.get("/third-eye/status")
async def third_eye_status():
    try:
        from agent import THIRD_EYE_AVAILABLE, _mm
        if not THIRD_EYE_AVAILABLE:
            return {"error": "Third Eye not available", "available": False}
        return {
            "available": True,
            "total_models": len(_mm.models),
            "failover_chain": _mm.get_failover_chain(),
            "models": [
                {
                    "model": m["model"],
                    "provider": m.get("provider", "unknown"),
                    "latency": m.get("latency_s", "?"),
                    "categories": _mm.categorize(m["model"]),
                    "working": _mm.health.get(m["model"], {}).get("working", True),
                }
                for m in _mm.models
            ],
        }
    except Exception as e:
        return {"error": str(e), "available": False}


@router.post("/third-eye/discover")
async def third_eye_discover():
    try:
        from free_model_discovery import discover_all
        results = discover_all()
        try:
            from agent import _mm
            _mm._load()
        except Exception:
            pass
        return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/third-eye/best/{task}")
async def third_eye_best_model(task: str):
    try:
        from agent import _get_best_free_model
        return {"task": task, "best_model": _get_best_free_model(task)}
    except Exception as e:
        from agent import DEFAULT_MODEL
        return {"task": task, "best_model": DEFAULT_MODEL, "error": str(e)}


@router.get("/moe/experts")
async def moe_experts():
    import moe_router
    import agent_specialists
    router = moe_router.MoERouter()
    for expert in agent_specialists.create_default_agents().values():
        router.add_expert(moe_router.ExpertProfile(expert_name=expert.role, model="gemma3:1b"))
    return router.get_expert_status()


@router.get("/moe/route")
async def moe_route(task: str = ""):
    import moe_router
    router = moe_router.MoERouter()
    classification = router.classifier.classify(task)
    expert = router.policy.select_expert(classification, list(router.experts.values()))
    return {"status": "ok", "classification": classification, "routed_to": expert.expert_name}


@router.post("/vlm/process")
async def vlm_process(request: Request):
    try:
        data = await request.json()
        import multimodal_engine
        engine = multimodal_engine.VLMEngine()
        result = await engine.process_image(data.get("image", ""), data.get("prompt", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/mimo/process")
async def mimo_process(request: Request):
    try:
        data = await request.json()
        import multimodal_engine
        import agent_core
        mimo = multimodal_engine.MimoArchitecture()
        for inp in data.get("inputs", []):
            mimo.add_input(inp.get("name", "input"), inp.get("type", "text"), inp.get("data"), inp.get("priority", 1))
        results = await mimo.process_multi_input(data.get("inputs", []), agent_core.Task(description=data.get("task_description", "")))
        merged = await mimo.merge_outputs(results)
        return {"status": "ok", "inputs_processed": len(data.get("inputs", [])), "merged_output": merged}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/reasoning/config")
async def reasoning_config():
    return {"status": "ok", "config": {"enabled": True, "max_steps": 10, "style": "chain_of_thought"}}


@router.post("/reasoning/config")
async def reasoning_config_set(request: Request):
    try:
        data = await request.json()
        return {"status": "ok", "config": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/hermes/status")
async def hermes_status():
    return {"status": "ok", "hermes_available": True}
