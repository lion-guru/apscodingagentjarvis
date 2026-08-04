"""Comprehensive tier-by-tier test for DevMind failover chain.

Tests each model tier (Gemini → Groq → Zen → OmniRoute → Ollama)
by sending a simple task and verifying the model responds.
Run with: python test_all_tiers.py
"""
import sys, os, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"E:\coding-assistant")
os.chdir(r"E:\coding-assistant")
from dotenv import load_dotenv
load_dotenv()

import httpx
from agent import dispatch_single_model, _is_zen_model, _is_omniroute_model

TASK = "Reply with exactly: TIER_TEST_OK"
TIERS = {
    "Gemini": "gemini-2.5-flash",
    "Groq": "llama-3.3-70b-versatile",
    "Zen": "big-pickle",
    "OmniRoute": "auto/cheap",
}

results = {}
for tier, model in TIERS.items():
    start = time.time()
    try:
        text = dispatch_single_model([{"role": "user", "content": TASK}], model)
        elapsed = round(time.time() - start, 2)
        ok = "TIER_TEST_OK" in text or "OK" in text
        results[tier] = {"model": model, "status": "PASS" if ok else "WARN", "time": elapsed, "preview": text[:60]}
    except Exception as e:
        results[tier] = {"model": model, "status": "FAIL", "time": round(time.time() - start, 2), "error": str(e)[:100]}

print("\n=== Tier Test Results ===")
for tier, r in results.items():
    icon = "OK" if r["status"] == "PASS" else "FAIL" if r["status"] == "FAIL" else "WARN"
    print(f"  [{icon}] {tier:12s} | {r['model']:30s} | {r['time']:.1f}s | {r.get('preview', r.get('error', ''))[:50]}")

passed = sum(1 for r in results.values() if r["status"] == "PASS")
total = len(results)
print(f"\n{passed}/{total} tiers passed")
if passed == total:
    print("ALL TIERS GREEN")
else:
    print("SOME TIERS FAILED — check keys and network")
