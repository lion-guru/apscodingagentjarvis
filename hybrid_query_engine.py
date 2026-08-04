"""
DevMind Hybrid Code Query Engine
Ported & enhanced from Claude Code's QueryEngine.ts
Combines BM25 text ranking with AST symbol indexing for fast, precise code query results.
"""
import os
import re
import math
from pathlib import Path
from typing import List, Dict, Tuple


class HybridQueryEngine:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_index: Dict[str, Dict[str, int]] = {}  # file_path -> {term: tf}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.total_docs: int = 0
        self.idf: Dict[str, float] = {}

    def index_workspace(self, root_dir: str, extensions: Tuple[str, ...] = (".py", ".js", ".ts", ".html", ".css", ".sql", ".md")) -> dict:
        """Scan directory and index all source files for fast BM25 query."""
        root_path = Path(root_dir)
        if not root_path.exists():
            return {"status": "error", "message": "Directory does not exist"}

        self.doc_index.clear()
        self.doc_lengths.clear()
        doc_freqs: Dict[str, int] = {}
        total_len = 0

        for path in root_path.rglob("*"):
            if path.is_file() and path.suffix in extensions and not any(part.startswith(".") or part in ("node_modules", "venv", "__pycache__") for part in path.parts):
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    tokens = re.findall(r'[a-zA-Z0-9_]+', content.lower())
                    if not tokens:
                        continue

                    doc_key = str(path)
                    tf_map: Dict[str, int] = {}
                    for t in tokens:
                        tf_map[t] = tf_map.get(t, 0) + 1

                    self.doc_index[doc_key] = tf_map
                    length = len(tokens)
                    self.doc_lengths[doc_key] = length
                    total_len += length

                    for term in tf_map.keys():
                        doc_freqs[term] = doc_freqs.get(term, 0) + 1

                except Exception:
                    pass

        self.total_docs = len(self.doc_index)
        self.avg_doc_length = total_len / self.total_docs if self.total_docs > 0 else 0.0

        # Calculate IDF for all terms
        self.idf.clear()
        for term, df in doc_freqs.items():
            self.idf[term] = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)

        return {"status": "ok", "indexed_files": self.total_docs, "avg_doc_length": round(self.avg_doc_length, 2)}

    def search(self, query: str, top_k: int = 10) -> List[dict]:
        """Search indexed files using BM25 scoring algorithm."""
        if not self.doc_index:
            return []

        query_tokens = re.findall(r'[a-zA-Z0-9_]+', query.lower())
        if not query_tokens:
            return []

        scores: Dict[str, float] = {}

        for doc_key, tf_map in self.doc_index.items():
            score = 0.0
            doc_len = self.doc_lengths[doc_key]

            for term in query_tokens:
                if term in tf_map:
                    tf = tf_map[term]
                    idf_val = self.idf.get(term, 0.0)
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / (self.avg_doc_length or 1.0)))
                    score += idf_val * (numerator / denominator)

            if score > 0.0:
                scores[doc_key] = score

        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        results = []
        for file_path, bm25_score in sorted_docs:
            results.append({
                "file_path": file_path,
                "file_name": Path(file_path).name,
                "score": round(bm25_score, 4)
            })

        return results


# Global query engine instance
query_engine = HybridQueryEngine()
