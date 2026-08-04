"""
DevMind Extension Marketplace & Plugin Engine
Enables searching, installing, and managing plugins/extensions inside DevMind UI.
"""
import json
from pathlib import Path

PLUGINS_DB_PATH = Path.home() / ".devmind" / "installed_plugins.json"

AVAILABLE_MARKETPLACE_PLUGINS = [
    {
        "id": "theme-cyberpunk-neon",
        "name": "⚡ Iron Man Cyberpunk Theme",
        "author": "JARVIS Systems",
        "version": "2.5.0",
        "description": "Arc Reactor glowing cyan & violet dark theme for DevMind Web IDE.",
        "category": "Theme",
        "installed": True
    },
    {
        "id": "plugin-git-lens",
        "name": "🔍 Git Lens & PR Reviewer",
        "author": "Claude Code Port",
        "version": "1.4.0",
        "description": "Blame annotations, PR reviewers, and diff security audit.",
        "category": "Version Control",
        "installed": True
    },
    {
        "id": "plugin-voice-jarvis",
        "name": "🎙️ Realtime Voice Assistant",
        "author": "JARVIS Core",
        "version": "3.0.0",
        "description": "Speech-to-text hands-free voice command controller.",
        "category": "Voice & AI",
        "installed": True
    },
    {
        "id": "plugin-ollama-accelerator",
        "name": "⚡ Ollama Zero-Cost Offline Engine",
        "author": "DevMind Labs",
        "version": "2.1.0",
        "description": "Local model execution for Qwen 2.5 Coder & DeepSeek Coder.",
        "category": "Local AI",
        "installed": True
    },
    {
        "id": "plugin-mcp-connector",
        "name": "🔌 Universal MCP Tool Connector",
        "author": "Antigravity SDK",
        "version": "1.8.0",
        "description": "Connect 250+ Model Context Protocol server tools seamlessly.",
        "category": "Integration",
        "installed": True
    }
]

class DevMindPluginEngine:
    def __init__(self):
        PLUGINS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not PLUGINS_DB_PATH.exists():
            PLUGINS_DB_PATH.write_text(json.dumps(AVAILABLE_MARKETPLACE_PLUGINS, indent=2), encoding="utf-8")

    def get_marketplace(self) -> list:
        """Get list of all extensions in marketplace."""
        try:
            if PLUGINS_DB_PATH.exists():
                return json.loads(PLUGINS_DB_PATH.read_text(encoding="utf-8"))
            return AVAILABLE_MARKETPLACE_PLUGINS
        except Exception:
            return AVAILABLE_MARKETPLACE_PLUGINS

    def toggle_plugin(self, plugin_id: str) -> dict:
        """Install or toggle extension plugin state."""
        try:
            plugins = self.get_marketplace()
            for p in plugins:
                if p["id"] == plugin_id:
                    p["installed"] = not p["installed"]
                    PLUGINS_DB_PATH.write_text(json.dumps(plugins, indent=2), encoding="utf-8")
                    status_str = "installed" if p["installed"] else "uninstalled"
                    return {"status": "ok", "message": f"Plugin '{p['name']}' {status_str} successfully."}
            return {"status": "error", "message": f"Plugin '{plugin_id}' not found."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Global Instance
plugin_engine = DevMindPluginEngine()
