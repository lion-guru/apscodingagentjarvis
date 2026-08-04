with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix if statement bodies - they should be indented 4 spaces more than the if
# Line 1560 (index 1559): await send inside if clean_text: -> 24 spaces
lines[1559] = '                        await send("assistant_text", {"content": clean_text})\n'

# Line 1564 (index 1563): model = ai_mention inside if ai_mention: -> 24 spaces
lines[1563] = '                        model = ai_mention\n'

# Line 1565 (index 1564): await send inside if ai_mention: -> 24 spaces  
lines[1564] = '                        await send("info", {"content": f"🔄 Model delegating task to {model}..."})\n'

# Line 1566 (index 1565): session append inside if ai_mention: -> 24 spaces
lines[1565] = '                        session["messages"].append({"role": "user", "content": f"Please continue the task as {model}."})\n'

# Line 1567 (index 1566): continue inside if ai_mention: -> 24 spaces
lines[1566] = '                        continue\n'

# Line 1570 (index 1569): await send inside if not tool_calls: -> 24 spaces
lines[1569] = '                        await send("done", {})\n'

# Line 1571 (index 1570): break inside if not tool_calls: -> 24 spaces
lines[1570] = '                        break\n'

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed if statement bodies!')