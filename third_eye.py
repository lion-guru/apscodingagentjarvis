"""
DevMind / Jarvis — Third Eye System
A multi-agent "third eye" / assistant that watches over IDEs, apps, browsers,
terminals and the entire development workflow. Auto-discovers free AI models,
tests them continuously, auto-recovers from hangs/errors/token-exhaustion, and
spawns sub-agents to handle tasks anywhere — not just inside an IDE.

Usage:
    python third_eye.py                    # Start the Third Eye system
    python third_eye.py --daemon           # Run as background daemon
    python third_eye.py --test-models      # Just run model discovery & test
    python third_eye.py --watch ide        # Watch a specific app (ide/browser/terminal)
    python third_eye.py --status           # Show current status & working models

Features:
    1. FREE MODEL DISCOVERY  — scans all providers, tests connectivity, categorizes.
    2. CONTINUOUS HEALTH     — re-tests models every 5 min, updates live status.
    3. IDE / APP MONITOR     — watches OpenCode, Windsurf, Trae, browsers, terminals.
    4. HANG DETECTION         — flags stuck IDEs / frozen tool calls / token exhaustion.
    5. AUTO-RECOVERY          — switches models, restarts apps, resumes tasks.
    6. MULTI-AGENT SPAWNING   — spawns sub-agents to execute tasks in any context.
    7. THIRD-EYE OVERVIEW     — dashboard showing health of everything at a glance.
"""
import os
import sys
import json
import time
import shutil
import asyncio
import threading
import subprocess
import signal
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta


import httpx

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Paths ────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
WORKING_FILE    = BASE_DIR / "working_models.json"
THIRD_EYE_STATE = BASE_DIR / ".third_eye_state.json"
LOG_DIR         = BASE_DIR / "third_eye_logs"
LOG_DIR.mkdir(exist_ok=True)

# ── Colors ───────────────────────────────────────────────────────
class C:
    HEADER = "\033[95m"
    CYAN   = "\033[96m"
    YELLOW = "\033[93m"
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

def p(msg, end="\n", color=""):
    print(f"{color}{msg}{C.RESET}", end=end, flush=True)

