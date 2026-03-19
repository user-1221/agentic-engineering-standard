---
name: testing
scope: common
priority: high
overridable_fields:
  - min_coverage
  - max_test_duration
defaults:
  min_coverage: 80
  max_test_duration: "5s"
---

# Testing Standards

## Coverage Requirements
- Maintain a minimum of ${min_coverage}% code coverage on all new code
- Coverage should never decrease with a new change — add tests for any code you modify
- Measure branch coverage, not just line coverage

## Test Structure
- Follow the Arrange-Act-Assert (AAA) pattern in every test
- One logical assertion per test — test one behavior at a time
- Name tests to describe the behavior: `test_returns_404_when_user_not_found`
- Group related tests in describe/context blocks or test classes

## Test Speed
- Individual unit tests must complete within ${max_test_duration}
- Prefer in-memory fakes and stubs over mocks that verify call sequences
- Isolate tests from external systems (network, filesystem, databases)
- Tag slow integration tests so they can be run separately

## Test Quality
- Tests are first-class code — apply the same style and review standards
- Do not test implementation details; test observable behavior
- Avoid test interdependence — each test must pass when run in isolation
- Delete tests that no longer validate meaningful behavior
