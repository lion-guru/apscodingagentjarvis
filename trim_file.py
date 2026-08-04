with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("</html>")
if pos != -1:
    clean_text = text[:pos + len("</html>")] + "\n"
    with open("web/index.html", "w", encoding="utf-8") as f:
        f.write(clean_text)
    print("Successfully trimmed web/index.html to clean </html> ending!")