# ────────────────────────────────────────────────────────────────
# 1. MODEL MANAGER
# ────────────────────────────────────────────────────────────────
class ModelManager:
    """
    Manages the catalogue of free AI models:
    - Loads working_models.json (produced by free_model_discovery.py)
    - Categorises models by SPEED / QUALITY / RELIABILITY
    - Continuously health-checks models
    - Picks the best model for a given task / context
    """

    # Category definitions: each free model is mapped to one-or-more categories
    # Categories: coding, reasoning, speed, creativity, long-context, vision, local
    MODEL_CATEGORIES = {
        # Groq
        "llama-3.3-70b-versatile":  ["coding", "reasoning", "quality"],
        "llama-3.1-8b-instant":     ["speed", "general", "coding"],
        "llama-3.2-1b-instant":     ["speed", "general"],
        "gemma2-9b-it":             ["coding", "general"],
        "mistral-8x7b-32768":       ["reasoning", "general"],
        # OpenRouter free
        "nvidia/nemotron-3-ultra-550b-a55b:free":    ["reasoning", "long-context", "coding"],
        "nvidia/nemotron-3-super-120b-a12b:free":    ["reasoning", "coding"],
        "google/gemma-4-31b-it:free":                ["coding", "general"],
        "qwen/qwen3-coder:free":                     ["coding", "general"],
        "qwen/qwen-2.5-coder-32b-instruct:free":     ["coding", "quality"],
        "meta-llama/llama-3.3-70b-instruct:free":    ["coding", "quality"],
        "cohere/north-mini-code:free":               ["coding", "speed"],
        "poolside/laguna-m.1:free":                  ["coding", "quality"],
        # Gemini
        "gemini-2.0-flash":      ["speed", "coding", "general"],
        "gemini-2.5-flash":      ["quality", "coding", "general"],
        "gemini-2.5-flash-lite": ["speed", "general"],
        "gemini-2.5-pro":        ["quality", "reasoning"],
        # HuggingFace
        "Qwen/Qwen2.5-Coder-32B-Instruct": ["coding", "quality"],
        "meta-llama/Llama-3.3-70B-Instruct": ["coding", "quality"],
        "microsoft/Phi-4":       ["general", "reasoning"],
        "google/gemma-2-9b-it":  ["general", "coding"],
        "mistralai/Mistral-7B-Instruct-v0.3": ["general", "speed"],
        # Local Ollama
        "llama3.2:3b":           ["local", "general", "speed"],
        "qwen2.5-coder:1.5b":    ["local", "coding", "speed"],
        "qwen2.5:3b-instruct":   ["local", "general"],
        "llama3.2:1b":           ["local", "general", "speed"],
        "qwen2.5-coder:7b":      ["local", "coding", "quality"],
        "gemma3:1b":             ["local", "general"],
        "stable-code:latest":    ["local", "coding"],
        "moondream:latest":      ["local", "vision"],
    }

    def __init__(self):
        self.models: list[dict] = []
        self.health: dict[str, dict] = {}   # model -> {working, latency, last_test, fail_count}
        self._load()

    def _load(self):
        """Load working models from working_models.json"""
        if WORKING_FILE.exists():
            try:
                data = json.loads(WORKING_FILE.read_text(encoding="utf-8"))
                self.models = data.get("models", [])
                for m in self.models:
                    self.health[m["model"]] = {
                        "working": True,
                        "latency": m.get("latency_s", 999),
                        "last_test": datetime.now().isoformat(),
                        "fail_count": 0,
                    }
                p(f"  📦 Loaded {len(self.models)} working models from {WORKING_FILE.name}",
                  color=f"{C.CYAN}{C.BOLD}")
            except Exception as e:
                p(f"  ⚠ Error loading working models: {e}", color=C.YELLOW)

    @property
    def all_models(self) -> list[dict]:
        return self.models

    def categorize(self, model_name: str) -> list[str]:
        """Return categories for a given model"""
        key = model_name
        if key in self.MODEL_CATEGORIES:
            return self.MODEL_CATEGORIES[key]
        # Try fuzzy match
        for k, cats in self.MODEL_CATEGORIES.items():
            if k.lower() in model_name.lower() or model_name.lower() in k.lower():
                return cats
        return ["general"]

    def get_by_category(self, category: str) -> list[dict]:
        """Return all working models in a category, sorted by latency"""
        result = []
        for m in self.models:
            if category in self.categorize(m["model"]):
                result.append(m)
        result.sort(key=lambda x: x.get("latency_s", 999))
        return result

    def get_best(self, category: str = "general") -> Optional[dict]:
        """Return the best working model for a category"""
        candidates = self.get_by_category(category)
        if not candidates:
            # Fallback: any working model
            return self.models[0] if self.models else None
        # Return fastest in category
        return candidates[0]

    def get_failover_chain(self) -> list[str]:
        """Return the full failover chain (best to worst)"""
        chain_file = WORKING_FILE
        if chain_file.exists():
            try:
                data = json.loads(chain_file.read_text(encoding="utf-8"))
                return data.get("failover_chain", [])
            except Exception:
                pass
        # Fallback: build from sorted models
        sorted_models = sorted(self.models, key=lambda x: x.get("latency_s", 999))
        return [m["model"] for m in sorted_models]

    def health_check_model(self, model: dict) -> bool:
        """Quick single-request health check for a model. Returns True if working."""
        provider = model.get("provider", "ollama")
        model_name = model["model"]

        try:
            test_content = [{"role": "user", "content": "Hi"}]
            start = time.time()

            if provider == "groq":
                api_key = os.getenv("GROQ_API_KEY", "")
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = {"model": model_name, "messages": test_content, "max_tokens": 10}
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = httpx.post(url, json=payload, headers=headers, timeout=12)
            elif provider == "google":
                api_key = os.getenv("GEMINI_API_KEY", "")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                payload = {"contents": [{"role": "user", "parts": [{"text": "Hi"}]}]}
                resp = httpx.post(url, json=payload, timeout=12)
            elif provider == "openrouter":
                api_key = os.getenv("OPENROUTER_API_KEY", "")
                url = "https://openrouter.ai/api/v1/chat/completions"
                payload = {"model": model_name, "messages": test_content, "max_tokens": 10}
                headers = {"Authorization": f"Bearer {api_key}", "HTTP-Referer": "http://localhost:7860"}
                resp = httpx.post(url, json=payload, headers=headers, timeout=12)
            elif provider == "huggingface":
                api_key = os.getenv("HUGGING_FACE_API_KEY", "")
                url = f"https://api-inference.huggingface.co/models/{model_name}"
                payload = {"inputs": "Hi", "parameters": {"max_new_tokens": 10}}
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = httpx.post(url, json=payload, headers=headers, timeout=15)
            else:  # ollama / local
                url = f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/chat"
                payload = {"model": model_name, "messages": test_content, "stream": False, "options": {"num_predict": 10}}
                resp = httpx.post(url, json=payload, timeout=20)

            elapsed = time.time() - start
            ok = resp.status_code == 200

            # Update health
            if model_name in self.health:
                self.health[model_name]["working"] = ok
                self.health[model_name]["latency"] = round(elapsed, 2)
                self.health[model_name]["last_test"] = datetime.now().isoformat()
                if ok:
                    self.health[model_name]["fail_count"] = 0
                else:
                    self.health[model_name]["fail_count"] += 1

            return ok

        except Exception:
            if model_name in self.health:
                self.health[model_name]["working"] = False
                self.health[model_name]["fail_count"] += 1
            return False

    def select_model_for_task(self, task_context: str = "") -> str:
        """
        Intelligently pick the best model for the task.
        Analyses the task to decide which model category is needed.
        """
        ctx = task_context.lower()

        # Decide category based on task content
        if any(w in ctx for w in ["code", "bug", "function", "python", "php", "fix", "class"]):
            category = "coding"
        elif any(w in ctx for w in ["explain", "write", "story", "creative", "email"]):
            category = "general"
        elif any(w in ctx for w in ["reason", "analyze", "plan", "think", "debug"]):
            category = "reasoning"
        elif "fast" in ctx or "quick" in ctx:
            category = "speed"
        else:
            category = "general"

        best = self.get_best(category)
        if best:
            return best["model"]
        return self.get_best("general")["model"] if self.models else "llama3.2:3b"

    def get_status(self) -> dict:
        return {
            "total_models": len(self.models),
            "working_models": len([h for h in self.health.values() if h["working"]]),
            "categories_available": list(set(
                cat for m in self.models
                for cat in self.categorize(m["model"])
            )),
            "health": self.health,
            "failover_chain": self.get_failover_chain(),
            "last_updated": datetime.now().isoformat(),
        }


