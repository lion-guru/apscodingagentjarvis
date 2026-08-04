with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix the entire for loop block (lines 1575-1595, indices 1574-1594)
# for loop at line 1575 (index 1574) is at 28 spaces
# Body of for loop should be at 32 spaces
# Code after for loop should be at 28 spaces

# Line 1575 (index 1574): for tc in tool_calls: - already at 28, keep as is
# Lines 1576-1577 (indices 1575-1576): tool_name, params - should be 32 spaces
lines[1575] = '                                    tool_name = tc["tool"]\n'
lines[1576] = '                                    params = tc["params"]\n'

# Line 1578 (index 1577): blank - 32 spaces (already fixed)
# Line 1579 (index 1578): await send tool_start - 32 spaces (already fixed)

# Lines 1580-1590 (indices 1579-1589): inside for loop body - all 32 spaces
lines[1579] = '                                \n'
lines[1580] = '                                loop = asyncio.get_event_loop()\n'
lines[1581] = '                                result = await loop.run_in_executor(\n'
lines[1582] = '                                    None, lambda tn=tool_name, p=params: execute_tool(tools_registry, tn, p)\n'
lines[1583] = '                                )\n'
lines[1584] = '                                \n'
lines[1585] = '                                await send("tool_result", {\n'
lines[1586] = '                                    "tool": tool_name, \n'
lines[1587] = '                                    "result": result.output[:2000],\n'
lines[1588] = '                                    "success": result.success\n'
lines[1589] = '                                })\n'
lines[1590] = '                                tool_results.append(f"Tool \'{tool_name}\' result:\\n{result.output}")\n'

# Line 1591 (index 1590): blank after for loop - 28 spaces
lines[1590] = '                            \n'

# Lines 1592-1594 (indices 1591-1593): after for loop - 28 spaces
lines[1591] = '                            combined = "\\n\\n".join(tool_results)\n'
lines[1592] = '                            session["messages"].append({"role": "user", "content": f"Tool results:\\n{combined}"})\n'

# Line 1595 (index 1594): blank - 28 spaces
lines[1593] = '                            \n'

# Line 1596 (index 1595): if ai_mention check - this is outside the for loop but inside the try/except
# Need to check context... Let me look at the next lines
# Actually line 1595 in original was index 1594, let me check what comes next

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed for loop block!')