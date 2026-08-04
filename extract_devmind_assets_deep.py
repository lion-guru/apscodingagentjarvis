import struct
import json
import os

asar_path = r"c:\Users\abhay\AppData\Local\Programs\stonic_dsktp\resources\app.asar"
out_dir = r"E:\coding-assistant\devmind_resources\app_container_unpacked"

if not os.path.exists(asar_path):
    print("ASAR archive not found.")
    exit()

print(f"Opening ASAR archive: {asar_path}")

with open(asar_path, "rb") as f:
    f.seek(4)
    header_size = struct.unpack("<I", f.read(4))[0]
    json_size = struct.unpack("<I", f.read(4))[0]
    string_len = struct.unpack("<I", f.read(4))[0]
    
    header_json_raw = f.read(string_len).decode("utf-8")
    header_data = json.loads(header_json_raw)
    
    base_offset = 8 + header_size
    extracted_count = [0]
    
    def extract_node(node, current_path=""):
        if "files" in node:
            for name, child in node["files"].items():
                rel_path = os.path.join(current_path, name)
                if "files" in child:
                    extract_node(child, rel_path)
                else:
                    if "offset" in child and "size" in child:
                        offset = int(child["offset"]) + base_offset
                        size = int(child["size"])
                        
                        target_file_path = os.path.join(out_dir, rel_path)
                        os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
                        
                        f.seek(offset)
                        content = f.read(size)
                        
                        with open(target_file_path, "wb") as out_f:
                            out_f.write(content)
                        extracted_count[0] += 1

    extract_node(header_data)

print(f"Deep extraction complete! Extracted {extracted_count[0]} files into {out_dir}")
