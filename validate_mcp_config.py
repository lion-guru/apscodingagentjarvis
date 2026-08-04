"""
Simple MCP Configuration Validator
Validates the MCP config structure and fallback setup without actually starting servers
"""
import sys
import io
import json
from pathlib import Path

# Fix Windows console encoding for Unicode/emoji support
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

MCP_CONFIG = Path(".devmind/mcp_config.json")

def validate_config():
    print("=" * 50)
    print("MCP Configuration Validator")
    print("=" * 50)
    print()
    
    if not MCP_CONFIG.exists():
        print(f"[ERROR] Config file not found: {MCP_CONFIG}")
        return False
    
    with open(MCP_CONFIG, "r", encoding="utf-8") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in config: {e}")
            return False
    
    print("[OK] Config file loaded successfully")
    print()
    
    # Check mcpServers section
    if "mcpServers" not in config:
        print("[ERROR] Missing 'mcpServers' section")
        return False
    
    servers = config["mcpServers"]
    print(f"[OK] Found {len(servers)} MCP servers configured")
    print()
    
    # Categorize servers
    local_servers = []
    cloud_servers = []
    disabled_servers = []
    
    for name, cfg in servers.items():
        disabled = cfg.get("disabled", False)
        is_http = "url" in cfg
        
        if disabled:
            disabled_servers.append(name)
        elif is_http:
            cloud_servers.append(name)
        else:
            local_servers.append(name)
    
    print("Server Categories:")
    print(f"  Local (Zero Token):    {len(local_servers)}")
    print(f"  Cloud (Fallback):      {len(cloud_servers)}")
    print(f"  Disabled:              {len(disabled_servers)}")
    print()
    
    # Check fallback config
    if "fallbackConfig" in config:
        fallback = config["fallbackConfig"]
        print("[OK] Fallback configuration found")
        print(f"  Enabled:              {fallback.get('enabled', False)}")
        print(f"  Strategy:             {fallback.get('strategy', 'none')}")
        print(f"  Timeout (seconds):    {fallback.get('timeout', 30)}")
        print(f"  Max Retries:          {fallback.get('maxRetries', 2)}")
        print()
        
        if fallback.get("enabled"):
            print("[SUCCESS] Fallback mechanism is ENABLED")
            print("  Local servers will be tried first")
            print("  Cloud fallbacks will activate if local fails")
        else:
            print("[WARNING] Fallback mechanism is DISABLED")
    else:
        print("[WARNING] No fallback configuration found")
    
    print()
    print("Local Servers (Zero Token Cost):")
    for name in local_servers:
        print(f"  - {name}")

    print()
    print("Cloud Fallback Servers:")
    for name in cloud_servers:
        print(f"  - {name}")
    
    print()
    print("=" * 50)
    print("[SUCCESS] Configuration is valid!")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    validate_config()
