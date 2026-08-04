---
name: test-gen
description: Generate comprehensive tests for Python code
version: 1.0.0
---

# Test Generation Skill

## Instructions
When generating tests:
1. **Identify testable functions**: Find all public functions and classes
2. **Write unit tests**: Test each function in isolation
3. **Cover edge cases**: Empty inputs, None values, boundary conditions
4. **Use pytest**: Follow pytest conventions and fixtures
5. **Include assertions**: Every test must verify expected behavior

## Test Structure
- `test_<module_name>.py` for each source module
- `test_<class_name>.py` for complex classes
- Use `pytest.raises` for expected exceptions
- Use `pytest.mark.parametrize` for multiple input combinations