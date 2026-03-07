"""Framework-aware configuration overlays for aes init.

Provides base project type configs (api, web-frontend, fullstack, cli-tool,
library) and framework-specific overlays that augment them with tailored
skills, rules, and permissions.

When ``aes init`` detects a framework (e.g. FastAPI), it:
1. Looks up the base config for the project type (e.g. "api").
2. Merges any framework-specific overlay on top.

This replaces the "other" domain dead-end with useful, framework-aware
scaffolding for most real-world projects.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from aes.domains import DomainConfig, SkillDef, WorkflowDef, WorkflowStateDef, WorkflowTransitionDef


# ---------------------------------------------------------------------------
# Framework overlay data class
# ---------------------------------------------------------------------------

@dataclass
class FrameworkOverlay:
    """Lightweight overlay that augments a base project type config."""

    framework: str
    extra_rules: List[str] = field(default_factory=list)
    extra_skills: List[SkillDef] = field(default_factory=list)
    extra_quick_ref: str = ""
    extra_gotchas: List[str] = field(default_factory=list)
    permissions_shell_execute: List[str] = field(default_factory=list)
    permissions_file_write: List[str] = field(default_factory=list)
    permissions_confirm_shell: List[str] = field(default_factory=list)
    permissions_deny_shell: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Universal skills (used across base configs)
# ---------------------------------------------------------------------------

_TEST_RUNNER = SkillDef(
    id="test-runner",
    name="Run Tests",
    version="1.0.0",
    description="Run the project test suite with coverage reporting",
    stage=1,
    phase="quality",
    trigger_command="",  # filled by framework overlay
    error_strategy="fail-fast",
    tags=["testing", "quality"],
    runbook_purpose="Run the full test suite and report results with coverage.",
    runbook_when="- After making code changes\n- Before committing\n- Before deployment",
    runbook_how="1. Run the test suite\n2. Check for failures\n3. Review coverage report\n4. Fix any failures before continuing",
    runbook_decision_tree="Run tests\n  |- All pass? -> Continue with task\n  |- Failures? -> Read failure output, fix, re-run\n  \\- Coverage dropped? -> Add tests for uncovered code",
    runbook_error_handling="- **Test failure**: Read the full error, fix the root cause, re-run\n- **Import error**: Check dependencies are installed\n- **Timeout**: Look for hanging async operations or infinite loops",
)

_LINT_FIX = SkillDef(
    id="lint-fix",
    name="Lint and Fix",
    version="1.0.0",
    description="Run linters and auto-fix style issues",
    stage=2,
    phase="quality",
    trigger_command="",
    error_strategy="fail-fast",
    tags=["linting", "quality", "style"],
    runbook_purpose="Run linters to catch style issues and auto-fix what's possible.",
    runbook_when="- Before committing code\n- After major refactoring\n- When CI reports lint failures",
    runbook_how="1. Run the linter with auto-fix enabled\n2. Review any remaining issues that couldn't be auto-fixed\n3. Fix manually if needed",
    runbook_decision_tree="Run linter\n  |- All clean? -> Continue\n  |- Auto-fixable? -> Apply fixes, verify\n  \\- Manual fix needed? -> Fix and re-run",
    runbook_error_handling="- **Config error**: Check linter config file exists and is valid\n- **Parse error**: File has syntax errors -- fix those first",
)

_DB_MIGRATE = SkillDef(
    id="db-migrate",
    name="Database Migrate",
    version="1.0.0",
    description="Run database migrations safely",
    stage=3,
    phase="infrastructure",
    trigger_command="",
    error_strategy="fail-fast",
    tags=["database", "migrations"],
    runbook_purpose="Apply pending database migrations safely with rollback awareness.",
    runbook_when="- Schema changes needed\n- After pulling new code with migrations\n- During deployment",
    runbook_how="1. Check current migration status\n2. Review pending migrations\n3. Apply migrations\n4. Verify schema is correct",
    runbook_decision_tree="Check migration status\n  |- No pending? -> Skip\n  |- Pending migrations?\n  |   |- Review for destructive changes (DROP, DELETE)\n  |   |- Safe changes? -> Apply\n  |   \\- Destructive? -> Confirm with user first\n  \\- Migration fails? -> Check error, do NOT retry blindly",
    runbook_error_handling="- **Migration conflict**: Resolve the conflict, do not skip\n- **Lock timeout**: Another process may hold the lock\n- **Data loss warning**: Stop and confirm with user",
)


# ---------------------------------------------------------------------------
# Base project type configs
# ---------------------------------------------------------------------------

_API_WORKFLOW = WorkflowDef(
    id="feature-lifecycle",
    entity="feature",
    description="Feature development lifecycle for API services",
    states=[
        WorkflowStateDef("planned", "Requirements understood", initial=True),
        WorkflowStateDef("implementing", "Code being written", active=True),
        WorkflowStateDef("testing", "Tests running"),
        WorkflowStateDef("deployed", "Live in target environment", terminal=True),
        WorkflowStateDef("blocked", "Cannot proceed", terminal=True),
    ],
    transitions=[
        WorkflowTransitionDef("planned", "implementing",
                              conditions=["Requirements are clear"]),
        WorkflowTransitionDef("implementing", "testing",
                              conditions=["Implementation complete"]),
        WorkflowTransitionDef("testing", "deployed",
                              conditions=["All tests pass"]),
        WorkflowTransitionDef("testing", "implementing",
                              conditions=["Tests fail"],
                              description="Fix failing tests"),
    ],
)

API_CONFIG = DomainConfig(
    instructions_description="API service with endpoints, authentication, and database.",
    instructions_quick_ref="",  # filled by framework overlay
    instructions_project_structure="",  # generic, filled by overlay or /setup
    instructions_rules=[
        "**Tests first** -- run tests after every change.",
        "**Auth on every endpoint** -- use middleware, not per-route checks.",
        "**No raw SQL** -- use an ORM or query builder. Parameterize if raw SQL is unavoidable.",
        "**Validate inputs** -- never trust user input at API boundaries.",
    ],
    instructions_workflow_phases=[
        {"title": "Understand Requirements", "content": "What endpoint? What data? What auth?"},
        {"title": "Implement", "content": "Migration (if DB) -> endpoint -> validation -> tests."},
        {"title": "Test (DO NOT SKIP)", "content": "Unit + integration tests must pass."},
        {"title": "Deploy", "content": "Staging first, verify, then production."},
    ],
    instructions_key_principle="Every endpoint is tested, authenticated, and validated. Ship incrementally.",
    instructions_gotchas=[],
    skills=[_TEST_RUNNER, _LINT_FIX],
    orchestrator_pipeline="implement -> test -> review -> deploy",
    orchestrator_status_flow="planned -> implementing -> testing -> deployed",
    orchestrator_decision_tree="1. Understand the requirement\n2. Check if migration needed\n3. Implement the endpoint\n4. Write tests\n5. Run tests\n6. Fix failures\n7. Ready for review/deploy",
    orchestrator_when_to_stop="- Feature implemented and tests passing\n- Deployed and verified",
    workflow=_API_WORKFLOW,
    permissions_shell_execute=[],
    permissions_file_write=["src/**", "tests/**"],
    permissions_deny_shell=["rm -rf *"],
    permissions_confirm_shell=["git push *"],
)

_FRONTEND_WORKFLOW = WorkflowDef(
    id="feature-lifecycle",
    entity="feature",
    description="Feature development lifecycle for frontend apps",
    states=[
        WorkflowStateDef("planned", "Design/requirements understood", initial=True),
        WorkflowStateDef("implementing", "Building component", active=True),
        WorkflowStateDef("testing", "Tests + visual review"),
        WorkflowStateDef("deployed", "Live", terminal=True),
    ],
    transitions=[
        WorkflowTransitionDef("planned", "implementing",
                              conditions=["Requirements are clear"]),
        WorkflowTransitionDef("implementing", "testing",
                              conditions=["Component renders correctly"]),
        WorkflowTransitionDef("testing", "deployed",
                              conditions=["Tests pass"]),
        WorkflowTransitionDef("testing", "implementing",
                              conditions=["Tests fail or visual issues"]),
    ],
)

FRONTEND_CONFIG = DomainConfig(
    instructions_description="Frontend application with components, routing, and state management.",
    instructions_rules=[
        "**Component-first** -- build small, reusable components.",
        "**Type safety** -- avoid `any` types. Use proper interfaces.",
        "**Accessible** -- use semantic HTML, ARIA attributes where needed.",
        "**Test interactions** -- test user behavior, not implementation details.",
    ],
    instructions_workflow_phases=[
        {"title": "Understand", "content": "What does the user see? What interactions?"},
        {"title": "Build", "content": "Component -> styling -> state -> integration."},
        {"title": "Test", "content": "Unit tests + visual review."},
        {"title": "Ship", "content": "Build, deploy, verify."},
    ],
    instructions_key_principle="Build for the user. Components should be small, tested, and accessible.",
    skills=[_TEST_RUNNER, _LINT_FIX],
    orchestrator_pipeline="design -> implement -> test -> deploy",
    orchestrator_status_flow="planned -> implementing -> testing -> deployed",
    workflow=_FRONTEND_WORKFLOW,
    permissions_shell_execute=["npm run *", "npx *"],
    permissions_file_write=["src/**", "tests/**", "__tests__/**"],
    permissions_deny_shell=["rm -rf *"],
    permissions_confirm_shell=["npm run deploy*", "git push *"],
)

FULLSTACK_CONFIG = DomainConfig(
    instructions_description="Full-stack application with frontend, API, and database.",
    instructions_rules=[
        "**Type safety everywhere** -- shared types between frontend and API.",
        "**API-first** -- design the API contract before building UI.",
        "**Test both layers** -- unit tests for logic, integration tests for API, component tests for UI.",
        "**Migrations before code** -- schema changes go first.",
    ],
    instructions_workflow_phases=[
        {"title": "Plan", "content": "API contract -> data model -> UI wireframe."},
        {"title": "Backend", "content": "Migration -> API endpoint -> validation -> tests."},
        {"title": "Frontend", "content": "Component -> API integration -> tests."},
        {"title": "Ship", "content": "All tests pass -> staging -> production."},
    ],
    instructions_key_principle="Full-stack means full responsibility. Test every layer.",
    skills=[_TEST_RUNNER, _LINT_FIX, _DB_MIGRATE],
    orchestrator_pipeline="plan -> backend -> frontend -> test -> deploy",
    orchestrator_status_flow="planned -> backend -> frontend -> testing -> deployed",
    workflow=_API_WORKFLOW,  # reuse API workflow
    permissions_shell_execute=["npm run *", "npx *"],
    permissions_file_write=["src/**", "app/**", "tests/**", "migrations/**"],
    permissions_deny_shell=["rm -rf *", "DROP DATABASE *"],
    permissions_confirm_shell=["npm run deploy*", "git push *"],
)

CLI_CONFIG = DomainConfig(
    instructions_description="Command-line tool with subcommands, argument parsing, and user interaction.",
    instructions_rules=[
        "**Clear error messages** -- users see stderr, make it helpful.",
        "**Exit codes matter** -- 0 for success, non-zero for failure.",
        "**Test the CLI** -- test argument parsing, output format, and error cases.",
        "**Progressive disclosure** -- simple defaults, flags for power users.",
    ],
    instructions_workflow_phases=[
        {"title": "Design", "content": "What commands? What flags? What output?"},
        {"title": "Implement", "content": "Command handler -> argument parsing -> output formatting."},
        {"title": "Test", "content": "Unit tests + CLI integration tests."},
        {"title": "Release", "content": "Version bump -> changelog -> publish."},
    ],
    instructions_key_principle="A CLI is a user interface. Treat it like one.",
    skills=[_TEST_RUNNER, _LINT_FIX],
    orchestrator_pipeline="design -> implement -> test -> release",
    orchestrator_status_flow="planned -> implementing -> testing -> released",
    permissions_shell_execute=[],
    permissions_file_write=["src/**", "tests/**"],
    permissions_deny_shell=["rm -rf *"],
    permissions_confirm_shell=["git push *"],
)

LIBRARY_CONFIG = DomainConfig(
    instructions_description="Reusable library or package for other projects to consume.",
    instructions_rules=[
        "**Public API is a contract** -- don't break it without a major version bump.",
        "**100% public API tested** -- every exported function has tests.",
        "**Document everything public** -- docstrings on all exported symbols.",
        "**No side effects on import** -- library code should be inert until called.",
    ],
    instructions_workflow_phases=[
        {"title": "Design API", "content": "What does the consumer need? Keep the surface small."},
        {"title": "Implement", "content": "Internal logic -> public API -> tests -> docs."},
        {"title": "Test", "content": "Unit tests + edge cases + docs tests."},
        {"title": "Publish", "content": "Version bump -> changelog -> publish to registry."},
    ],
    instructions_key_principle="Libraries are consumed by others. Stability and clarity above all.",
    skills=[_TEST_RUNNER, _LINT_FIX],
    orchestrator_pipeline="design -> implement -> test -> document -> publish",
    orchestrator_status_flow="planned -> implementing -> testing -> published",
    permissions_shell_execute=[],
    permissions_file_write=["src/**", "lib/**", "tests/**"],
    permissions_deny_shell=["rm -rf *"],
    permissions_confirm_shell=["git push *"],
)

# Project type -> base config
BASE_CONFIGS: Dict[str, DomainConfig] = {
    "api": API_CONFIG,
    "web-frontend": FRONTEND_CONFIG,
    "fullstack": FULLSTACK_CONFIG,
    "cli-tool": CLI_CONFIG,
    "library": LIBRARY_CONFIG,
}


# ---------------------------------------------------------------------------
# Framework overlays
# ---------------------------------------------------------------------------

FRAMEWORK_OVERLAYS: Dict[str, FrameworkOverlay] = {
    "fastapi": FrameworkOverlay(
        framework="fastapi",
        extra_rules=[
            "**Pydantic models for all requests/responses** -- no raw dicts.",
            "**Async by default** -- use `async def` for route handlers.",
            "**Dependency injection** -- use FastAPI's `Depends()` for shared logic.",
        ],
        extra_skills=[
            SkillDef(
                id="db-migrate",
                name="Database Migrate",
                version="1.0.0",
                description="Run Alembic database migrations",
                stage=3,
                phase="infrastructure",
                trigger_command="alembic upgrade head",
                error_strategy="fail-fast",
                tags=["database", "alembic", "migrations"],
                runbook_purpose="Run Alembic migrations to update the database schema.",
                runbook_when="- Schema changes needed\n- After pulling code with new migrations",
                runbook_how="1. `alembic current` -- check current revision\n2. `alembic heads` -- see pending migrations\n3. `alembic upgrade head` -- apply all pending\n4. Verify with `alembic current`",
                runbook_decision_tree="Check alembic status\n  |- Up to date? -> Skip\n  |- Pending? -> Review migration, then apply\n  \\- Conflict? -> Resolve merge conflict in migrations/",
                runbook_error_handling="- **Migration conflict**: `alembic merge heads` to create merge migration\n- **Apply error**: `alembic downgrade -1` to rollback last",
            ),
        ],
        extra_quick_ref="uvicorn app.main:app --reload    # start dev server\nalembic upgrade head              # run migrations\nalembic revision --autogenerate   # create migration\npython -m pytest -v               # run tests",
        extra_gotchas=[
            "Use `Optional[X]` not `X | None` for Pydantic fields (Python 3.9 compat).",
            "Background tasks run after response -- don't rely on them for critical work.",
            "`Depends()` creates a new instance per request by default.",
        ],
        permissions_shell_execute=[
            "python -m pytest *",
            "uvicorn *",
            "alembic *",
        ],
        permissions_file_write=["app/**", "src/**", "tests/**", "alembic/**"],
        permissions_confirm_shell=["alembic downgrade *"],
    ),

    "django": FrameworkOverlay(
        framework="django",
        extra_rules=[
            "**Use Django ORM** -- no raw SQL unless absolutely necessary.",
            "**Class-based views for complex logic** -- function views for simple endpoints.",
            "**Settings via environment** -- use `django-environ` or similar.",
        ],
        extra_skills=[
            SkillDef(
                id="db-migrate",
                name="Database Migrate",
                version="1.0.0",
                description="Run Django database migrations",
                stage=3,
                phase="infrastructure",
                trigger_command="python manage.py migrate",
                error_strategy="fail-fast",
                tags=["database", "django", "migrations"],
                runbook_purpose="Run Django migrations to update the database schema.",
                runbook_when="- Schema changes needed\n- After pulling code with new migrations",
                runbook_how="1. `python manage.py showmigrations` -- check status\n2. `python manage.py makemigrations` -- generate if needed\n3. `python manage.py migrate` -- apply pending\n4. Verify with `python manage.py showmigrations`",
                runbook_decision_tree="Check migration status\n  |- Up to date? -> Skip\n  |- Model changes? -> makemigrations first, then migrate\n  \\- Conflict? -> Resolve, then migrate",
                runbook_error_handling="- **Conflict**: Resolve migration graph conflicts\n- **Data migration needed**: Write custom migration with `RunPython`",
            ),
        ],
        extra_quick_ref="python manage.py runserver        # start dev server\npython manage.py migrate          # run migrations\npython manage.py makemigrations   # create migration\npython manage.py test             # run tests",
        extra_gotchas=[
            "Always run `makemigrations` before `migrate` to catch model changes.",
            "Don't edit migration files manually unless writing data migrations.",
            "`select_related` and `prefetch_related` prevent N+1 queries.",
        ],
        permissions_shell_execute=[
            "python manage.py *",
            "python -m pytest *",
        ],
        permissions_file_write=["*/models.py", "*/views.py", "*/serializers.py", "*/tests.py", "*/admin.py", "*/urls.py", "tests/**"],
        permissions_confirm_shell=["python manage.py flush *"],
    ),

    "flask": FrameworkOverlay(
        framework="flask",
        extra_rules=[
            "**Application factory pattern** -- use `create_app()` for testability.",
            "**Blueprints for organization** -- don't put everything in one file.",
            "**Extensions for common tasks** -- Flask-SQLAlchemy, Flask-Migrate, etc.",
        ],
        extra_quick_ref="flask run --reload                # start dev server\nflask db upgrade                  # run migrations\npython -m pytest -v               # run tests",
        extra_gotchas=[
            "Flask runs in debug mode only when `FLASK_DEBUG=1` is set.",
            "Use `flask.current_app` inside request context, not the app instance.",
        ],
        permissions_shell_execute=[
            "flask *",
            "python -m pytest *",
        ],
    ),

    "nextjs": FrameworkOverlay(
        framework="nextjs",
        extra_rules=[
            "**Server components by default** -- only use `'use client'` when needed.",
            "**App Router** -- use the `app/` directory for routing.",
            "**Server actions for mutations** -- prefer over API routes for form submissions.",
        ],
        extra_quick_ref="npm run dev                       # start dev server\nnpm run build                     # production build\nnpm run test                      # run tests\nnpm run lint                      # run linter",
        extra_gotchas=[
            "Server components can't use hooks or browser APIs -- add `'use client'` first.",
            "`fetch()` in server components is cached by default -- use `{ cache: 'no-store' }` for dynamic data.",
            "Environment variables prefixed with `NEXT_PUBLIC_` are exposed to the browser.",
        ],
        permissions_shell_execute=[
            "npm run *",
            "npx *",
        ],
        permissions_file_write=["app/**", "src/**", "components/**", "lib/**", "tests/**", "__tests__/**"],
    ),

    "express": FrameworkOverlay(
        framework="express",
        extra_rules=[
            "**Middleware for cross-cutting concerns** -- auth, logging, error handling.",
            "**Router for organization** -- separate route files per resource.",
            "**Error middleware last** -- `(err, req, res, next)` at the end of the chain.",
        ],
        extra_quick_ref="npm run dev                       # start dev server\nnpm run test                      # run tests\nnpm run lint                      # run linter",
        extra_gotchas=[
            "Error middleware must have 4 parameters `(err, req, res, next)` or Express skips it.",
            "Always call `next(err)` in async route handlers to propagate errors.",
        ],
        permissions_shell_execute=[
            "npm run *",
            "npx *",
            "node *",
        ],
    ),

    "react": FrameworkOverlay(
        framework="react",
        extra_rules=[
            "**Hooks for state** -- prefer `useState` and `useReducer` over class components.",
            "**Composition over inheritance** -- build with small, composable components.",
            "**Memoize expensive renders** -- use `React.memo`, `useMemo`, `useCallback` when needed.",
        ],
        extra_quick_ref="npm run dev                       # start dev server\nnpm run build                     # production build\nnpm run test                      # run tests",
        extra_gotchas=[
            "State updates are batched -- don't read state immediately after setting it.",
            "Effect cleanup runs before re-running -- return a cleanup function from `useEffect`.",
        ],
        permissions_shell_execute=[
            "npm run *",
            "npx *",
        ],
        permissions_file_write=["src/**", "tests/**", "__tests__/**"],
    ),
}


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def resolve_config(
    project_type: str,
    frameworks: List[str],
    language: str,
    test_command: Optional[str] = None,
    build_command: Optional[str] = None,
) -> Optional[DomainConfig]:
    """Resolve a DomainConfig for a project type + detected frameworks.

    Returns None if no matching base config exists (caller should fall back
    to the existing domain-based or "other" scaffolding).
    """
    base = BASE_CONFIGS.get(project_type)
    if base is None:
        return None

    config = deepcopy(base)

    # Apply framework overlays
    for fw in frameworks:
        overlay = FRAMEWORK_OVERLAYS.get(fw)
        if overlay is None:
            continue

        # Merge rules
        config.instructions_rules.extend(overlay.extra_rules)

        # Merge skills (avoid duplicates by ID)
        existing_ids = {s.id for s in config.skills}
        for skill in overlay.extra_skills:
            if skill.id not in existing_ids:
                config.skills.append(skill)
                existing_ids.add(skill.id)

        # Merge quick ref
        if overlay.extra_quick_ref:
            if config.instructions_quick_ref:
                config.instructions_quick_ref += "\n" + overlay.extra_quick_ref
            else:
                config.instructions_quick_ref = overlay.extra_quick_ref

        # Merge gotchas
        config.instructions_gotchas.extend(overlay.extra_gotchas)

        # Merge permissions
        config.permissions_shell_execute.extend(overlay.permissions_shell_execute)
        config.permissions_file_write.extend(overlay.permissions_file_write)
        config.permissions_confirm_shell.extend(overlay.permissions_confirm_shell)
        config.permissions_deny_shell.extend(overlay.permissions_deny_shell)

    # Set test command on test-runner skill
    if test_command:
        for skill in config.skills:
            if skill.id == "test-runner" and not skill.trigger_command:
                skill.trigger_command = test_command

    # Set build command in quick ref if not already present
    if build_command and build_command not in (config.instructions_quick_ref or ""):
        if config.instructions_quick_ref:
            config.instructions_quick_ref += f"\n{build_command}"
        else:
            config.instructions_quick_ref = build_command

    # Deduplicate permissions lists
    config.permissions_shell_execute = list(dict.fromkeys(config.permissions_shell_execute))
    config.permissions_file_write = list(dict.fromkeys(config.permissions_file_write))
    config.permissions_confirm_shell = list(dict.fromkeys(config.permissions_confirm_shell))
    config.permissions_deny_shell = list(dict.fromkeys(config.permissions_deny_shell))

    return config
