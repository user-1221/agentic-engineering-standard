"""CLI configuration and paths."""

from __future__ import annotations

import sys
from pathlib import Path

# Resource directories — handle PyInstaller bundles and normal installs
if getattr(sys, "frozen", False):
    # Running as PyInstaller bundle
    _BASE = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    SCHEMAS_DIR = _BASE / "aes" / "schemas"
    SCAFFOLD_DIR = _BASE / "aes" / "scaffold"
else:
    # Normal install (pip, editable, source)
    SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"
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
DECISIONS_DIR = "memory/decisions"
OVERRIDES_DIR = "overrides"
LOCAL_FILE = "local.yaml"
LOCAL_EXAMPLE_FILE = "local.example.yaml"
BOM_FILE = "bom.yaml"

# Schema file mapping
SCHEMA_MAP = {
    "agent": "agent.schema.json",
    "skill": "skill.schema.json",
    "workflow": "workflow.schema.json",
    "registry": "registry.schema.json",
    "permissions": "permissions.schema.json",
    "bom": "bom.schema.json",
    "decision-record": "decision-record.schema.json",
}
