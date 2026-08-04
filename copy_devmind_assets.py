import os
import shutil

src_audio = r"c:\Users\abhay\AppData\Local\Programs\stonic_dsktp\resources\audio"
dest_audio = r"e:\coding-assistant\web\audio"

src_public = r"c:\Users\abhay\AppData\Local\Programs\stonic_dsktp\resources\public"
dest_assets = r"e:\coding-assistant\web\assets"

os.makedirs(dest_audio, exist_ok=True)
os.makedirs(dest_assets, exist_ok=True)

copied_audio = 0
if os.path.exists(src_audio):
    for f in os.listdir(src_audio):
        s = os.path.join(src_audio, f)
        d = os.path.join(dest_audio, f)
        if os.path.isfile(s):
            shutil.copy2(s, d)
            copied_audio += 1

copied_assets = 0
if os.path.exists(src_public):
    for f in os.listdir(src_public):
        s = os.path.join(src_public, f)
        d = os.path.join(dest_assets, f)
        if os.path.isfile(s):
            shutil.copy2(s, d)
            copied_assets += 1

print(f"Copied {copied_audio} audio files and {copied_assets} asset files successfully.")
