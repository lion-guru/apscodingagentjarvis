with open('E:/coding-assistant/third_eye.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix the try/except indentation (should be 8 spaces inside method)
for i in range(len(lines)):
    if i < 664 or i >= 690:
        continue
    line = lines[i]
    stripped = line.lstrip()
    if not stripped:
        continue
    if stripped.startswith('try:') or stripped.startswith('except Exception:'):
        lines[i] = '        ' + stripped + '\n'
    elif stripped.startswith('return {') or stripped.startswith('"current_ide"') or stripped.startswith('"has_driver"') or stripped.startswith('"last_output"') or stripped.startswith('"detected_error"'):
        lines[i] = '            ' + stripped + '\n'
    elif stripped == '}':
        lines[i] = '            ' + stripped + '\n'
    elif stripped == '}':
        lines[i] = '        ' + stripped + '\n'
    elif stripped == 'except Exception:':
        lines[i] = '        ' + stripped + '\n'

with open('E:/coding-assistant/third_eye.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed try/except indentation!')