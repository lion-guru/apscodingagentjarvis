import os
import shutil

target_dir = r"E:\coding-assistant"

print("Rebranding and organizing all assets under DevMind AI Studio...")

# 1. Clean up old stonic directories and rename to devmind_resources
stonic_ext = os.path.join(target_dir, "stonic_extracted")
stonic_res = os.path.join(target_dir, "stonic_resources")
devmind_res = os.path.join(target_dir, "devmind_resources")

os.makedirs(devmind_res, exist_ok=True)

if os.path.exists(stonic_ext):
    dst = os.path.join(devmind_res, "app_container_unpacked")
    if not os.path.exists(dst):
        shutil.move(stonic_ext, dst)
    else:
        shutil.rmtree(stonic_ext, ignore_errors=True)

if os.path.exists(stonic_res):
    shutil.rmtree(stonic_res, ignore_errors=True)

# 2. Rename old stonic scripts & reports
renames = [
    ("stonic_deep_scan_report.txt", "devmind_deep_scan_report.txt"),
    ("deep_scan_stonic.py", "deep_scan_devmind.py"),
    ("copy_stonic_assets.py", "copy_devmind_assets.py"),
    ("extract_stonic_assets_deep.py", "extract_devmind_assets_deep.py"),
    ("import_all_stonic_resources.py", "import_all_devmind_resources.py"),
    ("organize_stonic_structure.py", "organize_devmind_structure.py")
]

for old_name, new_name in renames:
    old_p = os.path.join(target_dir, old_name)
    new_p = os.path.join(target_dir, new_name)
    if os.path.exists(old_p):
        if os.path.exists(new_p):
            os.remove(old_p)
        else:
            os.rename(old_p, new_p)

print("Rebranding complete! All assets and files are now under DevMind AI Studio.")
