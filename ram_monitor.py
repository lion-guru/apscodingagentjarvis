"""
RAM Monitor — Auto-swap local→cloud model when RAM > threshold
Prevents system hang by offloading to cloud when local resources are tight.
"""
import os
import time
import logging
import threading
from typing import Optional, Callable

logger = logging.getLogger("ram_monitor")

# Thresholds
RAM_WARN_PCT = float(os.getenv("RAM_WARN_PCT", "75"))
RAM_SWAP_PCT = float(os.getenv("RAM_SWAP_PCT", "90"))
RAM_KILL_PCT = float(os.getenv("RAM_KILL_PCT", "95"))

# Cloud fallback models (free)
CLOUD_FALLBACK_MODELS = [
    "google/gemini-2.5-flash",      # OpenRouter, free
    "llama-3.1-8b-instant",         # Groq, free
    "llama-3.3-70b-versatile",      # Groq, free
]

# Local models ordered by size (smallest first for RAM conservation)
LOCAL_MODEL_ORDER = [
    "gemma3:1b",                    # 815MB - lightest
    "qwen2.5-coder:1.5b",          # 986MB - small coder
    "llama3.2:1b",                  # 1.3GB - small general
    "phi3:mini",                    # 2.2GB - logic specialist
    "qwen2.5:3b",                   # 1.9GB - best local coding+Hindi
]

# State
_current_model = None
_swap_callback: Optional[Callable] = None
_monitor_thread: Optional[threading.Thread] = None
_running = False
_last_swap_time = 0
_swap_cooldown = 30  # seconds between swaps


def get_ram_info() -> dict:
    """Get current RAM status."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
            "swap_percent": swap.percent if swap else 0,
            "status": _ram_status(mem.percent),
        }
    except ImportError:
        return {
            "total_gb": 0,
            "available_gb": 0,
            "used_gb": 0,
            "percent": 0,
            "swap_percent": 0,
            "status": "unknown (psutil not installed)",
        }


def _ram_status(pct: float) -> str:
    if pct >= RAM_KILL_PCT:
        return "CRITICAL"
    elif pct >= RAM_SWAP_PCT:
        return "HIGH — swap to cloud"
    elif pct >= RAM_WARN_PCT:
        return "WARNING"
    return "OK"


def should_swap_to_cloud() -> bool:
    """Check if we should swap to cloud model."""
    info = get_ram_info()
    return info["percent"] >= RAM_SWAP_PCT


def get_cloud_model() -> str:
    """Get next available cloud fallback model."""
    for model in CLOUD_FALLBACK_MODELS:
        if "groq" in model.lower() or "gemini" in model.lower():
            return model
    return CLOUD_FALLBACK_MODELS[0]


def swap_model(new_model: str, reason: str = ""):
    """Swap the active model to a cloud fallback."""
    global _current_model, _last_swap_time

    now = time.time()
    if now - _last_swap_time < _swap_cooldown:
        logger.debug("[RAM] Swap cooldown active, skipping")
        return

    old_model = _current_model
    _current_model = new_model
    _last_swap_time = now

    logger.warning(f"[RAM] SWAPPED model: {old_model} → {new_model} ({reason})")

    if _swap_callback:
        try:
            _swap_callback(old_model, new_model, reason)
        except Exception as e:
            logger.error(f"[RAM] Swap callback error: {e}")


def on_swap(callback: Callable):
    """Register callback for model swaps: callback(old_model, new_model, reason)."""
    global _swap_callback
    _swap_callback = callback


def check_and_swap() -> dict:
    """
    Check RAM and swap if needed.
    Returns swap status.
    """
    info = get_ram_info()
    pct = info["percent"]

    if pct >= RAM_KILL_PCT:
        cloud = get_cloud_model()
        swap_model(cloud, f"RAM CRITICAL ({pct:.0f}%)")
        # Also unload STT model to free memory
        try:
            from stt_engine import unload as stt_unload
            stt_unload()
            logger.warning("[RAM] Unloaded STT model to free memory")
        except ImportError:
            pass
        return {"swapped": True, "reason": "critical", "ram_pct": pct}

    elif pct >= RAM_SWAP_PCT:
        cloud = get_cloud_model()
        swap_model(cloud, f"RAM HIGH ({pct:.0f}%)")
        return {"swapped": True, "reason": "high", "ram_pct": pct}

    return {"swapped": False, "reason": "ok", "ram_pct": pct}


def start_monitor(interval_sec: float = 5.0):
    """Start background RAM monitor thread."""
    global _running, _monitor_thread

    if _running:
        return

    _running = True

    def _monitor_loop():
        while _running:
            try:
                info = get_ram_info()
                pct = info["percent"]

                if pct >= RAM_KILL_PCT:
                    logger.critical(f"[RAM] CRITICAL: {pct:.0f}% — swapping to cloud")
                    check_and_swap()
                elif pct >= RAM_SWAP_PCT:
                    logger.warning(f"[RAM] HIGH: {pct:.0f}% — may swap to cloud")
                    check_and_swap()
                elif pct >= RAM_WARN_PCT:
                    logger.info(f"[RAM] WARNING: {pct:.0f}%")
            except Exception as e:
                logger.error(f"[RAM] Monitor error: {e}")

            time.sleep(interval_sec)

    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()
    logger.info(f"[RAM] Monitor started (interval={interval_sec}s, swap={RAM_SWAP_PCT}%)")


def stop_monitor():
    """Stop background RAM monitor."""
    global _running
    _running = False
    logger.info("[RAM] Monitor stopped")


def get_status() -> dict:
    """Full status for API endpoint."""
    info = get_ram_info()
    return {
        "ram": info,
        "thresholds": {
            "warn_pct": RAM_WARN_PCT,
            "swap_pct": RAM_SWAP_PCT,
            "kill_pct": RAM_KILL_PCT,
        },
        "current_model": _current_model,
        "cloud_fallback": get_cloud_model(),
        "monitoring": _running,
    }
