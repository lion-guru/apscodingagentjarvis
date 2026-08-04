import ast, sys

try:
    with open('server.py', encoding='utf-8') as f:
        src = f.read()
    ast.parse(src)
    with open('syntax_result.txt', 'w') as out:
        out.write('SYNTAX OK - server.py has no Python syntax errors\n')
except SyntaxError as e:
    with open('syntax_result.txt', 'w') as out:
        out.write(f'SYNTAX ERROR at line {e.lineno}: {e.msg}\n')
        out.write(f'  Text: {e.text}\n')
except Exception as e:
    with open('syntax_result.txt', 'w') as out:
        out.write(f'ERROR: {e}\n')
