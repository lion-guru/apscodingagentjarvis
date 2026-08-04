import os
import sys
from agent import DEFAULT_WORKSPACE, get_abs_path, create_tool_registry, execute_tool

print("==================================================")
print("DevMind - APSDreamHome Integration Test")
print("==================================================")
print(f"Default Workspace: {DEFAULT_WORKSPACE}")

# Test 1: Workspace Resolution
abs_playwright = get_abs_path("playwright.config.js")
print(f"Resolved 'playwright.config.js': {abs_playwright}")
assert "apsdreamhome" in str(abs_playwright).lower()

# Test 2: Tools Execution Test
tools = create_tool_registry()
res = execute_tool(tools, "list_files", {"path": "."})
print("\n[list_files result]:")
print(res.output[:300])

print("\n✅ DevMind APSDreamHome Integration Verified Successfully!")