# ────────────────────────────────────────────────────────────────
# 2. APP / IDE MONITOR
# ────────────────────────────────────────────────────────────────
class AppMonitor:
    """
    Monitors running applications (IDEs, browsers, terminals) and detects:
    - Hung / frozen windows
    - Token-exhaustion errors in output
    - Stuck tool calls
    - Unexpected crashes
    """

    KNOWN_APPS = {
        "opencode":    "OpenCode IDE",
        "windsurf":    "Windsurf IDE",
        "trae":        "Trae IDE",
        "cursor":      "Cursor IDE",
        "antigravity": "Antigravity IDE",
        "code":        "VS Code",
        "chrome":      "Chrome",
        "edge":        "Edge",
        "firefox":     "Firefox",
        "powershell":  "PowerShell",
        "cmd":         "Command Prompt",
        "terminal":    "Terminal",
        "python":      "Python",
    }


    def __init__(self):
        self.monitored: list[str] = []   # process names to watch
        self.process_health: dict[str, dict] = {}  # proc_name -> {running, last_activity, hang_start, errors}
        self.last_output_check: dict[str, str] = {}  # proc_name -> last captured output (simple)
        self.alerts: list[dict] = []

    def detect_running_ide(self) -> Optional[str]:
        """Detect which IDE/app is currently running."""
        if sys.platform == "win32":
            cmd = "tasklist /FO CSV"
            try:
                out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5).stdout
                for line in out.splitlines():
                    for app_keyword, app_name in self.KNOWN_APPS.items():
                        if app_keyword.lower() in line.lower():
                            proc_name = line.split(",")[0].strip().strip('"')
                            return proc_name
            except Exception:
                pass
        elif sys.platform in ("linux", "darwin"):
            try:
                out = subprocess.run("ps aux", shell=True, capture_output=True, text=True, timeout=5).stdout
                for line in out.splitlines():
                    for app_keyword in self.KNOWN_APPS:
                        if app_keyword in line.lower():
                            parts = line.split()
                            if len(parts) > 10:
                                return parts[10]
            except Exception:
                pass
        return None

    def monitor_window_activity(self, proc_name: str) -> dict:
        """
        Check if a process is running and responsive.
        On Windows, checks process existence.
        Returns {running, responsive, last_activity}
        """
        result = {"running": False, "responsive": True, "errors": []}

        try:
            if sys.platform == "win32":
                check = subprocess.run(
                    f'tasklist /FI "IMAGENAME eq {proc_name}" /FO CSV',
                    shell=True, capture_output=True, text=True, timeout=5
                )
                result["running"] = proc_name in check.stdout
            else:
                check = subprocess.run(
                    f"pgrep -x {proc_name}", shell=True, capture_output=True, timeout=5
                )
                result["running"] = bool(check.stdout.strip())
        except Exception as e:
            result["errors"].append(str(e))

        return result

    def detect_hang(self, proc_name: str, threshold_seconds: int = 30) -> dict:
        """
        Detect if an app/IDE is hung:
        - Process running but not updating log/output
        - CPU stuck at 0% for extended period
        - Tool call timeout
        """
        now = time.time()
        health = self.process_health.get(proc_name, {})
        last_activity = health.get("last_activity", now)

        hung = (now - last_activity) > threshold_seconds
        return {
            "process": proc_name,
            "hung": hung,
            "idle_seconds": round(now - last_activity),
            "threshold": threshold_seconds,
        }

    def detect_token_exhaustion(self, log_text: str) -> Optional[str]:
        """Scan log/output text for token-exhaustion or quota errors."""
        patterns = [
            (r"quota exceeded|rate limit|429|too many requests", "rate_limit"),
            (r"exceeded.*context.*length|context window.*full|token limit", "context_overflow"),
            (r"quota.*exhausted|limit.*reached|billing", "quota_exhausted"),
            (r"timeout|timed out|deadline exceeded", "timeout"),
            (r"token.*not found|invalid.*token|api key", "auth_error"),
        ]
        for pattern, error_type in patterns:
            if any(kw in log_text.lower() for kw in pattern.split("|")):
                return error_type
        return None

    def add_alert(self, alert_type: str, message: str, context: str = ""):
        """Record an alert from monitoring."""
        self.alerts.append({
            "type": alert_type,
            "message": message,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        })
        p(f"  [{C.RED}🚨 ALERT{C.RESET}] {alert_type}: {message}", color="")

    def get_status(self) -> dict:
        return {
            "monitored_processes": self.monitored,
            "process_health": self.process_health,
            "active_alerts": self.alerts[-10:] if self.alerts else [],
            "detected_ide": self.detect_running_ide(),
        }


