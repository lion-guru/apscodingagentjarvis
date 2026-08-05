import subprocess
import os
import threading
from typing import Dict, List, Optional


class TerminalManager:
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def create_session(self, session_id: str, cwd: Optional[str] = None) -> dict:
        cwd = cwd or os.getcwd()
        try:
            if os.name == "nt":
                process = subprocess.Popen(
                    ["cmd.exe"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    text=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                process = subprocess.Popen(
                    [os.environ.get("SHELL", "/bin/bash")],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    text=True,
                    start_new_session=True
                )
            with self._lock:
                self.sessions[session_id] = {
                    "process": process,
                    "cwd": cwd,
                    "created": True,
                    "output": [],
                    "pid": process.pid
                }
            return {"status": "ok", "session_id": session_id, "pid": process.pid, "cwd": cwd}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def execute_command(self, session_id: str, command: str) -> dict:
        with self._lock:
            session = self.sessions.get(session_id)
        if not session:
            return {"status": "error", "message": f"Session {session_id} not found"}
        process = session["process"]
        try:
            if os.name == "nt":
                full_command = command + "\n"
                process.stdin.write(full_command)
                process.stdin.flush()
            else:
                full_command = command + "\n"
                process.stdin.write(full_command)
                process.stdin.flush()
            output = ""
            try:
                output = process.stdout.readline()
            except Exception:
                pass
            session["output"].append({"command": command, "output": output.strip() if output else ""})
            return {"status": "ok", "command": command, "output": output.strip() if output else ""}
        except BrokenPipeError:
            return {"status": "error", "message": "Process terminated"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_output(self, session_id: str) -> List[dict]:
        with self._lock:
            session = self.sessions.get(session_id)
        if not session:
            return []
        return session.get("output", [])

    def get_cwd(self, session_id: str) -> str:
        with self._lock:
            session = self.sessions.get(session_id)
        if not session:
            return os.getcwd()
        return session.get("cwd", os.getcwd())

    def list_sessions(self) -> List[dict]:
        result = []
        with self._lock:
            for sid, session in self.sessions.items():
                result.append({
                    "session_id": sid,
                    "cwd": session.get("cwd", ""),
                    "pid": session.get("pid", 0),
                    "command_count": len(session.get("output", []))
                })
        return result

    def kill_session(self, session_id: str) -> dict:
        with self._lock:
            session = self.sessions.pop(session_id, None)
        if not session:
            return {"status": "error", "message": "Session not found"}
        try:
            process = session["process"]
            if os.name == "nt":
                process.terminate()
            else:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
            return {"status": "ok", "message": f"Session {session_id} terminated"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def kill_all(self) -> dict:
        with self._lock:
            sessions = list(self.sessions.items())
            self.sessions.clear()
        for sid, session in sessions:
            try:
                session["process"].terminate()
            except Exception:
                pass
        return {"status": "ok", "message": f"All {len(sessions)} sessions terminated"}

    def get_history(self, session_id: str) -> List[str]:
        with self._lock:
            session = self.sessions.get(session_id)
        if not session:
            return []
        return [item["command"] for item in session.get("output", [])]


terminal_manager = TerminalManager()


def create_session(session_id: str, cwd: str = None) -> dict:
    return terminal_manager.create_session(session_id, cwd)

def execute_command(session_id: str, command: str) -> dict:
    return terminal_manager.execute_command(session_id, command)

def get_output(session_id: str, tail: int = 100) -> list:
    output = terminal_manager.get_output(session_id)
    if tail and len(output) > tail:
        output = output[-tail:]
    return output

def kill_session(session_id: str) -> dict:
    return terminal_manager.kill_session(session_id)

def list_sessions() -> list:
    return terminal_manager.list_sessions()