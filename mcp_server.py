"""
DevMind MCP Server
Model Context Protocol server for external tool integration.
Provides tool registry and MCP server management.
"""
import json
import subprocess
from pathlib import Path
from datetime import datetime

MCP_CONFIG_DIR = Path.home() / ".devmind" / "mcp"
MCP_SERVERS_DIR = Path.home() / ".devmind" / "mcp_servers"

class MCPManager:
    def __init__(self):
        MCP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        MCP_SERVERS_DIR.mkdir(parents=True, exist_ok=True)
        self.servers = {}
        self.tool_registry = {}

    def register_server(self, name: str, command: str, args: list[str] = None,
                          env: dict = None, description: str = "") -> dict:
        """Register an MCP server."""
        server = {
            "name": name,
            "command": command,
            "args": args or [],
            "env": env or {},
            "description": description,
            "registered_at": datetime.now().isoformat(),
            "status": "registered",
        }
        self.servers[name] = server

        server_file = MCP_SERVERS_DIR / f"{name}.json"
        server_file.write_text(json.dumps(server, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "server": server}

    def list_servers(self) -> list[dict]:
        """List all registered MCP servers."""
        servers = []
        if MCP_SERVERS_DIR.exists():
            for f in MCP_SERVERS_DIR.glob("*.json"):
                try:
                    servers.append(json.loads(f.read_text(encoding="utf-8")))
                except Exception:
                    pass
        return servers

    def start_server(self, name: str) -> dict:
        """Start an MCP server process."""
        if name not in self.servers:
            return {"status": "error", "error": f"Server '{name}' not registered"}

        server = self.servers[name]
        try:
            process = subprocess.Popen(
                [server["command"]] + server["args"],
                env={**server.get("env", {})},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            server["process"] = process.pid
            server["status"] = "running"
            return {"status": "ok", "server": server, "pid": process.pid}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def stop_server(self, name: str) -> dict:
        """Stop an MCP server process."""
        if name not in self.servers:
            return {"status": "error", "error": f"Server '{name}' not registered"}

        server = self.servers[name]
        if "process" in server:
            try:
                import os, signal
                os.kill(server["process"], signal.SIGTERM)
                server["status"] = "stopped"
                return {"status": "ok", "message": f"Server '{name}' stopped"}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        return {"status": "ok", "message": f"Server '{name}' was not running"}

    def call_tool(self, server_name: str, tool_name: str, params: dict) -> dict:
        """Call a tool from an MCP server."""
        if server_name not in self.servers:
            return {"status": "error", "error": f"Server '{server_name}' not found"}
        return {"status": "ok", "result": f"Tool '{tool_name}' called on '{server_name}' with params: {params}"}

    def get_tool_registry(self) -> dict:
        """Get the full tool registry."""
        return self.tool_registry

    def register_tool(self, name: str, description: str, params_schema: dict,
                        handler: callable) -> dict:
        """Register a tool in the registry."""
        self.tool_registry[name] = {
            "name": name,
            "description": description,
            "params_schema": params_schema,
            "handler": handler.__name__ if hasattr(handler, "__name__") else str(handler),
        }
        return {"status": "ok", "tool": name}


mcp_manager = MCPManager()