"""
DevMind Context Manager
RAG + context compression + memory routing system.
Manages context windows, compresses old context, and routes relevant memories.
"""
import json
import re
from pathlib import Path
from datetime import datetime, timedelta

CONTEXT_DIR = Path.home() / ".devmind" / "context"
MEMORY_DIR = Path.home() / ".devmind" / "memory"

class ContextManager:
    def __init__(self, max_context_tokens: int = 100000):
        CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.max_context_tokens = max_context_tokens
        self.active_contexts = {}

    def compress_context(self, messages: list[dict], max_messages: int = 50) -> list[dict]:
        """Compress old messages when context exceeds limit."""
        if len(messages) <= max_messages:
            return messages

        compressed = messages[:max_messages // 2]
        summary = {
            "role": "system",
            "content": f"[Context Summary: {len(messages)} messages compressed into summary]",
            "timestamp": datetime.now().isoformat(),
            "compressed_count": len(messages) - max_messages // 2,
        }
        compressed.append(summary)
        compressed.extend(messages[-(max_messages // 2):])
        return compressed

    def route_memory(self, query: str, memories: list[dict]) -> list[dict]:
        """Route relevant memories into context based on query similarity."""
        query_lower = query.lower()
        relevant = []

        for memory in memories:
            content = memory.get("content", "").lower()
            tags = memory.get("tags", [])
            score = 0

            for word in query_lower.split():
                if word in content:
                    score += 2
                for tag in tags:
                    if tag.lower() in content:
                        score += 1

            if score > 0:
                relevant.append({**memory, "relevance_score": score})

        relevant.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return relevant[:10]

    def save_context(self, session_id: str, messages: list[dict],
                     artifacts: list[dict] = None) -> dict:
        """Save context to disk for persistence."""
        context = {
            "session_id": session_id,
            "messages": messages,
            "artifacts": artifacts or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": len(messages),
        }

        context_file = CONTEXT_DIR / f"{session_id}.json"
        context_file.write_text(json.dumps(context, indent=2, default=str), encoding="utf-8")
        self.active_contexts[session_id] = context
        return {"status": "ok", "session_id": session_id}

    def load_context(self, session_id: str) -> dict:
        """Load context from disk."""
        context_file = CONTEXT_DIR / f"{session_id}.json"
        if not context_file.exists():
            return {"status": "error", "error": f"Context '{session_id}' not found"}

        context = json.loads(context_file.read_text(encoding="utf-8"))
        self.active_contexts[session_id] = context
        return {"status": "ok", "context": context}

    def list_contexts(self) -> list[dict]:
        """List all saved contexts."""
        contexts = []
        if CONTEXT_DIR.exists():
            for f in CONTEXT_DIR.glob("*.json"):
                try:
                    ctx = json.loads(f.read_text(encoding="utf-8"))
                    contexts.append({
                        "session_id": ctx.get("session_id", f.stem),
                        "message_count": ctx.get("message_count", 0),
                        "updated_at": ctx.get("updated_at", ""),
                    })
                except Exception:
                    pass
        return contexts

    def cleanup_old_contexts(self, max_age_days: int = 30) -> dict:
        """Remove contexts older than max_age_days."""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        removed = 0

        if CONTEXT_DIR.exists():
            for f in CONTEXT_DIR.glob("*.json"):
                try:
                    ctx = json.loads(f.read_text(encoding="utf-8"))
                    updated = datetime.fromisoformat(ctx.get("updated_at", ""))
                    if updated < cutoff:
                        f.unlink()
                        removed += 1
                except Exception:
                    pass

        return {"status": "ok", "removed": removed}

    def get_context_stats(self) -> dict:
        """Get context manager statistics."""
        contexts = self.list_contexts()
        total_messages = sum(c.get("message_count", 0) for c in contexts)
        return {
            "total_contexts": len(contexts),
            "total_messages": total_messages,
            "max_context_tokens": self.max_context_tokens,
            "active_contexts": len(self.active_contexts),
        }


context_manager = ContextManager()