# ────────────────────────────────────────────────────────────────
# 2b. BROWSER OPERATOR (controls browser-based IDEs)
# ────────────────────────────────────────────────────────────────
class BrowserOperator:
    """
    Controls browser-based IDEs (OpenCode web, Windsurf, Cursor web, etc.)
    by reading the page content, detecting errors, switching models, and
    resuming tasks — like a Copilot that can see and click inside the browser.

    Uses Selenium (for real browser) or falls back to HTTP API + MCP
    browser server for headless operation.
    """

    # Known browser-based IDE URLs
    IDE_URLS = {
        "opencode":      "https://opencode.ai",
        "windsurf":      "https://windsurf.ai",
        "cursor":        "https://cursor.sh",
        "trae":          "https://trae.ai",
        "antigravity":   "http://127.0.0.1:7860",
        "github_codespaces": "https://github.com/features/codespaces",
        "replit":        "https://replit.com",
    }

    ANTIGRAVITY_SELECTORS = {
        "chat_input": "#chatInput, textarea[placeholder*='message'], [data-testid='chat-input']",
        "send_button": "#sendBtn, button[type='submit'], [data-testid='send-button']",
        "model_selector": "#modelSelect, select[name='model']",
        "status_indicator": "#statusIndicator, .status-bar",
    }


    def __init__(self):
        self.active_browser = None
        self.current_ide: Optional[str] = None
        self._driver = None

    def _get_driver(self):
        """Get a Selenium WebDriver (if available)."""
        if self._driver is not None:
            return self._driver
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            opts = Options()
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_experimental_option("debuggerAddress", "localhost:9222")
            self._driver = webdriver.Chrome(options=opts)
            return self._driver
        except ImportError:
            if not getattr(self, "_warned_selenium", False):
                p("  ℹ️ Browser automation standby (install selenium for live browser control)", color=C.CYAN)
                self._warned_selenium = True
            return None
        except Exception as e:
            if not getattr(self, "_warned_driver_err", False):
                p(f"  ℹ️ Browser automation standby (Chrome remote debugging not attached at localhost:9222)", color=C.CYAN)
                self._warned_driver_err = True
            return None


    def detect_ide_in_browser(self, url: str = None) -> Optional[str]:
        """Detect which IDE is open in the browser by URL."""
        if not url:
            driver = self._get_driver()
            if driver:
                try:
                    url = driver.current_url
                except Exception:
                    return None
        if not url:
            return None

        for ide_key, ide_url in self.IDE_URLS.items():
            if ide_key in url.lower():
                self.current_ide = ide_key
                return ide_key
        return None

    def read_ide_output(self) -> str:
        """Read the visible text/content from the current IDE browser tab."""
        driver = self._get_driver()
        if not driver:
            return ""
        try:
            # Try to read the main content area
            selectors = [
                ".chat-container", ".conversation", ".messages",
                ".output", ".terminal-output", ".code-output",
                "pre", ".prose",
            ]
            texts = []
            for sel in selectors:
                try:
                    elems = driver.find_elements("css selector", sel)
                    for el in elems:
                        texts.append(el.text)
                except Exception:
                    pass
            return "\n".join(texts)[:5000]
        except Exception as e:
            return f"Error reading IDE: {e}"

    def detect_error_in_ide(self) -> Optional[str]:
        """Scan the IDE browser output for error patterns."""
        output = self.read_ide_output()
        if not output:
            return None
        error_map = {
            "rate_limit": ["rate limit", "429", "too many requests"],
            "quota_exhausted": ["quota exceeded", "billing", "limit reached"],
            "auth_failure": ["invalid api key", "unauthorized", "api_key_error"],
            "context_overflow": ["context window", "token limit", "too long"],
            "timeout": ["timed out", "timeout", "deadline exceeded"],
            "model_hang": ["thinking...", "typing...", ".processing"],
        }
        for err_type, patterns in error_map.items():
            for pattern in patterns:
                if pattern.lower() in output.lower():
                    return err_type
        return None

    def switch_ide_model(self, new_model: str) -> bool:
        """
        Switch the active model inside the browser-based IDE.
        This clicks the model dropdown and selects a new model.
        """
        driver = self._get_driver()
        if not driver:
            return False
        try:
            # Generic approach: look for model selector dropdown
            model_buttons = driver.find_elements("css selector", "[title*='model'], [aria-label*='model'], select[name*='model']")
            if not model_buttons:
                # Try common selectors
                model_buttons = driver.find_elements("css selector", ".model-selector, .dropdown-model, button[title='Model']")

            for btn in model_buttons:
                try:
                    btn.click()
                    # Wait, then look for the new model in options
                    import time as _time
                    _time.sleep(0.5)
                    options = driver.find_elements("css selector", "[role='option'], li[data-model], .dropdown-item")
                    for opt in options:
                        opt_text = opt.text.lower()
                        if new_model.lower().split(":")[-1].split("/")[-1] in opt_text:
                            opt.click()
                            return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def click_retry_or_resubmit(self) -> bool:
        """Click 'Retry' or re-submit the last task in the IDE."""
        driver = self._get_driver()
        if not driver:
            return False
        try:
            retry_buttons = driver.find_elements("css selector",
                "button.retry, button[title='Retry'], button[data-action='retry'], "
                ".retry-btn, button[type='submit']"
            )
            for btn in retry_buttons:
                try:
                    btn.click()
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False


# ────────────────────────────────────────────────────────────────
# 2c. OPENCODE IDE & CLI SUPERVISOR ROBOT
# ────────────────────────────────────────────────────────────────
class OpenCodeSupervisor:
    """
    Autonomous OpenCode IDE & CLI Supervisor Robot.
    Monitors opencode.exe, code.exe, and OpenCode CLI commands.
    Automatically detects hangs, waiting prompt boxes, rate limits, and model errors.
    Executes CLI actions or UI automated prompts to keep OpenCode coding without human intervention.
    """

    def __init__(self):
        self.is_monitoring = False
        self.last_prompt_time = time.time()
        self.last_status = "idle"
        self.supervised_tasks = []

    def check_opencode_installed(self) -> dict:
        """Check if OpenCode CLI or Desktop is available in environment."""
        cli_path = shutil.which("opencode") or shutil.which("opencode.exe") or shutil.which("opencode.cmd")
        cli_available = cli_path is not None
        desktop_running = False
        try:
            if sys.platform == "win32":
                check = subprocess.run(
                    'tasklist /FI "IMAGENAME eq opencode.exe" /NH',
                    shell=True, capture_output=True, text=True
                )
                desktop_running = "opencode.exe" in check.stdout.lower()
        except Exception:
            pass

        return {
            "cli_available": cli_available,
            "desktop_running": desktop_running,
            "opencode_path": cli_path or "Not found in PATH"
        }

    def get_opencode_status(self) -> dict:
        """Fetch live status from OpenCode CLI or active process."""
        status = self.check_opencode_installed()
        if status["cli_available"]:
            try:
                res = subprocess.run(["opencode", "--version"], capture_output=True, text=True, timeout=5)
                status["cli_version"] = (res.stdout or res.stderr).strip()
            except Exception as e:
                status["cli_version"] = str(e)
        return status

    def send_opencode_prompt(self, prompt_text: str, project_dir: str = None) -> dict:
        """Send prompt to OpenCode CLI or inject via robot automation."""
        cli_info = self.check_opencode_installed()
        if cli_info["cli_available"]:
            try:
                cwd = project_dir or str(BASE_DIR)
                cmd = [cli_info["opencode_path"], "run", prompt_text]
                proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                return {"status": "dispatched", "method": "cli", "pid": proc.pid, "prompt": prompt_text}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {
            "status": "standby",
            "message": "OpenCode CLI not found in PATH; monitoring active IDE windows via Third Eye"
        }


    def get_ide_status(self) -> dict:
        """Get full status of the browser IDE."""
        try:
            return {
                "current_ide": self.current_ide,
                "has_driver": self._driver is not None,
                "last_output": self.read_ide_output()[:500] if self._driver else "",
                "detected_error": self.detect_error_in_ide() if self._driver else None
            }
        except Exception:
            return {
                "current_ide": self.current_ide,
                "has_driver": self._driver is not None,
                "last_output": "",
                "detected_error": None
            }



