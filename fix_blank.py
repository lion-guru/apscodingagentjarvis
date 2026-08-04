with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 1543 (index 1542): blank line with wrong indentation
lines[1542] = '                    \n'

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed blank line!')