with open('E:/coding-assistant/third_eye.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the get_ide_status method and replace with error-handled version
for i, line in enumerate(lines):
    if 'def get_ide_status(self) -> dict:' in line:
        new_method = [
            '        def get_ide_status(self) -> dict:\n',
            '            """Get full status of the browser IDE."""\n',
            '            try:\n',
            '                return {\n',
            '                    "current_ide": self.current_ide,\n',
            '                    "has_driver": self._driver is not None,\n',
            '                    "last_output": self.read_ide_output()[:500] if self._driver else "",\n',
            '                    "detected_error": self.detect_error_in_ide() if self._driver else None\n',
            '                }\n',
            '            except Exception:\n',
            '                return {\n',
            '                    "current_ide": self.current_ide,\n',
            '                    "has_driver": self._driver is not None,\n',
            '                    "last_output": "",\n',
            '                    "detected_error": None\n',
            '                }\n',
            '\n'
        ]
        # Find end of method
        j = i + 1
        while j < len(lines) and (lines[j].startswith(' ') or lines[j].strip() == ''):
            if lines[j].strip().startswith('def ') and len(lines[j]) - len(lines[j].lstrip()) <= 4:
                break
            if lines[j].strip().startswith('class ') and len(lines[j]) - len(lines[j].lstrip()) == 0:
                break
            j += 1
        
        lines[i:j] = new_method
        print(f'Replaced method at lines {i+1}-{j}')
        break

with open('E:/coding-assistant/third_eye.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Updated method with error handling!')