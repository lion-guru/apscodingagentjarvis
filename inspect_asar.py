import struct
import json
import os

asar_path = r"c:\Users\abhay\AppData\Local\Programs\stonic_dsktp\resources\app.asar"
out_path = r"e:\coding-assistant\asar_contents.txt"

if not os.path.exists(asar_path):
    print("app.asar not found.")
    exit()

with open(asar_path, "rb") as f:
    f.seek(4)
    header_size = struct.unpack("<I", f.read(4))[0]
    json_size = struct.unpack("<I", f.read(4))[0]
    string_len = struct.unpack("<I", f.read(4))[0]
    
    header_json_raw = f.read(string_len).decode("utf-8")
    header_data = json.loads(header_json_raw)

paths = []
def walk_asar(tree, current_path=""):
    if "files" in tree:
        for name, child in tree["files"].items():
            path = os.path.join(current_path, name)
            if "files" in child:
                walk_asar(child, path)
            else:
                paths.append((path, child.get("size", 0), child.get("offset", 0)))

walk_asar(header_data)

lines = []
lines.append(f"Total files inside app.asar: {len(paths)}\n")
lines.append("--- All Files & Tools inside app.asar ---\n")

# Group by category/extension
categories = {}
for p, size, offset in sorted(paths, key=lambda x: x[0]):
    ext = os.path.splitext(p)[1].lower() or "no_ext"
    categories.setdefault(ext, []).append((p, size))
    lines.append(f"{size:>10} bytes | {p}")

with open(out_path, "w", encoding="utf-8") as out:
    out.write("\n".join(lines))

print(f"Inspection complete. Written {len(paths)} file records to {out_path}")
