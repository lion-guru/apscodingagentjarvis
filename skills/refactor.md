---
name: refactor
description: Safely refactor code while preserving behavior
version: 1.0.0
---

# Refactor Skill

## Instructions
When refactoring code:
1. **Understand the code**: Read the full function/class before making changes
2. **Preserve behavior**: All tests must pass after refactoring
3. **Small steps**: Make one change at a time, test after each
4. **Rename carefully**: Use find-and-replace across the entire workspace
5. **Extract methods**: Break large functions into smaller, focused ones
6. **Remove duplication**: Identify repeated patterns and extract shared code

## Safety Rules
- Never change public API signatures without updating all callers
- Always run linter after refactoring
- Keep git history clean with meaningful commit messages