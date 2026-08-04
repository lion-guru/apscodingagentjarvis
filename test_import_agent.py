try:
    import agent
    print("✅ SUCCESS: agent.py imported with ZERO errors!")
    with open("e:\\coding-assistant\\agent_syntax_status.txt", "w") as f:
        f.write("CLEAN")
except Exception as e:
    print(f"❌ ERROR importing agent.py: {e}")
    with open("e:\\coding-assistant\\agent_syntax_status.txt", "w") as f:
        f.write(f"ERROR: {e}")
