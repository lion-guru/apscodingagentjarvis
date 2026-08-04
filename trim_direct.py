path = r"E:\coding-assistant\web\index.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

target = "</html>"
idx = text.find(target)
if idx != -1:
    clean_content = text[:idx + len(target)]
    with open(path, "w", encoding="utf-8") as f:
        f.write(clean_content)
    print("SUCCESSFULLY TRIMMED web/index.html to", len(clean_content.splitlines()), "lines!")
else:
    print("Could not find target")
