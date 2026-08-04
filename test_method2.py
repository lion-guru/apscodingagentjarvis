method_code = """def get_ide_status(self) -> dict:
        \"\"\"Get full status of the browser IDE.\"\"\"
        return {
            \"current_ide\": self.current_ide,
            \"has_driver\": self._driver is not None,
            \"last_output\": self.read_ide_output()[:500],
            \"detected_error\": self.detect_error_in_ide(),
        }
"""

namespace = {}
exec(method_code, namespace)
get_ide_status = namespace['get_ide_status']

class TestClass:
    pass

TestClass.get_ide_status = get_ide_status
print('Defined:', 'get_ide_status' in dir(TestClass))
t = TestClass()
print('Result:', t.get_ide_status())