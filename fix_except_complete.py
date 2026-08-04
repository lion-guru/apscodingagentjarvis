with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The except block is missing the await send("error") line
# Current state:
# Line 1539 (index 1538): except at 20 spaces
# Line 1540 (index 1539): break at 24 spaces - but missing the await send line!
# Line 1541 (index 1540): blank at 25 spaces
# Line 1542 (index 1541): blank at 21 spaces
# Line 1543 (index 1542): est_output_tokens at 20 spaces - this should be after the except block

# Need to insert the await send("error") line after except, before break
# And fix the indentation

lines[1539] = '                        await send("error", {"content": f"Model Error: {str(e)}"})\n'
lines[1540] = '                        break\n'
lines[1541] = '                        \n'
lines[1542] = '                    \n'

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed except block with await send!')