"""
DevMind Master Database Manager
Global SQLite storage for projects, long-term memory, token costs, and task queues.
Location: ~/.devmind/master_db.sqlite
"""
import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

DB_DIR = Path.home() / ".devmind"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "master_db.sqlite"


def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize master SQLite database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Projects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        path TEXT UNIQUE NOT NULL,
        tech_stack TEXT,
        last_active TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Master memory table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS master_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_path TEXT,
        category TEXT,
        insight TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Token cost tracking table (inspired by Claude Code cost-tracker.ts)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS token_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model TEXT NOT NULL,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        est_cost_usd REAL DEFAULT 0.0,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 5. Cron schedules & timers table (inspired by Claude Code ScheduleCronTool)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cron_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_path TEXT NOT NULL,
        cron_expression TEXT,
        duration_seconds INTEGER,
        prompt TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 6. API Keys table — supports multiple keys per provider
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        key_name TEXT NOT NULL,
        key_value TEXT NOT NULL,
        label TEXT DEFAULT '',
        email TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        is_primary INTEGER DEFAULT 0,
        last_used_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider, key_name)
    )
    """)

    conn.commit()
    conn.close()


def add_cron_schedule(project_path: str, prompt: str, cron_expression: str = "", duration_seconds: int = 0) -> dict:
    """Store a background cron job or timer in master database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO cron_schedules (project_path, cron_expression, duration_seconds, prompt)
    VALUES (?, ?, ?, ?)
    """, (project_path, cron_expression, duration_seconds, prompt))
    conn.commit()
    cron_id = cursor.lastrowid
    conn.close()
    return {"status": "scheduled", "cron_id": cron_id, "prompt": prompt}


def get_active_cron_schedules(project_path: str = "") -> List[dict]:
    """List all active background cron jobs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if project_path:
        cursor.execute("SELECT * FROM cron_schedules WHERE project_path = ? AND status = 'active'", (project_path,))
    else:
        cursor.execute("SELECT * FROM cron_schedules WHERE status = 'active'")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cancel_cron_schedule(cron_id: int) -> dict:
    """Cancel a scheduled cron job or timer."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE cron_schedules SET status = 'cancelled' WHERE id = ?", (cron_id,))
    conn.commit()
    conn.close()
    return {"status": "cancelled", "cron_id": cron_id}


def register_project(name: str, path: str, tech_stack: str = "") -> dict:
    """Register or update a project in the master database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    try:
        cursor.execute("""
        INSERT INTO projects (name, path, tech_stack, last_active)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            name=excluded.name,
            tech_stack=excluded.tech_stack,
            last_active=excluded.last_active
        """, (name, str(Path(path).resolve()), tech_stack, now))
        conn.commit()
        return {"status": "ok", "project": name, "path": str(Path(path).resolve())}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def list_projects() -> List[dict]:
    """Get all registered projects on this PC."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects ORDER BY last_active DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

get_all_projects = list_projects


def add_master_memory(insight: str, project_path: str = "", category: str = "architecture"):
    """Store long-term insight into master memory database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO master_memory (project_path, category, insight)
    VALUES (?, ?, ?)
    """, (project_path, category, insight))
    conn.commit()
    conn.close()
    return {"status": "ok", "insight": insight}


def query_master_memory(project_path: str = "") -> List[dict]:
    """Retrieve long-term insights from master memory."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if project_path:
        cursor.execute("SELECT * FROM master_memory WHERE project_path = ? ORDER BY created_at DESC", (project_path,))
    else:
        cursor.execute("SELECT * FROM master_memory ORDER BY created_at DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def queue_task(project_path: str, task_description: str) -> dict:
    """Queue a task in master agent task queue."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO agent_tasks (project_path, task_description, status)
    VALUES (?, ?, 'pending')
    """, (project_path, task_description))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return {"status": "queued", "task_id": task_id, "task": task_description}


