"""
Ollama Client - Lightweight HTTP client for Ollama API.

Uses only Python standard library (urllib) - no external dependencies.
Communicates with local Ollama server for AI reasoning tasks.

Usage:
    client = OllamaClient({'base_url': 'http://localhost:11434', 'model': 'qwen2.5:7b'})
    if client.is_available():
        response = client.generate("Fix this PHP code: ...")
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class OllamaClient:
    """Lightweight Ollama API client using stdlib only."""

    def __init__(self, config: dict):
        if 'base_url' in config:
            self.base_url = config['base_url']
        else:
            self.host = config.get('host', 'localhost')
            self.port = config.get('port', 11434)
            self.base_url = f"http://{self.host}:{self.port}"
        self.model = config.get('model', 'qwen2.5:7b')
        self.timeout = config.get('timeout_ms', 30000) / 1000.0

    def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, system: str = '', max_tokens: int = 4096) -> str:
        """
        Generate a response from Ollama.

        Args:
            prompt: The user prompt
            system: System prompt for context
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.7,
                'num_predict': max_tokens
            }
        }

        if system:
            payload['system'] = system

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result.get('response', '')
        except Exception as e:
            return f"[Ollama error: {e}]"

    def chat(self, messages: list) -> str:
        """
        Chat completion with message history.

        Args:
            messages: List of {"role": "user"/"assistant"/"system", "content": "..."}

        Returns:
            Assistant response text
        """
        payload = {
            'model': self.model,
            'messages': messages,
            'stream': False,
            'options': {
                'temperature': 0.7
            }
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                msg = result.get('message', {})
                return msg.get('content', '')
        except Exception as e:
            return f"[Ollama error: {e}]"
