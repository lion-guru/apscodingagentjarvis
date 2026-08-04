---
name: code-review
description: Perform a structured code review of a file or directory.
when_to_use: After writing or editing code, before considering a task complete.
version: 1.0
arguments: path
argument-hint: path/to/file-or-dir
allowed-tools: read_file search_code git run_command
---

# Code Review

Review the code at the path provided and report findings.

## Instructions

1. Read the target: `read_file` (for a file) or `list_files` + search (for a directory).
2. Check for:
   - Bugs: off-by-one, None/uninitialized access, resource leaks
   - Security: hardcoded secrets, shell injection, unsafe eval
   - Performance: obvious quadratic loops, N+1 queries, blocking calls in loops
3. Verify with `run_command` (e.g. `py_compile`, `npm run build`, or a linter) when applicable.
4. Report findings in plain text labels:

   Scope: Review of <path>
   Result: <overall assessment — is it correct/secure/maintainable?>
   Key files: <files examined>
   Issues: <numbered list of issues with severity and line references>

## Arguments

- `path`: the file or directory to review. Substituted from $path.
