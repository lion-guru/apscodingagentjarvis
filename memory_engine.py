"""
DevMind Smart Memory Engine & Decay Manager
Ported and enhanced from Claude Code's memdir (findRelevantMemories.ts & memoryAge.ts)
Provides smart memory indexing, relevance scoring, and automatic decay pruning.
"""
import os
import re
import json
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from master_db import get_db_connection, add_master_memory

MEMORY_FILE = Path.home() / ".jarvis" / "MEMORY.md"
MEMORY_DIR  = Path.home() / ".devmind" / "memories"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class MemoryEngine:
    def __init__(self):
        self.decay_days = 30  # Memories decay score after 30 days unless reinforced

    def add_memory(self, insight: str, category: str = "architecture", project_path: str = "") -> dict:
        """Add a new memory to master database and file store."""
        try:
            # 1. Save to SQLite Master DB
            add_master_memory(insight, project_path, category)
            
            # 2. Append to MEMORY.md file for IDE visibility
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = f"\n- [{now_str}] [{category.upper()}] {insight}"
            
            if not MEMORY_FILE.exists():
                MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
                MEMORY_FILE.write_text("# DevMind Master Memory\n", encoding="utf-8")
                
            current_text = MEMORY_FILE.read_text(encoding="utf-8")
            if insight not in current_text:
                with open(MEMORY_FILE, "a", encoding="utf-8") as f:
                    f.write(entry + "\n")
                    
            return {"status": "ok", "insight": insight}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def find_relevant_memories(self, query_prompt: str, top_k: int = 5) -> List[dict]:
        """
        Inspired by Claude Code findRelevantMemories.ts
        Score & rank memories based on relevance to current user prompt.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, project_path, category, insight, created_at FROM master_memory ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        tokens = set(re.findall(r'\w+', query_prompt.lower()))
        if not tokens:
            return [dict(r) for r in rows[:top_k]]

        scored_memories: List[Tuple[float, dict]] = []

        for r in rows:
            item = dict(r)
            insight_text = item["insight"].lower()
            insight_tokens = set(re.findall(r'\w+', insight_text))
            
            # 1. Lexical overlap score (Jaccard similarity)
            overlap = len(tokens.intersection(insight_tokens))
            similarity_score = overlap / max(len(tokens), 1)

            # 2. Age decay score calculation (inspired by memoryAge.ts)
            created_dt = datetime.strptime(item["created_at"][:19], "%Y-%m-%d %H:%M:%S") if item["created_at"] else datetime.now()
            age_days = (datetime.now() - created_dt).days
            decay_factor = math.exp(-age_days / self.decay_days)  # exponential decay

            final_score = similarity_score * decay_factor

            if similarity_score > 0.05 or age_days < 7:  # Keep recent or relevant memories
                item["relevance_score"] = round(final_score, 4)
                scored_memories.append((final_score, item))

        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in scored_memories[:top_k]]

    def get_memory_context(self, user_prompt: str) -> str:
        """Format top relevant memories for prompt injection."""
        memories = self.find_relevant_memories(user_prompt)
        if not memories:
            return ""
        
        lines = ["## 🧠 Relevant Master Memories (Ported from Claude Code memdir)"]
        for m in memories:
            lines.append(f"- [{m.get('category', 'general').upper()}] {m['insight']}")
        return "\n".join(lines) + "\n"


# Global singleton instance
memory_engine = MemoryEngine()
