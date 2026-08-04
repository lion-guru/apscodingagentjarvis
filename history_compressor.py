"""
DevMind History & Trajectory Compressor Engine
Derived from Hermes Trajectory Compression Strategy.
Compresses long agent conversation histories within target token limits while preserving
system prompts, initial user instructions, and recent active turns.
"""

from typing import List, Dict, Any, Optional

def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars ~ 1 token)."""
    return len(str(text)) // 4

def compress_conversation_history(
    messages: List[Dict[str, Any]],
    target_max_tokens: int = 8000,
    protect_last_n_turns: int = 4
) -> List[Dict[str, Any]]:
    """
    Compresses conversation history to stay under target_max_tokens.
    Strategy:
      1. Protect system prompt and first user turn (System & Intent)
      2. Protect last N turns (Recent Context)
      3. Summarize / prune middle turns if total token count exceeds target
    """
    total_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
    if total_tokens <= target_max_tokens or len(messages) <= (2 + protect_last_n_turns):
        return messages

    # Split into protected head, middle, and protected tail
    head = messages[:2]  # System prompt + initial user request
    tail = messages[-protect_last_n_turns:]  # Last N turns
    middle = messages[2:-protect_last_n_turns]

    if not middle:
        return messages

    # Estimate middle tokens
    middle_tokens = sum(estimate_tokens(m.get("content", "")) for m in middle)
    compressed_summary = (
        f"[Context Compressed: {len(middle)} intermediate tool/chat execution turns "
        f"({middle_tokens} tokens) compressed to preserve memory and token budget.]"
    )

    summary_message = {
        "role": "system",
        "content": compressed_summary
    }

    compressed_history = head + [summary_message] + tail
    return compressed_history
