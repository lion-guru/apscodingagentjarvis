with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(1538, 1560):
    line = lines[i]
    spaces = len(line) - len(line.lstrip())
    if spaces < 12:  # Only show lines with reasonable indentation
        print(f'{i+1}: [{spaces}] {line[:80].encode("ascii", "replace").decode()}')