import os
import json
import httpx
import math
from pathlib import Path

# Load .env file if it exists
env_path = Path(".env")
if not env_path.exists():
    env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DB_FILE = ".devmind_index.json"

# Preferred embedding models (multilingual, Hindi support)
EMBEDDING_MODEL_PREF = os.getenv("EMBEDDING_MODEL", "nomic-embed-text-v2-moe")

# Devanagari detection for Hindi-aware embedding
import re as _re
_DEVANAGARI_RANGE = _re.compile(r'[\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F]')

def _is_hindi(text: str) -> bool:
    """Check if text contains Devanagari (Hindi) characters."""
    return bool(_DEVANAGARI_RANGE.search(text))

def _get_installed_models() -> list[str]:
    """Fetch installed Ollama models."""
    try:
        resp = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=3.0)
        if resp.status_code == 200:
            return [m.get("name") for m in resp.json().get("models", []) if m.get("name")]
    except Exception:
        pass
    return []

def _ollama_embed(model_name: str, text: str) -> list[float] | None:
    """Try embedding with a specific Ollama model. Returns None on failure."""
    # Try modern /api/embed first
    try:
        resp = httpx.post(
            f"{OLLAMA_BASE}/api/embed",
            json={"model": model_name, "input": text},
            timeout=15.0
        )
        resp.raise_for_status()
        res_json = resp.json()
        if "embeddings" in res_json:
            return res_json["embeddings"][0]
        if "embedding" in res_json:
            return res_json["embedding"]
    except Exception:
        pass

    # Fallback to older /api/embeddings
    try:
        resp = httpx.post(
            f"{OLLAMA_BASE}/api/embeddings",
            json={"model": model_name, "prompt": text},
            timeout=15.0
        )
        resp.raise_for_status()
        res_json = resp.json()
        if "embedding" in res_json:
            return res_json["embedding"]
    except Exception:
        pass

    return None

