import json
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class SessionManager:
    def __init__(self, storage_dir: str = None):
        self.storage_dir = storage_dir or os.path.join(os.path.expanduser("~"), ".devmind", "sessions")
        os.makedirs(self.storage_dir, exist_ok=True)
        self._lock = threading.Lock()
        self._active_sessions: Dict[str, dict] = {}

    def create_session(self, session_id: str, workspace: str = "") -> Dict:
        with self._lock:
            session = {
                "session_id": session_id,
                "workspace": workspace,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": [],
                "artifacts": [],
                "knowledge_items": [],
                "agent_state": "idle",
                "current_task": None
            }
            self._active_sessions[session_id] = session
            self._save_session(session)
            return session

    def get_session(self, session_id: str) -> Optional[Dict]:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                session = self._load_session(session_id)
            return session

    def add_message(self, session_id: str, role: str, content: str) -> Optional[Dict]:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                session = self._load_session(session_id)
            if not session:
                return None
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            session["messages"].append(message)
            session["updated_at"] = datetime.now().isoformat()
            self._save_session(session)
            return message

    def add_artifact(self, session_id: str, artifact_type: str, content: str) -> Optional[Dict]:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                session = self._load_session(session_id)
            if not session:
                return None
            artifact = {
                "type": artifact_type,
                "content": content,
                "created_at": datetime.now().isoformat()
            }
            session["artifacts"].append(artifact)
            session["updated_at"] = datetime.now().isoformat()
            self._save_session(session)
            return artifact

    def add_knowledge_item(self, session_id: str, ki_id: str) -> Optional[Dict]:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                session = self._load_session(session_id)
            if not session:
                return None
            if ki_id not in session["knowledge_items"]:
                session["knowledge_items"].append(ki_id)
                session["updated_at"] = datetime.now().isoformat()
                self._save_session(session)
            return {"status": "ok", "ki_id": ki_id}

    def set_agent_state(self, session_id: str, state: str, task: Optional[str] = None) -> Optional[Dict]:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                session = self._load_session(session_id)
            if not session:
                return None
            session["agent_state"] = state
            if task is not None:
                session["current_task"] = task
            session["updated_at"] = datetime.now().isoformat()
            self._save_session(session)
            return session

    def list_sessions(self) -> List[Dict]:
        with self._lock:
            return [
                {
                    "session_id": s["session_id"],
                    "workspace": s.get("workspace", ""),
                    "created_at": s.get("created_at", ""),
                    "updated_at": s.get("updated_at", ""),
                    "agent_state": s.get("agent_state", "idle"),
                    "message_count": len(s.get("messages", [])),
                    "artifact_count": len(s.get("artifacts", []))
                }
                for s in self._active_sessions.values()
            ]

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
            filepath = os.path.join(self.storage_dir, f"{session_id}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False

    def get_recent_context(self, session_id: str, max_messages: int = 20) -> List[Dict]:
        session = self.get_session(session_id)
        if not session:
            return []
        messages = session.get("messages", [])
        return messages[-max_messages:] if len(messages) > max_messages else messages

    def get_all_knowledge_for_session(self, session_id: str) -> List[Dict]:
        session = self.get_session(session_id)
        if not session:
            return []
        from knowledge_items import knowledge_items
        result = []
        for ki_id in session.get("knowledge_items", []):
            ki = knowledge_items.get_item(ki_id)
            if ki:
                result.append(ki)
        return result

    def _save_session(self, session: Dict):
        filepath = os.path.join(self.storage_dir, f"{session['session_id']}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)

    def _load_session(self, session_id: str) -> Optional[Dict]:
        filepath = os.path.join(self.storage_dir, f"{session_id}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                session = json.load(f)
            with self._lock:
                self._active_sessions[session_id] = session
            return session
        except (json.JSONDecodeError, IOError):
            return None

    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        cutoff = datetime.now() - timedelta(days=max_age_days)
        removed = 0
        with self._lock:
            for sid in list(self._active_sessions.keys()):
                session = self._active_sessions[sid]
                try:
                    updated = datetime.fromisoformat(session.get("updated_at", ""))
                    if updated < cutoff:
                        self.delete_session(sid)
                        removed += 1
                except (ValueError, TypeError):
                    pass
        return removed


session_manager = SessionManager()


def create_session(session_id: str, workspace: str = "") -> dict:
    return session_manager.create_session(session_id, workspace)

def add_message(session_id: str, role: str, content: str) -> dict:
    return session_manager.add_message(session_id, role, content)

def get_session(session_id: str) -> dict:
    return session_manager.get_session(session_id)

def list_sessions() -> list:
    return session_manager.list_sessions()