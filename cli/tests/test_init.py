"""Tests for aes init command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from aes.__main__ import cli
from aes.validator import validate_agent_dir


# Shorthand for common init invocations
def _init(tmp_path, **overrides):
    """Run ``aes init`` with explicit flags.  Returns the CliRunner result."""
    args = {
        "name": "test-project",
        "domain": "ml",
        "language": "python",
        "path": str(tmp_path),
    }
    args.update(overrides)
    cmd = ["init"]
    for key, val in args.items():
        if val is True:
            cmd.append(f"--{key}")
        elif val is False:
            cmd.append(f"--no-{key}")
        elif val is not None:
            cmd.extend([f"--{key}", str(val)])
    runner = CliRunner()
    return runner.invoke(cli, cmd)


class TestInit:
    def test_init_creates_agent_dir(self, tmp_path):
        result = _init(tmp_path)
        assert result.exit_code == 0
        assert (tmp_path / ".agent").exists()
        assert (tmp_path / ".agent" / "agent.yaml").exists()
        assert (tmp_path / ".agent" / "instructions.md").exists()
        assert (tmp_path / ".agent" / "permissions.yaml").exists()
        assert (tmp_path / ".agentignore").exists()

    def test_init_creates_skills_dir(self, tmp_path):
        result = _init(tmp_path)
        assert result.exit_code == 0
        assert (tmp_path / ".agent" / "skills").exists()
        assert (tmp_path / ".agent" / "skills" / "ORCHESTRATOR.md").exists()

    def test_init_creates_memory_dir(self, tmp_path):
        result = _init(tmp_path)
        assert result.exit_code == 0
        assert (tmp_path / ".agent" / "memory").exists()
        assert (tmp_path / ".agent" / "memory" / "project.md").exists()

    def test_init_agent_yaml_is_valid(self, tmp_path):
        _init(tmp_path)
        agent_yaml = tmp_path / ".agent" / "agent.yaml"
        with open(agent_yaml) as f:
            data = yaml.safe_load(f)
        assert data["aes"] == "1.0"
        assert data["name"] == "test-project"
        assert data["domain"] == "ml"

    def test_init_no_skills(self, tmp_path):
        result = _init(tmp_path, skills=False)
        assert result.exit_code == 0
        assert not (tmp_path / ".agent" / "skills").exists()

    def test_init_with_registry(self, tmp_path):
        result = _init(tmp_path, registry=True)
        assert result.exit_code == 0
        assert (tmp_path / ".agent" / "registry").exists()

    def test_init_typescript_permissions(self, tmp_path):
        _init(tmp_path, domain="web", language="typescript")
        perms = tmp_path / ".agent" / "permissions.yaml"
        with open(perms) as f:
            data = yaml.safe_load(f)
        execute = data["allow"]["shell"]["execute"]
        assert any("npm" in cmd for cmd in execute)

    def test_init_python_agentignore(self, tmp_path):
        _init(tmp_path)
        content = (tmp_path / ".agentignore").read_text()
        assert "__pycache__" in content
        assert ".venv" in content

    def test_init_creates_local_files(self, tmp_path):
        result = _init(tmp_path)
        assert result.exit_code == 0
        assert (tmp_path / ".agent" / "local.yaml").exists()
        assert (tmp_path / ".agent" / "local.example.yaml").exists()

    def test_init_agentignore_includes_local(self, tmp_path):
        _init(tmp_path)
        content = (tmp_path / ".agentignore").read_text()
        assert ".agent/local.yaml" in content


class TestDomainAwareInitML:
    """Test ML domain generates real content instead of TODOs."""

    def test_ml_instructions_have_real_content(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "resource limits" in content.lower() or "Resource limits" in content
        assert "HPO" in content or "Optuna" in content
        assert "TODO" not in content

    def test_ml_generates_skill_files(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        skills_dir = tmp_path / ".agent" / "skills"
        assert (skills_dir / "discover.skill.yaml").exists()
        assert (skills_dir / "discover.md").exists()
        assert (skills_dir / "examine.skill.yaml").exists()
        assert (skills_dir / "examine.md").exists()
        assert (skills_dir / "classify.skill.yaml").exists()
        assert (skills_dir / "classify.md").exists()
        assert (skills_dir / "train.skill.yaml").exists()
        assert (skills_dir / "train.md").exists()
        assert (skills_dir / "evaluate.skill.yaml").exists()
        assert (skills_dir / "evaluate.md").exists()
        assert (skills_dir / "package.skill.yaml").exists()
        assert (skills_dir / "package.md").exists()
        assert (skills_dir / "publish.skill.yaml").exists()
        assert (skills_dir / "publish.md").exists()

    def test_ml_skill_manifests_have_content(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        with open(tmp_path / ".agent" / "skills" / "train.skill.yaml") as f:
            data = yaml.safe_load(f)
        assert data["id"] == "train"
        assert data["name"] == "Train Models"
        assert len(data["inputs"]["required"]) > 0
        assert "TODO" not in data["description"]

    def test_ml_generates_workflow(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        wf_path = tmp_path / ".agent" / "workflows" / "dataset-pipeline.yaml"
        assert wf_path.exists()
        with open(wf_path) as f:
            data = yaml.safe_load(f)
        assert data["id"] == "dataset-pipeline"
        assert len(data["states"]) >= 7
        assert len(data["transitions"]) >= 6

    def test_ml_orchestrator_has_real_content(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        content = (tmp_path / ".agent" / "skills" / "ORCHESTRATOR.md").read_text()
        assert "discover" in content
        assert "TODO" not in content

    def test_ml_agent_yaml_references_skills(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        with open(tmp_path / ".agent" / "agent.yaml") as f:
            data = yaml.safe_load(f)
        skill_ids = [s["id"] for s in data.get("skills", [])]
        assert "discover" in skill_ids
        assert "examine" in skill_ids
        assert "classify" in skill_ids
        assert "train" in skill_ids
        assert "evaluate" in skill_ids
        assert "package" in skill_ids
        assert "publish" in skill_ids

    def test_ml_permissions_have_domain_content(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        with open(tmp_path / ".agent" / "permissions.yaml") as f:
            data = yaml.safe_load(f)
        execute = data["allow"]["shell"]["execute"]
        assert any("pytest" in cmd for cmd in execute)
        assert "resource_limits" in data

    def test_ml_local_example_has_env_vars(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        content = (tmp_path / ".agent" / "local.example.yaml").read_text()
        assert "OPENML_APIKEY" in content
        assert "HF_TOKEN" in content


class TestDomainAwareInitWeb:
    """Test web domain generates real content."""

    def test_web_instructions_have_real_content(self, tmp_path):
        _init(tmp_path, name="test-web", domain="web", language="typescript")
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TypeScript strict" in content or "typescript" in content.lower()
        assert "TODO" not in content

    def test_web_generates_skill_files(self, tmp_path):
        _init(tmp_path, name="test-web", domain="web", language="typescript")
        skills_dir = tmp_path / ".agent" / "skills"
        assert (skills_dir / "scaffold.skill.yaml").exists()
        assert (skills_dir / "scaffold.md").exists()
        assert (skills_dir / "implement.skill.yaml").exists()
        assert (skills_dir / "implement.md").exists()
        assert (skills_dir / "test.skill.yaml").exists()
        assert (skills_dir / "test.md").exists()
        assert (skills_dir / "review.skill.yaml").exists()
        assert (skills_dir / "review.md").exists()
        assert (skills_dir / "deploy.skill.yaml").exists()
        assert (skills_dir / "deploy.md").exists()

    def test_web_generates_workflow(self, tmp_path):
        _init(tmp_path, name="test-web", domain="web", language="typescript")
        wf_path = tmp_path / ".agent" / "workflows" / "feature-lifecycle.yaml"
        assert wf_path.exists()
        with open(wf_path) as f:
            data = yaml.safe_load(f)
        assert data["id"] == "feature-lifecycle"
        state_ids = list(data["states"].keys())
        assert "planned" in state_ids
        assert "deployed" in state_ids


class TestDomainAwareInitDevOps:
    """Test devops domain generates real content."""

    def test_devops_instructions_have_real_content(self, tmp_path):
        _init(tmp_path, name="test-devops", domain="devops")
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "Terraform" in content or "terraform" in content
        assert "TODO" not in content

    def test_devops_generates_skill_files(self, tmp_path):
        _init(tmp_path, name="test-devops", domain="devops")
        skills_dir = tmp_path / ".agent" / "skills"
        assert (skills_dir / "provision.skill.yaml").exists()
        assert (skills_dir / "provision.md").exists()
        assert (skills_dir / "configure.skill.yaml").exists()
        assert (skills_dir / "configure.md").exists()
        assert (skills_dir / "deploy.skill.yaml").exists()
        assert (skills_dir / "deploy.md").exists()
        assert (skills_dir / "rollback.skill.yaml").exists()
        assert (skills_dir / "rollback.md").exists()
        assert (skills_dir / "monitor.skill.yaml").exists()
        assert (skills_dir / "monitor.md").exists()

    def test_devops_generates_workflow(self, tmp_path):
        _init(tmp_path, name="test-devops", domain="devops")
        wf_path = tmp_path / ".agent" / "workflows" / "service-lifecycle.yaml"
        assert wf_path.exists()
        with open(wf_path) as f:
            data = yaml.safe_load(f)
        assert data["id"] == "service-lifecycle"
        assert len(data["states"]) >= 7


class TestDomainAwareInitResearch:
    """Test research domain generates real content."""

    def test_research_instructions_have_real_content(self, tmp_path):
        _init(tmp_path, name="test-research", domain="research")
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "content processing" in content.lower() or "ingests" in content.lower()
        assert "TODO" not in content

    def test_research_generates_skill_files(self, tmp_path):
        _init(tmp_path, name="test-research", domain="research")
        skills_dir = tmp_path / ".agent" / "skills"
        assert (skills_dir / "ingest.skill.yaml").exists()
        assert (skills_dir / "ingest.md").exists()
        assert (skills_dir / "parse.skill.yaml").exists()
        assert (skills_dir / "parse.md").exists()
        assert (skills_dir / "analyze.skill.yaml").exists()
        assert (skills_dir / "analyze.md").exists()
        assert (skills_dir / "organize.skill.yaml").exists()
        assert (skills_dir / "organize.md").exists()
        assert (skills_dir / "display.skill.yaml").exists()
        assert (skills_dir / "display.md").exists()

    def test_research_generates_workflow(self, tmp_path):
        _init(tmp_path, name="test-research", domain="research")
        wf_path = tmp_path / ".agent" / "workflows" / "content-pipeline.yaml"
        assert wf_path.exists()
        with open(wf_path) as f:
            data = yaml.safe_load(f)
        assert data["id"] == "content-pipeline"
        assert len(data["states"]) >= 5

    def test_research_agent_yaml_references_skills(self, tmp_path):
        _init(tmp_path, name="test-research", domain="research")
        with open(tmp_path / ".agent" / "agent.yaml") as f:
            data = yaml.safe_load(f)
        skill_ids = [s["id"] for s in data.get("skills", [])]
        assert "ingest" in skill_ids
        assert "parse" in skill_ids
        assert "analyze" in skill_ids
        assert "organize" in skill_ids
        assert "display" in skill_ids


class TestWorkflowCommands:
    """Test workflow command scaffolding for all domains."""

    def test_ml_train_command(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        cmd_path = tmp_path / ".agent" / "commands" / "train.md"
        assert cmd_path.exists()
        content = cmd_path.read_text()
        assert "/train" in content
        assert "Worker Identity" in content
        assert "operations.md" in content

    def test_ml_build_command(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        cmd_path = tmp_path / ".agent" / "commands" / "build.md"
        assert cmd_path.exists()
        content = cmd_path.read_text()
        assert "/build" in content
        assert "Project Structure" in content
        assert "Model Registry" in content

    def test_ml_build_is_first_command(self, tmp_path):
        """ML /build should be the first workflow command (shown in post-init hint)."""
        _init(tmp_path, name="test-ml", domain="ml")
        with open(tmp_path / ".agent" / "agent.yaml") as f:
            data = yaml.safe_load(f)
        commands = data.get("commands", [])
        # Filter to workflow commands (exclude setup)
        wf_cmds = [c for c in commands if c.get("id") != "setup"]
        assert len(wf_cmds) >= 2
        assert wf_cmds[0]["id"] == "build"
        assert wf_cmds[0]["trigger"] == "/build"

    def test_web_build_command(self, tmp_path):
        _init(tmp_path, name="test-web", domain="web", language="typescript")
        cmd_path = tmp_path / ".agent" / "commands" / "build.md"
        assert cmd_path.exists()
        content = cmd_path.read_text()
        assert "/build" in content

    def test_devops_provision_command(self, tmp_path):
        _init(tmp_path, name="test-devops", domain="devops")
        cmd_path = tmp_path / ".agent" / "commands" / "provision.md"
        assert cmd_path.exists()
        content = cmd_path.read_text()
        assert "/provision" in content

    def test_research_process_command(self, tmp_path):
        _init(tmp_path, name="test-research", domain="research")
        cmd_path = tmp_path / ".agent" / "commands" / "process.md"
        assert cmd_path.exists()
        content = cmd_path.read_text()
        assert "/process" in content

    def test_research_build_command(self, tmp_path):
        _init(tmp_path, name="test-research", domain="research")
        cmd_path = tmp_path / ".agent" / "commands" / "build.md"
        assert cmd_path.exists()
        content = cmd_path.read_text()
        assert "/build" in content
        assert "Source Adapters" in content
        assert "Topic Taxonomy" in content

    def test_research_build_is_first_command(self, tmp_path):
        """Research /build should be the first workflow command."""
        _init(tmp_path, name="test-research", domain="research")
        with open(tmp_path / ".agent" / "agent.yaml") as f:
            data = yaml.safe_load(f)
        commands = data.get("commands", [])
        wf_cmds = [c for c in commands if c.get("id") != "setup"]
        assert len(wf_cmds) >= 2
        assert wf_cmds[0]["id"] == "build"
        assert wf_cmds[0]["trigger"] == "/build"

    def test_workflow_command_registered_in_agent_yaml(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        with open(tmp_path / ".agent" / "agent.yaml") as f:
            data = yaml.safe_load(f)
        commands = data.get("commands", [])
        train_cmds = [c for c in commands if c.get("id") == "train"]
        assert len(train_cmds) == 1
        assert train_cmds[0]["trigger"] == "/train"

    def test_other_domain_gets_build_command(self, tmp_path):
        _init(tmp_path, name="test-other", domain="other")
        commands_dir = tmp_path / ".agent" / "commands"
        # Should get setup.md + build.md from DEV_ASSIST_BASE_CONFIG
        cmd_files = sorted(f.name for f in commands_dir.glob("*.md"))
        assert cmd_files == ["build.md", "setup.md"]

    def test_explicit_domain_other_gets_build(self, tmp_path):
        """--domain other (explicit CLI, non-interactive) gets /build."""
        _init(tmp_path, name="test-explicit", domain="other")
        build_path = tmp_path / ".agent" / "commands" / "build.md"
        assert build_path.exists()
        content = build_path.read_text()
        assert "build" in content.lower()


class TestOperationsMemory:
    """Test operations memory file generation with unified chronological log."""

    def test_ml_has_operations_md(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        ops_path = tmp_path / ".agent" / "memory" / "operations.md"
        assert ops_path.exists()
        content = ops_path.read_text()
        assert "Operations Memory" in content
        assert "Activity Log" in content

    def test_ml_operations_has_workers_table(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        content = (tmp_path / ".agent" / "memory" / "operations.md").read_text()
        assert "| /build |" in content
        assert "| /train |" in content
        assert "Read Cursor" in content

    def test_ml_operations_has_worker_specialty(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        content = (tmp_path / ".agent" / "memory" / "operations.md").read_text()
        assert "Constructing ML pipeline" in content
        assert "Executing ML training" in content

    def test_ml_operations_has_issues_section(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        content = (tmp_path / ".agent" / "memory" / "operations.md").read_text()
        assert "Issues & Decisions" in content

    def test_research_has_operations_md(self, tmp_path):
        _init(tmp_path, name="test-research", domain="research")
        ops_path = tmp_path / ".agent" / "memory" / "operations.md"
        assert ops_path.exists()
        content = ops_path.read_text()
        assert "| /build |" in content
        assert "| /process |" in content

    def test_other_domain_has_operations_md(self, tmp_path):
        """Other domain now gets operations.md since it has /build command."""
        _init(tmp_path, name="test-other", domain="other")
        ops_path = tmp_path / ".agent" / "memory" / "operations.md"
        assert ops_path.exists()
        content = ops_path.read_text()
        assert "| /build |" in content

    def test_orchestrator_references_operations(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        content = (tmp_path / ".agent" / "skills" / "ORCHESTRATOR.md").read_text()
        assert "operations.md" in content


class TestFallbackDomains:
    """Domains without domain config fall back to TODO templates."""

    def test_other_domain_has_todos(self, tmp_path):
        _init(tmp_path, name="test-other", domain="other")
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" in content

    def test_data_pipeline_domain_has_todos(self, tmp_path):
        _init(tmp_path, name="test-dp", domain="data-pipeline")
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" in content

    def test_other_domain_no_skill_files(self, tmp_path):
        _init(tmp_path, name="test-other", domain="other")
        skills_dir = tmp_path / ".agent" / "skills"
        assert (skills_dir / "ORCHESTRATOR.md").exists()
        skill_files = list(skills_dir.glob("*.skill.yaml"))
        assert len(skill_files) == 0

    def test_other_domain_no_workflow_files(self, tmp_path):
        _init(tmp_path, name="test-other", domain="other")
        wf_dir = tmp_path / ".agent" / "workflows"
        wf_files = list(wf_dir.glob("*.yaml"))
        assert len(wf_files) == 0

    def test_other_domain_has_smart_todos(self, tmp_path):
        _init(tmp_path, name="test-other", domain="other")
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "<!-- AGENT:" in content
        assert "If code exists:" in content
        assert "If greenfield:" in content


class TestSetupCommand:
    """Tests for /setup command generation and auto-sync."""

    def test_setup_md_generated_for_other_domain(self, tmp_path):
        result = _init(tmp_path, name="test-other", domain="other")
        assert result.exit_code == 0
        setup_path = tmp_path / ".agent" / "commands" / "setup.md"
        assert setup_path.exists()
        content = setup_path.read_text()
        assert "Phase 0: Detect Context" in content
        assert "Phase 1: Understand the Project" in content
        # With DEV_ASSIST_BASE_CONFIG, "other" now gets domain-style setup
        assert "Review and customize" in content or "Refine Instructions" in content

    def test_setup_md_generated_for_ml_domain(self, tmp_path):
        result = _init(tmp_path, name="test-ml", domain="ml")
        assert result.exit_code == 0
        setup_path = tmp_path / ".agent" / "commands" / "setup.md"
        assert setup_path.exists()
        content = setup_path.read_text()
        assert "Review and customize" in content or "Refine Instructions" in content

    def test_setup_registered_in_agent_yaml_other(self, tmp_path):
        _init(tmp_path, name="test-other", domain="other")
        with open(tmp_path / ".agent" / "agent.yaml") as f:
            data = yaml.safe_load(f)
        commands = data.get("commands", [])
        setup_cmds = [c for c in commands if c.get("id") == "setup"]
        assert len(setup_cmds) == 1
        assert setup_cmds[0]["trigger"] == "/setup"
        assert setup_cmds[0]["path"] == "commands/setup.md"

    def test_setup_registered_in_agent_yaml_ml(self, tmp_path):
        _init(tmp_path, name="test-ml", domain="ml")
        with open(tmp_path / ".agent" / "agent.yaml") as f:
            data = yaml.safe_load(f)
        commands = data.get("commands", [])
        setup_cmds = [c for c in commands if c.get("id") == "setup"]
        assert len(setup_cmds) == 1
        assert setup_cmds[0]["trigger"] == "/setup"

    def test_commands_dir_created(self, tmp_path):
        _init(tmp_path, name="test-other", domain="other")
        assert (tmp_path / ".agent" / "commands").is_dir()

    def test_auto_sync_creates_claude_md(self, tmp_path):
        result = _init(tmp_path, name="test-other", domain="other")
        assert result.exit_code == 0
        assert (tmp_path / "CLAUDE.md").exists()
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "test-other" in content

    def test_auto_sync_creates_cursorrules(self, tmp_path):
        result = _init(tmp_path, name="test-other", domain="other")
        assert result.exit_code == 0
        assert (tmp_path / ".cursorrules").exists()

    def test_auto_sync_creates_copilot_instructions(self, tmp_path):
        result = _init(tmp_path, name="test-other", domain="other")
        assert result.exit_code == 0
        assert (tmp_path / ".github" / "copilot-instructions.md").exists()

    def test_auto_sync_creates_windsurfrules(self, tmp_path):
        result = _init(tmp_path, name="test-other", domain="other")
        assert result.exit_code == 0
        assert (tmp_path / ".windsurfrules").exists()

    def test_auto_sync_ml_domain_has_real_content_in_claude_md(self, tmp_path):
        result = _init(tmp_path, name="test-ml", domain="ml")
        assert result.exit_code == 0
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "test-ml" in content
        setup_cmd = tmp_path / ".claude" / "commands" / "setup.md"
        assert setup_cmd.exists()
        assert "/setup" in setup_cmd.read_text()

    def test_auto_sync_manifest_created(self, tmp_path):
        _init(tmp_path, name="test-other", domain="other")
        assert (tmp_path / ".aes-sync.json").exists()

    def test_setup_md_other_domain_has_review_language(self, tmp_path):
        """With DEV_ASSIST_BASE_CONFIG fallback, 'other' gets domain-style setup."""
        _init(tmp_path, name="test-other", domain="other")
        content = (tmp_path / ".agent" / "commands" / "setup.md").read_text()
        assert "Review and customize" in content

    def test_init_output_mentions_setup(self, tmp_path):
        result = _init(tmp_path, name="test-other", domain="other")
        assert "/setup" in result.output

    def test_init_creates_mcp_json(self, tmp_path):
        import json
        result = _init(tmp_path, name="test-mcp", domain="other")
        assert result.exit_code == 0
        mcp_path = tmp_path / ".mcp.json"
        assert mcp_path.exists()
        data = json.loads(mcp_path.read_text())
        assert "mcpServers" in data
        assert "aes-registry" in data["mcpServers"]
        assert data["mcpServers"]["aes-registry"]["command"] == "aes-mcp"

    def test_init_does_not_overwrite_existing_mcp_json(self, tmp_path):
        # Pre-existing .mcp.json should not be overwritten
        mcp_path = tmp_path / ".mcp.json"
        mcp_path.write_text('{"existing": true}\n')
        result = _init(tmp_path, name="test-mcp", domain="other")
        assert result.exit_code == 0
        assert mcp_path.read_text() == '{"existing": true}\n'


class TestSmartDetection:
    """Test framework-aware auto-detection when no --domain is given."""

    def test_fastapi_project_detected(self, tmp_path):
        """FastAPI project gets framework-specific skills."""
        (tmp_path / "requirements.txt").write_text("fastapi>=0.100\nuvicorn\nsqlalchemy\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        result = _init(tmp_path, name="test-api", domain=None, language=None)
        assert result.exit_code == 0
        # Should have generated skill files (not TODO scaffolding)
        skills_dir = tmp_path / ".agent" / "skills"
        assert (skills_dir / "test-runner.skill.yaml").exists()
        assert (skills_dir / "test-runner.md").exists()
        # Instructions should have real content
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" not in content

    def test_nextjs_project_detected(self, tmp_path):
        """Next.js project gets fullstack config."""
        import json
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": {"next": "14.0.0", "react": "18.0.0"},
        }))
        (tmp_path / "tsconfig.json").write_text("{}\n")
        result = _init(tmp_path, name="test-next", domain=None, language=None)
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" not in content

    def test_empty_project_falls_back(self, tmp_path):
        """Empty project still works with TODO scaffolding."""
        result = _init(tmp_path, name="test-empty", domain=None, language=None)
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" in content

    def test_explicit_domain_overrides_detection(self, tmp_path):
        """--domain ml overrides auto-detection even in a FastAPI project."""
        (tmp_path / "requirements.txt").write_text("fastapi>=0.100\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        result = _init(tmp_path, name="test-override", domain="ml", language="python")
        assert result.exit_code == 0
        # Should use ML domain, not API detection
        skills_dir = tmp_path / ".agent" / "skills"
        assert (skills_dir / "discover.skill.yaml").exists()


class TestAutoDetect:
    """Test zero-arg init with auto-detection."""

    def test_init_zero_args(self, tmp_path):
        """aes init with only --path works."""
        result = _init(tmp_path, name=None, domain="other", language=None)
        assert result.exit_code == 0
        assert (tmp_path / ".agent" / "agent.yaml").exists()

    def test_init_auto_detect_name(self, tmp_path):
        """Name derived from directory name."""
        project = tmp_path / "My Cool App"
        project.mkdir()
        result = _init(project, name=None, domain="other", language=None)
        assert result.exit_code == 0
        with open(project / ".agent" / "agent.yaml") as f:
            data = yaml.safe_load(f)
        assert data["name"] == "my-cool-app"

    def test_init_auto_detect_language_python(self, tmp_path):
        """Finds pyproject.toml -> python."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        result = _init(tmp_path, name=None, domain="other", language=None)
        assert result.exit_code == 0
        with open(tmp_path / ".agent" / "agent.yaml") as f:
            data = yaml.safe_load(f)
        assert data["runtime"]["language"] == "python"

    def test_init_auto_detect_language_typescript(self, tmp_path):
        """Finds tsconfig.json -> typescript."""
        (tmp_path / "tsconfig.json").write_text("{}\n")
        result = _init(tmp_path, name=None, domain="other", language=None)
        assert result.exit_code == 0
        with open(tmp_path / ".agent" / "agent.yaml") as f:
            data = yaml.safe_load(f)
        assert data["runtime"]["language"] == "typescript"

    def test_init_auto_detect_language_fallback(self, tmp_path):
        """Empty dir -> other."""
        result = _init(tmp_path, name=None, domain="other", language=None)
        assert result.exit_code == 0
        with open(tmp_path / ".agent" / "agent.yaml") as f:
            data = yaml.safe_load(f)
        assert data["runtime"]["language"] == "other"

    def test_init_domain_defaults_to_other(self, tmp_path):
        """No --domain -> generic scaffold with TODOs."""
        result = _init(tmp_path, name="test-default", domain="other", language="python")
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" in content

    def test_init_domain_ml_still_works(self, tmp_path):
        """--domain ml -> pre-filled content."""
        result = _init(tmp_path, name="test-ml", domain="ml", language="python")
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" not in content
        assert "HPO" in content or "Optuna" in content


