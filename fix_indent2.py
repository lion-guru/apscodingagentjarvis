import re

with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix the indentation issue around line 1538
# The except block should be at 24 spaces (same as try at line 1185)
# Current except is at 20 spaces, code after at various wrong indents

fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Check if this is the problematic except line (20 spaces)
    if line.startswith('                    except Exception as e:'):
        # This should be 24 spaces
        fixed_lines.append('                            except Exception as e:\n')
        i += 1
        # Fix the next lines that are at wrong indentation
        while i < len(lines):
            next_line = lines[i]
            stripped = next_line.lstrip()
            if not stripped:
                # Empty line - keep as is
                fixed_lines.append('\n')
                i += 1
                continue
            if stripped.startswith('await send("error"'):
                fixed_lines.append('                                ' + stripped)
            elif stripped.startswith('break'):
                fixed_lines.append('                                break\n')
            elif stripped.startswith('session["messages"]'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('# Send token'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('est_input_tokens'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('est_output_tokens'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('est_total_tokens'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('await send("token_usage"'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('"model"') or stripped.startswith('"input_tokens"') or stripped.startswith('"output_tokens"') or stripped.startswith('"total_tokens"') or stripped.startswith('})'):
                fixed_lines.append('                                ' + stripped)
            elif stripped.startswith('# Extract tool calls'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('tool_calls ='):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('clean_text ='):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('if clean_text:'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('await send("assistant_text"'):
                fixed_lines.append('                                ' + stripped)
            elif stripped.startswith('ai_mention ='):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('if ai_mention:'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('model = ai_mention'):
                fixed_lines.append('                                ' + stripped)
            elif stripped.startswith('await send("info"'):
                fixed_lines.append('                                ' + stripped)
            elif stripped.startswith('session["messages"].append'):
                fixed_lines.append('                                ' + stripped)
            elif stripped.startswith('continue'):
                fixed_lines.append('                                ' + stripped)
            elif stripped.startswith('if not tool_calls:'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('await send("done"'):
                fixed_lines.append('                                ' + stripped)
            elif stripped.startswith('break'):
                fixed_lines.append('                                break\n')
            elif stripped.startswith('# Execute tools'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('tool_results ='):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('for tc in tool_calls:'):
                fixed_lines.append('                            ' + stripped)
            elif stripped.startswith('tool_name ='):
                fixed_lines.append('                                ' + stripped)
            elif stripped.startswith('params ='):
                fixed_lines.append('                                ' + stripped)
            else:
                # For any other line, just add it as-is
                fixed_lines.append(next_line)
            i += 1
            # Stop after we've processed enough lines
            if i < len(lines) and not lines[i].lstrip().startswith(('await', 'break', 'session', '#', 'est_', '"model"', '"input', '"output', '"total', '})', 'tool_calls', 'clean_text', 'if clean', 'ai_mention', 'if ai_', 'model =', 'continue', 'if not', '    ')):
                # Check if we're back to normal indentation (24 spaces for code blocks)
                next_stripped = lines[i].lstrip()
                if next_stripped and not lines[i].startswith('                            ') and not lines[i].startswith('                                '):
                    # We've reached the end of the block
                    pass
        continue
    fixed_lines.append(line)
    i += 1

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print('Fixed indentation!')