def get_pending_tasks(project_path: str = "") -> List[dict]:
    """Get pending background tasks."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if project_path:
        cursor.execute("SELECT * FROM agent_tasks WHERE project_path = ? AND status = 'pending'", (project_path,))
    else:
        cursor.execute("SELECT * FROM agent_tasks WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_token_usage(model: str, input_tokens: int, output_tokens: int, cost_usd: float = 0.0):
    """Record model token usage in database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO token_costs (model, input_tokens, output_tokens, est_cost_usd)
    VALUES (?, ?, ?, ?)
    """, (model, input_tokens, output_tokens, cost_usd))
    conn.commit()
    conn.close()


def get_token_summary() -> dict:
    """Return aggregated token consumption summary across models."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        SUM(input_tokens) as total_input,
        SUM(output_tokens) as total_output,
        SUM(est_cost_usd) as total_cost,
        COUNT(*) as total_calls
    FROM token_costs
    """)
    row = cursor.fetchone()
    conn.close()
    return {
        "total_input_tokens": row["total_input"] or 0,
        "total_output_tokens": row["total_output"] or 0,
        "total_tokens": (row["total_input"] or 0) + (row["total_output"] or 0),
        "total_cost_usd": round(row["total_cost"] or 0.0, 4),
        "total_llm_calls": row["total_calls"] or 0
    }


# ─── API Keys Management ─────────────────────────────────────────

def save_api_key(provider: str, key_name: str, key_value: str, label: str = "", email: str = "", is_primary: bool = False) -> dict:
    """Save or update an API key. Supports multiple keys per provider."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if is_primary:
            cursor.execute("UPDATE api_keys SET is_primary = 0 WHERE provider = ?", (provider,))
        cursor.execute("""
            INSERT INTO api_keys (provider, key_name, key_value, label, email, is_primary)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider, key_name) DO UPDATE SET
                key_value = excluded.key_value,
                label = excluded.label,
                email = excluded.email,
                is_primary = excluded.is_primary
        """, (provider, key_name, key_value, label, email, 1 if is_primary else 0))
        conn.commit()
        return {"status": "ok", "provider": provider, "key_name": key_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_api_key(provider: str, key_name: str = "") -> dict:
    """Get an API key by provider. Returns primary key or specific key_name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    row = None
    if key_name:
        cursor.execute("SELECT * FROM api_keys WHERE provider = ? AND key_name = ? AND is_active = 1", (provider, key_name))
        row = cursor.fetchone()
    else:
        cursor.execute("SELECT * FROM api_keys WHERE provider = ? AND is_primary = 1 AND is_active = 1", (provider,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT * FROM api_keys WHERE provider = ? AND is_active = 1 ORDER BY id LIMIT 1", (provider,))
            row = cursor.fetchone()
    conn.close()
    if row:
        return {"status": "ok", "key": dict(row)}
    return {"status": "not_found", "provider": provider}


def get_all_api_keys(provider: str = "") -> list:
    """List all API keys, optionally filtered by provider."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if provider:
        cursor.execute("SELECT * FROM api_keys WHERE provider = ? ORDER BY is_primary DESC, id", (provider,))
    else:
        cursor.execute("SELECT * FROM api_keys ORDER BY provider, is_primary DESC, id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_api_keys_masked(provider: str = "") -> list:
    """List all API keys with masked values for safe display."""
    keys = get_all_api_keys(provider)
    masked = []
    for k in keys:
        val = k["key_value"]
        if len(val) > 12:
            display = val[:8] + "..." + val[-4:]
        else:
            display = "***"
        masked.append({
            "id": k["id"],
            "provider": k["provider"],
            "key_name": k["key_name"],
            "key_masked": display,
            "label": k["label"],
            "email": k["email"],
            "is_active": k["is_active"],
            "is_primary": k["is_primary"],
            "created_at": k["created_at"],
        })
    return masked


def delete_api_key(provider: str, key_name: str) -> dict:
    """Delete an API key."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM api_keys WHERE provider = ? AND key_name = ?", (provider, key_name))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    return {"status": "ok" if deleted else "not_found", "deleted": deleted}


def set_primary_key(provider: str, key_name: str) -> dict:
    """Set a specific key as primary for a provider."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE api_keys SET is_primary = 0 WHERE provider = ?", (provider,))
    cursor.execute("UPDATE api_keys SET is_primary = 1 WHERE provider = ? AND key_name = ?", (provider, key_name))
    conn.commit()
    conn.close()
    return {"status": "ok", "provider": provider, "primary": key_name}


def mark_key_used(provider: str, key_name: str):
    """Update last_used_at timestamp for a key."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE provider = ? AND key_name = ?", (provider, key_name))
    conn.commit()
    conn.close()


def save_keys_from_env():
    """Save all API keys from .env file to database."""
    import os
    env_keys = {
        "GEMINI_API_KEY": {"provider": "google", "label": "Google Gemini"},
        "GROQ_API_KEY": {"provider": "groq", "label": "Groq"},
        "OPENROUTER_API_KEY": {"provider": "openrouter", "label": "OpenRouter"},
        "OPENAI_API_KEY": {"provider": "openai", "label": "OpenAI"},
        "ANTHROPIC_API_KEY": {"provider": "anthropic", "label": "Anthropic"},
        "OPENCODE_API_KEY": {"provider": "opencode", "label": "OpenCode"},
        "ZENMUX_API_KEY": {"provider": "zenmux", "label": "ZenMux"},
        "OLLAMA_API_KEY": {"provider": "ollama_cloud", "label": "Ollama Cloud"},
        "GOOGLE_SPEECH_API_KEY": {"provider": "google_speech", "label": "Google Speech"},
        "HUGGING_FACE_API_KEY": {"provider": "huggingface", "label": "Hugging Face"},
        "AZURE_AI_KEY": {"provider": "azure", "label": "Azure AI"},
    }
    saved = 0
    for env_name, info in env_keys.items():
        val = os.getenv(env_name, "")
        if val and len(val) > 5:
            email = os.getenv("OLLAMA_EMAIL", "") if info["provider"] == "ollama_cloud" else ""
            result = save_api_key(info["provider"], env_name, val, label=info["label"], email=email, is_primary=True)
            if result["status"] == "ok":
                saved += 1
    return {"saved": saved, "total": len(env_keys)}


def get_key(env_var_name: str) -> str:
    """Get API key by env var name. Tries SQLite first, falls back to os.getenv()."""
    # Map env var names to SQLite provider names
    _ENV_TO_PROVIDER = {
        "GEMINI_API_KEY": "google",
        "GROQ_API_KEY": "groq",
        "OPENROUTER_API_KEY": "openrouter",
        "OPENAI_API_KEY": "openai",
        "ANTHROPIC_API_KEY": "anthropic",
        "OPENCODE_API_KEY": "opencode",
        "ZENMUX_API_KEY": "zenmux",
        "OLLAMA_API_KEY": "ollama_cloud",
        "GOOGLE_SPEECH_API_KEY": "google_speech",
        "HUGGING_FACE_API_KEY": "huggingface",
        "AZURE_AI_KEY": "azure",
    }
    provider = _ENV_TO_PROVIDER.get(env_var_name, "")
    if not provider:
        # Fallback: strip suffixes and guess
        provider = env_var_name.replace("_API_KEY", "").replace("_KEY", "").lower()
    result = get_api_key(provider)
    if result.get("status") == "ok":
        return result["key"]["key_value"]
    return os.getenv(env_var_name, "")


# Auto-initialize database on module import
init_db()
