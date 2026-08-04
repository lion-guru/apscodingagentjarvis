with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix blank lines after except block (lines 1594 and 1596, 0-indexed 1593 and 1595)
lines[1593] = '                    \n'  # 20 spaces
lines[1595] = '                    \n'  # 20 spaces

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed blank lines!')