import re

with open('E:/coding-assistant/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The issue: except at line 1538 is at 20 spaces, should be 24 (same as try at line 1185)
# Also the code after it needs to be at 24 spaces

# Find the problematic pattern and fix it
# The pattern is: 20 spaces + "except Exception as e:" followed by code at 24/25 spaces
# Should be: 24 spaces + "except Exception as e:" followed by code at 28 spaces

lines = content.split('\n')
fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Check if this is the problematic except line (20 spaces)
    if line.startswith('                    except Exception as e:'):
        # This should be 24 spaces
        fixed_lines.append('                            except Exception as e:')
        i += 1
        # Fix the next lines that are at wrong indentation
        while i < len(lines):
            next_line = lines[i]
            if next_line.startswith('                        await send("error"'):
                fixed_lines.append('                                await send("error", {"content": f"Model Error: {str(e)}"})')
            elif next_line.startswith('                        break'):
                fixed_lines.append('                                break')
            elif next_line.startswith('                     '):
                # This is the session["messages"] line at 21 spaces, should be 28
                fixed_lines.append('                            session["messages"].append({"role": "assistant", "content": full_response})')
            elif next_line.startswith('                     '):
                # Skip empty lines at wrong indent
                pass
            else:
                # Other lines - just add as-is for now
                fixed_lines.append(next_line)
            i += 1
            # Stop after we've fixed the block
            if i < len(lines) and not lines[i].startswith('                     ') and not lines[i].startswith('                        '):
                break
        continue
    fixed_lines.append(line)
    i += 1

with open('E:/coding-assistant/server.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(fixed_lines))

print('Fixed indentation!')