"""
DevMind IDE Bridge
Cursor/Windsurf/OpenCode integration, config generation, and cross-IDE plugin bridge.
"""
import json
from pathlib import Path
from datetime import datetime

BRIDGE_DIR = Path.home() / ".devmind" / "bridges"

class IDEBridge:
    def __init__(self):
        BRIDGE_DIR.mkdir(parents=True, exist_ok=True)

    def generate_cursor_config(self, workspace: str = "E:\\coding-assistant") -> dict:
        """Generate .cursor/rules/ configuration for Cursor IDE."""
        rules = {
            "rules": [
                {
                    "name": "devmind-integration",
                    "description": "DevMind AI IDE integration rules",
                    "content": (
                        "When working in this workspace, use DevMind for AI-assisted coding.\n"
                        "Default model: gemma3:1b (local Ollama)\n"
                        "Fallback: OpenCode Zen (free cloud)\n"
                        "Last resort: OpenRouter/Groq (paid)\n"
                        "Always prefer local models for privacy and cost savings."
                    ),
                }
            ]
        }

        cursor_dir = Path(workspace) / ".cursor" / "rules"
        cursor_dir.mkdir(parents=True, exist_ok=True)
        config_file = cursor_dir / "devmind-rules.json"
        config_file.write_text(json.dumps(rules, indent=2), encoding="utf-8")

        bridge = {
            "ide": "cursor",
            "config_path": str(config_file),
            "workspace": workspace,
            "generated_at": datetime.now().isoformat(),
        }

        bridge_file = BRIDGE_DIR / "cursor_config.json"
        bridge_file.write_text(json.dumps(bridge, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "bridge": bridge}

    def generate_windsurf_config(self, workspace: str = "E:\\coding-assistant") -> dict:
        """Generate Windsurf MCP configuration."""
        config = {
            "mcpServers": {
                "devmind": {
                    "command": "python",
                    "args": ["-m", "server"],
                    "env": {
                        "OLLAMA_HOST": "http://localhost:11434",
                        "DEVMIND_WORKSPACE": workspace,
                    }
                }
            }
        }

        windsurf_dir = Path(workspace) / ".windsurf"
        windsurf_dir.mkdir(parents=True, exist_ok=True)
        config_file = windsurf_dir / "mcp_config.json"
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

        bridge = {
            "ide": "windsurf",
            "config_path": str(config_file),
            "workspace": workspace,
            "generated_at": datetime.now().isoformat(),
        }

        bridge_file = BRIDGE_DIR / "windsurf_config.json"
        bridge_file.write_text(json.dumps(bridge, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "bridge": bridge}

    def generate_opencode_config(self, workspace: str = "E:\\coding-assistant") -> dict:
        """Generate OpenCode plugin configuration."""
        config = {
            "plugins": [
                {
                    "name": "devmind",
                    "version": "1.0.0",
                    "description": "DevMind AI IDE integration",
                    "config": {
                        "workspace": workspace,
                        "default_model": "gemma3:1b",
                        "fallback_models": ["opencode-zen", "openrouter-gemini"],
                    }
                }
            ]
        }

        opencode_dir = Path(workspace) / ".opencode"
        opencode_dir.mkdir(parents=True, exist_ok=True)
        config_file = opencode_dir / "plugin.json"
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

        bridge = {
            "ide": "opencode",
            "config_path": str(config_file),
            "workspace": workspace,
            "generated_at": datetime.now().isoformat(),
        }

        bridge_file = BRIDGE_DIR / "opencode_config.json"
        bridge_file.write_text(json.dumps(bridge, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "bridge": bridge}

    def list_bridges(self) -> list[dict]:
        """List all generated bridge configs."""
        bridges = []
        if BRIDGE_DIR.exists():
            for f in BRIDGE_DIR.glob("*.json"):
                try:
                    bridges.append(json.loads(f.read_text(encoding="utf-8")))
                except Exception:
                    pass
        return bridges


ide_bridge = IDEBridge()