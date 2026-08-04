"""Model usage tracker: predicts quota/rate-limit exhaustion BEFORE it happens,
so the failover engine can switch models proactively instead of reactively.

Records every model call (timestamp, tokens, model), tracks per-day/per-minute
consumption against known free-tier limits, and exposes quota status so the
agent can hand off work to the next model before a 429 strikes.

Manual config (optional): ~/.devmind/model_config.json
{
  "failover_chain": ["gemini-2.5-flash", "llama-3.3-70b-versatile"],  // user's own order
  "disabled_models": ["llama-3.1-8b-instant"],
  "switch_threshold": 0.85,          // switch when a model hits 85% of its quota
  "manual_override": false            // true = never auto-switch, only manual chain
}
"""
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
USAGE_FILE = Path.home() / ".devmind" / "model_usage.json"
CONFIG_FILE = Path.home() / ".devmind" / "model_config.json"

# Known free-tier limits per model family (requests per day / per minute).
# Values approximate published free tiers; overridable in model_config.json.
DEFAULT_QUOTAS = {
    "gemini-2.5-flash":        {"per_day": 500, "per_minute": 15},
    "gemini-2.5-flash-lite":   {"per_day": 1000, "per_minute": 30},
    "gemini-2.5-pro":          {"per_day": 50, "per_minute": 5},
    "llama-3.3-70b-versatile": {"per_day": 14400, "per_minute": 30},   # Groq tier
    "llama-3.1-8b-instant":    {"per_day": 14400, "per_minute": 30},
    "llama-3.2-1b-instant":    {"per_day": 14400, "per_minute": 30},
}

# OpenRouter :free models — most have 50 req/day, 20 req/min tier.
DEFAULT_OR_QUOTA = {"per_day": 50, "per_minute": 20}

# OpenCode Zen free models (trial tier) — generous but still finite.
DEFAULT_ZEN_QUOTA = {"per_day": 500, "per_minute": 20}

# OmniRoute local gateway — 290+ providers, auto-fallback, generous free tier.
DEFAULT_OMNIROUTE_QUOTA = {"per_day": 2000, "per_minute": 60}

_LOCK = threading.Lock()


class UsageTracker:
    def __init__(self):
        self._cache = {"calls": [], "quota_overrides": {}}
        self._load()

    def _load(self):
        try:
            if USAGE_FILE.exists():
                data = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
                self._cache = data
                # Prune calls older than 24h to keep the file small
                cutoff = time.time() - 24 * 3600
                self._cache["calls"] = [c for c in self._cache["calls"]
                                        if c.get("ts", 0) > cutoff]
        except Exception:
            self._cache = {"calls": [], "quota_overrides": {}}

    def _save(self):
        try:
            USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            USAGE_FILE.write_text(
                json.dumps(self._cache, indent=1, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ── Quota knowledge ───────────────────────────────────────────
    def _quota_for(self, model: str) -> dict:
        key = model.lower()
        overrides = self._cache.get("quota_overrides", {})
        if key in overrides:
            return overrides[key]
        for fam, quota in DEFAULT_QUOTAS.items():
            if fam in key:
                return quota
        if ":free" in key:
            return dict(DEFAULT_OR_QUOTA)
        if key in {"big-pickle", "deepseek-v4-flash-free", "mimo-v2.5-free",
                   "ling-3.0-flash-free", "laguna-s-2.1-free", "north-mini-code-free",
                   "nemotron-3-ultra-free"}:
            return dict(DEFAULT_ZEN_QUOTA)
        if key.startswith("auto/") or key == "omniroute":
            return dict(DEFAULT_OMNIROUTE_QUOTA)
        # Unknown model: no known cap → never considered draining
        return {"per_day": None, "per_minute": None}

    def set_quota(self, model: str, per_day=None, per_minute=None):
        q = {"per_day": per_day, "per_minute": per_minute}
        self._cache.setdefault("quota_overrides", {})[model.lower()] = q
        self._save()

    # ── Recording ─────────────────────────────────────────────────
    def record_call(self, model: str, input_tokens: int = 0,
                    output_tokens: int = 0, success: bool = True,
                    task_type: str = "general"):
        with _LOCK:
            self._cache["calls"].append({
                "model": model,
                "ts": time.time(),
                "in": int(input_tokens or 0),
                "out": int(output_tokens or 0),
                "success": success,
                "task": task_type,
            })
            # Trim to last 2000 entries
            if len(self._cache["calls"]) > 2000:
                self._cache["calls"] = self._cache["calls"][-2000:]
            self._save()

    # ── Quota status ──────────────────────────────────────────────
    def quota_status(self, model: str) -> dict:
        """Return usage vs quota. ratio > switch_threshold ⇒ draining."""
        now = time.time()
        day_start = now - 24 * 3600
        minute_start = now - 60

        key = model.lower()
        calls = [c for c in self._cache["calls"] if c["model"].lower() == key]
        day_calls = sum(1 for c in calls if c["ts"] > day_start)
        min_calls = sum(1 for c in calls if c["ts"] > minute_start)
        day_tokens = sum(c["in"] + c["out"] for c in calls if c["ts"] > day_start)

        q = self._quota_for(model)
        day_limit = q.get("per_day")
        min_limit = q.get("per_minute")

        day_ratio = (day_calls / day_limit) if day_limit else 0.0
        min_ratio = (min_calls / min_limit) if min_limit else 0.0
        # A 429 on record bumps perceived pressure even if quota unknown
        recent_429 = sum(1 for c in calls[-10:]
                         if c.get("success") is False)

        return {
            "model": model,
            "day_calls": day_calls,
            "day_limit": day_limit,
            "day_ratio": round(day_ratio, 3),
            "min_calls": min_calls,
            "min_limit": min_limit,
            "min_ratio": round(min_ratio, 3),
            "day_tokens": day_tokens,
            "recent_failures": recent_429,
            "draining": bool((day_limit and day_ratio >= 0.85) or
                             (min_limit and min_ratio >= 0.85) or
                             recent_429 >= 3),
            "drained": bool((day_limit and day_ratio >= 1.0) or
                            (min_limit and min_ratio >= 1.0)),
        }

    def is_healthy(self, model: str) -> bool:
        """True if the model still has quota headroom (for proactive switching)."""
        st = self.quota_status(model)
        return not st["drained"] and not st["draining"]

    def reset(self):
        """Clear usage history (e.g. new day)."""
        self._cache["calls"] = []
        self._save()

    # ── Manual config ─────────────────────────────────────────────
    @staticmethod
    def load_manual_config() -> dict:
        try:
            if CONFIG_FILE.exists():
                return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def apply_manual_failover_chain(self, auto_chain: list) -> list:
        """If user defined their own chain in model_config.json, honour it."""
        cfg = self.load_manual_config()
        chain = cfg.get("failover_chain") or auto_chain
        disabled = set(cfg.get("disabled_models", []))
        result = []
        for m in chain:
            if m and m not in disabled and m not in result:
                result.append(m)
        return result


usage_tracker = UsageTracker()


def get_quota_status(model: str) -> dict:
    return usage_tracker.quota_status(model)


def record_model_call(model: str, **kw):
    usage_tracker.record_call(model, **kw)


def switch_threshold() -> float:
    cfg = usage_tracker.load_manual_config()
    return float(cfg.get("switch_threshold", 0.85))
