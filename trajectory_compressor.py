"""
DevMind Trajectory Compressor — Hermes-Grade, Zero External Dependencies

Full LLM-assisted trajectory compression ported from hermes-runtime/trajectory_compressor.py
but with ZERO hermes dependencies. Uses httpx for LLM calls, char-based token estimation,
and the same protected-head / protected-tail / compress-middle algorithm.

Strategy:
  1. Protect first turns: system, first human, first assistant, first tool
  2. Protect last N turns (recent context)
  3. Compress MIDDLE turns: accumulate from start of compressible region until savings met
  4. Replace compressed turns with a single LLM-generated summary
  5. Snap boundaries to avoid orphaned tool_call / <tool_call> pairs
  6. Track detailed compression metrics
"""

import os
import time
import json
import asyncio
import httpx
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class CompressionConfig:
    target_max_tokens: int = 8000
    summary_target_tokens: int = 500
    protect_first_system: bool = True
    protect_first_human: bool = True
    protect_first_assistant: bool = True
    protect_first_tool: bool = True
    protect_last_n_turns: int = 4
    summarization_model: str = "gemini-2.5-flash"
    temperature: float = 0.3
    max_retries: int = 3
    retry_delay: int = 2
    summary_notice: bool = True
    summary_notice_text: str = (
        "\n\n[Some previous turns were compressed to preserve context. "
        "Key information has been summarized below.]"
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class CompressionMetrics:
    original_tokens: int = 0
    compressed_tokens: int = 0
    tokens_saved: int = 0
    compression_ratio: float = 1.0
    original_turns: int = 0
    compressed_turns: int = 0
    turns_removed: int = 0
    compress_start: int = -1
    compress_end: int = -1
    turns_in_region: int = 0
    was_compressed: bool = False
    skipped_under_target: bool = False
    still_over_limit: bool = False
    api_calls: int = 0
    api_errors: int = 0
    summary_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "tokens_saved": self.tokens_saved,
            "compression_ratio": round(self.compression_ratio, 4),
            "original_turns": self.original_turns,
            "compressed_turns": self.compressed_turns,
            "turns_removed": self.turns_removed,
            "compression_region": {
                "start": self.compress_start,
                "end": self.compress_end,
                "count": self.turns_in_region,
            },
            "was_compressed": self.was_compressed,
            "skipped_under_target": self.skipped_under_target,
            "still_over_limit": self.still_over_limit,
            "api_calls": self.api_calls,
            "api_errors": self.api_errors,
        }


# ---------------------------------------------------------------------------
# Token estimation (no transformers dependency)
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Estimate token count. ~4 chars per token for English, ~2 for CJK-heavy text."""
    if not text:
        return 0
    # Rough heuristic: 1 token ≈ 4 chars (works well for code + English)
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# LLM Summarization (httpx only, no openai dependency)
# ---------------------------------------------------------------------------

def _call_llm_sync(
    messages: List[Dict[str, str]],
    model: str = "gemini-2.5-flash",
    max_tokens: int = 1000,
    temperature: float = 0.3,
) -> str:
    """Call an LLM for summarization via Gemini or Groq API directly with httpx."""
    # Try Gemini first
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
            contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in messages]
            payload = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}}
            resp = httpx.post(url, json=payload, timeout=30.0)
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            pass

    # Fallback: Groq
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        try:
            headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            payload = {"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
            resp = httpx.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    # Fallback: OpenRouter
    or_key = os.getenv("OPENROUTER_API_KEY", "")
    if or_key:
        try:
            headers = {"Authorization": f"Bearer {or_key}", "Content-Type": "application/json"}
            payload = {"model": "google/gemma-2-9b-it:free", "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
            resp = httpx.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    return ""


async def _call_llm_async(
    messages: List[Dict[str, str]],
    model: str = "gemini-2.5-flash",
    max_tokens: int = 1000,
    temperature: float = 0.3,
) -> str:
    """Async version of _call_llm_sync."""
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
            contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in messages]
            payload = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}}
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            pass

    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        try:
            headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            payload = {"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    return ""


# ---------------------------------------------------------------------------
# Boundary helpers (avoid orphaned <tool_call> / <tool_response> pairs)
# ---------------------------------------------------------------------------

def _is_boundary_clean(trajectory: List[Dict[str, Any]], idx: int) -> bool:
    """True if index is at end or the turn is NOT a tool response."""
    return idx >= len(trajectory) or trajectory[idx].get("role") != "tool"


def _snap_boundary(
    trajectory: List[Dict[str, Any]], idx: int, min_idx: int, max_idx: int
) -> int:
    """Move boundary to nearest clean position (forward preferred)."""
    forward = idx
    while forward < max_idx and not _is_boundary_clean(trajectory, forward):
        forward += 1
    if _is_boundary_clean(trajectory, forward):
        return forward
    backward = idx
    while backward > min_idx and not _is_boundary_clean(trajectory, backward):
        backward -= 1
    return backward


# ---------------------------------------------------------------------------
# Protected turn finder
# ---------------------------------------------------------------------------

def _find_protected(
    trajectory: List[Dict[str, Any]], config: CompressionConfig
) -> Tuple[set, int, int]:
    """Find protected indices and compressible region bounds."""
    n = len(trajectory)
    protected = set()
    first_system = first_human = first_assistant = first_tool = None

    for i, turn in enumerate(trajectory):
        role = turn.get("role", "")
        if role == "system" and first_system is None:
            first_system = i
        elif role == "user" and first_human is None:
            first_human = i
        elif role == "assistant" and first_assistant is None:
            first_assistant = i
        elif role == "tool" and first_tool is None:
            first_tool = i

    if config.protect_first_system and first_system is not None:
        protected.add(first_system)
    if config.protect_first_human and first_human is not None:
        protected.add(first_human)
    if config.protect_first_assistant and first_assistant is not None:
        protected.add(first_assistant)
    if config.protect_first_tool and first_tool is not None:
        protected.add(first_tool)

    for i in range(max(0, n - config.protect_last_n_turns), n):
        protected.add(i)

    head_protected = sorted(i for i in protected if i < n // 2)
    tail_protected = sorted(i for i in protected if i >= n // 2)

    compress_start = (max(head_protected) + 1) if head_protected else 0
    compress_end = min(tail_protected) if tail_protected else n

    return protected, compress_start, compress_end


# ---------------------------------------------------------------------------
# Summarization prompt
# ---------------------------------------------------------------------------

SUMMARY_PROMPT = """Summarize the following agent conversation turns concisely. This summary will replace these turns in the conversation history.

