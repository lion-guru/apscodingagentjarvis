"""
DevMind Inter-AI Communicator — Peer-to-Peer AI Knowledge Exchange Protocol
Enables DevMind to interview and communicate with external LLM models (Gemini, Claude, GPT-4o, DeepSeek) to learn new techniques.
"""
import httpx
import json
import time
from pathlib import Path

KNOWLEDGE_BANK_FILE = Path.home() / ".devmind" / "ai_knowledge_bank.json"

class InterAICommunicator:
    def __init__(self):
        KNOWLEDGE_BANK_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not KNOWLEDGE_BANK_FILE.exists():
            KNOWLEDGE_BANK_FILE.write_text(json.dumps({"learned_insights": [], "exchanges_count": 0}, indent=2), encoding="utf-8")

    def communicate_and_learn(self, target_model: str = "gemini-2.5-flash", topic: str = "Advanced RAG and LoRA Fine-Tuning") -> dict:
        """Conducted peer-to-peer AI knowledge exchange interview."""
        prompt = f"Explain the top 3 best practices for {topic} in modular Python code with exact implementation examples."
        
        try:
            from agent import ollama_chat
            response = ollama_chat([{"role": "user", "content": prompt}], model=target_model)
            
            insight_item = {
                "id": f"insight_{int(time.time())}",
                "target_model": target_model,
                "topic": topic,
                "knowledge_snippet": response[:500],
                "timestamp": time.time()
            }
            
            # Save to Knowledge Bank
            bank = json.loads(KNOWLEDGE_BANK_FILE.read_text(encoding="utf-8"))
            bank["learned_insights"].append(insight_item)
            bank["exchanges_count"] += 1
            KNOWLEDGE_BANK_FILE.write_text(json.dumps(bank, indent=2), encoding="utf-8")
            
            # Persist memory to Master DB
            try:
                from master_db import master_db
                master_db.add_memory(
                    key=f"inter_ai_{insight_item['id']}",
                    val=f"Inter-AI Knowledge Exchange with {target_model} on '{topic}': {response[:300]}",
                    category="ai_peer_learning"
                )
            except Exception:
                pass

            return {
                "status": "success",
                "target_model": target_model,
                "topic": topic,
                "insight_id": insight_item["id"],
                "learned_snippet": response[:400]
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_knowledge_bank(self) -> dict:
        try:
            if KNOWLEDGE_BANK_FILE.exists():
                return json.loads(KNOWLEDGE_BANK_FILE.read_text(encoding="utf-8"))
            return {"learned_insights": [], "exchanges_count": 0}
        except Exception as e:
            return {"error": str(e)}

# Global Instance
ai_communicator = InterAICommunicator()
