"""
DevMind / Jarvis — Automatic Dependency Downloader
===================================================
Jo large binary files GitHub par nahi hain (node.exe, ffmpeg.exe, chromium)
wo yeh script automatically download kar leta hai.
Run this once after cloning the repo:  python setup_dependencies.py
"""
import os
import sys
import zipfile
import shutil
import platform
import urllib.request
from pathlib import Path

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

ROOT = Path(__file__).parent

def print_header(title: str):
    print(f"\n{CYAN}{BOLD}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{BOLD}{'='*60}{RESET}\n")

def download_file(url: str, dest: Path, label: str):
    """Download with progress bar."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  ⬇️  Downloading {label}...")

    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(100, downloaded * 100 // total_size)
            mb = downloaded / 1_048_576
            total_mb = total_size / 1_048_576
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r     [{bar}] {pct}% ({mb:.1f}/{total_mb:.1f} MB)", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, dest, reporthook)
        print(f"\r  {GREEN}✅ {label} downloaded!{RESET}              ")
        return True
    except Exception as e:
        print(f"\r  {RED}❌ Failed: {e}{RESET}")
        return False

def extract_zip(zip_path: Path, extract_to: Path, label: str):
    """Extract zip and optionally move single file."""
    print(f"  📦 Extracting {label}...")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_to)
        zip_path.unlink()
        print(f"  {GREEN}✅ {label} extracted!{RESET}")
        return True
    except Exception as e:
        print(f"  {RED}❌ Extract failed: {e}{RESET}")
        return False

# ─────────────────────────────────────────────────────────────
# 1. Node.js (for MCP servers)
# ─────────────────────────────────────────────────────────────
def setup_nodejs():
    node_dir   = ROOT / "bin"
    node_exe   = node_dir / "node.exe"

    if node_exe.exists():
        print(f"  {GREEN}✅ Node.js already present: {node_exe}{RESET}")
        return True

    # Check if system Node is available
    if shutil.which("node"):
        print(f"  {GREEN}✅ Node.js found in system PATH — no local copy needed.{RESET}")
        return True

    print(f"  {YELLOW}⚠️  Node.js not found — downloading portable version...{RESET}")

    url = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-win-x64.zip"
    zip_path = ROOT / "_tmp_node.zip"

    if not download_file(url, zip_path, "Node.js v20.18.0"):
        return False

    tmp_dir = ROOT / "_tmp_node_extract"
    if not extract_zip(zip_path, tmp_dir, "Node.js"):
        return False

    # Move contents of extracted folder into bin/
    extracted_folder = next(tmp_dir.iterdir())
    node_dir.mkdir(exist_ok=True)
    for item in extracted_folder.iterdir():
        shutil.move(str(item), str(node_dir / item.name))
    shutil.rmtree(tmp_dir)

    if node_exe.exists():
        print(f"  {GREEN}✅ Node.js installed at: {node_exe}{RESET}")
        return True
    return False

# ─────────────────────────────────────────────────────────────
# 2. FFmpeg (for audio/video processing)
# ─────────────────────────────────────────────────────────────
def setup_ffmpeg():
    ffmpeg_dir = ROOT / "devmind_resources" / "binaries"
    ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe"

    if ffmpeg_exe.exists():
        print(f"  {GREEN}✅ FFmpeg already present.{RESET}")
        return True

    if shutil.which("ffmpeg"):
        print(f"  {GREEN}✅ FFmpeg found in system PATH — no local copy needed.{RESET}")
        return True

    print(f"  {YELLOW}⚠️  FFmpeg not found — downloading...{RESET}")

    url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    zip_path = ROOT / "_tmp_ffmpeg.zip"

    if not download_file(url, zip_path, "FFmpeg"):
        return False

    tmp_dir = ROOT / "_tmp_ffmpeg_extract"
    if not extract_zip(zip_path, tmp_dir, "FFmpeg"):
        return False

    # Find ffmpeg.exe deep inside
    for exe in tmp_dir.rglob("ffmpeg.exe"):
        ffmpeg_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(exe), str(ffmpeg_exe))
        break

    shutil.rmtree(tmp_dir, ignore_errors=True)

    if ffmpeg_exe.exists():
        print(f"  {GREEN}✅ FFmpeg installed at: {ffmpeg_exe}{RESET}")
        return True
    return False

# ─────────────────────────────────────────────────────────────
# 3. Mediapipe WASM (for gesture recognition)
# ─────────────────────────────────────────────────────────────
def setup_mediapipe_wasm():
    wasm_dir = ROOT / "web" / "assets" / "mediapipe" / "wasm"
    target   = wasm_dir / "vision_wasm_internal.wasm"

    if target.exists():
        print(f"  {GREEN}✅ Mediapipe WASM already present.{RESET}")
        return True

    print(f"  {YELLOW}⚠️  Mediapipe WASM files missing — downloading from CDN...{RESET}")

    wasm_dir.mkdir(parents=True, exist_ok=True)
    base_url = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm/"
    files    = [
        "vision_wasm_internal.wasm",
        "vision_wasm_internal.js",
        "vision_wasm_module_internal.wasm",
        "vision_wasm_module_internal.js",
        "vision_wasm_nosimd_internal.wasm",
        "vision_wasm_nosimd_internal.js",
    ]

    success = 0
    for f in files:
        dest = wasm_dir / f
        if dest.exists():
            success += 1
            continue
        if download_file(base_url + f, dest, f):
            success += 1

    if success >= 4:
        print(f"  {GREEN}✅ Mediapipe WASM files ready ({success}/{len(files)}).{RESET}")
        return True
    return False

# ─────────────────────────────────────────────────────────────
# 4. Python venv + pip packages
# ─────────────────────────────────────────────────────────────
def setup_python_venv():
    venv_python = ROOT / "venv" / "Scripts" / "python.exe"

    if not venv_python.exists():
        print(f"  🔧 Creating Python virtual environment...")
        os.system(f'python -m venv "{ROOT / "venv"}"')

    if venv_python.exists():
        print(f"  {GREEN}✅ Python venv ready.{RESET}")
        pip = ROOT / "venv" / "Scripts" / "pip.exe"
        print(f"  📦 Installing Python packages from requirements.txt...")
        os.system(f'"{pip}" install --upgrade pip -q')
        os.system(f'"{pip}" install fastapi uvicorn websockets httpx pydantic jinja2 psutil python-multipart aiofiles -q')
        print(f"  {GREEN}✅ Python packages installed.{RESET}")
        return True
    else:
        print(f"  {RED}❌ Could not create venv — make sure Python 3.10+ is installed.{RESET}")
        return False

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print_header("🚀 JARVIS DevMind — Auto Dependency Setup")
    print(f"  Workspace: {ROOT}\n")

    results = {}

    print(f"\n{BOLD}[1/4] Node.js{RESET}")
    results["Node.js"] = setup_nodejs()

    print(f"\n{BOLD}[2/4] FFmpeg{RESET}")
    results["FFmpeg"] = setup_ffmpeg()

    print(f"\n{BOLD}[3/4] Mediapipe WASM{RESET}")
    results["Mediapipe WASM"] = setup_mediapipe_wasm()

    print(f"\n{BOLD}[4/4] Python venv + packages{RESET}")
    results["Python venv"] = setup_python_venv()

    # Summary
    print_header("📊 Setup Summary")
    all_ok = True
    for name, ok in results.items():
        icon = f"{GREEN}✅" if ok else f"{YELLOW}⚠️ "
        print(f"  {icon}  {name}{RESET}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print(f"{GREEN}{BOLD}🎉 All dependencies ready! Launch with:{RESET}")
        print(f"   {CYAN}python server.py{RESET}  or  {CYAN}START_SERVER.bat{RESET}\n")
    else:
        print(f"{YELLOW}⚠️  Some optional dependencies skipped (software will still mostly work).{RESET}")
        print(f"   Core features (AI chat, code editor) work fine without them.\n")

if __name__ == "__main__":
    main()