def get_embedding(text: str) -> list[float]:
    """
    Fetch text embedding with Hindi-aware model selection.
    For Hindi text, prefers nomic-embed-text-v2-moe (100 languages).
    Falls back through Gemini → v2-moe → v1 → other installed models.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    has_hindi = _is_hindi(text)

    # 1. Try Gemini models (English only — skip for pure Hindi)
    if gemini_key and not has_hindi:
        for model_name in ["text-embedding-004", "embedding-001"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:embedContent?key={gemini_key}"
                payload = {
                    "model": f"models/{model_name}",
                    "content": {"parts": [{"text": text}]}
                }
                resp = httpx.post(url, headers={"Content-Type": "application/json"},
                                  json=payload, timeout=5.0)
                resp.raise_for_status()
                return resp.json()["embedding"]["values"]
            except Exception as e:
                print(f"[Embedding] Gemini {model_name} failed: {e}")

    # 2. Try Ollama models — Hindi-aware ordering
    installed = _get_installed_models()

    # Build priority list: v2-moe first for Hindi, v1 for English
    if has_hindi:
        preferred = ["nomic-embed-text-v2-moe", "nomic-embed-text:latest"]
    else:
        preferred = ["nomic-embed-text:latest", "nomic-embed-text-v2-moe"]

    # Add any other installed embedding models as fallbacks
    for m in installed:
        if m not in preferred and "embed" in m.lower():
            preferred.append(m)

    last_err = None
    for model_name in preferred:
        result = _ollama_embed(model_name, text)
        if result is not None:
            return result
        last_err = f"Model {model_name} failed"

    raise RuntimeError(
        f"Failed to generate embeddings.\n"
        f"Hindi text: {has_hindi}\n"
        f"Installed models: {installed}\n"
        f"Fix: ollama pull nomic-embed-text-v2-moe\n"
        f"Last error: {last_err}"
    )

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a*b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a*a for a in v1))
    norm_b = math.sqrt(sum(b*b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def chunk_file(path: Path, content: str) -> list[dict]:
    """Break a code file into semantic chunks (lines of code or classes/functions)."""
    lines = content.splitlines()
    chunks = []
    current_chunk = []
    current_size = 0
    max_chunk_size = 500  # Words/tokens approximate
    
    for line_num, line in enumerate(lines, 1):
        current_chunk.append((line_num, line))
        current_size += len(line.split())
        
        if current_size >= max_chunk_size:
            chunk_text = "\n".join(l[1] for l in current_chunk)
            chunks.append({
                "path": str(path),
                "start_line": current_chunk[0][0],
                "end_line": current_chunk[-1][0],
                "text": chunk_text
            })
            current_chunk = current_chunk[-len(current_chunk)//3:] # 30% overlap
            current_size = sum(len(l[1].split()) for l in current_chunk)
            
    if current_chunk:
        chunk_text = "\n".join(l[1] for l in current_chunk)
        chunks.append({
            "path": str(path),
            "start_line": current_chunk[0][0],
            "end_line": current_chunk[-1][0],
            "text": chunk_text
        })
        
    return chunks

def load_db(cwd: str) -> dict:
    db_path = Path(cwd) / DB_FILE
    if db_path.exists():
        try:
            return json.loads(db_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"files": {}, "chunks": []}

def save_db(cwd: str, db: dict):
    db_path = Path(cwd) / DB_FILE
    db_path.write_text(json.dumps(db, indent=2), encoding="utf-8")

def index_directory(cwd: str) -> str:
    """Scan and index all code files in the directory."""
    db = load_db(cwd)
    indexed_files = db.get("files", {})
    chunks = db.get("chunks", [])
    
    # Supported code extensions
    extensions = {'.py', '.js', '.ts', '.tsx', '.html', '.css', '.json', '.go', '.java', '.cpp', '.h', '.sh', '.bat'}
    
    scanned_paths = []
    for root, dirs, files in os.walk(cwd):
        # Ignore common build folders
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '__pycache__', 'dist', 'build', '.next', '.agents', 'venv', '.venv', 'env')]
        for f in files:
            if f.startswith('.'):
                continue
            path = Path(root) / f
            if path.suffix in extensions:
                scanned_paths.append(path)

    # 1. Remove deleted files from index
    scanned_str_paths = {str(p) for p in scanned_paths}
    chunks = [c for c in chunks if c["path"] in scanned_str_paths]
    for p in list(indexed_files.keys()):
        if p not in scanned_str_paths:
            del indexed_files[p]

    # 2. Add or update modified files
    updated_count = 0
    for path in scanned_paths:
        mtime = path.stat().st_mtime
        str_path = str(path)
        
        # Skip if file was not modified
        if str_path in indexed_files and indexed_files[str_path] == mtime:
            continue
            
        # Remove old chunks for this file
        chunks = [c for c in chunks if c["path"] != str_path]
        
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            file_chunks = chunk_file(path.relative_to(cwd), content)
            
            for chunk in file_chunks:
                # Add absolute path to mtime map but store relative in chunk path
                chunk["path"] = str(path.relative_to(cwd))
                try:
                    chunk["embedding"] = get_embedding(chunk["text"])
                except Exception:
                    chunk["embedding"] = []
                chunks.append(chunk)
                
            indexed_files[str_path] = mtime
            updated_count += 1
        except Exception as e:
            print(f"[Index Error] Failed to index {path}: {e}")

    db["files"] = indexed_files
    db["chunks"] = chunks
    save_db(cwd, db)
    
    return f"Indexed {len(scanned_paths)} files. Newly indexed/updated: {updated_count} files. Total chunks: {len(chunks)}"

def keyword_search_fallback(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """Fallback search using keyword token matching if embeddings aren't working."""
    def get_tokens(text: str):
        return set(re.findall(r'[a-zA-Z_]\w*', text.lower()))
        
    query_tokens = get_tokens(query)
    if not query_tokens:
        return [{k: v for k, v in c.items() if k != "embedding"} for c in chunks[:top_n]]
        
    scored_chunks = []
    for chunk in chunks:
        chunk_tokens = get_tokens(chunk["text"])
        overlap = query_tokens.intersection(chunk_tokens)
        
        # Jaccard/Overlap similarity
        score = len(overlap) / len(query_tokens) if query_tokens else 0.0
        scored_chunks.append((score, chunk))
        
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    top_matches = []
    for score, chunk in scored_chunks[:top_n]:
        clean_chunk = {k: v for k, v in chunk.items() if k != "embedding"}
        clean_chunk["similarity"] = round(score, 3)
        top_matches.append(clean_chunk)
        
    return top_matches

import re

def query_database(cwd: str, query: str, top_n: int = 5) -> list[dict]:
    """Retrieve top matches using embeddings, falling back to TF-IDF keyword overlap on error."""
    db = load_db(cwd)
    chunks = db.get("chunks", [])
    if not chunks:
        return []
        
    try:
        query_emb = get_embedding(query)
        if chunks and not chunks[0].get("embedding"):
            raise ValueError("No embeddings found in the database. Downgrading to keyword search.")
            
        results = []
        for chunk in chunks:
            if not chunk.get("embedding"):
                continue
            sim = cosine_similarity(query_emb, chunk["embedding"])
            results.append((sim, chunk))
            
        results.sort(key=lambda x: x[0], reverse=True)
        
        top_matches = []
        for sim, chunk in results[:top_n]:
            clean_chunk = {k: v for k, v in chunk.items() if k != "embedding"}
            clean_chunk["similarity"] = round(sim, 3)
            top_matches.append(clean_chunk)
            
        return top_matches
    except Exception as e:
        print(f"[RAG Info] Embedding search failed ({e}). Falling back to local Keyword Search...")
        return keyword_search_fallback(query, chunks, top_n)
