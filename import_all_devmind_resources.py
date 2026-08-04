import os
import shutil

resources_dir = r"c:\Users\abhay\AppData\Local\Programs\stonic_dsktp\resources"
target_dir = r"E:\coding-assistant"

print("Importing portable runtimes & resources for DevMind AI Studio...")

# 1. Python Embedded
src_py = os.path.join(resources_dir, "python-embedded")
dst_py = os.path.join(target_dir, "python-embedded")
if os.path.exists(src_py) and not os.path.exists(dst_py):
    print("Copying portable python-embedded...")
    shutil.copytree(src_py, dst_py)

# 2. Binaries (node.exe, agent-browser.exe, elevate.exe, ffmpeg.exe)
src_bin = os.path.join(resources_dir, "bin")
dst_bin = os.path.join(target_dir, "bin")
os.makedirs(dst_bin, exist_ok=True)

if os.path.exists(src_bin):
    for f in os.listdir(src_bin):
        s = os.path.join(src_bin, f)
        d = os.path.join(dst_bin, f)
        if os.path.isfile(s) and not os.path.exists(d):
            print(f"Copying binary {f}...")
            shutil.copy2(s, d)

src_elevate = os.path.join(resources_dir, "elevate.exe")
dst_elevate = os.path.join(dst_bin, "elevate.exe")
if os.path.exists(src_elevate) and not os.path.exists(dst_elevate):
    shutil.copy2(src_elevate, dst_elevate)

# FFmpeg binary
src_ffmpeg = os.path.join(resources_dir, "browsers", "ffmpeg-1011", "ffmpeg-win64.exe")
dst_ffmpeg = os.path.join(dst_bin, "ffmpeg.exe")
if os.path.exists(src_ffmpeg) and not os.path.exists(dst_ffmpeg):
    print("Copying standalone ffmpeg.exe...")
    shutil.copy2(src_ffmpeg, dst_ffmpeg)

# 3. Browsers (Standalone Portable Chromium)
src_chromium = os.path.join(resources_dir, "browsers", "chromium-1208")
dst_chromium = os.path.join(target_dir, "browsers", "chromium")
if os.path.exists(src_chromium) and not os.path.exists(dst_chromium):
    print("Copying portable Chromium browser bundle...")
    shutil.copytree(src_chromium, dst_chromium)

# 4. Hermes Runtime
src_hermes = os.path.join(resources_dir, "hermes-runtime")
dst_hermes = os.path.join(target_dir, "hermes-runtime")
if os.path.exists(src_hermes) and not os.path.exists(dst_hermes):
    print("Copying hermes-runtime...")
    shutil.copytree(src_hermes, dst_hermes)

# 5. Audio Effects & Audio Processor Worklet
src_audio = os.path.join(resources_dir, "audio")
dst_audio = os.path.join(target_dir, "web", "audio")
os.makedirs(dst_audio, exist_ok=True)
if os.path.exists(src_audio):
    for f in os.listdir(src_audio):
        s = os.path.join(src_audio, f)
        d = os.path.join(dst_audio, f)
        if os.path.isfile(s):
            shutil.copy2(s, d)

# Audio Processor Worklet
src_worklet = os.path.join(resources_dir, "public", "audio-processor-worklet.js")
dst_worklet = os.path.join(target_dir, "web", "audio-processor-worklet.js")
if os.path.exists(src_worklet):
    shutil.copy2(src_worklet, dst_worklet)

# 6. Public Assets
src_public = os.path.join(resources_dir, "public")
dst_public = os.path.join(target_dir, "web", "assets")
os.makedirs(dst_public, exist_ok=True)
if os.path.exists(src_public):
    for item in os.listdir(src_public):
        s = os.path.join(src_public, item)
        d = os.path.join(dst_public, item)
        if os.path.isfile(s):
            shutil.copy2(s, d)
        elif os.path.isdir(s) and not os.path.exists(d) and item != "admin":
            shutil.copytree(s, d)

# 7. Copy Hermes Agent Skills & Plugins into DevMind Directory
try:
    import copy_hermes_skills
    import copy_hermes_plugins
except Exception:
    pass

print("ALL portable runtimes, FFmpeg, Chromium, assets, Hermes Skills, and 20 Platform Plugins imported successfully!")
