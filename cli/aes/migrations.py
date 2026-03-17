"""Migration definitions for aes upgrade."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Must stay in sync with cli/aes/scaffold/agent.yaml.jinja
CURRENT_SPEC_VERSION = "1.2"


@dataclass
class MigrationFile:
    """A file that should exist after a migration is applied."""

    relative_path: str  # relative to .agent/, e.g. "commands/memory.md"
    template_name: str  # Jinja template to render from scaffold/
    manifest_entry: Optional[Dict[str, str]] = None  # entry to add to agent.yaml
    manifest_section: str = ""  # "commands" or "skills"


@dataclass
class Migration:
    """A single version migration step."""

    from_version: str  # e.g. "1.0"
    to_version: str  # e.g. "1.1"
    description: str
    files: List[MigrationFile] = field(default_factory=list)


MIGRATIONS: List[Migration] = [
    Migration(
        from_version="1.0",
        to_version="1.1",
        description="Add /memory command for auto-triggered memory review",
        files=[
            MigrationFile(
                relative_path="commands/memory.md",
                template_name="memory_command.md.jinja",
                manifest_entry={
                    "id": "memory",
                    "path": "commands/memory.md",
                    "trigger": "/memory",
                    "description": "Review conversation and save learnings to agent memory",
                },
                manifest_section="commands",
            ),
        ],
    ),
    Migration(
        from_version="1.1",
        to_version="1.2",
        description="Add AI-BOM, decision records, and extended agent manifest",
        files=[
            MigrationFile(
                relative_path="bom.yaml",
                template_name="bom.yaml.jinja",
            ),
        ],
    ),
]


def applicable_migrations(current_version: str) -> List[Migration]:
    """Return migrations needed to go from *current_version* to latest."""
    current = tuple(int(x) for x in current_version.split("."))
    return [
        m
        for m in MIGRATIONS
        if tuple(int(x) for x in m.from_version.split(".")) >= current
    ]
