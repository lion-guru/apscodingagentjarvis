"""
DevMind Search Engine
Enhanced RAG search with BM25 + hybrid pipeline.
Combines keyword search (BM25) with semantic vector search.
"""
import json
import math
import re
from pathlib import Path
from collections import Counter

SEARCH_INDEX_FILE = Path.home() / ".devmind" / "search_index.json"

class SearchEngine:
    def __init__(self):
        SEARCH_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not SEARCH_INDEX_FILE.exists():
            SEARCH_INDEX_FILE.write_text(json.dumps({"documents": [], "indexed_files": 0}, indent=2), encoding="utf-8")

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r'\w+', text.lower())

    def _bm25_score(self, query_tokens: list[str], doc_tokens: list[str],
                    avg_doc_len: float, k1: float = 1.5, b: float = 0.75) -> float:
        if not query_tokens or not doc_tokens:
            return 0.0
        n = len(doc_tokens)
        if n == 0:
            return 0.0
        idf_sum = 0.0
        for token in set(query_tokens):
            df = sum(1 for t in doc_tokens if t == token)
            if df == 0:
                continue
            idf = math.log((1 + 0) / (df + 0.5) + 1)
            tf = doc_tokens.count(token)
            numerator = idf * tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (n / avg_doc_len))
            idf_sum += numerator / denominator
        return idf_sum

    def index_workspace(self, workspace_path: str = "E:\\coding-assistant") -> dict:
        """Build search index for workspace files."""
        try:
            target_dir = Path(workspace_path)
            if not target_dir.exists():
                return {"status": "error", "error": f"Path not found: {workspace_path}"}

            documents = []
            file_count = 0

            for p in target_dir.rglob("*"):
                if p.is_file() and p.suffix in [".py", ".html", ".js", ".css", ".md", ".json", ".txt"]:
                    if any(part.startswith(".") or part in ("node_modules", "venv", "__pycache__") for part in p.parts):
                        continue
                    try:
                        content = p.read_text(encoding="utf-8", errors="ignore")
                        tokens = self._tokenize(content)
                        documents.append({
                            "file_path": str(p),
                            "text": content[:5000],
                            "tokens": list(set(tokens)),
                            "token_list": tokens,
                        })
                        file_count += 1
                    except Exception:
                        pass

            SEARCH_INDEX_FILE.write_text(json.dumps({"documents": documents, "indexed_files": file_count}, indent=2), encoding="utf-8")
            return {"status": "ok", "indexed_files": file_count, "total_docs": len(documents)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def search(self, query: str, top_k: int = 10, method: str = "hybrid") -> list[dict]:
        """Search indexed files using BM25, semantic, or hybrid method."""
        try:
            if not SEARCH_INDEX_FILE.exists():
                return []

            data = json.loads(SEARCH_INDEX_FILE.read_text(encoding="utf-8"))
            query_tokens = self._tokenize(query)
            if not query_tokens:
                return []

            documents = data.get("documents", [])
            if not documents:
                return []

            if method == "bm25":
                all_token_lists = [d.get("token_list", []) for d in documents]
                avg_doc_len = sum(len(t) for t in all_token_lists) / max(1, len(all_token_lists))
                scored = []
                for doc in documents:
                    doc_tokens = doc.get("token_list", [])
                    score = self._bm25_score(query_tokens, doc_tokens, avg_doc_len)
                    if score > 0:
                        scored.append((score, doc))
                scored.sort(key=lambda x: x[0], reverse=True)
            elif method == "semantic":
                query_set = set(query_tokens)
                scored = []
                for doc in documents:
                    doc_tokens = set(doc.get("tokens", []))
                    overlap = len(query_set.intersection(doc_tokens))
                    if overlap > 0:
                        score = overlap / math.sqrt(len(query_set) * max(1, len(doc_tokens)))
                        scored.append((score, doc))
                scored.sort(key=lambda x: x[0], reverse=True)
            else:
                scored = []
                for doc in documents:
                    doc_tokens = set(doc.get("tokens", []))
                    overlap = len(set(query_tokens).intersection(doc_tokens))
                    if overlap > 0:
                        bm25_score = self._bm25_score(query_tokens, doc.get("token_list", []),
                                                      sum(len(d.get("token_list", [])) for d in documents) / max(1, len(documents)))
                        semantic_score = overlap / math.sqrt(len(set(query_tokens)) * max(1, len(doc_tokens)))
                        combined = 0.4 * bm25_score + 0.6 * semantic_score
                        scored.append((combined, doc))
                scored.sort(key=lambda x: x[0], reverse=True)

            return [
                {
                    "score": round(s[0], 4),
                    "file_path": s[1]["file_path"],
                    "snippet": s[1]["text"][:200],
                    "method": method,
                }
                for s in scored[:top_k]
            ]
        except Exception as e:
            return []


search_engine = SearchEngine()

# Module-level wrapper functions for server.py compatibility
def index_workspace(workspace):
    return search_engine.index_workspace(workspace)

def search(query, top_k=10, method="hybrid"):
    return search_engine.search(query, top_k, method)