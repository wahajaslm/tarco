# Coding Guidelines

These guidelines complement the contributor guide in `AGENTS.md` and apply to all Python code in this repository.

## General
- Target Python 3.11+ and use type hints throughout.
- Prefer explicit imports; remove unused imports and variables.
- Avoid wildcard imports and `from module import *` patterns.

## Error Handling
- Do not use bare `except:` clauses. Always catch `Exception` or a more specific subtype.
- Log errors with context before raising or handling them.

## Style
- Follow [PEP 8](https://peps.python.org/pep-0008/) conventions.
- Run `ruff check` on any modified Python files before committing.
- Use descriptive variable and function names; keep functions small and single-purpose.
- Include docstrings for all public modules, classes, and functions.

## Testing
- Add or update tests for new features or bug fixes.
- Ensure `pytest` passes locally before pushing changes.
- Tests should be deterministic and not depend on external network access.

Adhering to these guidelines keeps the codebase clean, maintainable, and production-ready.
