# DevMind AI Studio — Complete Standalone Architecture

DevMind AI Studio is an ultra-powerful, 100% offline, zero-dependency, multi-agent AI coding IDE. It combines the best of VS Code, Cursor, Agent Town, and Hermes AI Agent Runtime into a single portable workspace.

---

## 🛠️ Complete Integrated Ecosystem Architecture

```
                                  ┌──────────────────────────────────────────┐
                                  │      DevMind AI Web IDE (Port 7860)      │
                                  │   CodeMirror 6 + Multi-Tab UI + Audio    │
                                  └────────────────────┬─────────────────────┘
                                                       │
         ┌─────────────────────────────────────────────┼─────────────────────────────────────────────┐
         ▼                                             ▼                                             ▼
┌──────────────────┐                         ┌──────────────────┐                         ┌──────────────────┐
│   Agent Town     │                         │   "DEV" Voice    │                         │ Hermes Multi-    │
│  Pixel Office    │                         │  Wake Word Engine│                         │ Channel Engine   │
│  (Port 3000)     │                         │(dev_wake_word_bg)│                         │ (20 Platforms)   │
└────────┬─────────┘                         └────────┬─────────┘                         └────────┬─────────┘
         │                                            │                                            │
         └────────────────────────────────────────────┼────────────────────────────────────────────┘
                                                      │
                                                      ▼
                                   ┌──────────────────────────────────────┐
                                   │      Embedded Portable Runtimes      │
                                   ├──────────────────────────────────────┤
                                   │  • Portable Python 3.11              │
                                   │  • Standalone Node.exe               │
                                   │  • Headless Chromium Engine          │
                                   │  • Standalone FFmpeg Media Engine    │
                                   │  • Hermes Trajectory Compressor      │
                                   │  • 68 Hermes Agent Skill Packages    │
                                   │  • 19 Infrastructure Plugins        │
                                   └──────────────────────────────────────┘
```

---

## 🚀 Key Integrated Features

### 1. 🎮 Integrated 2D Pixel Office Workspace
- Embedded **Agent Town (`http://localhost:3000`)** directly inside the DevMind Activity Bar (`🎮 Pixel Office` tab).
- Visualize multi-agent swarms working at desks in real-time.

### 2. 🎙️ "DEV" Background Voice Assistant
- Continuously listens for **"Dev"**, **"Hey Dev"**, or **"DevMind"**.
- Triggers instant AI coding actions and parses voice commands without pressing keys.

### 3. ⚡ Hermes Trajectory Context Compressor
- Based on the Hermes Trajectory Compression Strategy (`history_compressor.py`).
- Protects System Prompts + First Turn + Last N Turns while summarizing intermediate tool calls.
- Reduces token usage by **up to 90%** during long coding sessions.

### 4. 🌐 20 Messaging Platform Adapters
- Includes channel bridges for **Telegram, Discord, Slack, WhatsApp, Email, SMS, Google Chat, Teams, Matrix**, and more.
- Allows DevMind to operate as a remote coding bot on your favorite chat app.

### 5. 🧳 100% Portable & Zero-Dependency Execution
- Contains standalone `python-embedded`, `node.exe`, `agent-browser.exe`, `ffmpeg.exe`, and `chromium`.
- Copy `E:\coding-assistant` to any USB Pendrive or PC and run `start_portable.bat` — **no installation required!**

### 6. 📦 1-Click Desktop Executable Generator
- Double-click [`build_portable_exe.bat`](file:///E:/coding-assistant/build_portable_exe.bat) to package the entire IDE into a standalone Windows `.exe` application.

---

## 📌 Quick Launch Commands

| Action | Command / Link |
|---|---|
| 🎮 **Launch Everything (IDE + Pixel + Voice)** | 👉 **[`start_portable.bat`](file:///E:/coding-assistant/start_portable.bat)** |
| 🔍 **Run Asset Importer & Deep Scanner** | 👉 **[`run_importer.bat`](file:///E:/coding-assistant/run_importer.bat)** |
| 📦 **Build Windows Executable (.exe)** | 👉 **[`build_portable_exe.bat`](file:///E:/coding-assistant/build_portable_exe.bat)** |
| 🌐 **DevMind Web IDE URL** | **[http://localhost:7860](http://localhost:7860)** |
| 🎮 **Agent Town Workspace URL** | **[http://localhost:3000](http://localhost:3000)** |

---

## 📄 Forensic Audit Report
Detailed forensic scan report containing endpoints, keys, and internal router configurations:
👉 **[`stonic_deep_scan_report.txt`](file:///E:/coding-assistant/stonic_deep_scan_report.txt)**