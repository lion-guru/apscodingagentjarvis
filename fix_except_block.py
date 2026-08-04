with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The except at line 1538 is at 20 spaces (correct, matches try at line 1185)
# Code inside except should be at 24 spaces
# Code after the try/except block should be at 20 spaces

# Lines 1539-1541 (indices 1538-1540): inside except - should be 24 spaces
lines[1538] = '                        await send("error", {"content": f"Model Error: {str(e)}"})\n'
lines[1539] = '                        break\n'
lines[1540] = '                        \n'

# Lines 1542+ (index 1541+): after except block - should be 20 spaces
# These are currently at 32 spaces, need to be 20 spaces

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed except block indentation!')