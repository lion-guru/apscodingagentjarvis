with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The structure:
# try at line 1185 (index 1184): 20 spaces
# ... if/elif/else branches ...
# except at line 1538 (index 1537): 20 spaces (matches try)
#   await send("error") - 24 spaces
#   break - 24 spaces
# blank line after except - 20 spaces
# code after except block - 20 spaces

# Fix except line (index 1537) to 20 spaces
lines[1537] = '                    except Exception as e:\n'

# Fix except body (indices 1538-1539) to 24 spaces
lines[1538] = '                        await send("error", {"content": f"Model Error: {str(e)}"})\n'
lines[1539] = '                        break\n'

# Fix blank lines after except (indices 1540-1542) to 20 spaces
lines[1540] = '                    \n'
lines[1541] = '                    \n'
lines[1542] = '                    \n'

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed except structure!')