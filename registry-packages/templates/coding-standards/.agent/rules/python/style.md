---
name: style
scope: python
priority: high
---

# Python Style

## PEP 8 Compliance
- Follow PEP 8 as the baseline for all Python code
- Use `black` for automated formatting with default settings (line length 88, or project override)
- Use `isort` to sort imports with the `black` profile for compatibility
- Run `ruff` or `flake8` for linting in CI

## Type Hints
- Add type annotations to all function signatures (parameters and return types)
- Use `from __future__ import annotations` for modern annotation syntax on Python 3.10+
- Prefer `Optional[X]` over `X | None` for broader compatibility
- Use `TypedDict`, `Protocol`, and `dataclass` to define structured data shapes
- Run `mypy --strict` (or `pyright`) in CI to catch type errors

## Docstrings
- Write docstrings for all public modules, classes, and functions
- Use Google-style or NumPy-style docstrings — pick one and be consistent across the project
- Include `Args`, `Returns`, and `Raises` sections for non-trivial functions
- Keep the one-line summary under 79 characters

## Module Layout
- Standard import order: `__future__`, stdlib, third-party, local — separated by blank lines
- Place constants and module-level configuration near the top, after imports
- Use `__all__` to explicitly declare the public API of a module
- Avoid circular imports — extract shared types into a dedicated `types.py` module
