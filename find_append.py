with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'session["messages"].append' in line:
        spaces = len(line) - len(line.lstrip())
        print(f'{i+1}: [{spaces}] {line.strip()}')