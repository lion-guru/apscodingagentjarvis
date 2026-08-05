"""Integration tests for API endpoints — test the route modules via FastAPI TestClient."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from httpx import AsyncClient, ASGITransport
from server import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


class TestAIEndpoints:
    @pytest.mark.anyio
    async def test_models(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/models")
            assert resp.status_code == 200
            data = resp.json()
            assert "models" in data or "error" in data

    @pytest.mark.anyio
    async def test_health(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/health")
            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data

    @pytest.mark.anyio
    async def test_hermes_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/hermes/status")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_reasoning_config(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/reasoning/config")
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("status") == "ok"


class TestSystemEndpoints:
    @pytest.mark.anyio
    async def test_memory_search(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/memory/search", params={"query": "test"})
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_memory_stats(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/memory/stats")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_model_failover_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/model/failover-status")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_offline_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/offline/status")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_system_metrics(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/system/metrics")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_mesh_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/mesh/status")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_model_usage(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/model/usage")
            assert resp.status_code == 200


class TestKnowledgeEndpoints:
    @pytest.mark.anyio
    async def test_self_healing_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/self-healing/status")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_verify_history(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/verify/history")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_multi_brain_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/ai/multi-brain/status")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_learning_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/learning/status")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_skills_list(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/skills/list")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_eval_benchmarks(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/eval/benchmarks")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_voice_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/voice/status")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_zenmux_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/zenmux/status")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_mcp_validate(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/mcp/validate")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_worker_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/worker/status")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_setup_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/setup/status")
            assert resp.status_code == 200


class TestIDEEndpoints:
    @pytest.mark.anyio
    async def test_ide_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/ide/status")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_terminal_sessions(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/terminal/sessions")
            assert resp.status_code == 200
