# .claude/rules/code-style.md

# Code Style Guide

## General
- Prefer clear, readable code over clever code
- Write small, focused functions that do one thing
- Remove unused imports, variables and dead code

## Python
- Add comments where needed, but don't splash them everywhere
- Use f-strings, not '%' or '.format()'
- Use pathlib for paths
- Use dataclasses or Pydantic for structured data
- Use logging, not print, for diagnostics

## Naming
- PascalCase for classes
- snake_case.py for files/modules
- UPPER_SNAKE_CASE for constants
- Keep names descriptive and simple
