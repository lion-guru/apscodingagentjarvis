with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix the except block at lines 1538-1543 (indices 1537-1542)
# Current state is messed up. Let me fix it properly:
# except Exception as e:          <- 20 spaces (line 1538, index 1537)
#     await send("error", ...)    <- 24 spaces (line 1539, index 1538)
#     break                        <- 24 spaces (line 1540, index 1539)
#                                 <- 24 spaces (line 1541, index 1540)
#                                 <- 20 spaces (line 1542, index 1541)

lines[1538] = '                        await send("error", {"content": f"Model Error: {str(e)}"})\n'
lines[1539] = '                        break\n'
lines[1540] = '                        \n'
lines[1541] = '                    \n'

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed except block order!')