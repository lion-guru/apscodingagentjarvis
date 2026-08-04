with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(1535, 1550):
    line = lines[i]
    spaces = len(line) - len(line.lstrip())
    safe_line = line[:80].encode('ascii', 'replace').decode()
    print(f'{i+1}: [{spaces}] {safe_line}')