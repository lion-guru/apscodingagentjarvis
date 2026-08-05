"""
DevMind Knowledge Routes — Learning, Skills, Verification, Self-Healing, Multi-Brain, Eval, Voice, ZenMux
"""
from fastapi import APIRouter, Request
import os

router = APIRouter(prefix="/api", tags=["knowledge"])


@router.get("/project/style-guide")
async def project_style_guide():
    try:
        from learning_engine import scan_codebase_for_styles
        guide = scan_codebase_for_styles(os.getcwd())
        return {"status": "ok", "style_guide": guide}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/project/learn")
async def project_learn(request: Request):
    try:
        data = await request.json()
        from learning_engine import learn_new_rule
        result = learn_new_rule(os.getcwd(), data.get("category", "general"), data.get("rule", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/code/search")
async def code_search(request: Request):
    try:
        data = await request.json()
        from hybrid_query_engine import query_engine
        if not query_engine.doc_index:
            query_engine.index_workspace(os.getcwd())
        results = query_engine.search(data.get("query", ""), data.get("limit", 10))
        return {"status": "ok", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/code/index")
async def code_index(request: Request):
    try:
        data = await request.json()
        from hybrid_query_engine import query_engine
        result = query_engine.index_workspace(data.get("cwd", os.getcwd()))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/self-healing/status")
async def self_healing_status():
    try:
        from self_healing_workflow import self_healing_workflow
        report = self_healing_workflow.get_failure_report()
        return {"status": "ok", "active": True, "report": report}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/self-healing/attempt")
async def self_healing_attempt(request: Request):
    try:
        data = await request.json()
        from self_healing_workflow import attempt_heal
        result = attempt_heal(data.get("task", ""), data.get("error", ""), data.get("context", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/verify/check")
async def verify_check(request: Request):
    try:
        data = await request.json()
        from verification_system import verification_system
        result = verification_system.verify_changes(data.get("file_path", ""), data.get("project_path", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/verify/history")
async def verify_history():
    try:
        from verification_system import verification_system
        return {"status": "ok", "history": verification_system.get_verification_report()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/ai/multi-brain/status")
async def multi_brain_status():
    try:
        from multi_brain_coordinator import multi_brain_coordinator
        return {"status": "ok", "active_models": list(multi_brain_coordinator.active_models.keys())}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/ai/multi-brain/plan")
async def multi_brain_plan(request: Request):
    try:
        data = await request.json()
        from multi_brain_coordinator import multi_brain_coordinator
        result = await multi_brain_coordinator.coordinate_task(data.get("task", ""), data.get("context", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/learning/status")
async def learning_status():
    try:
        from web_learning_engine import learning_engine
        kb = learning_engine.get_knowledge_base()
        return {"status": "ok", "knowledge_base": kb}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/learning/research")
async def learning_research(request: Request):
    try:
        data = await request.json()
        from web_learning_engine import learning_engine
        result = learning_engine.research_and_upgrade(data.get("topic", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/skills/list")
async def skills_list():
    try:
        from skill_synthesis import skill_synthesizer
        return {"status": "ok", "skills": skill_synthesizer.get_active_skills()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/skills/generate")
async def skills_generate(request: Request):
    try:
        data = await request.json()
        from skill_synthesis import synthesize_new_skill
        result = synthesize_new_skill(data.get("task", ""), data.get("context", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/eval/benchmarks")
async def eval_benchmarks():
    try:
        from devmind_eval import evaluator
        return {"status": "ok", "benchmarks": evaluator.get_summary()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/eval/run")
async def eval_run(request: Request):
    try:
        data = await request.json()
        from devmind_eval import evaluator
        result = evaluator.run_benchmark(data.get("model", ""), data.get("task_type", "python_refactor"))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/voice/status")
async def voice_status():
    try:
        from jarvis_voice import voice_core
        return {"status": "ok", "trigger_word": voice_core.trigger_word}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/voice/parse")
async def voice_parse(request: Request):
    try:
        data = await request.json()
        from jarvis_voice import voice_core
        result = voice_core.parse_voice_command(data.get("transcript", ""))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/ai/communicate")
async def ai_communicate(request: Request):
    try:
        data = await request.json()
        from inter_ai_communicator import ai_communicator
        result = ai_communicator.communicate_and_learn(
            data.get("target_model", "gemini-2.5-flash"),
            data.get("topic", "Advanced coding techniques")
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/ai/communicate/knowledge-bank")
async def ai_communicate_knowledge_bank():
    try:
        from inter_ai_communicator import ai_communicator
        return {"status": "ok", "knowledge_bank": ai_communicator.get_knowledge_bank()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/rag/query")
async def rag_query(request: Request):
    try:
        data = await request.json()
        from rag_vector_engine import DevMindRAGEngine
        engine = DevMindRAGEngine()
        results = engine.query(data.get("query", ""), data.get("limit", 5)) if hasattr(engine, 'query') else []
        return {"status": "ok", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/rag/index")
async def rag_index(request: Request):
    try:
        data = await request.json()
        from rag_vector_engine import DevMindRAGEngine
        engine = DevMindRAGEngine()
        result = engine.index_file(data.get("file_path", "")) if hasattr(engine, 'index_file') else {"status": "not_implemented"}
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/tasks/queue")
async def tasks_queue():
    try:
        from overnight_worker import overnight_worker
        return {"status": "ok", "queue": overnight_worker.get_queue()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/tasks/submit")
async def tasks_submit(request: Request):
    try:
        data = await request.json()
        from overnight_worker import overnight_worker
        result = overnight_worker.add_task(data.get("prompt", ""), data.get("category", "coding"))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/worker/status")
async def worker_status():
    try:
        from overnight_worker import overnight_worker
        queue = overnight_worker.get_queue()
        pending = len([t for t in queue.get("tasks", []) if t.get("status") == "pending"])
        return {"status": "ok", "pending_tasks": pending, "queue": queue}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/worker/start")
async def worker_start(request: Request):
    try:
        from overnight_worker import overnight_worker
        result = overnight_worker.setup_startup_recovery()
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/mcp/validate")
async def mcp_validate():
    try:
        from validate_mcp_config import validate_config
        result = validate_config()
        return {"status": "ok", "valid": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/setup/status")
async def setup_status():
    try:
        from setup_wizard import load_and_seed_keys
        env_vars = load_and_seed_keys()
        keys_status = {}
        for key in ["GEMINI_API_KEY", "OPENROUTER_API_KEY", "GROQ_API_KEY", "ZENMUX_API_KEY"]:
            val = env_vars.get(key, "")
            keys_status[key] = "configured" if val and len(val) > 10 else "missing"
        return {"status": "ok", "setup": keys_status}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/setup/check-keys")
async def setup_check_keys():
    try:
        from setup_wizard import load_and_seed_keys
        env_vars = load_and_seed_keys()
        return {"status": "ok", "result": {"keys": list(env_vars.keys())}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/projects")
async def get_projects():
    try:
        from master_db import get_all_projects
        return {"projects": get_all_projects()}
    except Exception as e:
        return {"projects": [], "error": str(e)}


@router.get("/cost/summary")
async def get_cost_summary():
    try:
        from cost_tracker import tracker
        return tracker.get_summary()
    except Exception as e:
        return {"error": str(e), "total_tokens": 0, "total_cost_usd": 0.0, "saved_vs_openai": 0.0}


@router.get("/knowledge/list")
async def knowledge_list():
    try:
        import knowledge_items
        items = knowledge_items.get_summaries()
        return {"status": "ok", "items": items}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/knowledge/add")
async def knowledge_add(request: Request):
    try:
        data = await request.json()
        import knowledge_items
        result = knowledge_items.add_item(data.get("title", ""), data.get("content", ""), data.get("category", "general"))
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/zenmux/status")
async def zenmux_status():
    try:
        api_key = os.getenv("ZENMUX_API_KEY")
        return {"status": "ok", "configured": bool(api_key), "platform": "https://zenmux.ai/platform/management"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/zenmux/chat")
async def zenmux_chat(request: Request):
    try:
        data = await request.json()
        api_key = os.getenv("ZENMUX_API_KEY")
        if not api_key:
            return {"status": "error", "message": "ZENMUX_API_KEY not configured"}
        import httpx as _httpx
        url = "https://zenmux.ai/api/v1/chat/completions"
        payload = {
            "model": data.get("model", "gpt-3.5-turbo"),
            "messages": data.get("messages", [{"role": "user", "content": data.get("prompt", "Hello")}]),
            "max_tokens": data.get("max_tokens", 2000),
            "temperature": data.get("temperature", 0.7),
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        async with _httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                result = resp.json()
                return {"status": "ok", "response": result["choices"][0]["message"]["content"], "model": payload["model"]}
            else:
                return {"status": "error", "message": f"ZenMux API error: {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