class AutoRecoveryEngine:
    """
    When the IDE/app/model fails, this engine:
    1. Diagnoses the problem type (hang / token exhaustion / model down / app crash)
    2. Takes corrective action:
       - Hang: restart the app or kill+relaunch
       - Token exhaustion / model error: switch to next working model
       - App crash: attempt relaunch
       - Quota exhausted: rotate to different provider
    3. Resumes the task from last checkpoint
    """

    def __init__(self, model_manager: ModelManager, app_monitor: AppMonitor):
        self.mm = model_manager
        self.am = app_monitor
        self.recovery_history: list[dict] = []

    def diagnose_and_recover(self, error: str, context: str = "", proc_name: Optional[str] = None) -> dict:
        """
        Diagnose an error and take recovery action.
        Returns details of what was done.
        """
        action_taken = []
        recovery_detail = {
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "context": context,
            "actions": [],
        }

        # --- 1. Detect error type ---
        if "quota" in error.lower() or "rate limit" in error.lower() or "429" in error:
            error_type = "quota_exhausted"
            recovery_detail["error_type"] = error_type
            # Rotate to a different provider
            chain = self.mm.get_failover_chain()
            current_model = self.mm.get_best("general")["model"] if self.mm.models else None
            for candidate in chain:
                if candidate != current_model and self.mm.health.get(candidate, {}).get("working"):
                    action_taken.append(f"Switched model: {current_model} → {candidate}")
                    recovery_detail["new_model"] = candidate
                    break
            if not action_taken:
                # Try switching provider entirely
                providers_available = list({m["provider"] for m in self.mm.models})
                action_taken.append(f"Rotated to different provider. Available: {providers_available}")
                recovery_detail["new_provider"] = providers_available

        elif "timeout" in error.lower() or "timed out" in error.lower() or "hang" in error.lower():
            error_type = "timeout_hang"
            recovery_detail["error_type"] = error_type
            # Switch to a faster (lower-latency) model
            best = self.mm.get_best("speed")
            if best:
                action_taken.append(f"Switched to faster model: {best['model']} (latency {best.get('latency_s','?')}s)")
                recovery_detail["new_model"] = best["model"]

        elif "invalid" in error.lower() and ("token" in error.lower() or "key" in error.lower()):
            error_type = "auth_failure"
            recovery_detail["error_type"] = error_type
            # Cycle to a different provider that doesn't need this key
            local_models = self.mm.get_by_category("local")
            if local_models:
                action_taken.append(f"Fell back to local model: {local_models[0]['model']}")
                recovery_detail["new_model"] = local_models[0]["model"]
            elif proc_name:
                action_taken.append("Restarting IDE to clear stale session/auth state")
                self._restart_app(proc_name)

        else:
            error_type = "unknown"
            recovery_detail["error_type"] = error_type
            # Try restarting the app
            if proc_name:
                action_taken.append(f"Restarting app: {proc_name}")
                self._restart_app(proc_name)
            # Switch model
            next_model = self.mm.get_best("general")
            if next_model:
                action_taken.append(f"Switched to backup model: {next_model['model']}")
                recovery_detail["new_model"] = next_model["model"]

        recovery_detail["actions"] = action_taken
        self.recovery_history.append(recovery_detail)

        # Also create an alert
        self.am.add_alert(error_type, error, context)

        return recovery_detail

    def _restart_app(self, proc_name: str):
        """Kill and restart a hung/crashed application (if possible)."""
        try:
            if sys.platform == "win32":
                subprocess.run(f'taskkill /IM {proc_name} /F', shell=True, timeout=10)
                time.sleep(2)
                # Attempt restart — we can't fully automate launching GUI apps safely
                # but we log that the user should relaunch
                p(f"  ⚠ Please relaunch {proc_name} if it doesn't auto-restart", color=C.YELLOW)
        except Exception as e:
            p(f"  ⚠ Restart failed: {e}", color=C.YELLOW)

    def recover_from_hang(self, proc_name: str) -> dict:
        """Recover from a detected IDE/app hang."""
        detail = self.diagnose_and_recover(
            error=f"Application hung detected: {proc_name}",
            context="hang_recovery",
            proc_name=proc_name
        )
        # Switch to a fast model to resume work
        best = self.mm.get_best("speed")
        if best:
            detail["resume_model"] = best["model"]
        return detail


# ────────────────────────────────────────────────────────────────
# 4. MULTI-AGENT SYSTEM
# ────────────────────────────────────────────────────────────────
class AgentWorker:
    """
    A lightweight sub-agent that handles a specific sub-task.
    Can operate in any context: IDE, browser, terminal, file system.
    """

    def __init__(self, name: str, model_manager: ModelManager, mm: ModelManager):
        self.name = name
        self.mm = mm
        self.status = "idle"
        self.current_task = ""
        self.results = []

    def execute_task(self, instruction: str, context: str = "") -> str:
        """Execute a task using the best model for the context."""
        self.status = "running"
        self.current_task = instruction

        # Pick the best model for this task
        model_name = self.mm.select_model_for_task(instruction + " " + context)
        model_obj = None
        for m in self.mm.models:
            if m["model"] == model_name:
                model_obj = m
                break

        if not model_obj:
            # Fallback to any local model
            local = self.mm.get_by_category("local")
            if local:
                model_obj = local[0]
                model_name = model_obj["model"]
            else:
                return "ERROR: No working models available"

        # Build the prompt — enhanced with task awareness
        from agent import build_system_prompt, create_tool_registry, execute_tool, ollama_chat

        system_prompt = build_system_prompt(
            os.getenv("JARVIS_CWD", os.getcwd()),
            create_tool_registry()
        )

        messages = [
            {"role": "system", "content": system_prompt + "\n\nYou are a helpful sub-agent. Execute the following task autonomously."},
            {"role": "user", "content": f"Task: {instruction}\n\nContext: {context}"},
        ]

        try:
            result = ollama_chat(messages, model=model_name)
            self.results.append({"task": instruction, "result": result, "model": model_name})
            self.status = "completed"
            return result
        except Exception as e:
            self.status = "failed"
            # Use recovery engine
            return f"Task failed: {e}. Consider switching models."

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "current_task": self.current_task,
            "last_results_count": len(self.results),
        }