Write the summary from a neutral perspective describing what the assistant did and learned. Include:
1. What actions the assistant took (tool calls, searches, file operations)
2. Key information or results obtained
3. Any important decisions or findings
4. Relevant data, file names, values, or outputs

Keep the summary factual and informative. Target approximately {target_tokens} tokens.

---
TURNS TO SUMMARIZE:
{content}
---

Write only the summary, starting with "[CONTEXT SUMMARY]:" prefix."""


def _extract_content(
    trajectory: List[Dict[str, Any]], start: int, end: int
) -> str:
    """Extract turn content for summarization."""
    parts = []
    for i in range(start, end):
        turn = trajectory[i]
        role = turn.get("role", "unknown")
        content = turn.get("content", "")
        if len(content) > 3000:
            content = content[:1500] + "\n...[truncated]...\n" + content[-500:]
        parts.append(f"[Turn {i} - {role.upper()}]:\n{content}")
    return "\n\n".join(parts)


def _generate_summary(
    content: str, config: CompressionConfig, metrics: CompressionMetrics
) -> str:
    """Generate LLM summary with retries."""
    prompt = SUMMARY_PROMPT.format(
        target_tokens=config.summary_target_tokens, content=content
    )
    messages = [{"role": "user", "content": prompt}]

    for attempt in range(config.max_retries):
        try:
            metrics.api_calls += 1
            result = _call_llm_sync(
                messages,
                model=config.summarization_model,
                max_tokens=config.summary_target_tokens * 2,
                temperature=config.temperature,
            )
            if result:
                text = result.strip()
                if not text.startswith("[CONTEXT SUMMARY]:"):
                    text = f"[CONTEXT SUMMARY]: {text}"
                return text
        except Exception:
            metrics.api_errors += 1
            if attempt < config.max_retries - 1:
                time.sleep(config.retry_delay * (attempt + 1))

    return (
        "[CONTEXT SUMMARY]: [Summary generation failed — "
        "previous turns compressed to save context space.]"
    )


async def _generate_summary_async(
    content: str, config: CompressionConfig, metrics: CompressionMetrics
) -> str:
    """Async version of _generate_summary."""
    prompt = SUMMARY_PROMPT.format(
        target_tokens=config.summary_target_tokens, content=content
    )
    messages = [{"role": "user", "content": prompt}]

    for attempt in range(config.max_retries):
        try:
            metrics.api_calls += 1
            result = await _call_llm_async(
                messages,
                model=config.summarization_model,
                max_tokens=config.summary_target_tokens * 2,
                temperature=config.temperature,
            )
            if result:
                text = result.strip()
                if not text.startswith("[CONTEXT SUMMARY]:"):
                    text = f"[CONTEXT SUMMARY]: {text}"
                return text
        except Exception:
            metrics.api_errors += 1
            if attempt < config.max_retries - 1:
                await asyncio.sleep(config.retry_delay * (attempt + 1))

    return (
        "[CONTEXT SUMMARY]: [Summary generation failed — "
        "previous turns compressed to save context space.]"
    )


# ---------------------------------------------------------------------------
# Core compression (sync)
# ---------------------------------------------------------------------------

def compress_trajectory(
    trajectory: List[Dict[str, Any]],
    config: Optional[CompressionConfig] = None,
) -> Tuple[List[Dict[str, Any]], CompressionMetrics]:
    """
    Compress a trajectory to fit within target token budget.

    Same algorithm as hermes-runtime TrajectoryCompressor.compress_trajectory()
    but zero external dependencies.

    Args:
        trajectory: List of {"role": ..., "content": ...} messages
        config: Compression configuration

    Returns:
        (compressed_trajectory, metrics)
    """
    if config is None:
        config = CompressionConfig()

    metrics = CompressionMetrics()
    metrics.original_turns = len(trajectory)

    turn_tokens = [estimate_tokens(t.get("content", "")) for t in trajectory]
    total_tokens = sum(turn_tokens)
    metrics.original_tokens = total_tokens

    # Skip if already under target
    if total_tokens <= config.target_max_tokens:
        metrics.skipped_under_target = True
        metrics.compressed_tokens = total_tokens
        metrics.compressed_turns = len(trajectory)
        metrics.compression_ratio = 1.0
        return trajectory, metrics

    # Find protected regions
    protected, compress_start, compress_end = _find_protected(trajectory, config)
    compress_start = _snap_boundary(trajectory, compress_start, compress_start, compress_end)

    if compress_start >= compress_end:
        metrics.compressed_tokens = total_tokens
        metrics.compressed_turns = len(trajectory)
        metrics.still_over_limit = True
        return trajectory, metrics

    # Calculate savings needed
    tokens_to_save = total_tokens - config.target_max_tokens
    target_compress_tokens = tokens_to_save + config.summary_target_tokens

    # Accumulate turns until savings met
    accumulated = 0
    compress_until = compress_start
    for i in range(compress_start, compress_end):
        accumulated += turn_tokens[i]
        compress_until = i + 1
        if accumulated >= target_compress_tokens:
            break

    if accumulated < target_compress_tokens and compress_until < compress_end:
        compress_until = compress_end
        accumulated = sum(turn_tokens[compress_start:compress_end])

    compress_until = _snap_boundary(trajectory, compress_until, compress_start, compress_end)
    if compress_until <= compress_start:
        metrics.compressed_tokens = total_tokens
        metrics.compressed_turns = len(trajectory)
        metrics.still_over_limit = True
        return trajectory, metrics

    metrics.compress_start = compress_start
    metrics.compress_end = compress_until
    metrics.turns_in_region = compress_until - compress_start

    # Extract and summarize
    content = _extract_content(trajectory, compress_start, compress_until)
    summary = _generate_summary(content, config, metrics)
    metrics.summary_text = summary

    # Build compressed trajectory
    compressed = []
    for i in range(compress_start):
        turn = trajectory[i].copy()
        if turn.get("role") == "system" and config.summary_notice:
            turn["content"] = turn["content"] + config.summary_notice_text
        compressed.append(turn)

    compressed.append({"role": "user", "content": summary})

    for i in range(compress_until, len(trajectory)):
        compressed.append(trajectory[i].copy())

    metrics.compressed_turns = len(compressed)
    metrics.compressed_tokens = sum(estimate_tokens(t.get("content", "")) for t in compressed)
    metrics.turns_removed = metrics.original_turns - metrics.compressed_turns
    metrics.tokens_saved = metrics.original_tokens - metrics.compressed_tokens
    metrics.compression_ratio = metrics.compressed_tokens / max(metrics.original_tokens, 1)
    metrics.was_compressed = True
    metrics.still_over_limit = metrics.compressed_tokens > config.target_max_tokens

    return compressed, metrics


# ---------------------------------------------------------------------------
# Core compression (async)
# ---------------------------------------------------------------------------

async def compress_trajectory_async(
    trajectory: List[Dict[str, Any]],
    config: Optional[CompressionConfig] = None,
) -> Tuple[List[Dict[str, Any]], CompressionMetrics]:
    """Async version of compress_trajectory."""
    if config is None:
        config = CompressionConfig()

    metrics = CompressionMetrics()
    metrics.original_turns = len(trajectory)

    turn_tokens = [estimate_tokens(t.get("content", "")) for t in trajectory]
    total_tokens = sum(turn_tokens)
    metrics.original_tokens = total_tokens

    if total_tokens <= config.target_max_tokens:
        metrics.skipped_under_target = True
        metrics.compressed_tokens = total_tokens
        metrics.compressed_turns = len(trajectory)
        metrics.compression_ratio = 1.0
        return trajectory, metrics

    protected, compress_start, compress_end = _find_protected(trajectory, config)
    compress_start = _snap_boundary(trajectory, compress_start, compress_start, compress_end)

    if compress_start >= compress_end:
        metrics.compressed_tokens = total_tokens
        metrics.compressed_turns = len(trajectory)
        metrics.still_over_limit = True
        return trajectory, metrics

    tokens_to_save = total_tokens - config.target_max_tokens
    target_compress_tokens = tokens_to_save + config.summary_target_tokens

    accumulated = 0
    compress_until = compress_start
    for i in range(compress_start, compress_end):
        accumulated += turn_tokens[i]
        compress_until = i + 1
        if accumulated >= target_compress_tokens:
            break

    if accumulated < target_compress_tokens and compress_until < compress_end:
        compress_until = compress_end
        accumulated = sum(turn_tokens[compress_start:compress_end])

    compress_until = _snap_boundary(trajectory, compress_until, compress_start, compress_end)
    if compress_until <= compress_start:
        metrics.compressed_tokens = total_tokens
        metrics.compressed_turns = len(trajectory)
        metrics.still_over_limit = True
        return trajectory, metrics

    metrics.compress_start = compress_start
    metrics.compress_end = compress_until
    metrics.turns_in_region = compress_until - compress_start

    content = _extract_content(trajectory, compress_start, compress_until)
    summary = await _generate_summary_async(content, config, metrics)
    metrics.summary_text = summary

    compressed = []
    for i in range(compress_start):
        turn = trajectory[i].copy()
        if turn.get("role") == "system" and config.summary_notice:
            turn["content"] = turn["content"] + config.summary_notice_text
        compressed.append(turn)

    compressed.append({"role": "user", "content": summary})

    for i in range(compress_until, len(trajectory)):
        compressed.append(trajectory[i].copy())

    metrics.compressed_turns = len(compressed)
    metrics.compressed_tokens = sum(estimate_tokens(t.get("content", "")) for t in compressed)
    metrics.turns_removed = metrics.original_turns - metrics.compressed_turns
    metrics.tokens_saved = metrics.original_tokens - metrics.compressed_tokens
    metrics.compression_ratio = metrics.compressed_tokens / max(metrics.original_tokens, 1)
    metrics.was_compressed = True
    metrics.still_over_limit = metrics.compressed_tokens > config.target_max_tokens

    return compressed, metrics


# ---------------------------------------------------------------------------
# High-level API (backward compatible with old history_compressor interface)
# ---------------------------------------------------------------------------

def compress_conversation_history(
    messages: List[Dict[str, Any]],
    target_max_tokens: int = 8000,
    protect_last_n_turns: int = 4,
) -> List[Dict[str, Any]]:
    """
    Drop-in replacement for old history_compressor.compress_conversation_history().
    Uses hermes-grade compression under the hood.
    """
    config = CompressionConfig(
        target_max_tokens=target_max_tokens,
        protect_last_n_turns=protect_last_n_turns,
    )
    compressed, _ = compress_trajectory(messages, config)
    return compressed


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Demo: compress a sample trajectory
    sample = [
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": "Write a Python function to sort a list."},
        {"role": "assistant", "content": "Here's a sort function:\n```python\ndef sort_list(lst):\n    return sorted(lst)\n```"},
        {"role": "user", "content": "Now add error handling."},
        {"role": "assistant", "content": "Added try/except blocks and type validation."},
        {"role": "user", "content": "Write tests for it."},
        {"role": "assistant", "content": "Created test_sort.py with 5 test cases covering edge cases."},
        {"role": "user", "content": "Run the tests."},
        {"role": "assistant", "content": "All 5 tests passed. Coverage: 94%."},
        {"role": "user", "content": "Deploy to production."},
        {"role": "assistant", "content": "Deployed successfully to production environment."},
    ]

    config = CompressionConfig(target_max_tokens=200)
    compressed, metrics = compress_trajectory(sample, config)

    print(f"Original: {metrics.original_tokens} tokens, {metrics.original_turns} turns")
    print(f"Compressed: {metrics.compressed_tokens} tokens, {metrics.compressed_turns} turns")
    print(f"Saved: {metrics.tokens_saved} tokens, ratio: {metrics.compression_ratio:.2%}")
    print(f"Compressed region: turns {metrics.compress_start}-{metrics.compress_end}")
    print(f"\nCompressed trajectory:")
    for i, turn in enumerate(compressed):
        content = turn["content"][:100] + "..." if len(turn["content"]) > 100 else turn["content"]
        print(f"  [{i}] {turn['role']}: {content}")
