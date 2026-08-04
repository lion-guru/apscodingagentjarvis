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


# Auto-initialize database on module import
init_db()
