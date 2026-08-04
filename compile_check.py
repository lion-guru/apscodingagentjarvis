import subprocess
result = subprocess.run(['py', '-m', 'py_compile', 'E:/coding-assistant/server.py'], capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)