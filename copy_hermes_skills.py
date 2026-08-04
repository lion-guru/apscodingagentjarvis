import os
import shutil

src_skills = r"E:\coding-assistant\hermes-runtime\src\skills"
dst_skills = r"E:\coding-assistant\skills"

os.makedirs(dst_skills, exist_ok=True)

copied_count = 0
if os.path.exists(src_skills):
    for category in os.listdir(src_skills):
        cat_path = os.path.join(src_skills, category)
        if os.path.isdir(cat_path) and category != "__pycache__":
            for skill_folder in os.listdir(cat_path):
                s_path = os.path.join(cat_path, skill_folder)
                d_path = os.path.join(dst_skills, skill_folder)
                if os.path.isdir(s_path) and not os.path.exists(d_path):
                    shutil.copytree(s_path, d_path)
                    copied_count += 1
                    print(f"Copied skill: [{category}] -> {skill_folder}")

print(f"Successfully copied {copied_count} Hermes agent skills into {dst_skills}!")
