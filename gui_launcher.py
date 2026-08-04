"""
Agentic Dev System — Desktop GUI Control Panel
Provides a graphical control panel to monitor and manage the agentic dev system.
"""
import os
import sys
import subprocess
import threading
import time
import json
import webbrowser
from pathlib import Path
from datetime import datetime
from tkinter import ttk, messagebox

import tkinter as tk
from tkinter import filedialog

DEFAULT_PROJECT_ROOT = r"C:\xampp\htdocs\apsdreamhome"
WORKING_DIR = str(Path(__file__).parent)
LOG_FILE = os.path.join(WORKING_DIR, "logs", "agent_heartbeat.log")
STATE_FILE = os.path.join(WORKING_DIR, "state", "agent_state.json")
CONFIG_FILE = os.path.join(WORKING_DIR, "config.json")
PY_AGENTIC_DIR = os.path.join(WORKING_DIR, "py_agentic")


class AgenticDevGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Agentic Dev System — Control Panel")
        self.root.geometry("820x620")
        self.root.resizable(False, False)

        self.server_process = None
        self.is_running = False

        self.BG_COLOR = "#0f172a"
        self.FG_COLOR = "#f8fafc"
        self.CARD_BG = "#1e293b"
        self.BORDER = "#334155"
        self.ACCENT = "#6366f1"
        self.GREEN = "#10b981"
        self.RED = "#ef4444"
        self.AMBER = "#f59e0b"

        self.root.configure(bg=self.BG_COLOR)

        header = tk.Frame(root, bg=self.BG_COLOR, pady=12)
        header.pack(fill="x")

        tk.Label(
            header, text="Agentic Dev System",
            font=("Segoe UI", 20, "bold"), bg=self.BG_COLOR, fg="#a5b4fc"
        ).pack()

        tk.Label(
            header, text="Autonomous multi-agent development pipeline for APS Dream Home",
            font=("Segoe UI", 10), bg=self.BG_COLOR, fg="#94a3b8"
        ).pack()

        notebook = ttk.Notebook(root, style="Dark.TNotebook")
        notebook.pack(fill="both", expand=True, padx=20, pady=10)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Dark.TNotebook", background=self.BG_COLOR, borderwidth=0)
        self.style.configure(
            "Dark.TFrame", background=self.CARD_BG, borderwidth=0
        )
        self.style.configure(
            "Dark.TNotebook.Tab",
            background=self.CARD_BG,
            foreground=self.FG_COLOR,
            padding=[12, 6],
            font=("Segoe UI", 10, "bold"),
        )
        self.style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", self.ACCENT)],
            foreground=[("selected", self.FG_COLOR)],
        )

        self._build_dashboard_tab(notebook)
        self._build_dashboard_tab_extra(notebook)
        self._build_config_tab(notebook)
        self._build_logs_tab(notebook)

        self._start_auto_refresh()

        self.status_bar = tk.Label(
            root,
            text="Ready",
            font=("Segoe UI", 9, "bold"),
            bg=self.BG_COLOR,
            fg="#94a3b8",
            anchor="w",
            padx=20,
            pady=8,
        )
        self.status_bar.pack(fill="x")

        self._load_state()

    def _build_dashboard_tab(self, notebook):
        frame = ttk.Frame(notebook, style="Dark.TFrame")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        stats_frame = tk.Frame(frame, bg=self.CARD_BG, bd=1, relief="solid",
                               highlightbackground=self.BORDER, highlightthickness=1)
        stats_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            stats_frame, text="Quick Stats",
            font=("Segoe UI", 12, "bold"), bg=self.CARD_BG, fg=self.FG_COLOR
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.stats_grid = tk.Frame(stats_frame, bg=self.CARD_BG)
        self.stats_grid.pack(fill="x", padx=15, pady=(0, 15))

        self.stat_labels = {}
        stat_fields = [
            ("cycles", "Cycles", "0"),
            ("project", "Project", ""),
            ("last_run", "Last Run", ""),
            ("ollama", "AI Backend", ""),
            ("agents", "Agents", "7"),
        ]
        for i, (key, label, default) in enumerate(stat_fields):
            row = i // 3
            col = i % 3
            lbl = tk.Label(
                self.stats_grid,
                text=f"{label}:\n{default}",
                font=("Segoe UI", 9), bg=self.CARD_BG, fg="#cbd5e1",
                justify="center", anchor="center"
            )
            lbl.grid(row=row, column=col, padx=10, pady=8, sticky="nsew")
            self.stat_labels[key] = lbl
        for i in range(3):
            self.stats_grid.grid_columnconfigure(i, weight=1)

        btn_frame = tk.Frame(frame, bg=self.CARD_BG, bd=1, relief="solid",
                             highlightbackground=self.BORDER, highlightthickness=1)
        btn_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            btn_frame, text="Controls",
            font=("Segoe UI", 12, "bold"), bg=self.CARD_BG, fg=self.FG_COLOR
        ).pack(anchor="w", padx=15, pady=(15, 10))

        controls_inner = tk.Frame(btn_frame, bg=self.CARD_BG)
        controls_inner.pack(fill="x", padx=15, pady=(0, 15))

        self.start_btn = tk.Button(
            controls_inner, text="▶ Start Agentic System",
            command=self.start_system,
            bg=self.GREEN, fg="white", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=15, pady=8, cursor="hand2"
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = tk.Button(
            controls_inner, text="⏹ Stop",
            command=self.stop_system,
            bg=self.RED, fg="white", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=15, pady=8, cursor="hand2",
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=(0, 10))

        tk.Button(
            controls_inner, text="🔍 Refresh State",
            command=self._load_state,
            bg=self.ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=15, pady=8, cursor="hand2"
        ).pack(side="left")

        links_frame = tk.Frame(frame, bg=self.CARD_BG, bd=1, relief="solid",
                               highlightbackground=self.BORDER, highlightthickness=1)
        links_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            links_frame, text="Quick Links",
            font=("Segoe UI", 12, "bold"), bg=self.CARD_BG, fg=self.FG_COLOR
        ).pack(anchor="w", padx=15, pady=(15, 10))

        links_inner = tk.Frame(links_frame, bg=self.CARD_BG)
        links_inner.pack(fill="x", padx=15, pady=(0, 15))

        link_btns = [
            ("🌐 Open Admin Panel", self._open_admin),
            ("🧪 Run E2E Tests", self._run_e2e),
            ("🔓 OpenCode IDE", self._launch_opencode),
            ("📁 Open Project Folder", self._open_project),
            ("📄 AGENTS.md", self._open_agents_md),
        ]
        for text, cmd in link_btns:
            tk.Button(
                links_inner, text=text, command=cmd,
                bg=self.CARD_BG, fg=self.FG_COLOR, font=("Segoe UI", 9),
                relief="solid", borderwidth=1,
                activebackground=self.ACCENT, activeforeground="white",
                padx=12, pady=6, cursor="hand2"
            ).pack(anchor="w", pady=3)

        notebook._dashboard_frame = frame

    def _build_config_tab(self, notebook):
        frame = ttk.Frame(notebook, style="Dark.TFrame")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        config_frame = tk.Frame(frame, bg=self.CARD_BG, bd=1, relief="solid",
                                highlightbackground=self.BORDER, highlightthickness=1)
        config_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(
            config_frame, text="Configuration",
            font=("Segoe UI", 14, "bold"), bg=self.CARD_BG, fg=self.FG_COLOR
        ).pack(anchor="w", padx=15, pady=(15, 15))

        self.config_vars = {}

        configs = self._load_config()
        form = tk.Frame(config_frame, bg=self.CARD_BG)
        form.pack(fill="x", padx=15, pady=(0, 15))

        row = 0
        for key, label_text, entry_width in [
            ("project_root", "Project Root:", 55),
            ("mode", "Mode:", 20),
            ("cycles", "Max Cycles:", 15),
            ("interval", "Interval (sec):", 15),
        ]:
            tk.Label(form, text=label_text, font=("Segoe UI", 9, "bold"),
                      bg=self.CARD_BG, fg=self.FG_COLOR).grid(row=row, column=0, sticky="w", pady=6)
            var = tk.StringVar(value=configs.get(key, ""))
            if key in ("cycles", "interval"):
                entry = tk.Entry(form, textvariable=var, font=("Consolas", 9),
                                 width=entry_width, bg="#0f172a", fg="#38bdf8",
                                 insertbackground="white")
            elif key == "mode":
                entry = ttk.Combobox(form, textvariable=var, values=["continuous", "single"],
                                     state="readonly", width=entry_width - 2, font=("Segoe UI", 9))
            else:
                entry = tk.Entry(form, textvariable=var, font=("Segoe UI", 9),
                                 width=entry_width, bg="#0f172a", fg="#38bdf8",
                                 insertbackground="white")
            entry.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=6)
            self.config_vars[key] = var
            row += 1

        self.save_config_btn = tk.Button(
            form, text="💾 Save Config",
            command=self._save_config,
            bg="#10b981", fg="white", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=15, pady=6, cursor="hand2"
        )
        self.save_config_btn.grid(row=row, column=0, columnspan=2, sticky="w", pady=(15, 0))

        tk.Label(
            config_frame,
            text="AI Model (Ollama): " + (configs.get("model", "qwen2.5:7b")),
            font=("Segoe UI", 9), bg=self.CARD_BG, fg="#94a3b8"
        ).pack(anchor="w", padx=15, pady=(10, 0))

        notebook._config_frame = frame

    def _build_dashboard_tab_extra(self, notebook):
        """Add a live activity monitor widget to the dashboard."""
        dash = getattr(notebook, "_dashboard_frame", None)
        if not dash:
            return

        activity_frame = tk.Frame(dash, bg=self.CARD_BG, bd=1, relief="solid",
                                  highlightbackground=self.BORDER, highlightthickness=1)
        activity_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(
            activity_frame, text="Live Agent Activity",
            font=("Segoe UI", 12, "bold"), bg=self.CARD_BG, fg=self.FG_COLOR
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.activity_text = tk.Text(activity_frame, bg="#0f172a", fg="#e2e8f0",
                                     font=("Consolas", 8), wrap="word",
                                     height=8, state="disabled",
                                     borderwidth=0, highlightthickness=0)
        self.activity_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def _start_auto_refresh(self):
        """Start auto-refresh of dashboard stats and activity log."""
        self._auto_refresh()

    def _auto_refresh(self):
        """Refresh dashboard every 5 seconds if running."""
        if self.is_running:
            self._load_state()
            self._load_activity()
        self.root.after(5000, self._auto_refresh)

    def _load_activity(self):
        """Load recent activity from log file."""
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                recent = "".join(lines[-20:])
                self.activity_text.config(state="normal")
                self.activity_text.delete("1.0", tk.END)
                self.activity_text.insert(tk.END, recent)
                self.activity_text.see(tk.END)
                self.activity_text.config(state="disabled")
        except Exception:
            pass

    def _build_logs_tab(self, notebook):
        frame = ttk.Frame(notebook, style="Dark.TFrame")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        toolbar = tk.Frame(frame, bg=self.CARD_BG, bd=1, relief="solid",
                           highlightbackground=self.BORDER, highlightthickness=1)
        toolbar.pack(fill="x", padx=10, pady=(0, 5))

        tk.Button(
            toolbar, text="🔄 Refresh",
            command=self._load_logs,
            bg="#334155", fg="white", font=("Segoe UI", 9, "bold"),
            relief="flat", padx=12, pady=5, cursor="hand2"
        ).pack(side="left", padx=10, pady=8)

        tk.Button(
            toolbar, text="🗑 Clear Log",
            command=self._clear_log,
            bg="#dc2626", fg="white", font=("Segoe UI", 9, "bold"),
            relief="flat", padx=12, pady=5, cursor="hand2"
        ).pack(side="left", padx=5, pady=8)

        self.log_text = tk.Text(frame, bg="#0f172a", fg="#e2e8f0",
                                font=("Consolas", 8), wrap="none",
                                insertbackground="white", state="disabled",
                                borderwidth=1, highlightbackground="#334155")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        scroll_y = ttk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        scroll_y.pack(side="right", fill="y", padx=(0, 5), pady=5)
        self.log_text.configure(yscrollcommand=scroll_y.set)

        scroll_x = ttk.Scrollbar(frame, orient="horizontal", command=self.log_text.xview)
        scroll_x.pack(side="bottom", fill="x", padx=5, pady=(0, 5))
        self.log_text.configure(xscrollcommand=scroll_x.set)

        self._load_logs()
        notebook._logs_frame = frame

    def _load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            if "scheduler" in config:
                config["mode"] = config["scheduler"].get("mode", "continuous")
                config["interval"] = str(config["scheduler"].get("cycle_interval_ms", 30000) // 1000)
            if "ollama" in config:
                config.setdefault("model", config["ollama"].get("model", "qwen2.5:7b"))
            return config
        except Exception:
            return {
                "project_root": DEFAULT_PROJECT_ROOT,
                "mode": "continuous",
                "cycles": "999",
                "interval": "30",
                "model": "qwen2.5:7b",
            }

    def _save_config(self):
        configs = {}
        for key, var in self.config_vars.items():
            configs[key] = var.get()

        try:
            existing = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    existing = json.load(f)
            if "scheduler" in existing:
                existing["scheduler"]["mode"] = configs["mode"]
                existing["scheduler"]["cycle_interval_ms"] = int(configs["interval"]) * 1000
            existing["project"] = "APS Dream Home"
            existing["project_root"] = configs["project_root"]
            with open(CONFIG_FILE, "w") as f:
                json.dump(existing, f, indent=2)
            messagebox.showinfo("Success", "Config saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config:\n{e}")

    def _load_state(self):
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                for key, label in [("cycles", "Cycles"), ("project", "Project"),
                                   ("last_run", "Last Run"), ("ollama", "AI Backend")]:
                    val = state.get(key, "")
                    if key == "cycles":
                        val = str(val)
                    elif key == "project":
                        val = state.get("project", "APS Dream Home")
                    elif key == "last_run":
                        val = state.get("last_run", "")
                    elif key == "ollama":
                        val = "Available" if self._check_ollama() else "Not available"
                    self.stat_labels.get(key, tk.Label()).config(
                        text=f"{label}:\n{val}" if val else f"{label}: —"
                    )
        except Exception:
            pass

    def _check_ollama(self):
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags")
            urllib.request.urlopen(req, timeout=3)
            return True
        except Exception:
            return False

    def _load_logs(self):
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = "No log file found. Run the agentic system to generate logs.\n"
            self.log_text.config(state="normal")
            self.log_text.delete("1.0", tk.END)
            self.log_text.insert(tk.END, content)
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        except Exception as e:
            self.log_text.config(state="normal")
            self.log_text.delete("1.0", tk.END)
            self.log_text.insert(tk.END, f"Error loading logs: {e}\n")
            self.log_text.config(state="disabled")

    def _clear_log(self):
        if messagebox.askyesno("Confirm", "Clear the log file?"):
            try:
                open(LOG_FILE, "w").close()
                self._load_logs()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def start_system(self):
        self.status_bar.config(text="Starting agentic dev system...", fg="#f59e0b")
        self.start_btn.config(state="disabled", text="⏳ Starting...")

        def run():
            python_exe = sys.executable
            cmd = [python_exe, "main.py", "--cycles", "999", "--interval", "30"]
            self.server_process = subprocess.Popen(
                cmd,
                cwd=PY_AGENTIC_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.is_running = True
            self.root.after(0, lambda: self._on_system_started())
            try:
                self.server_process.wait()
            except Exception:
                pass
            self.root.after(0, lambda: self._on_system_stopped())

        threading.Thread(target=run, daemon=True).start()

    def _on_system_started(self):
        self.is_running = True
        self.start_btn.config(state="disabled", text="▶ Running...")
        self.stop_btn.config(state="normal")
        self.status_bar.config(text="Agentic dev system running", fg="#10b981")

    def _on_system_stopped(self):
        self.is_running = False
        self.start_btn.config(state="normal", text="▶ Start Agentic System")
        self.stop_btn.config(state="disabled")
        self.status_bar.config(text="Stopped", fg="#94a3b8")

    def stop_system(self):
        if self.server_process and self.server_process.poll() is None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except Exception:
                self.server_process.kill()
        self._on_system_stopped()
        self.status_bar.config(text="Stopping...", fg="#f59e0b")

    def _open_admin(self):
        url = f"http://localhost/apsdreamhome/admin/login?test_login=1"
        webbrowser.open(url)

    def _run_e2e(self):
        try:
            result = subprocess.run(
                ["node", "testing/visual_tests/E2E_MASTER_TEST.mjs"],
                cwd=DEFAULT_PROJECT_ROOT,
                capture_output=True, text=True, timeout=300
            )
            messagebox.showinfo("E2E Results",
                f"Return code: {result.returncode}\n\n"
                f"Output (last 2000 chars):\n{result.stdout[-2000:]}")
        except FileNotFoundError:
            messagebox.showerror("Error", "Node.js not found. Please install Node.js.")
        except Exception as e:
            messagebox.showerror("Error", f"E2E failed:\n{e}")

    def _launch_opencode(self):
        try:
            subprocess.Popen([
                "C:\\Users\\abhay\\OpenCode-Starter.bat"
            ], cwd="C:\\Users\\abhay")
        except FileNotFoundError:
            messagebox.showerror("Error", "OpenCode launcher not found.\n"
                "Expected at C:\\Users\\abhay\\OpenCode-Starter.bat")

    def _open_project(self):
        try:
            os.start(DEFAULT_PROJECT_ROOT)
        except Exception:
            webbrowser.open(f"file:///{DEFAULT_PROJECT_ROOT}")

    def _open_agents_md(self):
        path = os.path.join(DEFAULT_PROJECT_ROOT, "AGENTS.md")
        if os.path.exists(path):
            webbrowser.open(f"file:///{path}")
        else:
            messagebox.showerror("Error", "AGENTS.md not found in project root")


def main():
    root = tk.Tk()
    app = AgenticDevGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()