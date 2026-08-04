# Agent Town — Live Pixel AI Workspace Status & Guide

> **Status**: ✅ **ACTIVE & RUNNING**  
> **Local Server URL**: [http://localhost:3000](http://localhost:3000)  
> **WebSocket Gateway**: `ws://localhost:3000/api/gateway` → `ws://127.0.0.1:18789/`  
> **Project Directory**: `E:\coding-assistant\agent-town`

---

## 🚀 One-Click Launchers

You can launch Agent Town at any time using the pre-configured Windows batch launchers:

- 🎮 **Dev Server (Live Edit Mode)**: [`start_agent_town.bat`](file:///E:/coding-assistant/start_agent_town.bat)
- ⚡ **Instant Server (Pre-built)**: [`start_agent_town_instant.bat`](file:///E:/coding-assistant/start_agent_town_instant.bat)
- 🛠️ **Full Setup & Re-clone**: [`setup_agent_town.bat`](file:///E:/coding-assistant/setup_agent_town.bat)

---

## 🛠️ Technology Stack

- **Framework**: Next.js 16 (App Router) + React 19 + TypeScript 5
- **Game Engine**: Phaser 3 (48x48 Pixel Art Engine)
- **Styling**: Tailwind CSS 4 + Custom Pixel HUD
- **Package Manager**: pnpm (515 dependencies installed)
- **Real-Time Gateway**: WebSocket / SSE

---

## 📁 Source Code Structure (`E:\coding-assistant\agent-town`)

```
agent-town/
├── app/                  # Next.js App Router (pages & API routes)
├── components/           # React UI components & Phaser Pixel Canvas
├── public/               # Tilemaps, sprites, sound effects, HUD assets
├── server.ts             # Custom HTTP + WebSocket Proxy Gateway
├── package.json          # Dependencies & npm scripts
└── tsconfig.json         # TypeScript configuration
```

---

## 🌐 Public Tunnels & Remote Access

To expose Agent Town or DevMind IDE to mobile/remote devices:
- **ngrok Launcher**: [`start-ngrok-tunnel.bat`](file:///C:/Users/abhay/start-ngrok-tunnel.bat)
- **ngrok Dashboard**: [http://localhost:4040](http://localhost:4040)
