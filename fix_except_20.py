with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The try at line 1185 is at 20 spaces
# The except at current line 1539 (index 1538) is at 24 spaces - needs to be 20
# Code inside except (lines 1540-1542, indices 1539-1541) should be at 24 spaces
# Blank line after except (index 1542) should be at 20 spaces

# Fix except line
lines[1538] = '                    except Exception as e:\n'

# Code inside except - already at 24 spaces, keep as is
# Blank line after except (index 1542) - fix to 20 spaces
lines[1542] = '                    \n'

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed except to 20 spaces!')