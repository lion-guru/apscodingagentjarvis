"""
DevMind / Jarvis — Free AI Model Auto-Discovery & Testing System
Automatically discovers and tests all available free AI models across providers.
Saves working models to working_models.json for the agent failover chain.
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

import httpx

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Load .env
def load_env():
    for env_path in [Path(".env"), Path.home() / ".env"]:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"\'')
            break

load_env()

RESULTS_FILE = Path("working_models.json")
OLLAMA_BASE = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# ── Color helpers ────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def fail(msg): print(f"  {RED}✗{RESET} {msg}")
def info(msg): print(f"  {CYAN}→{RESET} {msg}")


# ── Provider Testers ─────────────────────────────────────────────

def test_google_gemini() -> list[dict]:
    """Test Google Gemini free models"""
    models = []
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        fail("GEMINI_API_KEY not set — skipping Google Gemini")
        return models

    # Models to test (free tier) — updated for 2026
    # gemini-1.5-* are deprecated; gemini-2.5-* are the current free models
    gemini_models = [
        ("gemini-2.5-flash",      "Latest flash, 500 req/day free (WORKS with new key)"),
        ("gemini-2.5-flash-lite", "Highest free RPM, 1000 req/day"),
        ("gemini-2.5-pro",        "Pro tier, highest quality free"),
        ("gemini-2.0-flash",      "Fast flash (may have quota limits)"),
        ("gemini-2.0-flash-exp",  "Experimental flash"),
    ]

    info("Testing Google Gemini free models...")
    test_payload = {
        "contents": [{"role": "user", "parts": [{"text": "Say hi in 5 words"}]}],
    }

    for model_id, desc in gemini_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
            start = time.time()
            resp = httpx.post(url, json=test_payload, timeout=15.0)
            elapsed = round(time.time() - start, 2)

            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                ok(f"{model_id} — {desc} [{elapsed}s]")
                models.append({
                    "provider": "google",
                    "model": model_id,
                    "display_name": f"Google {model_id}",
                    "description": desc,
                    "latency_s": elapsed,
                    "response_preview": text[:60],
                    "free_tier": True,
                    "requires_key": "GEMINI_API_KEY",
                })
            else:
                err = resp.json().get("error", {}).get("message", resp.text[:80])
                fail(f"{model_id} — {err}")
        except Exception as e:
            fail(f"{model_id} — {e}")

    return models


def test_groq() -> list[dict]:
    """Test Groq free models (OpenAI-compatible API)"""
    models = []
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        fail("GROQ_API_KEY not set — skipping Groq")
        return models

    info("Testing Groq free models (fastest inference)...")
    groq_models = [
        ("llama-3.3-70b-versatile",  "Llama 3.3 70B, top quality free"),
        ("llama-3.1-8b-instant",     "Llama 3.1 8B, fastest"),
        ("llama-3.2-1b-instant",     "Llama 3.2 1B, very fast"),
        ("gemma2-9b-it",             "Google Gemma 2"),
        ("qwen-qwq-32b",             "Qwen QwQ 32B reasoning"),
        ("mixtral-8x7b-32768",       "Mixtral MoE, 32K context"),
        ("deepseek-r1-distill-llama-70b", "DeepSeek R1 distilled"),
        ("meta-llama/llama-4-scout-17b-16e-instruct", "Llama 4 Scout"),
        ("meta-llama/llama-4-maverick-17b-128e-instruct", "Llama 4 Maverick"),
        ("qwen-2.5-coder-32b",       "Qwen 2.5 Coder 32B"),
        ("qwen-2.5-32b",             "Qwen 2.5 32B"),
        ("qwen/qwen-2.5-coder-32b",  "Qwen 2.5 Coder (slash form)"),
    ]

    for model_id, desc in groq_models:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": "Say hi in 5 words"}],
                "max_tokens": 30,
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            start = time.time()
            resp = httpx.post(url, json=payload, headers=headers, timeout=15.0)
            elapsed = round(time.time() - start, 2)

            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"]
                ok(f"{model_id} — {desc} [{elapsed}s]")
                models.append({
                    "provider": "groq",
                    "model": model_id,
                    "display_name": f"Groq {model_id}",
                    "description": desc,
                    "latency_s": elapsed,
                    "response_preview": text[:60],
                    "free_tier": True,
                    "requires_key": "GROQ_API_KEY",
                })
            else:
                err = resp.json().get("error", {}).get("message", resp.text[:80])
                fail(f"{model_id} — {err}")
        except Exception as e:
            fail(f"{model_id} — {e}")

    return models


def test_openrouter() -> list[dict]:
    """Test OpenRouter free models"""
    models = []
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        fail("OPENROUTER_API_KEY not set — skipping OpenRouter")
        return models

    info("Testing OpenRouter free models...")
    or_models = [
        ("nvidia/nemotron-3-ultra-550b-a55b:free",      "550B MoE, 1M context, top free model"),
        ("nvidia/nemotron-3-super-120b-a12b:free",      "120B MoE, fast reasoning"),
        ("google/gemma-4-31b-it:free",                   "Google Gemma 4, 262K context"),
        ("google/gemma-4-26b-a4b-it:free",               "Google Gemma 4, smaller/faster"),
        ("qwen/qwen3-coder:free",                        "Qwen3 Coder, best for code"),
        ("qwen/qwen-2.5-coder-32b-instruct:free",       "Qwen 2.5 Coder 32B"),
        ("meta-llama/llama-3.3-70b-instruct:free",       "Llama 3.3 70B"),
        ("meta-llama/llama-3.2-1b-instruct:free",        "Llama 3.2 1B, very fast"),
        ("cohere/north-mini-code:free",                  "Cohere code model"),
        ("poolside/laguna-m.1:free",                     "Poolside coding model"),
    ]

    for model_id, desc in or_models:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": "Say hi in 5 words"}],
                "max_tokens": 30,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "http://localhost:7860",
                "X-OpenRouter-Title": "DevMind Model Discovery",
                "Content-Type": "application/json",
            }
            start = time.time()
            resp = httpx.post(url, json=payload, headers=headers, timeout=15.0)
            elapsed = round(time.time() - start, 2)

            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"]
                ok(f"{model_id} — {desc} [{elapsed}s]")
                models.append({
                    "provider": "openrouter",
                    "model": model_id,
                    "display_name": f"OpenRouter {model_id.replace(':free','')}",
                    "description": desc,
                    "latency_s": elapsed,
                    "response_preview": text[:60],
                    "free_tier": True,
                    "requires_key": "OPENROUTER_API_KEY",
                })
            elif resp.status_code == 401 and "Authentication" in resp.text:
                # Key is invalid — skip remaining OpenRouter models
                fail(f"{model_id} — invalid API key (rest of OpenRouter models skipped)")
                break
            else:
                err = resp.json().get("error", {}).get("message", resp.text[:80])
                fail(f"{model_id} — {err}")
        except Exception as e:
            fail(f"{model_id} — {e}")

    return models


def test_zenmux() -> list[dict]:
    """Test ZenMux free AI chat platform"""
    models = []
    api_key = os.getenv("ZENMUX_API_KEY")
    if not api_key:
        fail("ZENMUX_API_KEY not set — skipping ZenMux")
        return models

    info("Testing ZenMux free AI chat models...")
    zenmux_models = [
        ("zenmux-free-chat", "ZenMux Free AI Chat - unlimited free conversations"),
    ]

    for model_id, desc in zenmux_models:
        try:
            url = "https://zenmux.ai/api/v1/chat/completions"
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Say hi in 5 words"}],
                "max_tokens": 30,
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            start = time.time()
            resp = httpx.post(url, json=payload, headers=headers, timeout=15.0)
            elapsed = round(time.time() - start, 2)

            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"]
                ok(f"{model_id} — {desc} [{elapsed}s]")
                models.append({
                    "provider": "zenmux",
                    "model": model_id,
                    "display_name": f"ZenMux {model_id}",
                    "description": desc,
                    "latency_s": elapsed,
                    "response_preview": text[:60],
                    "free_tier": True,
                    "requires_key": "ZENMUX_API_KEY",
                })
            else:
                err = resp.text[:80]
                fail(f"{model_id} — {err}")
        except Exception as e:
            fail(f"{model_id} — {e}")

    return models


def test_huggingface() -> list[dict]:
    """Test HuggingFace free inference API"""
    models = []
    api_key = os.getenv("HUGGING_FACE_API_KEY")
    if not api_key:
        fail("HUGGING_FACE_API_KEY not set — skipping HuggingFace")
        return models

    info("Testing HuggingFace free inference models...")
    hf_models = [
        ("Qwen/Qwen2.5-Coder-32B-Instruct",  "Qwen 2.5 Coder 32B"),
        ("meta-llama/Llama-3.3-70B-Instruct", "Llama 3.3 70B"),
        ("microsoft/Phi-4",                    "Microsoft Phi-4"),
        ("google/gemma-2-9b-it",               "Google Gemma 2 9B"),
        ("mistralai/Mistral-7B-Instruct-v0.3","Mistral 7B"),
    ]

    for model_id, desc in hf_models:
        try:
            url = f"https://api-inference.huggingface.co/models/{model_id}"
            payload = {"inputs": "Say hi in 5 words", "parameters": {"max_new_tokens": 20}}
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            start = time.time()
            resp = httpx.post(url, json=payload, headers=headers, timeout=12.0)
            elapsed = round(time.time() - start, 2)

            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    text = data[0].get("generated_text", "")
                else:
                    text = str(data)[:100]
                ok(f"{model_id} — {desc} [{elapsed}s]")
                models.append({
                    "provider": "huggingface",
                    "model": model_id,
                    "display_name": f"HuggingFace {model_id.split('/')[-1]}",
                    "description": desc,
                    "latency_s": elapsed,
                    "response_preview": text[:60],
                    "free_tier": True,
                    "requires_key": "HUGGING_FACE_API_KEY",
                })
            elif resp.status_code == 503 and "temporarily unavailable" in resp.text:
                # Model loading — skip
                fail(f"{model_id} — loading (skipped)")
            else:
                err = resp.text[:80]
                fail(f"{model_id} — {err}")
                # DNS/network error → skip rest
                if "getaddrinfo" in str(err) or "Connection" in str(err):
                    break
        except Exception as e:
            fail(f"{model_id} — {e}")
            # Network error → skip rest
            if "getaddrinfo" in str(e) or "Connection" in str(e):
                break

    return models


def test_ollama_local() -> list[dict]:
    """Test local Ollama models"""
    models = []
    info("Testing local Ollama models...")

    try:
        r = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=3.0)
        ollama_models = [m["name"] for m in r.json().get("models", [])]
    except Exception:
        fail("Ollama not running — skipping local models")
        return models

    if not ollama_models:
        info("No Ollama models installed")
        return models

    # Models that are too slow to test (skip them)
    SLOW_MODELS = {"qwen2.5-coder:7b", "qwen2.5:14b", "llama3:8b", "codellama:latest"}

    for model_id in ollama_models:
        if model_id in SLOW_MODELS:
            fail(f"{model_id} — skipped (known slow, >30s)")
            continue
        try:
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": "Say hi in 5 words"}],
                "stream": False,
                "options": {"num_predict": 30},
            }
            start = time.time()
            resp = httpx.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=30.0)
            elapsed = round(time.time() - start, 2)

            if resp.status_code == 200:
                text = resp.json()["message"]["content"]
                ok(f"{model_id} — local Ollama [{elapsed}s]")
                models.append({
                    "provider": "ollama",
                    "model": model_id,
                    "display_name": f"Ollama {model_id}",
                    "description": "Local model, free, no API key",
                    "latency_s": elapsed,
                    "response_preview": text[:60],
                    "free_tier": True,
                    "requires_key": None,
                })
            else:
                fail(f"{model_id} — status {resp.status_code}")
        except Exception as e:
            if "timed out" in str(e).lower():
                fail(f"{model_id} — timed out (>30s), too slow")
            else:
                fail(f"{model_id} — {e}")

    return models


# ── Main Discovery ───────────────────────────────────────────────

def discover_all() -> dict:
    """Run all provider tests and return combined results"""
    print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  🔍 DevMind — Free AI Model Discovery & Test{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 60}{RESET}\n")

    all_models = []

    # Test all providers
    all_models.extend(test_google_gemini())
    print()
    all_models.extend(test_groq())
    print()
    all_models.extend(test_openrouter())
    print()
    all_models.extend(test_zenmux())
    print()
    all_models.extend(test_huggingface())
    print()
    all_models.extend(test_ollama_local())
    print()

    # Build results
    results = {
        "discovered_at": datetime.now().isoformat(),
        "total_working": len(all_models),
        "providers_tested": list(set(m["provider"] for m in all_models)),
        "models": all_models,
        "best_by_provider": {},
        "failover_chain": [],
    }

    # Find best model per provider (lowest latency)
    provider_groups = {}
    for m in all_models:
        p = m["provider"]
        if p not in provider_groups:
            provider_groups[p] = []
        provider_groups[p].append(m)

    for provider, group in provider_groups.items():
        best = min(group, key=lambda x: x["latency_s"])
        results["best_by_provider"][provider] = best["model"]

    # Build optimal failover chain:
    # 1. Best Gemini (free, generous quota)
    # 2. Best Groq (fast inference)
    # 3. Best OpenRouter free (high quality)
    # 4. HuggingFace (backup)
    # 5. Local Ollama (last resort)
    priority_order = ["google", "groq", "zenmux", "openrouter", "huggingface", "ollama"]
    for provider in priority_order:
        if provider in provider_groups:
            best = min(provider_groups[provider], key=lambda x: x["latency_s"])
            results["failover_chain"].append(best["model"])

    # Save results
    RESULTS_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    # Print summary
    print(f"{BOLD}{GREEN}{'=' * 60}{RESET}")
    print(f"{BOLD}{GREEN}  📊 Discovery Complete — {len(all_models)} working models found{RESET}")
    print(f"{BOLD}{GREEN}{'=' * 60}{RESET}\n")

    print(f"{BOLD}Working Models by Provider:{RESET}")
    for provider in priority_order:
        if provider in provider_groups:
            group = provider_groups[provider]
            print(f"\n  {CYAN}{provider.upper()}{RESET} ({len(group)} models):")
            for m in sorted(group, key=lambda x: x["latency_s"]):
                print(f"    • {m['model']:<50} {DIM}[{m['latency_s']}s]{RESET}")

    if results["failover_chain"]:
        print(f"\n{BOLD}Recommended Failover Chain:{RESET}")
        for i, model in enumerate(results["failover_chain"], 1):
            print(f"  {i}. {model}")

    print(f"\n{DIM}Results saved to: {RESULTS_FILE.absolute()}{RESET}\n")
    return results


def get_working_models() -> dict:
    """Load previously discovered models, or run discovery if not found"""
    if RESULTS_FILE.exists():
        try:
            return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return discover_all()


if __name__ == "__main__":
    discover_all()
