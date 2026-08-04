with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix lines 1538-1565 (0-indexed: 1537-1564)
# The except at line 1538 should be at 24 spaces
# The code inside except should be at 28 spaces

# Line 1538 (index 1537): except Exception as e: -> 24 spaces
lines[1537] = '                            except Exception as e:\n'

# Line 1539 (index 1538): await send -> 28 spaces
lines[1538] = '                                await send("error", {"content": f"Model Error: {str(e)}"})\n'

# Line 1540 (index 1539): break -> 28 spaces
lines[1539] = '                                break\n'

# Line 1541 (index 1540): blank line -> 28 spaces
lines[1540] = '                                \n'

# Line 1542 (index 1541): session["messages"] -> 28 spaces
lines[1541] = '                                session["messages"].append({"role": "assistant", "content": full_response})\n'

# Line 1543 (index 1542): blank line -> 28 spaces
lines[1542] = '                                \n'

# Line 1544 (index 1543): # Send token usage info -> 28 spaces
lines[1543] = '                                # Send token usage info\n'

# Line 1545 (index 1544): est_input_tokens -> 28 spaces
lines[1544] = '                                est_input_tokens = sum(len(m.get("content", "")) for m in session["messages"]) // 4\n'

# Line 1546 (index 1545): est_output_tokens -> 28 spaces
lines[1545] = '                                est_output_tokens = len(full_response) // 4\n'

# Line 1547 (index 1546): est_total_tokens -> 28 spaces
lines[1546] = '                                est_total_tokens = est_input_tokens + est_output_tokens\n'

# Line 1548 (index 1547): await send("token_usage" -> 28 spaces
lines[1547] = '                                await send("token_usage", {\n'

# Line 1549 (index 1548): "model" -> 32 spaces
lines[1548] = '                                    "model": model,\n'

# Line 1550 (index 1549): "input_tokens" -> 32 spaces
lines[1549] = '                                    "input_tokens": est_input_tokens,\n'

# Line 1551 (index 1550): "output_tokens" -> 32 spaces
lines[1550] = '                                    "output_tokens": est_output_tokens,\n'

# Line 1552 (index 1551): "total_tokens" -> 32 spaces
lines[1551] = '                                    "total_tokens": est_total_tokens,\n'

# Line 1553 (index 1552): }) -> 28 spaces
lines[1552] = '                                })\n'

# Line 1554 (index 1553): blank line -> 28 spaces
lines[1553] = '                                \n'

# Line 1555 (index 1554): # Extract tool calls -> 28 spaces
lines[1554] = '                                # Extract tool calls\n'

# Line 1556 (index 1555): tool_calls = -> 28 spaces
lines[1555] = '                                tool_calls = extract_tool_calls(full_response)\n'

# Line 1557 (index 1556): clean_text = -> 28 spaces
lines[1556] = '                                clean_text = remove_tool_calls(full_response)\n'

# Line 1558 (index 1557): blank line -> 28 spaces
lines[1557] = '                                \n'

# Line 1559 (index 1558): if clean_text: -> 28 spaces
lines[1558] = '                                if clean_text:\n'

# Line 1560 (index 1559): await send("assistant_text" -> 32 spaces
lines[1559] = '                                    await send("assistant_text", {"content": clean_text})\n'

# Line 1561 (index 1560): blank line -> 28 spaces
lines[1560] = '                                \n'

# Line 1562 (index 1561): ai_mention = -> 28 spaces
lines[1561] = '                                ai_mention = parse_mention(full_response)\n'

# Line 1563 (index 1562): if ai_mention: -> 28 spaces
lines[1562] = '                                if ai_mention:\n'

# Line 1564 (index 1563): model = ai_mention -> 32 spaces
lines[1563] = '                                    model = ai_mention\n'

# Line 1565 (index 1564): await send("info" -> 32 spaces
lines[1564] = '                                    await send("info", {"content": f"🔄 Model delegating task to {model}..."})\n'

# Line 1566 (index 1565): session["messages"].append -> 32 spaces
lines[1565] = '                                    session["messages"].append({"role": "user", "content": f"Please continue the task as {model}."})\n'

# Line 1567 (index 1566): continue -> 32 spaces
lines[1566] = '                                    continue\n'

# Line 1568 (index 1567): blank line -> 28 spaces
lines[1567] = '                                \n'

# Line 1569 (index 1568): if not tool_calls: -> 28 spaces
lines[1568] = '                                if not tool_calls:\n'

# Line 1570 (index 1569): await send("done") -> 32 spaces
lines[1569] = '                                    await send("done", {})\n'

# Line 1571 (index 1570): break -> 32 spaces
lines[1570] = '                                    break\n'

# Line 1572 (index 1571): blank line -> 28 spaces
lines[1571] = '                                \n'

# Line 1573 (index 1572): # Execute tools -> 28 spaces
lines[1572] = '                                # Execute tools\n'

# Line 1574 (index 1573): tool_results = -> 28 spaces
lines[1573] = '                                tool_results = []\n'

# Line 1575 (index 1574): for tc in tool_calls: -> 28 spaces
lines[1574] = '                                for tc in tool_calls:\n'

# Line 1576 (index 1575): tool_name = -> 32 spaces
lines[1575] = '                                    tool_name = tc["tool"]\n'

# Line 1577 (index 1576): params = -> 32 spaces
lines[1576] = '                                    params = tc["params"]\n'

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed!')