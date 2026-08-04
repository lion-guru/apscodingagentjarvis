import os
import shutil

src_videos = r"e:\coding-assistant\stonic_extracted\dist\videos"
dst_videos = r"e:\coding-assistant\web\videos"

if os.path.exists(src_videos):
    os.makedirs(dst_videos, exist_ok=True)
    for f in os.listdir(src_videos):
        s = os.path.join(src_videos, f)
        d = os.path.join(dst_videos, f)
        if os.path.isfile(s):
            shutil.copy2(s, d)
            print(f"Copied video: {f}")

print("Video assets copied successfully!")
