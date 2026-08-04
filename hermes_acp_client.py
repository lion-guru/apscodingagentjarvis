"""
Hermes ACP Client for DevMind IDE.
Connects to the Hermes Agent ACP server for agent capabilities.
"""
import asyncio
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional


HERMES_RUNTIME = os.path.join(
    os.path.expanduser("~"),
    "AppData", "Local", "Programs", "stonic_dsktp", "resources", "hermes-runtime", "src"
)
HERMES_PYTHON = os.path.join(HERMES_RUNTIME, "python-embedded", "python.exe")


class HermesACPError(Exception):
    pass


class HermesACPClient:
    def __init__(self, hermes_python: str = None):
        self.hermes_python = hermes_python or HERMES_PYTHON
        self._process: subprocess.Popen = None
        self._request_id = 0
        self._pending: Dict[str, asyncio.Future] = {}
        self._connected = False

    async def connect(self) -> bool:
        if self._connected:
            return True
        if not os.path.exists(self.hermes_python):
            return False
        self._process = subprocess.Popen(
            [self.hermes_python, "-m", "acp_adapter.entry", "--check"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=HERMES_RUNTIME,
        )
        self._connected = True
        return True

    async def disconnect(self) -> None:
        if self._process:
            self._process.terminate()
            self._process = None
        self._connected = False

    async def send_request(self, method: str, params: dict = None) -> dict:
        self._request_id += 1
        request_id = str(self._request_id)
        request = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params:
            request["params"] = params

        future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        line = json.dumps(request) + "\n"
        self._process.stdin.write(line.encode("utf-8"))
        await self._process.stdin.drain()

        try:
            return await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            raise HermesACPError(f"Request {method} timed out")

    async def chat(self, message: str, session_id: str = None) -> dict:
        params = {"message": message}
        if session_id:
            params["session_id"] = session_id
        return await self.send_request("session/start", params)

    async def get_tools(self) -> list:
        return await self.send_request("tools/list")

    async def get_session_info(self, session_id: str) -> dict:
        return await self.send_request("session/get", {"session_id": session_id})

    async def list_sessions(self) -> list:
        return await self.send_request("session/list")

    async def send_user_message(self, session_id: str, message: str) -> dict:
        return await self.send_request("session/sendUserMessage", {
            "session_id": session_id,
            "message": message,
        })

    async def approve_tool_call(self, session_id: str, tool_call_id: str, approved: bool) -> dict:
        return await self.send_request("session/approveToolCall", {
            "session_id": session_id,
            "tool_call_id": tool_call_id,
            "approved": approved,
        })

    async def set_edit_approval(self, session_id: str, policy: str) -> dict:
        return await self.send_request("session/setEditApproval", {
            "session_id": session_id,
            "policy": policy,
        })


async def test_hermes_acp():
    client = HermesACPClient()
    connected = await client.connect()
    if not connected:
        print("Hermes ACP not available")
        return
    print("Connected to Hermes ACP")
    tools = await client.get_tools()
    print(f"Available tools: {tools}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_hermes_acp())
