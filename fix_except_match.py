with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The except at line 1539 (index 1538) should be at 20 spaces to match try at line 1185
# Currently at 24 spaces
lines[1538] = '                    except Exception as e:\n'

# The code inside except (lines 1540-1541, indices 1539-1540) should be at 24 spaces
lines[1539] = '                        await send("error", {"content": f"Model Error: {str(e)}"})\n'
lines[1540] = '                        break\n'
lines[1541] = '                        \n'

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed except to match try indentation!')