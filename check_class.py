with open('E:/coding-assistant/third_eye.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(420, 460):
    line = lines[i]
    spaces = len(line) - len(line.lstrip())
    print(f'{i+1}: [{spaces}] {repr(line[:80])}')