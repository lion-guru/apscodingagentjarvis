import os
import shutil

base_devmind = r"E:\coding-assistant\devmind_resources"
os.makedirs(base_devmind, exist_ok=True)

# Define clean folder targets
dirs = {
    "app_container_unpacked": os.path.join(base_devmind, "app_container_unpacked"),
    "audio": os.path.join(base_devmind, "audio"),
    "binaries": os.path.join(base_devmind, "binaries"),
    "browsers": os.path.join(base_devmind, "browsers"),
    "hermes_runtime": os.path.join(base_devmind, "hermes_runtime"),
    "public_assets": os.path.join(base_devmind, "public_assets")
}

for d in dirs.values():
    os.makedirs(d, exist_ok=True)

print("Organizing files under clean DevMind structure: E:\\coding-assistant\\devmind_resources...")

# 1. Sync Audio to audio
src_web_audio = r"E:\coding-assistant\web\audio"
if os.path.exists(src_web_audio):
    for f in os.listdir(src_web_audio):
        s = os.path.join(src_web_audio, f)
        d = os.path.join(dirs["audio"], f)
        if os.path.isfile(s):
            shutil.copy2(s, d)

# 2. Sync Binaries to binaries
src_bin = r"E:\coding-assistant\bin"
if os.path.exists(src_bin):
    for f in os.listdir(src_bin):
        s = os.path.join(src_bin, f)
        d = os.path.join(dirs["binaries"], f)
        if os.path.isfile(s):
            shutil.copy2(s, d)

# 3. Sync Public Assets to public_assets
src_web_assets = r"E:\coding-assistant\web\assets"
if os.path.exists(src_web_assets):
    for item in os.listdir(src_web_assets):
        s = os.path.join(src_web_assets, item)
        d = os.path.join(dirs["public_assets"], item)
        if not os.path.exists(d):
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

print(f"DevMind resources organized successfully in {base_devmind}!")
