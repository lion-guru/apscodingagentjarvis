with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix blank lines at indices 1540, 1541, 1542 from 21 to 20 spaces
lines[1540] = '                    \n'
lines[1541] = '                    \n'
lines[1542] = '                    \n'

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed blank lines!')