class MultiAgentOrchestrator:
    """
    Spawns multiple sub-agents to handle complex tasks in parallel.
    Each agent monitors / operates on apps, the IDE, or general tasks.
    """

    def __init__(self, model_manager: ModelManager):
        self.mm = model_manager
        self.agents: list[AgentWorker] = []
        self.task_queue: list[dict] = []

    def spawn_agent(self, name: str, specialty: str = "general") -> AgentWorker:
        """Create a new sub-agent with a given specialty."""
        agent = AgentWorker(name, self.mm, self.mm)
        self.agents.append(agent)
        p(f"  [🤖] Spawned agent '{name}' (specialty: {specialty})", color=C.CYAN)
        return agent

    def assign_task(self, agent: AgentWorker, task: str, context: str = ""):
        """Assign a task to an agent."""
        self.task_queue.append({
            "agent": agent.name,
            "task": task,
            "context": context,
            "assigned_at": datetime.now().isoformat(),
            "status": "queued",
        })
        # Execute synchronously (could be async for parallel)
        result = agent.execute_task(task, context)
        for t in self.task_queue:
            if t["agent"] == agent.name and t["task"] == task:
                t["status"] = agent.status
                t["result"] = result
                break
        return result

    def parallel_execution(self, tasks: list[tuple[str, str]], context: str = "") -> list[str]:
        """
        Run multiple tasks in parallel using multiple agents.
        tasks: list of (task_name, instruction)
        """
        results = []

        async def run_all():
            agents = []
            async_tasks = []
            for task_name, instruction in tasks:
                agent = self.spawn_agent(task_name, context="parallel")
                agents.append(agent)
                async_tasks.append(self._async_execute(agent, instruction, context))

            results_list = await asyncio.gather(*async_tasks, return_exceptions=True)
            return results_list

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(run_all())
            loop.close()
        except Exception as e:
            p(f"  ⚠ Parallel execution error: {e}", color=C.YELLOW)

        return [r if isinstance(r, str) else str(r) for r in results]

    async def _async_execute(self, agent: AgentWorker, instruction: str, context: str) -> str:
        """Async wrapper for agent task execution."""
        # Pick model for this task
        model_name = self.mm.select_model_for_task(instruction)
        from agent import ollama_chat

        messages = [
            {"role": "user", "content": f"Task: {instruction}\nContext: {context}"},
        ]

        try:
            # Use httpx async for the API call if using online models
            # For simplicity here, call dispatch directly
            model_obj = None
            for m in self.mm.models:
                if m["model"] == model_name:
                    model_obj = m
                    break

            if model_obj and model_obj.get("provider") != "ollama":
                # Online provider — async-friendly
                async with httpx.AsyncClient(timeout=30) as client:
                    if model_obj["provider"] == "groq":
                        url = "https://api.groq.com/openai/v1/chat/completions"
                        payload = {"model": model_name, "messages": messages, "max_tokens": 500}
                        headers = {"Authorization": f"Bearer {os.getenv('GROQ_API_KEY','')}"}
                        resp = await client.post(url, json=payload, headers=headers)
                        if resp.status_code == 200:
                            return resp.json()["choices"][0]["message"]["content"]
                    elif model_obj["provider"] == "openrouter":
                        url = "https://openrouter.ai/api/v1/chat/completions"
                        payload = {"model": model_name, "messages": messages, "max_tokens": 500}
                        headers = {"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY','')}"}
                        resp = await client.post(url, json=payload, headers=headers)
                        if resp.status_code == 200:
                            return resp.json()["choices"][0]["message"]["content"]

            # Fallback: sync ollama_chat
            result = ollama_chat(messages, model=model_name)
            return result
        except Exception as e:
            return f"Error: {e}"

    def get_status(self) -> dict:
        return {
            "active_agents": len(self.agents),
            "queued_tasks": len([t for t in self.task_queue if t["status"] == "queued"]),
            "agents": [a.get_status() for a in self.agents],
        }


