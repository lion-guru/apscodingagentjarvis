with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Remove duplicate except at line 1539 (index 1538)
del lines[1538]

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Removed duplicate except!')