with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix blank lines after except block
# Line 1541 (index 1540): blank line after except - should be 20 spaces
lines[1540] = '                    \n'

# Line 1542 (index 1541): blank line - should be 20 spaces  
lines[1541] = '                    \n'

# Line 1543 (index 1542): blank line - should be 20 spaces
lines[1542] = '                    \n'

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed blank lines!')