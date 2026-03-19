---
name: testing
scope: python
priority: high
---

# Python Testing

## pytest as the Test Runner
- Use `pytest` for all Python test suites — do not use `unittest` directly
- Place tests in a `tests/` directory that mirrors the `src/` structure
- Name test files `test_<module>.py` and test functions `test_<behavior>`

## Fixtures
- Use `@pytest.fixture` for shared setup — prefer fixtures over `setUp`/`tearDown`
- Scope fixtures appropriately: `function` (default) for isolation, `session` for expensive resources
- Use `tmp_path` and `monkeypatch` fixtures instead of manual temp dirs or patching
- Define shared fixtures in `conftest.py` at the appropriate directory level

## Parametrize
- Use `@pytest.mark.parametrize` to test multiple inputs without duplicating test functions
- Keep parameter sets readable — use `pytest.param(..., id="descriptive_name")` for clarity
- Combine parametrize with fixtures for matrix testing (e.g. multiple backends x multiple inputs)

## Mocking
- Prefer dependency injection over `unittest.mock.patch` — it produces less fragile tests
- When mocking is necessary, patch at the call site, not at the definition site
- Use `pytest-httpx` or `responses` for HTTP mocking instead of patching `requests` directly
- Assert mock interactions only when the **call itself** is the behavior under test
