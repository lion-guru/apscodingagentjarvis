"""
DevMind History Compressor — Backward-compatible wrapper.

The real implementation is now in trajectory_compressor.py (hermes-grade,
zero external dependencies). This module re-exports the API for backward
compatibility with existing imports.
"""

from trajectory_compressor import (
    compress_conversation_history,
    compress_trajectory,
    CompressionConfig,
    CompressionMetrics,
    estimate_tokens,
)

__all__ = [
    "compress_conversation_history",
    "compress_trajectory",
    "CompressionConfig",
    "CompressionMetrics",
    "estimate_tokens",
]
