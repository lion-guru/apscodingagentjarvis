"""
DevMind RAG Vector Engine — Codebase RAG & Semantic Vector Indexing
Provides semantic vector search, snippet indexing, and context retrieval over workspace files and AI knowledge.
Includes BM25 ranking for keyword-based relevance scoring.
"""
import os
import json
import math
import re
from pathlib import Path
from collections import Counter

RAG_INDEX_FILE = Path.home() / ".devmind" / "rag_vector_index.json"

class DevMindRAGEngine:
    def __init__(self):
        RAG_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not RAG_INDEX_FILE.exists():
            RAG_INDEX_FILE.write_text(json.dumps({"documents": [], "indexed_files": 0}, indent=2), encoding="utf-8")

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r'\w+', text.lower())

    def _bm25_score(self, query_tokens: list[str], doc_tokens: list[str],
                    avg_doc_len: float, k1: float = 1.5, b: float = 0.75) -> float:
        """Compute BM25 score for a query against a document."""
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
        """Build RAG vector chunks for files in workspace."""
        try:
            target_dir = Path(workspace_path)
            if not target_dir.exists():
                return {"status": "error", "error": f"Path not found: {workspace_path}"}

            documents = []
            file_count = 0

            for p in target_dir.rglob("*"):
                if p.is_file() and p.suffix in [".py", ".html", ".js", ".css", ".md", ".json"]:
                    if any(part.startswith(".") or part in ("node_modules", "venv", "__pycache__") for part in p.parts):
                        continue
                    try:
                        content = p.read_text(encoding="utf-8", errors="ignore")
                        chunks = [content[i:i+800] for i in range(0, len(content), 600)]
                        for idx, chunk in enumerate(chunks[:20]):
                            documents.append({
                                "file_path": str(p),
                                "chunk_id": idx,
                                "text": chunk,
                                "tokens": list(set(self._tokenize(chunk))),
                                "token_list": self._tokenize(chunk)
                            })
                        file_count += 1
                    except Exception:
                        pass

            RAG_INDEX_FILE.write_text(json.dumps({"documents": documents, "indexed_files": file_count}, indent=2), encoding="utf-8")
            return {"status": "ok", "indexed_files": file_count, "total_chunks": len(documents)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def search_rag(self, query: str, top_k: int = 3, method: str = "bm25") -> list[dict]:
        """Perform search over indexed chunks using BM25 or cosine similarity."""
        try:
            if not RAG_INDEX_FILE.exists():
                return []

            data = json.loads(RAG_INDEX_FILE.read_text(encoding="utf-8"))
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
            else:
                query_token_set = set(query_tokens)
                scored = []
                for doc in documents:
                    doc_tokens = set(doc.get("tokens", []))
                    overlap = len(query_token_set.intersection(doc_tokens))
                    if overlap > 0:
                        score = overlap / math.sqrt(len(query_token_set) * max(1, len(doc_tokens)))
                        scored.append((score, doc))
                scored.sort(key=lambda x: x[0], reverse=True)

            return [
                {
                    "score": round(s[0], 4),
                    "file_path": s[1]["file_path"],
                    "snippet": s[1]["text"][:300]
                }
                for s in scored[:top_k]
            ]
        except Exception as e:
            return []

# Global Instance
rag_engine = DevMindRAGEngine()
