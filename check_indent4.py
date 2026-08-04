with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(1588, 1610):
    line = lines[i]
    spaces = len(line) - len(line.lstrip())
    print(f'{i+1}: [{spaces}]')