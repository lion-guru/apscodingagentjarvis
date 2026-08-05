"""
TTS Engine — Edge-TTS (Microsoft, free) + pyttsx3 (offline fallback)
Auto-selects engine based on RAM usage and availability.
"""
import os
import time
import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("tts_engine")

# Edge-TTS voices (free, high quality, many languages)
DEFAULT_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")
FALLBACK_VOICE = "en-US-GuyNeural"

# Agent-specific voice mapping (12 agents)
AGENT_VOICES = {
    "planner":    "en-US-AriaNeural",
    "coder":      "en-US-GuyNeural",
    "reviewer":   "en-US-ChristopherNeural",
    "researcher": "en-US-SaraNeural",
    "healer":     "en-US-DavisNeural",
    "architect":  "en-US-TonyNeural",
    "deployer":   "en-US-JasonNeural",
    "monitor":    "en-US-DavisNeural",
    "memory":     "en-US-SaraNeural",
    "test_runner":"en-US-AvaNeural",
    "linter":     "en-US-ChristopherNeural",
    "inspector":  "en-US-JasonNeural",
}

# Agent personality params
AGENT_RATE_PITCH = {
    "planner":    {"rate": "+0%", "pitch": "+0Hz"},
    "coder":      {"rate": "+5%", "pitch": "-2Hz"},
    "reviewer":   {"rate": "-5%", "pitch": "+0Hz"},
    "researcher": {"rate": "+0%", "pitch": "+2Hz"},
    "healer":     {"rate": "+10%", "pitch": "-1Hz"},
    "architect":  {"rate": "-5%", "pitch": "-3Hz"},
    "deployer":   {"rate": "+10%", "pitch": "+0Hz"},
    "monitor":    {"rate": "+0%", "pitch": "-1Hz"},
    "memory":     {"rate": "-10%", "pitch": "+1Hz"},
    "test_runner":{"rate": "+15%", "pitch": "+0Hz"},
    "linter":     {"rate": "+5%", "pitch": "+0Hz"},
    "inspector":  {"rate": "+0%", "pitch": "+2Hz"},
}


def _get_ram_usage() -> float:
    """Current RAM usage as percentage."""
    try:
        import psutil
        return psutil.virtual_memory().percent
    except ImportError:
        return 0.0


def _get_edge_voice(agent: str = None) -> str:
    """Get voice name for agent or default."""
    if agent and agent in AGENT_VOICES:
        return AGENT_VOICES[agent]
    return DEFAULT_VOICE


def _get_edge_params(agent: str = None) -> dict:
    """Get rate/pitch params for agent."""
    if agent and agent in AGENT_RATE_PITCH:
        return AGENT_RATE_PITCH[agent]
    return {"rate": "+0%", "pitch": "+0Hz"}


async def _edge_tts_generate(text: str, voice: str, output_path: str,
                              rate: str = "+0%", pitch: str = "+0Hz"):
    """Generate speech using edge-tts (async)."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


def synthesize_edge(text: str, output_path: str = None,
                    voice: str = None, agent: str = None,
                    rate: str = None, pitch: str = None) -> dict:
    """
    Synthesize text to speech using Edge-TTS (Microsoft, free).
    Returns path to generated audio file.
    """
    voice = voice or _get_edge_voice(agent)
    params = _get_edge_params(agent)
    rate = rate or params["rate"]
    pitch = pitch or params["pitch"]

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        output_path = tmp.name
        tmp.close()

    start = time.time()
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(
            _edge_tts_generate(text, voice, output_path, rate, pitch)
        )
        loop.close()

        elapsed = time.time() - start
        logger.info(f"[TTS] Edge-TTS generated in {elapsed:.2f}s -> {output_path}")

        return {
            "success": True,
            "path": output_path,
            "engine": "edge-tts",
            "voice": voice,
            "processing_time_sec": round(elapsed, 2),
            "ram_usage_pct": _get_ram_usage(),
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "path": None,
            "engine": "edge-tts",
            "voice": voice,
            "processing_time_sec": round(time.time() - start, 2),
            "ram_usage_pct": _get_ram_usage(),
            "error": str(e)
        }


def synthesize_offline(text: str, output_path: str = None) -> dict:
    """
    Synthesize text using pyttsx3 (offline, Windows SAPI).
    Used as fallback when edge-tts fails or RAM is high.
    """
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        engine.setProperty('volume', 1.0)

        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            output_path = tmp.name
            tmp.close()

        start = time.time()
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        elapsed = time.time() - start

        return {
            "success": True,
            "path": output_path,
            "engine": "pyttsx3",
            "voice": "windows-sapi",
            "processing_time_sec": round(elapsed, 2),
            "ram_usage_pct": _get_ram_usage(),
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "path": None,
            "engine": "pyttsx3",
            "voice": "windows-sapi",
            "processing_time_sec": 0,
            "ram_usage_pct": _get_ram_usage(),
            "error": str(e)
        }


def synthesize(text: str, output_path: str = None,
               voice: str = None, agent: str = None,
               engine: str = "auto") -> dict:
    """
    Main TTS API. Auto-selects engine based on RAM.

    engine: "auto" | "edge" | "offline"
    """
    ram = _get_ram_usage()

    if ram > 90:
        logger.warning(f"[TTS] RAM high ({ram:.0f}%), using offline engine")
        return synthesize_offline(text, output_path)

    if engine == "offline":
        return synthesize_offline(text, output_path)

    if engine in ("auto", "edge"):
        result = synthesize_edge(text, output_path, voice, agent)
        if result["success"]:
            return result
        # Fallback to offline
        logger.warning("[TTS] Edge-TTS failed, falling back to offline")
        return synthesize_offline(text, output_path)

    return synthesize_offline(text, output_path)


def list_voices() -> list:
    """List available edge-tts voices."""
    try:
        import edge_tts
        loop = asyncio.new_event_loop()
        voices = loop.run_until_complete(edge_tts.list_voices())
        loop.close()
        return [{"name": v["ShortName"], "gender": v["Gender"],
                 "locale": v["Locale"]} for v in voices[:50]]
    except Exception:
        return [{"name": v, "gender": "unknown", "locale": "en-US"}
                for v in AGENT_VOICES.values()]
