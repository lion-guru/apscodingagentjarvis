with open('E:/coding-assistant/third_eye.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the get_ide_status method and replace it entirely
old_method_start = content.find('    def get_ide_status(self) -> dict:')
if old_method_start == -1:
    print("Method not found!")
else:
    # Find the end of the method (next method or class)
    next_method = content.find('\n    def ', old_method_start + 1)
    next_class = content.find('\nclass ', old_method_start + 1)
    
    if next_method == -1:
        next_method = len(content)
    if next_class == -1:
        next_class = len(content)
    
    method_end = min(next_method, next_class)
    
    # New method with proper indentation
    new_method = '''    def get_ide_status(self) -> dict:
        """Get full status of the browser IDE."""
        try:
            return {
                "current_ide": self.current_ide,
                "has_driver": self._driver is not None,
                "last_output": self.read_ide_output()[:500] if self._driver else "",
                "detected_error": self.detect_error_in_ide() if self._driver else None
            }
        except Exception:
            return {
                "current_ide": self.current_ide,
                "has_driver": self._driver is not None,
                "last_output": "",
                "detected_error": None
            }


'''
    
    new_content = content[:old_method_start] + new_method + content[method_end:]
    
    with open('E:/coding-assistant/third_eye.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print('Method replaced successfully!')