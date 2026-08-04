with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The try at line 1185 (index 1184) is at 20 spaces
# The except should be at 20 spaces
# Code inside except should be at 24 spaces
# Code after except block should be at 20 spaces

# Fix except line (currently at index 1538, line 1539)
lines[1538] = '                    except Exception as e:\n'

# Code inside except (indices 1539-1541) should be at 24 spaces
lines[1539] = '                        await send("error", {"content": f"Model Error: {str(e)}"})\n'
lines[1540] = '                        break\n'
lines[1541] = '                        \n'

# Blank line after except (index 1542) should be at 20 spaces
lines[1542] = '                    \n'

# Code after except (indices 1543+) should be at 20 spaces - they already are

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed except indentation to match try!')