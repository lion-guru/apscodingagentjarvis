import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class KnowledgeItems:
    def __init__(self, storage_dir: str = None):
        self.storage_dir = storage_dir or os.path.join(os.path.expanduser("~"), ".devmind", "knowledge")
        os.makedirs(self.storage_dir, exist_ok=True)

    def add_item(self, title: str, content: str, metadata: Optional[Dict] = None) -> Dict:
        item_id = self._generate_id()
        item = {
            "id": item_id,
            "title": title,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "summary": content[:200]
        }
        filepath = os.path.join(self.storage_dir, f"{item_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(item, f, indent=2, ensure_ascii=False)
        return item

    def get_item(self, item_id: str) -> Optional[Dict]:
        filepath = os.path.join(self.storage_dir, f"{item_id}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_items(self) -> List[Dict]:
        items = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.storage_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        item = json.load(f)
                    items.append(item)
                except (json.JSONDecodeError, IOError):
                    pass
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def search(self, query: str) -> List[Dict]:
        items = self.list_items()
        query_lower = query.lower()
        results = []
        for item in items:
            if query_lower in item.get("title", "").lower() or query_lower in item.get("content", "").lower():
                results.append(item)
        return results

    def update_item(self, item_id: str, content: Optional[str] = None, metadata: Optional[Dict] = None) -> Optional[Dict]:
        item = self.get_item(item_id)
        if not item:
            return None
        if content is not None:
            item["content"] = content
            item["summary"] = content[:200]
        if metadata is not None:
            item["metadata"].update(metadata)
        item["updated_at"] = datetime.now().isoformat()
        filepath = os.path.join(self.storage_dir, f"{item_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(item, f, indent=2, ensure_ascii=False)
        return item

    def delete_item(self, item_id: str) -> bool:
        filepath = os.path.join(self.storage_dir, f"{item_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    def get_summaries(self) -> List[Dict]:
        items = self.list_items()
        return [{"id": i["id"], "title": i["title"], "summary": i.get("summary", ""), "created_at": i.get("created_at", "")} for i in items]

    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())[:8]


knowledge_items = KnowledgeItems()


def add_item(title: str, content: str, category: str = "general", tags: list = None) -> dict:
    return knowledge_items.add_item(title, content, category, tags)

def get_summaries(limit: int = 50) -> list:
    return knowledge_items.get_summaries(limit)

def search(query: str, category: str = "", limit: int = 20) -> list:
    return knowledge_items.search(query, category, limit)