class TestInteractivePicker:
    """Test the interactive picker shown when nothing is detected."""

    def _run_interactive(self, tmp_path, input_text):
        """Run aes init interactively with simulated input.

        Patches sys.stdin.isatty to return True so the interactive code
        path is triggered (CliRunner's stdin is not a real TTY).
        """
        runner = CliRunner(mix_stderr=False)

        def _fake_isatty():
            return True

        with patch("aes.commands.init.sys") as mock_sys:
            mock_sys.stdin.isatty = _fake_isatty
            mock_sys.argv = ["aes", "init", "--path", str(tmp_path)]
            return runner.invoke(
                cli,
                ["init", "--path", str(tmp_path)],
                input=input_text,
            )

    def test_picker_api_python_fastapi(self, tmp_path):
        """Pick Dev-Assist -> API service -> Python -> FastAPI produces real config."""
        # 1=Dev-Assist, 1=API, 1=Python, 1=FastAPI
        result = self._run_interactive(tmp_path, "1\n1\n1\n1\n")
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" not in content
        skills_dir = tmp_path / ".agent" / "skills"
        assert (skills_dir / "test-runner.skill.yaml").exists()

    def test_picker_api_python_no_framework(self, tmp_path):
        """Pick Dev-Assist -> API service -> Python -> None still produces real config."""
        # 1=Dev-Assist, 1=API, 1=Python, 4=None (3 frameworks + None)
        result = self._run_interactive(tmp_path, "1\n1\n1\n4\n")
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" not in content

    def test_picker_cli_tool_go(self, tmp_path):
        """Pick Dev-Assist -> CLI tool -> Go produces cli-tool config."""
        # 1=Dev-Assist, 3=CLI tool, 4=Go, no framework picker for Go CLI
        result = self._run_interactive(tmp_path, "1\n3\n4\n")
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" not in content

    def test_picker_library_rust(self, tmp_path):
        """Pick Dev-Assist -> Library -> Rust produces library config."""
        # 1=Dev-Assist, 4=Library, 5=Rust, no framework picker
        result = self._run_interactive(tmp_path, "1\n4\n5\n")
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" not in content

    def test_picker_ml_pipeline(self, tmp_path):
        """Pick Agent-Integrated -> ML pipeline uses DOMAIN_CONFIGS['ml']."""
        # 2=Agent-Integrated, 1=ML pipeline
        result = self._run_interactive(tmp_path, "2\n1\n")
        assert result.exit_code == 0
        skills_dir = tmp_path / ".agent" / "skills"
        assert (skills_dir / "discover.skill.yaml").exists()
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" not in content

    def test_picker_devops(self, tmp_path):
        """Pick Dev-Assist -> DevOps uses DOMAIN_CONFIGS['devops']."""
        # 1=Dev-Assist, 5=DevOps
        result = self._run_interactive(tmp_path, "1\n5\n")
        assert result.exit_code == 0
        skills_dir = tmp_path / ".agent" / "skills"
        assert (skills_dir / "provision.skill.yaml").exists()

    def test_picker_skip(self, tmp_path):
        """Pick Dev-Assist -> Skip produces TODO scaffolding."""
        # 1=Dev-Assist, 6=Skip
        result = self._run_interactive(tmp_path, "1\n6\n")
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" in content

    def test_picker_web_app_typescript_nextjs(self, tmp_path):
        """Pick Dev-Assist -> Web app -> TypeScript -> Next.js."""
        # 1=Dev-Assist, 2=Web app, 2=TypeScript, 1=Nextjs
        result = self._run_interactive(tmp_path, "1\n2\n2\n1\n")
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" not in content

    def test_picker_research(self, tmp_path):
        """Pick Agent-Integrated -> Research uses DOMAIN_CONFIGS['research']."""
        # 2=Agent-Integrated, 2=Research
        result = self._run_interactive(tmp_path, "2\n2\n")
        assert result.exit_code == 0
        skills_dir = tmp_path / ".agent" / "skills"
        assert (skills_dir / "ingest.skill.yaml").exists()
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" not in content

    def test_picker_agent_integrated_custom(self, tmp_path):
        """Pick Agent-Integrated -> Custom produces TODO scaffolding with /build + /run."""
        # 2=Agent-Integrated, 3=Custom
        result = self._run_interactive(tmp_path, "2\n3\n")
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" in content
        # Should have /build and /run commands despite TODO instructions
        build_path = tmp_path / ".agent" / "commands" / "build.md"
        assert build_path.exists()
        assert "/build" in build_path.read_text()
        run_path = tmp_path / ".agent" / "commands" / "run.md"
        assert run_path.exists()
        assert "/run" in run_path.read_text()

    def test_picker_dev_assist_skip_gets_build_only(self, tmp_path):
        """Pick Dev-Assist -> Skip produces /build but not /run."""
        # 1=Dev-Assist, 6=Skip
        result = self._run_interactive(tmp_path, "1\n6\n")
        assert result.exit_code == 0
        commands_dir = tmp_path / ".agent" / "commands"
        assert (commands_dir / "build.md").exists()
        assert "/build" in (commands_dir / "build.md").read_text()
        # No /run for dev-assist
        assert not (commands_dir / "run.md").exists()

    def test_picker_mode_prompt_shown(self, tmp_path):
        """Mode selection prompt is displayed."""
        # 1=Dev-Assist, 6=Skip
        result = self._run_interactive(tmp_path, "1\n6\n")
        assert "How will the agent work" in result.output

    def test_picker_not_shown_when_detected(self, tmp_path):
        """When project files exist, picker is NOT shown — detection works."""
        (tmp_path / "requirements.txt").write_text("fastapi>=0.100\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        # Provide 'y' to confirm detected project
        result = self._run_interactive(tmp_path, "y\n")
        assert result.exit_code == 0
        # Should have used detection, not picker
        assert "No project files detected" not in result.output

    def test_picker_not_shown_with_explicit_domain(self, tmp_path):
        """--domain flag skips picker entirely."""
        result = _init(tmp_path, name="test-explicit", domain="ml", language="python")
        assert result.exit_code == 0
        assert "No project files detected" not in result.output

    def test_non_interactive_falls_through(self, tmp_path):
        """Non-interactive (--name flag) skips picker, falls to TODO."""
        result = _init(tmp_path, name="test-ci", domain=None, language=None)
        assert result.exit_code == 0
        content = (tmp_path / ".agent" / "instructions.md").read_text()
        assert "TODO" in content
