with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines 1542-1595 (indices 1541-1594): after try/except block - should be 20 spaces
# Currently at 32 spaces, need to reduce by 12 spaces

for i in range(1541, 1595):
    line = lines[i]
    stripped = line.lstrip()
    if stripped:
        # Reduce indentation from 32 to 20 (remove 12 spaces)
        if len(line) - len(stripped) >= 32:
            lines[i] = '                    ' + stripped
        elif len(line) - len(stripped) >= 28:
            lines[i] = '                    ' + stripped
        elif len(line) - len(stripped) >= 24:
            lines[i] = '                    ' + stripped

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed post-except block indentation!')