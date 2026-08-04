import os
import shutil

src_plugins = r"E:\coding-assistant\hermes-runtime\src\plugins"
dst_plugins = r"E:\coding-assistant\plugins"

if os.path.exists(src_plugins) and not os.path.exists(dst_plugins):
    print("Copying Hermes 19 Plugins & 20 Platform Adapters...")
    shutil.copytree(src_plugins, dst_plugins)
    print(f"Successfully copied all plugins into {dst_plugins}!")
elif os.path.exists(src_plugins) and os.path.exists(dst_plugins):
    for item in os.listdir(src_plugins):
        s = os.path.join(src_plugins, item)
        d = os.path.join(dst_plugins, item)
        if os.path.isdir(s) and not os.path.exists(d):
            shutil.copytree(s, d)
            print(f"Copied plugin: {item}")

print("Hermes Plugin Suite imported successfully!")
