---
name: code-review
description: Perform thorough code review checking for bugs, security issues, and best practices
version: 1.0.0
---

# Code Review Skill

## Instructions
When reviewing code, check for:
1. **Security**: eval/exec usage, pickle, hardcoded secrets, SQL injection, XSS
2. **Style**: Line length, trailing whitespace, naming conventions, imports
3. **Quality**: TODO/FIXME markers, dead code, unused imports, complexity
4. **Correctness**: Type hints, error handling, edge cases, race conditions

## Output Format
- List all issues found with severity (error/warning/info)
- Provide specific line numbers
- Suggest fixes where possible