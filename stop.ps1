param(
    [switch]$All,
    [switch]$Help
)

if ($Help) {
    Write-Output @"
DevMind/Jarvis Stop Script

Usage: .\stop.ps1 [options]

Options:
  -All     Stop all services (Ollama, OmniRoute, DevMind)
  -Help    Show this help message

By default, stops only the DevMind server.
Use -All to stop everything including Ollama and OmniRoute.
"@
    return
}

$ErrorActionPreference = "SilentlyContinue"

Write-Output "DevMind/Jarvis - Stop Script"
Write-Output ""

# ── Stop DevMind ──────────────────────────────────────────
Write-Output "[1] Stopping DevMind server..."
$uvicorn = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
if ($uvicorn) {
    Stop-Process -Name "uvicorn" -Force
    Write-Output "  DevMind server stopped (PID $($uvicorn.Id))."
} else {
    Write-Output "  DevMind server not running."
}

# ── Stop OmniRoute ──────────────────────────────────────
if ($All) {
    Write-Output "[2] Stopping OmniRoute gateway..."
    $omniroute = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*omniroute*" -or $_.CommandLine -like "*20128*"
    }
    if ($omniroute) {
        Stop-Process -Name "node" -Force -Confirm:$false
        Write-Output "  OmniRoute stopped (PID $($omniroute.Id))."
    } else {
        Write-Output "  OmniRoute not running."
    }
}

# ── Stop Ollama ──────────────────────────────────────────
if ($All) {
    Write-Output "[3] Stopping Ollama..."
    $ollama = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if ($ollama) {
        Stop-Process -Name "ollama" -Force
        Write-Output "  Ollama stopped (PID $($ollama.Id))."
    } else {
        Write-Output "  Ollama not running."
    }
}

Write-Output ""
Write-Output "Done."
