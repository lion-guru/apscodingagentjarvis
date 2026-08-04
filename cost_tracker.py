"""
DevMind Token Cost & Model Usage Tracker
Inspired by Claude Code's cost-tracker.ts & costHook.ts
Tracks input/output tokens and estimates costs across LLM providers.
"""
import os
import json
from datetime import datetime
from master_db import record_token_usage, get_token_summary

# Pricing per million tokens (USD)
MODEL_PRICING = {
    # Free / Local models (Cost $0.00)
    "gemini-2.0-flash": {"input": 0.0, "output": 0.0},
    "gemini-2.5-flash": {"input": 0.0, "output": 0.0},
    "gemini-2.5-pro":   {"input": 0.0, "output": 0.0},
    "llama-3.3-70b-versatile": {"input": 0.0, "output": 0.0},
    "llama-3.1-8b-instant":    {"input": 0.0, "output": 0.0},
    "llama3.2:3b":      {"input": 0.0, "output": 0.0},
    "qwen2.5-coder:7b": {"input": 0.0, "output": 0.0},
    # Commercial fallbacks (for cost estimation)
    "gpt-4o":          {"input": 2.50, "output": 10.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
}


class CostTracker:
    def __init__(self):
        self.session_input_tokens = 0
        self.session_output_tokens = 0

    def track(self, model: str, input_tokens: int, output_tokens: int) -> dict:
        """Track LLM invocation token usage and save to master DB."""
        pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
        cost = (input_tokens / 1_000_000 * pricing["input"]) + (output_tokens / 1_000_000 * pricing["output"])
        
        self.session_input_tokens += input_tokens
        self.session_output_tokens += output_tokens
        
        record_token_usage(model, input_tokens, output_tokens, cost)
        
        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": round(cost, 6),
            "session_total_tokens": self.session_input_tokens + self.session_output_tokens
        }

    @staticmethod
    def get_summary() -> dict:
        """Return total system token usage summary."""
        summary = get_token_summary()
        summary["saved_vs_openai"] = round(summary.get("total_tokens", 0) / 1_000_000 * 5.0, 2)  # Avg $5/M saved using free models
        return summary


# Global singleton instance
tracker = CostTracker()
