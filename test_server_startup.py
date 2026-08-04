import sys

try:
    import server
    print("✅ SUCCESS: server.py imported and FastAPI app created without any errors!")
    print(f"App title: '{server.app.title}'")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)
