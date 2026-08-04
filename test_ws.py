import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:7860/ws/chat/test_session"
    print(f"Connecting to {uri}")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected!")
            
            # Wait for cwd_changed and model_changed
            for _ in range(2):
                msg = await ws.recv()
                print("Received:", msg)

            # Change model to gemini-2.0-flash
            print("Changing model to gemini-2.0-flash")
            await ws.send(json.dumps({
                "type": "set_model",
                "model": "gemini-2.0-flash"
            }))
            
            msg = await ws.recv()
            print("Received:", msg)
            
            # Send a chat message
            print("Sending chat message")
            await ws.send(json.dumps({
                "type": "chat",
                "content": "Create a file named test_devmind_hello.txt that says 'Hello World'. Reply with DONE when finished.",
                "model": "gemini-2.0-flash"
            }))
            
            # Receive loop
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                print(f"Message type: {data.get('type')}")
                if data.get("type") == "error":
                    print("ERROR:", data.get("content"))
                    break
                elif data.get("type") == "done":
                    print("DONE received.")
                    break
                elif data.get("type") == "assistant_text":
                    print("ASSISTANT:", data.get("content"))
                    
    except Exception as e:
        print("WebSocket Error:", e)

if __name__ == "__main__":
    asyncio.run(test_websocket())
