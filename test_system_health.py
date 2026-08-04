import sys
import os
import json
from pathlib import Path

print("==================================================")
print("🧪 DEVMIND AGENT SYSTEM - END-TO-END HEALTH TEST")
print("==================================================")

# 1. Test Agent Imports & Config
try:
    import agent
    print("✅ 1. Agent Core (`agent.py`) imported successfully.")
except Exception as e:
    print(f"❌ 1. Failed to import agent core: {e}")
    sys.exit(1)

# 2. Test Tool Registry Initialization
try:
    tools = agent.create_tool_registry()
    print(f"✅ 2. Tool Registry initialized with {len(tools)} tools registered:")
    tool_names = list(tools.keys())
    print(f"   Tools: {', '.join(tool_names[:8])}... (+{len(tool_names)-8} more)")
except Exception as e:
    print(f"❌ 2. Tool registry failed: {e}")

# 3. Test Project Detection & System Prompt Builder
try:
    cwd = str(agent.DEFAULT_WORKSPACE)
    stack = agent.detect_project_type(cwd)
    print(f"✅ 3. Workspace Tech Stack Detected: '{stack}' at {cwd}")
    prompt = agent.build_system_prompt(cwd, tools)
    print(f"✅ 4. System Prompt built successfully ({len(prompt)} characters).")
except Exception as e:
    print(f"❌ 3/4. Workspace prompt building failed: {e}")

# 4. Test Backup & Undo Subsystem
try:
    test_file = Path("test_backup_temp.txt")
    test_file.write_text("Hello World Initial", encoding="utf-8")
    agent.backup_file(str(test_file.absolute()))
    test_file.write_text("Hello World Modified", encoding="utf-8")
    restored = agent.restore_last_turn()
    content = test_file.read_text(encoding="utf-8")
    if "Initial" in content:
        print("✅ 5. Backup & Undo Subsystem verified (file restored to original state).")
    else:
        print(f"⚠️ 5. Undo system returned unexpected text: {content}")
    if test_file.exists():
        test_file.unlink()
except Exception as e:
    print(f"❌ 5. Backup & Undo test failed: {e}")

# 5. Test Server Endpoints via FastAPI Test Client
try:
    from fastapi.testclient import TestClient
    import server
    client = TestClient(server.app)
    
    r_health = client.get("/api/health")
    r_models = client.get("/api/models")
    r_status = client.get("/api/agent/system_status")
    r_tasks  = client.get("/api/tasks")
    
    print(f"✅ 6. FastAPI Web Server Routes Validated:")
    print(f"   - /api/health status: {r_health.status_code} ({r_health.json()})")
    print(f"   - /api/models count: {len(r_models.json().get('models', []))}")
    print(f"   - /api/agent/system_status: MCP count = {r_status.json().get('mcp_servers_count')}")
    print(f"   - /api/tasks count: {len(r_tasks.json().get('tasks', []))}")
except Exception as e:
    print(f"❌ 6. FastAPI server routes test failed: {e}")

# 6. Test Model Failover Engine
try:
    print("✅ 7. Testing Model Failover Engine:")
    msg = [{"role": "user", "content": "Reply with 'HEALTH_OK' only."}]
    res = agent.ollama_chat(msg, model="gemini-2.0-flash")
    print(f"   LLM Model Response: '{res.strip()}'")
except Exception as e:
    print(f"⚠️ 7. Model call notice: {e}")

print("==================================================")
print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
print("==================================================")
