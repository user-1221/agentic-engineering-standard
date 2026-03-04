"""CLI configuration and paths."""

from __future__ import annotations

from pathlib import Path

# Schema directory — relative to the repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"
SCAFFOLD_DIR = Path(__file__).resolve().parent / "scaffold"

# Standard directory and file names
AGENT_DIR = ".agent"
MANIFEST_FILE = "agent.yaml"
INSTRUCTIONS_FILE = "instructions.md"
PERMISSIONS_FILE = "permissions.yaml"
AGENTIGNORE_FILE = ".agentignore"
AGENT_MD_FILE = "AGENT.md"
SKILLS_DIR = "skills"
VENDOR_DIR = "vendor"
REGISTRY_DIR = "registry"
WORKFLOWS_DIR = "workflows"
COMMANDS_DIR = "commands"
MEMORY_DIR = "memory"
OVERRIDES_DIR = "overrides"
LOCAL_FILE = "local.yaml"
LOCAL_EXAMPLE_FILE = "local.example.yaml"

# Schema file mapping
SCHEMA_MAP = {
    "agent": "agent.schema.json",
    "skill": "skill.schema.json",
    "workflow": "workflow.schema.json",
    "registry": "registry.schema.json",
    "permissions": "permissions.schema.json",
}
