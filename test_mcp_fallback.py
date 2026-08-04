"""
MCP Fallback Mechanism Test Script
Tests local MCP tools and automatically switches to cloud fallback if local fails
"""

import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import json
import subprocess
import time
from pathlib import Path

MCP_CONFIG = Path(".devmind/mcp_config.json")

def test_mcp_server(server_name: str, config: dict) -> bool:
    """Test if an MCP server is responsive"""
    print(f"Testing {server_name}...")
    
    try:
        cmd = config.get("command")
        args = config.get("args", [])
        
        # Handle npx on Windows - use full path or add npm to PATH
        if cmd == "npx":
            # Try to find npx in common locations
            npm_paths = [
                r"C:\Program Files\nodejs\npx.cmd",
                r"C:\Users\abhay\AppData\Roaming\npm\npx.cmd",
                "npx.cmd"
            ]
            for npm_path in npm_paths:
                if Path(npm_path).exists():
                    cmd = npm_path
                    break
            else:
                print(f"  [SKIP] {server_name} - npx not found in PATH")
                return False
        
        # Try to start the server process
        process = subprocess.Popen(
            [cmd] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Give it 5 seconds to start
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            print(f"  [OK] {server_name} is responsive")
            process.terminate()
            return True
        else:
            print(f"  [FAIL] {server_name} failed to start")
            return False
            
    except Exception as e:
        print(f"  [ERROR] {server_name} error: {e}")
        return False

def enable_fallback_server(server_name: str):
    """Enable a fallback cloud server"""
    with open(MCP_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    if server_name in config["mcpServers"]:
        config["mcpServers"][server_name]["disabled"] = False
        print(f"  [ACTION] Enabled fallback: {server_name}")
        
        with open(MCP_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

def main():
    print("=" * 50)
    print("MCP Fallback Mechanism Test")
    print("=" * 50)
    print()
    
    if not MCP_CONFIG.exists():
        print(f"Config file not found: {MCP_CONFIG}")
        return
    
    with open(MCP_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    servers = config.get("mcpServers", {})
    fallback_config = config.get("fallbackConfig", {})
    
    if not fallback_config.get("enabled", False):
        print("Fallback mechanism is disabled in config")
        return
    
    print("Testing local MCP servers...")
    print()
    
    local_servers = []
    failed_servers = []
    
    for name, cfg in servers.items():
        if cfg.get("priority") == "local" and not cfg.get("disabled", False):
            local_servers.append(name)
            if not test_mcp_server(name, cfg):
                failed_servers.append(name)
    
    print()
    print("=" * 50)
    print("Test Results:")
    print("=" * 50)
    print(f"Local servers tested: {len(local_servers)}")
    print(f"Successful: {len(local_servers) - len(failed_servers)}")
    print(f"Failed: {len(failed_servers)}")
    print()
    
    if failed_servers:
        print("Enabling fallback servers for failed local tools...")
        print()
        
        # Enable cloud fallbacks based on failure
        for failed in failed_servers:
            if "git" in failed.lower():
                enable_fallback_server("github-cloud")
            elif "search" in failed.lower():
                enable_fallback_server("brave-search")
        
        print()
        print("[SUCCESS] Fallback configuration updated")
    else:
        print("[SUCCESS] All local servers are working - no fallback needed")
    
    print()
    print("Done!")

if __name__ == "__main__":
    main()
