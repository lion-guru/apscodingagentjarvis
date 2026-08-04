---
name: security-audit
description: Scan a codebase for common security vulnerabilities.
when_to_use: Before deployment or after significant changes to auth/data handling.
version: 1.0
arguments: path
argument-hint: path-to-project
allowed-tools: search_code read_file git run_command
---

# Security Audit

Scan the project at $path for security vulnerabilities.

## Checks

1. **Secrets** — search for API keys, tokens, passwords committed to the repo.
2. **Auth** — look for weak/broken authentication, missing authorization checks.
3. **Injection** — SQL injection, command injection, XSS, path traversal.
4. **Dependencies** — check for known-vulnerable packages if a lockfile exists.
5. **Exposure** — debug endpoints, verbose error messages leaking internals, CORS misconfig.

## Output

Report in plain text labels:

   Scope: Security audit of <path>
   Result: <overall security posture>
   Key files: <files with findings>
   Issues: <severity-tagged list>

Do NOT fix anything unless the directive explicitly asks — auditing reports findings.
