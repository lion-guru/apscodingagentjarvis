with open('E:/coding-assistant/third_eye.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('E:/coding-assistant/check_output2.txt', 'w', encoding='utf-8') as out:
    for i in range(650, 690):
        line = lines[i]
        spaces = len(line) - len(line.lstrip())
        out.write(f'{i+1}: [{spaces}] {repr(line[:100])}\n')