with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix lines 1578-1579 (indices 1577-1578)
# The for loop is at 28 spaces, inner code should be at 32 spaces
# Line 1578 (index 1577) blank line: should be 32 spaces
# Line 1579 (index 1578): await send -> 32 spaces

lines[1577] = '                                \n'
lines[1578] = '                                await send("tool_start", {"tool": tool_name, "params": params})\n'

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed lines 1578-1579!')