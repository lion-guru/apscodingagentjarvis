param(
    [switch]$SkipOllama,
    [switch]$SkipOmniRoute,
    [switch]$SkipDevMind,
    [switch]$Help
)

if ($Help) {
    Write-Output @"
DevMind/Jarvis One-Click Startup Script

Usage: .\start.ps1 [options]

Options:
  -SkipOllama      Skip starting Ollama (use if already running)
  -SkipOmniRoute   Skip starting OmniRoute gateway
  -SkipDevMind     Skip starting DevMind server (useful for testing only)
  -Help            Show this help message

This script starts all required services in the correct order:
  1. Ollama (local models) - if not already running
  2. OmniRoute gateway (290+ providers) - if not already running
  3. DevMind server (FastAPI + WebSocket) - always

After all services are up, it runs a quick health check.
"@
    return
}

$ErrorActionPreference = "Stop"
$HOST.UI.RawUI.WindowTitle = "DevMind Startup"

Write-Output ""
Write-Output "============================================"
Write-Output "  DevMind/Jarvis - One-Click Startup"
Write-Output "============================================"
Write-Output ""

# ── Step 1: Ollama ──────────────────────────────────────────────
if (-not $SkipOllama) {
    Write-Output "[1/3] Checking Ollama..."
    try {
        $ollamaResp = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
        if ($ollamaResp.StatusCode -eq 200) {
            Write-Output "  Ollama is already running."
        }
    } catch {
        Write-Output "  Ollama not detected. Starting Ollama..."
        $ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
        if (-not $ollamaPath) {
            Write-Output "  ERROR: Ollama is not installed or not in PATH."
            Write-Output "  Download from https://ollama.com and install it first."
        } else {
            Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -PassThru
            Start-Sleep -Seconds 3
            Write-Output "  Ollama started."
        }
    }
    Write-Output ""
}

# ── Step 2: OmniRoute ───────────────────────────────────────────
if (-not $SkipOmniRoute) {
    Write-Output "[2/3] Checking OmniRoute gateway..."
    try {
        $orResp = Invoke-WebRequest -Uri "http://localhost:20128/v1/models" -TimeoutSec 5
        if ($orResp.StatusCode -eq 200) {
            Write-Output "  OmniRoute is already running on port 20128."
        }
    } catch {
        Write-Output "  OmniRoute not detected. Starting OmniRoute..."

        $omnirouteBin = $null
        $candidates = @(
            (Join-Path $SCRIPT_DIR "omniroute.cmd"),
            (Join-Path $SCRIPT_DIR "node_modules\.bin\omniroute.cmd"),
            (Join-Path $env:LOCALAPPDATA "npm\omniroute.cmd"),
            (Join-Path $env:APPDATA "npm\omniroute.cmd"),
            "omniroute.cmd"
        )
        foreach ($cand in $candidates) {
            if (Test-Path $cand) {
                $omnirouteBin = $cand
                break
            }
        }

        if (-not $omnirouteBin) {
            Write-Output "  ERROR: OmniRoute is not installed."
            Write-Output "  Run: npm install -g omniroute"
            Write-Output "  Or see SETUP.md for full instructions."
        } else {
            Start-Process -FilePath $omnirouteBin -WindowStyle Hidden -PassThru
            Start-Sleep -Seconds 5
            try {
                $orResp2 = Invoke-WebRequest -Uri "http://localhost:20128/v1/models" -TimeoutSec 5
                if ($orResp2.StatusCode -eq 200) {
                    Write-Output "  OmniRoute started successfully on port 20128."
                } else {
                    Write-Output "  WARNING: OmniRoute started but returned HTTP $($orResp2.StatusCode)."
                }
            } catch {
                Write-Output "  WARNING: OmniRoute process started but not yet responding. It may need more time."
            }
        }
    }
    Write-Output ""
}

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# ── Step 3: DevMind Server ──────────────────────────────────────
if (-not $SkipDevMind) {
    Write-Output "[3/3] Starting DevMind server..."

    $venvPython = Join-Path $SCRIPT_DIR "venv\Scripts\uvicorn.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Output "  ERROR: Virtual environment not found at venv\"
        Write-Output "  Run: python -m venv venv && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt"
    } else {
        $env:PYTHONUNBUFFERED = "1"
        Start-Process -FilePath $venvPython -ArgumentList "server:app --host 127.0.0.1 --port 7860 --reload" -WindowStyle Hidden -PassThru
        Start-Sleep -Seconds 3

        try {
            $dmResp = Invoke-WebRequest -Uri "http://127.0.0.1:7860/api/agent/system_status" -TimeoutSec 5
            if ($dmResp.StatusCode -eq 200) {
                $status = $dmResp.Content | ConvertFrom-Json
                Write-Output "  DevMind server is running on port 7860."
                Write-Output "  Workspace: $($status.workspace)"
                Write-Output "  MCP servers: $($status.mcp_servers_count)"
                Write-Output "  Keys loaded: $($status.keys_loaded | ConvertTo-Json -Compress)"
            }
        } catch {
            Write-Output "  WARNING: DevMind server started but health check failed. It may still be loading."
        }
    }
    Write-Output ""
}

# ── Health Check ────────────────────────────────────────────────
Write-Output "============================================"
Write-Output "  Health Check"
Write-Output "============================================"

$allOk = $true

try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:7860/api/agent/system_status" -TimeoutSec 5
    Write-Output "  [OK] DevMind server (port 7860)"
} catch {
    Write-Output "  [FAIL] DevMind server (port 7860) - $($_.Exception.Message)"
    $allOk = $false
}

try {
    $r = Invoke-WebRequest -Uri "http://localhost:20128/v1/models" -TimeoutSec 5
    $models = ($r.Content | ConvertFrom-Json).data.Count
    Write-Output "  [OK] OmniRoute gateway (port 20128) - $models models"
} catch {
    Write-Output "  [WARN] OmniRoute gateway (port 20128) - $($_.Exception.Message)"
}

try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    $ollamaModels = ($r.Content | ConvertFrom-Json).models.Count
    Write-Output "  [OK] Ollama (port 11434) - $ollamaModels models"
} catch {
    Write-Output "  [WARN] Ollama (port 11434) - not running or not installed"
}

Write-Output ""
if ($allOk) {
    Write-Output "  All core services are running. Open http://localhost:7860 to use DevMind."
    Write-Output "  WebSocket endpoint: ws://127.0.0.1:7860/ws/chat/your-session"
} else {
    Write-Output "  Some services are not running. Check the warnings above."
    Write-Output "  See SETUP.md for troubleshooting."
}
Write-Output ""
