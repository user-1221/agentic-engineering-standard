"""Schema validation engine for AES files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml
from jsonschema import Draft202012Validator, ValidationError

from aes.config import (
    SCHEMAS_DIR, SCHEMA_MAP, BOM_FILE, DECISIONS_DIR,
    LIFECYCLE_FILE, LEARNING_CONFIG_FILE, INSTINCTS_DIR,
    RULES_CONFIG_FILE, RULES_DIR, SCRIPTS_DIR,
)


@dataclass
class ValidationResult:
    """Result of validating a single file."""

    file_path: Path
    schema_type: str
    valid: bool
    errors: List[str] = field(default_factory=list)


def load_schema(schema_type: str) -> dict:
    """Load a JSON Schema by type name."""
    filename = SCHEMA_MAP.get(schema_type)
    if filename is None:
        raise ValueError(f"Unknown schema type: {schema_type}. Known: {list(SCHEMA_MAP.keys())}")
    schema_path = SCHEMAS_DIR / filename
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    with open(schema_path) as f:
        return json.load(f)


def load_yaml(file_path: Path) -> dict:
    """Load and parse a YAML file."""
    with open(file_path) as f:
        data = yaml.safe_load(f)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {file_path}, got {type(data).__name__}")
    return data


def validate_file(file_path: Path, schema_type: str) -> ValidationResult:
    """Validate a YAML file against a JSON Schema."""
    result = ValidationResult(file_path=file_path, schema_type=schema_type, valid=True)

    try:
        data = load_yaml(file_path)
    except Exception as e:
        result.valid = False
        result.errors.append(f"Failed to parse YAML: {e}")
        return result

    try:
        schema = load_schema(schema_type)
    except Exception as e:
        result.valid = False
        result.errors.append(f"Failed to load schema: {e}")
        return result

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    if errors:
        result.valid = False
        for error in errors:
            path = ".".join(str(p) for p in error.absolute_path) or "(root)"
            result.errors.append(f"  {path}: {error.message}")

    return result


def validate_agent_dir(agent_dir: Path) -> List[ValidationResult]:
    """Validate all files in a .agent/ directory."""
    results = []

    # Validate agent.yaml
    manifest_path = agent_dir / "agent.yaml"
    if manifest_path.exists():
        results.append(validate_file(manifest_path, "agent"))
    else:
        results.append(ValidationResult(
            file_path=manifest_path,
            schema_type="agent",
            valid=False,
            errors=["File not found: agent.yaml is required"],
        ))
        return results  # Can't continue without manifest

    # Load manifest to find referenced files
    try:
        manifest = load_yaml(manifest_path)
    except Exception:
        return results

    # Validate permissions
    agent_section = manifest.get("agent", {})
    permissions_path_str = agent_section.get("permissions")
    if permissions_path_str:
        permissions_path = agent_dir / permissions_path_str
        if permissions_path.exists():
            results.append(validate_file(permissions_path, "permissions"))
        else:
            results.append(ValidationResult(
                file_path=permissions_path,
                schema_type="permissions",
                valid=False,
                errors=[f"Referenced file not found: {permissions_path_str}"],
            ))

    # Validate skills
    for skill_ref in manifest.get("skills", []):
        manifest_rel = skill_ref.get("manifest")
        if manifest_rel:
            skill_path = agent_dir / manifest_rel
            if skill_path.exists():
                results.append(validate_file(skill_path, "skill"))
            else:
                results.append(ValidationResult(
                    file_path=skill_path,
                    schema_type="skill",
                    valid=False,
                    errors=[f"Referenced file not found: {manifest_rel}"],
                ))

        runbook_rel = skill_ref.get("runbook")
        if runbook_rel:
            runbook_path = agent_dir / runbook_rel
            if not runbook_path.exists():
                results.append(ValidationResult(
                    file_path=runbook_path,
                    schema_type="skill",
                    valid=False,
                    errors=[f"Referenced runbook not found: {runbook_rel}"],
                ))

    # Validate workflows
    for wf_ref in manifest.get("workflows", []):
        wf_path = agent_dir / wf_ref["path"]
        if wf_path.exists():
            results.append(validate_file(wf_path, "workflow"))
        else:
            results.append(ValidationResult(
                file_path=wf_path,
                schema_type="workflow",
                valid=False,
                errors=[f"Referenced file not found: {wf_ref['path']}"],
            ))

    # Validate registries
    for reg_ref in manifest.get("registries", []):
        reg_path = agent_dir / reg_ref["path"]
        if reg_path.exists():
            results.append(validate_file(reg_path, "registry"))
        else:
            results.append(ValidationResult(
                file_path=reg_path,
                schema_type="registry",
                valid=False,
                errors=[f"Referenced file not found: {reg_ref['path']}"],
            ))

    # Check command files exist
    for cmd_ref in manifest.get("commands", []):
        cmd_path = agent_dir / cmd_ref["path"]
        if not cmd_path.exists():
            results.append(ValidationResult(
                file_path=cmd_path,
                schema_type="command",
                valid=False,
                errors=[f"Referenced command file not found: {cmd_ref['path']}"],
            ))

    # Check instructions file exists
    instructions_rel = agent_section.get("instructions")
    if instructions_rel:
        instructions_path = agent_dir / instructions_rel
        if not instructions_path.exists():
            results.append(ValidationResult(
                file_path=instructions_path,
                schema_type="instructions",
                valid=False,
                errors=[f"Instructions file not found: {instructions_rel}"],
            ))

    # Validate bom.yaml (optional)
    bom_path = agent_dir / BOM_FILE
    if bom_path.exists():
        results.append(validate_file(bom_path, "bom"))

    # Validate decision records (optional)
    decisions_dir = agent_dir / DECISIONS_DIR
    if decisions_dir.exists() and decisions_dir.is_dir():
        for dr_file in sorted(decisions_dir.glob("*.yaml")):
            results.append(validate_file(dr_file, "decision-record"))

    # Validate lifecycle.yaml (optional)
    lifecycle_path = agent_dir / LIFECYCLE_FILE
    if lifecycle_path.exists():
        results.append(validate_file(lifecycle_path, "lifecycle"))
        # Warn if referenced scripts don't exist
        try:
            lc_data = load_yaml(lifecycle_path)
            scripts_dir = agent_dir / SCRIPTS_DIR
            for event_key in ("on_session_start", "on_session_end",
                              "pre_tool_use", "post_tool_use", "on_error"):
                for hook in (lc_data.get("hooks", {}) or {}).get(event_key, []):
                    cmd = hook.get("command", "")
                    if cmd and ".agent/scripts/" in cmd:
                        script_name = cmd.split(".agent/scripts/")[-1].split()[0]
                        if not (scripts_dir / script_name).exists():
                            results.append(ValidationResult(
                                file_path=lifecycle_path,
                                schema_type="lifecycle",
                                valid=True,
                                errors=[
                                    f"Hook '{hook.get('name', '?')}' references "
                                    f"script not found: scripts/{script_name} (warning)"
                                ],
                            ))
        except Exception:
            pass

    # Validate learning config (optional)
    learning_config_path = agent_dir / LEARNING_CONFIG_FILE
    if learning_config_path.exists():
        results.append(validate_file(learning_config_path, "learning-config"))

    # Validate instinct files (optional)
    instincts_base = agent_dir / INSTINCTS_DIR
    if instincts_base.exists() and instincts_base.is_dir():
        for instinct_file in sorted(instincts_base.glob("**/*.instinct.yaml")):
            results.append(validate_file(instinct_file, "instinct"))
            # Warn if active instinct has score below min_score
            try:
                inst_data = load_yaml(instinct_file)
                conf = inst_data.get("confidence", {})
                if (conf.get("status") == "active"
                        and conf.get("score", 1.0) < conf.get("min_score", 0.3)):
                    results.append(ValidationResult(
                        file_path=instinct_file,
                        schema_type="instinct",
                        valid=True,
                        errors=[
                            f"Instinct '{inst_data.get('metadata', {}).get('id', '?')}' "
                            f"is active but score ({conf['score']}) is below "
                            f"min_score ({conf.get('min_score', 0.3)}) (warning)"
                        ],
                    ))
            except Exception:
                pass

    # Validate rules config (optional)
    rules_config_path = agent_dir / RULES_CONFIG_FILE
    if rules_config_path.exists():
        results.append(validate_file(rules_config_path, "rules-config"))
        # Warn if configured language directories don't exist
        try:
            rules_data = load_yaml(rules_config_path)
            rules_base = agent_dir / RULES_DIR
            for lang in rules_data.get("languages", []):
                lang_dir = rules_base / lang
                if not lang_dir.exists():
                    results.append(ValidationResult(
                        file_path=rules_config_path,
                        schema_type="rules-config",
                        valid=True,
                        errors=[
                            f"Language directory not found: rules/{lang} (warning)"
                        ],
                    ))
        except Exception:
            pass

    # Validate skill dependency graph
    results.extend(_validate_skill_graph(agent_dir, manifest))

    # Quality checks (warnings)
    results.extend(_validate_skill_quality(agent_dir, manifest))

    return results


def _validate_skill_graph(
    agent_dir: Path,
    manifest: dict,
) -> List[ValidationResult]:
    """Validate depends_on/blocks references and detect cycles."""
    results: List[ValidationResult] = []

    # Collect all declared skill IDs from the manifest
    declared_ids = {s["id"] for s in manifest.get("skills", []) if "id" in s}
    if not declared_ids:
        return results

    # Build adjacency list for cycle detection (depends_on edges)
    adjacency: dict = {sid: [] for sid in declared_ids}

    for skill_ref in manifest.get("skills", []):
        manifest_rel = skill_ref.get("manifest")
        if not manifest_rel:
            continue
        skill_path = agent_dir / manifest_rel
        if not skill_path.exists():
            continue

        try:
            skill_data = load_yaml(skill_path)
        except Exception:
            continue

        skill_id = skill_data.get("id", skill_ref.get("id", "unknown"))

        # Check depends_on references
        for dep in skill_data.get("depends_on", []):
            dep_id = dep if isinstance(dep, str) else dep.get("skill", "")
            if not dep_id:
                continue
            if dep_id not in declared_ids:
                # Warning only — vendored skills may reference deps not
                # yet installed in this project.
                results.append(ValidationResult(
                    file_path=skill_path,
                    schema_type="skill",
                    valid=True,
                    errors=[f"depends_on references skill not in this project: '{dep_id}' (warning)"],
                ))
            else:
                adjacency.setdefault(skill_id, []).append(dep_id)

        # Check blocks references (warnings only — blocked skills may
        # exist in a larger system outside this project)
        for blocked in skill_data.get("blocks", []):
            if blocked not in declared_ids:
                results.append(ValidationResult(
                    file_path=skill_path,
                    schema_type="skill",
                    valid=True,
                    errors=[f"blocks references skill not in this project: '{blocked}' (warning)"],
                ))

    # Cycle detection via topological sort (Kahn's algorithm)
    in_degree: dict = {sid: 0 for sid in declared_ids}
    for sid, deps in adjacency.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[dep] += 1

    queue = [sid for sid, deg in in_degree.items() if deg == 0]
    visited = 0
    while queue:
        node = queue.pop(0)
        visited += 1
        for dep in adjacency.get(node, []):
            if dep in in_degree:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

    if visited < len(declared_ids):
        cycle_members = [sid for sid, deg in in_degree.items() if deg > 0]
        results.append(ValidationResult(
            file_path=agent_dir / "agent.yaml",
            schema_type="skill",
            valid=False,
            errors=[
                f"Circular dependency detected among skills: {', '.join(sorted(cycle_members))}"
            ],
        ))

    return results


def _validate_skill_quality(
    agent_dir: Path,
    manifest: dict,
) -> List[ValidationResult]:
    """Quality checks for skills (warnings only, valid=True).

    These catch common issues: bad descriptions, oversized runbooks,
    empty tags, and excessive skill counts.
    """
    results: List[ValidationResult] = []

    skills = manifest.get("skills", [])
    skill_count = len(skills)
    if skill_count > 50:
        results.append(ValidationResult(
            file_path=agent_dir / "agent.yaml",
            schema_type="skill",
            valid=True,
            errors=[
                f"Project has {skill_count} skills; recommended maximum is 50 (warning)"
            ],
        ))

    for skill_ref in skills:
        manifest_rel = skill_ref.get("manifest")
        if not manifest_rel:
            continue
        skill_path = agent_dir / manifest_rel
        if not skill_path.exists():
            continue

        try:
            skill_data = load_yaml(skill_path)
        except Exception:
            continue

        skill_id = skill_data.get("id", skill_ref.get("id", "unknown"))
        desc = skill_data.get("description", "")

        # Description contains TODO
        if "TODO" in desc:
            results.append(ValidationResult(
                file_path=skill_path,
                schema_type="skill",
                valid=True,
                errors=[
                    f"Skill '{skill_id}' description contains TODO (warning)"
                ],
            ))
        elif len(desc) < 20:
            results.append(ValidationResult(
                file_path=skill_path,
                schema_type="skill",
                valid=True,
                errors=[
                    f"Skill '{skill_id}' description is only {len(desc)} chars; "
                    f"aim for 20+ chars (warning)"
                ],
            ))

        if len(desc) > 1024:
            results.append(ValidationResult(
                file_path=skill_path,
                schema_type="skill",
                valid=True,
                errors=[
                    f"Skill '{skill_id}' description is {len(desc)} chars; "
                    f"maximum recommended is 1024 (warning)"
                ],
            ))

        # Empty tags check
        tags = skill_data.get("tags", [])
        if isinstance(tags, list) and any(
            isinstance(t, str) and not t.strip() for t in tags
        ):
            results.append(ValidationResult(
                file_path=skill_path,
                schema_type="skill",
                valid=True,
                errors=[
                    f"Skill '{skill_id}' has empty tag values (warning)"
                ],
            ))

        # Runbook size check
        runbook_rel = skill_ref.get("runbook")
        if runbook_rel:
            runbook_path = agent_dir / runbook_rel
            if runbook_path.exists():
                runbook_text = runbook_path.read_text()
                word_count = len(runbook_text.split())
                if word_count > 5000:
                    results.append(ValidationResult(
                        file_path=runbook_path,
                        schema_type="skill",
                        valid=True,
                        errors=[
                            f"Skill '{skill_id}' runbook is {word_count} words; "
                            f"recommended maximum is 5000 (warning)"
                        ],
                    ))

    return results
