with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix for loop body (lines 1576-1590, indices 1575-1589): should be 24 spaces
for i in range(1575, 1590):
    line = lines[i]
    stripped = line.lstrip()
    if stripped:
        lines[i] = '                        ' + stripped

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed for loop body!')