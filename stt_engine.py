"""
STT Engine — Faster-Whisper local speech-to-text
Falls back to cloud if RAM > 90%
"""
import os
import time
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("stt_engine")

# Model sizes: tiny < base < small < medium < large-v3
# For 12GB RAM CPU-only: base is optimal (~300MB RAM, fast)
DEFAULT_MODEL = os.getenv("STT_MODEL", "base")
WHISPER_MODEL = None


def _get_ram_usage() -> float:
    """Return current RAM usage as percentage (0-100)."""
    try:
        import psutil
        return psutil.virtual_memory().percent
    except ImportError:
        return 0.0


def _load_model(model_size: str = None):
    """Lazy-load faster-whisper model."""
    global WHISPER_MODEL
    if WHISPER_MODEL is not None:
        return WHISPER_MODEL

    model_size = model_size or DEFAULT_MODEL
    logger.info(f"[STT] Loading faster-whisper model: {model_size}")

    try:
        from faster_whisper import WhisperModel
        # CPU-optimized settings
        WHISPER_MODEL = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",  # int8 for CPU efficiency
            cpu_threads=4,
        )
        logger.info(f"[STT] Model loaded: {model_size}")
        return WHISPER_MODEL
    except Exception as e:
        logger.error(f"[STT] Failed to load model: {e}")
        return None


def transcribe_file(file_path: str, language: str = "en") -> dict:
    """
    Transcribe an audio file to text.

    Returns:
        {
            "success": bool,
            "text": str,
            "language": str,
            "duration_sec": float,
            "processing_time_sec": float,
            "model": str,
            "ram_usage_pct": float,
            "error": str | None
        }
    """
    ram = _get_ram_usage()
    if ram > 90:
        return {
            "success": False,
            "text": "",
            "language": language,
            "duration_sec": 0,
            "processing_time_sec": 0,
            "model": DEFAULT_MODEL,
            "ram_usage_pct": ram,
            "error": f"RAM too high ({ram:.0f}%). Use cloud STT instead."
        }

    model = _load_model()
    if model is None:
        return {
            "success": False,
            "text": "",
            "language": language,
            "duration_sec": 0,
            "processing_time_sec": 0,
            "model": DEFAULT_MODEL,
            "ram_usage_pct": ram,
            "error": "Failed to load whisper model"
        }

    start = time.time()
    try:
        segments, info = model.transcribe(
            file_path,
            language=language if language != "auto" else None,
            beam_size=3,
            vad_filter=True,  # Voice Activity Detection for speed
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )

        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        full_text = " ".join(text_parts)
        elapsed = time.time() - start

        return {
            "success": True,
            "text": full_text,
            "language": info.language,
            "duration_sec": info.duration,
            "processing_time_sec": round(elapsed, 2),
            "model": DEFAULT_MODEL,
            "ram_usage_pct": _get_ram_usage(),
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "language": language,
            "duration_sec": 0,
            "processing_time_sec": round(time.time() - start, 2),
            "model": DEFAULT_MODEL,
            "ram_usage_pct": _get_ram_usage(),
            "error": str(e)
        }


def transcribe_bytes(audio_bytes: bytes, filename: str = "audio.wav",
                     language: str = "en") -> dict:
    """Transcribe raw audio bytes."""
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix or ".wav",
                                     delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        return transcribe_file(tmp_path, language)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def unload():
    """Free memory by unloading the model."""
    global WHISPER_MODEL
    WHISPER_MODEL = None
    logger.info("[STT] Model unloaded")