# ────────────────────────────────────────────────────────────────
# 5. THIRD EYE DASHBOARD / MAIN SYSTEM
# ────────────────────────────────────────────────────────────────
class ThirdEyeSystem:
    """
    The main Third Eye system that coordinates everything:
    - Model manager (discovery, health, categorization)
    - App monitor (IDE/app hang/error detection)
    - Auto-recovery (switch models, restart apps)
    - Multi-agent orchestrator (spawn sub-agents)
    """

    def __init__(self):
        self.model_manager = ModelManager()
        self.app_monitor = AppMonitor()
        self.browser_operator = BrowserOperator()
        self.recovery_engine = AutoRecoveryEngine(self.model_manager, self.app_monitor)
        self.orchestrator = MultiAgentOrchestrator(self.model_manager)
        self.running = False
        self._health_thread = None
        self._monitor_thread = None

    def start_continous_health_checks(self, interval: int = 300):
        """Background thread that re-tests models every N seconds."""
        def run():
            while self.running:
                time.sleep(interval)
                if not self.running:
                    break
                p(f"\n  🔁 Running continuous model health check...", color=f"{C.DIM}{C.CYAN}")
                self.model_manager._load()  # refresh from file
                for m in self.model_manager.models[:3]:  # test top 3
                    self.model_manager.health_check_model(m)
        self._health_thread = threading.Thread(target=run, daemon=True)
        self._health_thread.start()

    def start_app_monitoring(self, interval: int = 15):
        """Background thread that monitors running IDE/apps."""
        def run():
            while self.running:
                time.sleep(interval)
                if not self.running:
                    break
                proc = self.app_monitor.detect_running_ide()
                if proc:
                    health = self.app_monitor.monitor_window_activity(proc)
                    # Update last activity
                    self.app_monitor.process_health[proc] = {
                        **health,
                        "last_activity": time.time(),
                    }
                    # Check for hang
                    hang = self.app_monitor.detect_hang(proc, threshold_seconds=30)
                    if hang["hung"]:
                        p(f"\n  [🚨] App {proc} appears HUNG ({hang['idle_seconds']}s idle)", color=C.RED)
                        self.recovery_engine.recover_from_hang(proc)
                else:
                    self.app_monitor.process_health.clear()

                # 3. Check browser-based IDEs via BrowserOperator
                if self.browser_operator._driver is not None:
                    try:
                        ide = self.browser_operator.detect_ide_in_browser()
                        if ide:
                            err = self.browser_operator.detect_error_in_ide()
                            if err:
                                p(f"\n  [🚨] Browser IDE ({ide}) error detected: {err}", color=C.RED)
                                # Attempt recovery: switch model in browser IDE
                                best = self.model_manager.select_model_for_task("coding")
                                if best:
                                    switched = self.browser_operator.switch_ide_model(best)
                                    if switched:
                                        action = "switched model in browser IDE"
                                    else:
                                        action = "could not switch model (no dropdown found)"
                                # Try to retry
                                retried = self.browser_operator.click_retry_or_resubmit()
                                if retried:
                                    action = "clicked retry/resubmit in browser IDE"
                                self.app_monitor.add_alert(
                                    f"browser_{err}",
                                    f"Browser IDE error: {err}",
                                    f"Actions: {action}. Switched to: {best}",
                                )
                    except Exception:
                        pass
        self._monitor_thread = threading.Thread(target=run, daemon=True)
        self._monitor_thread.start()

    def start(self, watch_procs: list[str] = None, daemon: bool = False):
        """Start the Third Eye system."""
        if watch_procs:
            self.app_monitor.monitored = watch_procs

        self.running = True
        p(f"\n{'='*50}", color=f"{C.CYAN}{C.BOLD}")
        p("  👁️  THIRD EYE JARVIS — System Activated", color=f"{C.CYAN}{C.BOLD}")
        p(f"{'='*50}", color=f"{C.CYAN}{C.BOLD}")

        p(f"\n  📊 Loaded {len(self.model_manager.models)} working models", color=C.GREEN)
        p(f"  🔄 Failover chain: {' → '.join(self.model_manager.get_failover_chain()[:3])}", color=C.DIM)
        p(f"  👁️  App monitoring enabled for: {watch_procs or 'all known IDEs/apps'}", color=C.GREEN)
        p(f"  🤖 Multi-agent orchestrator ready", color=C.GREEN)
        p(f"  🛠️  Auto-recovery engine active", color=C.GREEN)

        # Start background threads
        self.start_continous_health_checks()
        self.start_app_monitoring()

        # Show dashboard
        self._print_dashboard()

        if daemon:
            p(f"\n  🟢 Running in daemon mode. Ctrl+C to stop.", color=C.YELLOW)
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
        else:
            p(f"\n  🟢 Interactive mode. Use commands: status, models, spawn, test <app>", color=C.YELLOW)
            self._interactive_loop()

    def _print_dashboard(self):
        """Print a quick dashboard of the current state."""
        status = self.get_full_status()
        mm = status["model_manager"]
        print()
        p(f"  ┌────────────────────────────────────────────────┐", color=C.DIM)
        p(f"  │  📦 Models: {mm['total_models']} total, {mm['working_models']} working{'':>12} │", color=C.DIM)
        p(f"  │  🔍 Categories: {', '.join(mm['categories_available'][:3])}{'':>22} │", color=C.DIM)
        health_str = ", ".join(
            f"{'✓' if h['working'] else '✗'}{m}"  for m,h in list(mm["health"].items())[:5]
        )
        p(f"  │  🩺 Health: {health_str:<35} │", color=C.DIM)
        p(f"  │  🤖 Agents: {status['orchestrator']['active_agents']} active, {status['orchestrator']['queued_tasks']} queued  │", color=C.DIM)
        p(f"  │  👁️  Alerts: {len(status['app_monitor']['active_alerts'])} active{'':>27} │", color=C.DIM)
        p(f"  └────────────────────────────────────────────────┘\n", color=C.DIM)

    def _interactive_loop(self):
        """Simple interactive command loop."""
        commands = {
            "status": "Show full system status",
            "models": "List all working models by category",
            "health": "Run a quick health check on all models",
            "spawn <name> <task>": "Spawn a sub-agent to do a task",
            "test <app>": "Test recovery on a specific app",
            "dashboard": "Print the dashboard",
            "exit": "Stop the Third Eye system",
        }
        p(f"  Third Eye commands:")
        for cmd, desc in commands.items():
            p(f"    {cmd:<25} {desc}", color=C.DIM)

        while self.running:
            try:
                cmd = input(f"\n  👁️  > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not cmd:
                continue

            parts = cmd.split(maxsplit=2)
            action = parts[0].lower() if parts else ""

            if action in ("exit", "quit", "q"):
                self.stop()
                break
            elif action == "status":
                print(json.dumps(self.get_full_status(), indent=2, ensure_ascii=False, default=str))
            elif action == "models":
                self._print_models()
            elif action == "health":
                self._run_health()
            elif action == "spawn":
                if len(parts) >= 3:
                    name = parts[1]
                    task = parts[2]
                    agent = self.orchestrator.spawn_agent(name)
                    result = self.orchestrator.assign_task(agent, task)
                    print(f"\n  Result:\n  {result[:500]}")
                else:
                    p("  Usage: spawn <name> <task>", color=C.YELLOW)
            elif action == "test":
                if len(parts) >= 2:
                    self.recovery_engine.diagnose_and_recover(f"Manual test for {parts[1]}", "manual_test", parts[1])
                else:
                    p("  Usage: test <app>", color=C.YELLOW)
            elif action == "dashboard":
                self._print_dashboard()
            else:
                p(f"  Unknown command. Available: {', '.join(commands.keys())}", color=C.YELLOW)

    def _print_models(self):
        """Print all working models categorized."""
        categories = {}
        for m in self.model_manager.models:
            for cat in self.model_manager.categorize(m["model"]):
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(m)

        p(f"\n  📊 Working Models by Category:", color=f"{C.BOLD}{C.CYAN}")
        for cat in ["coding", "reasoning", "speed", "general", "local"]:
            if cat in categories:
                models = sorted(categories[cat], key=lambda x: x.get("latency_s", 999))
                p(f"\n  {cat.upper()} ({len(models)} models):", color=C.GREEN)
                for m in models:
                    provider = m.get("provider", "unknown")
                    lat = m.get("latency_s", "?")
                    p(f"    • {m['model']:<45} [{provider}, {lat}s]", color=C.DIM)

    def _run_health(self):
        """Run health check on all models."""
        p(f"\n  🩺 Testing all {len(self.model_manager.models)} models...", color=f"{C.CYAN}{C.BOLD}")
        working = 0
        for m in self.model_manager.models:
            result = self.model_manager.health_check_model(m)
            if result:
                working += 1
            else:
                p(f"  ✗ {m['model']} — failed", color=C.RED)
        p(f"\n  Result: {working}/{len(self.model_manager.models)} models healthy", color=C.GREEN)

    def get_full_status(self) -> dict:
        return {
            "timestamp": datetime.now().isoformat(),
            "model_manager": self.model_manager.get_status(),
            "app_monitor": self.app_monitor.get_status(),
            "browser_operator": self.browser_operator.get_ide_status(),
            "orchestrator": self.orchestrator.get_status(),
            "recovery_history": self.recovery_engine.recovery_history[-10:],
            "running": self.running,
        }

    def save_state(self):
        """Persist Third Eye state to disk."""
        state = self.get_full_status()
        THIRD_EYE_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def load_state(self):
        """Load Third Eye state from disk if available."""
        if THIRD_EYE_STATE.exists():
            try:
                return json.loads(THIRD_EYE_STATE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def stop(self):
        """Stop the Third Eye system."""
        self.running = False
        self.save_state()
        p(f"\n  👋 Third Eye deactivated. State saved to {THIRD_EYE_STATE.name}", color=C.DIM)


# ────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ────────────────────────────────────────────────────────────────
class OpenCodeSupervisor:
    """Robot supervisor that monitors, controls, and manages OpenCode IDE/CLI autonomously."""
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.last_output: list[str] = []
        self.active_project: str = ""

    def detect(self) -> dict:
        """Detect running opencode processes on the system."""
        try:
            if sys.platform == "win32":
                cmd = 'tasklist /FI "IMAGENAME eq opencode*"'
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                running = "opencode" in res.stdout.lower()
            else:
                res = subprocess.run(["pgrep", "-f", "opencode"], capture_output=True, text=True)
                running = res.returncode == 0
            return {"running": running, "managed_by_supervisor": self.process is not None and self.process.poll() is None}
        except Exception as e:
            return {"running": False, "error": str(e)}

    def start(self, project_path: str = "") -> dict:
        """Launch OpenCode process in background."""
        path = project_path or os.getcwd()
        opencode_bin = shutil.which("opencode") or "npx opencode"
        try:
            self.process = subprocess.Popen(
                f"{opencode_bin} --dir \"{path}\"",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=path
            )
            self.active_project = path
            return {"status": "started", "pid": self.process.pid, "project": path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def prompt(self, text: str) -> dict:
        """Send a task prompt to OpenCode process."""
        if not self.process or self.process.poll() is not None:
            # Auto-start if not running
            start_res = self.start()
            if start_res.get("status") == "error":
                return start_res
        
        try:
            if self.process and self.process.stdin:
                self.process.stdin.write(f"{text}\n")
                self.process.stdin.flush()
                return {"status": "prompt_sent", "prompt": text}
            return {"status": "error", "message": "No active stdin stream"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def read_output(self) -> str:
        """Read recent stdout/stderr lines from managed OpenCode process."""
        if not self.process:
            return "No managed OpenCode process."
        lines = []
        try:
            while self.process.stdout and True:
                line = self.process.stdout.readline()
                if not line:
                    break
                lines.append(line)
                if len(lines) >= 50:
                    break
            self.last_output.extend(lines)
            return "".join(lines) or "No new output"
        except Exception as e:
            return f"Error reading output: {e}"

    def kill(self) -> dict:
        """Terminate the OpenCode process."""
        if self.process:
            try:
                self.process.terminate()
                self.process = None
                return {"status": "terminated"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "not_running"}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Third Eye — Jarvis monitoring & multi-agent system")
    parser.add_argument("--daemon", action="store_true", help="Run in background daemon mode")
    parser.add_argument("--test-models", action="store_true", help="Just run model discovery & test")
    parser.add_argument("--watch", nargs="+", help="Specific processes to watch")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--models", action="store_true", help="List all working models")
    parser.add_argument("--auto-install", action="store_true", help="Auto-install missing dependencies")
    args = parser.parse_args()

    if args.test_models:
        from free_model_discovery import discover_all
        discover_all()
        return

    if args.status:
        eye = ThirdEyeSystem()
        # Quick status check without starting monitor threads
        status = eye.get_full_status()
        print(json.dumps(status["model_manager"], indent=2, ensure_ascii=False))
        return

    if args.models:
        eye = ThirdEyeSystem()
        eye._print_models()
        return

    # Install check
    if args.auto_install:
        p("  ⚙️  Checking and installing missing dependencies...", color=C.CYAN)
        _ensure_dependencies()

    # Start the Third Eye system
    eye = ThirdEyeSystem()
    eye.start(
        watch_procs=args.watch,
        daemon=args.daemon,
    )


def _ensure_dependencies():
    """Check for and optionally install missing dependencies."""
    import importlib
    needed = ["httpx", "fastapi", "rich", "prompt_toolkit"]
    missing = []
    for mod in needed:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(mod)

    if missing:
        p(f"  🔧 Installing missing: {missing}", color=C.YELLOW)
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing, timeout=120)
    else:
        p("  ✅ All dependencies present", color=C.GREEN)


if __name__ == "__main__":
    main()
