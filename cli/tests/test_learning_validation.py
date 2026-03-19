"""Tests for learning config and instinct schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aes.validator import validate_file, validate_agent_dir


@pytest.fixture
def tmp_yaml(tmp_path):
    """Write arbitrary YAML data to a temp file."""
    def _write(name, data):
        p = tmp_path / name
        p.write_text(yaml.dump(data, default_flow_style=False))
        return p
    return _write


class TestInstinctSchema:
    def test_valid_instinct(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("test.instinct.yaml", {
                "apiVersion": "aes/v1",
                "kind": "Instinct",
                "metadata": {
                    "id": "api-error-handling",
                    "created_at": "2026-03-15T10:30:00Z",
                    "last_validated": "2026-03-19T14:00:00Z",
                    "source_session": "session-abc123",
                    "tags": ["error-handling", "api"],
                },
                "pattern": {
                    "description": "Always implement retry with exponential backoff for API calls",
                    "trigger": "Agent is making external HTTP calls",
                    "action": "1. Wrap in try/catch\n2. Implement 3-retry backoff\n3. Add circuit breaker",
                    "evidence": [
                        {"session": "session-abc", "outcome": "Reduced errors by 90%"},
                    ],
                    "examples": [
                        {"context": "Payment gateway", "application": "Added retry + circuit breaker"},
                    ],
                },
                "confidence": {
                    "score": 0.85,
                    "validations": 4,
                    "contradictions": 0,
                    "decay_rate": 0.01,
                    "min_score": 0.3,
                    "status": "active",
                },
            }),
            "instinct",
        )
        assert result.valid, result.errors

    def test_minimal_instinct(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("min.instinct.yaml", {
                "apiVersion": "aes/v1",
                "kind": "Instinct",
                "metadata": {
                    "id": "test-pattern",
                    "created_at": "2026-03-15T10:30:00Z",
                    "last_validated": "2026-03-15T10:30:00Z",
                    "source_session": "session-001",
                },
                "pattern": {
                    "description": "A learned pattern",
                    "trigger": "Some context",
                    "action": "Do something",
                },
                "confidence": {
                    "score": 0.5,
                    "validations": 1,
                    "contradictions": 0,
                    "status": "candidate",
                },
            }),
            "instinct",
        )
        assert result.valid, result.errors

    def test_score_out_of_range(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("bad.instinct.yaml", {
                "apiVersion": "aes/v1",
                "kind": "Instinct",
                "metadata": {
                    "id": "bad",
                    "created_at": "2026-03-15T10:30:00Z",
                    "last_validated": "2026-03-15T10:30:00Z",
                    "source_session": "s1",
                },
                "pattern": {
                    "description": "x",
                    "trigger": "y",
                    "action": "z",
                },
                "confidence": {
                    "score": 1.5,
                    "validations": 0,
                    "contradictions": 0,
                    "status": "active",
                },
            }),
            "instinct",
        )
        assert not result.valid

    def test_invalid_status(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("bad-status.instinct.yaml", {
                "apiVersion": "aes/v1",
                "kind": "Instinct",
                "metadata": {
                    "id": "bad",
                    "created_at": "2026-03-15T10:30:00Z",
                    "last_validated": "2026-03-15T10:30:00Z",
                    "source_session": "s1",
                },
                "pattern": {
                    "description": "x",
                    "trigger": "y",
                    "action": "z",
                },
                "confidence": {
                    "score": 0.5,
                    "validations": 0,
                    "contradictions": 0,
                    "status": "deprecated",
                },
            }),
            "instinct",
        )
        assert not result.valid

    def test_missing_pattern_rejected(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("no-pattern.instinct.yaml", {
                "apiVersion": "aes/v1",
                "kind": "Instinct",
                "metadata": {
                    "id": "bad",
                    "created_at": "2026-03-15T10:30:00Z",
                    "last_validated": "2026-03-15T10:30:00Z",
                    "source_session": "s1",
                },
                "confidence": {
                    "score": 0.5,
                    "validations": 0,
                    "contradictions": 0,
                    "status": "candidate",
                },
            }),
            "instinct",
        )
        assert not result.valid

    def test_bad_id_pattern_rejected(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("bad-id.instinct.yaml", {
                "apiVersion": "aes/v1",
                "kind": "Instinct",
                "metadata": {
                    "id": "BAD ID",
                    "created_at": "2026-03-15T10:30:00Z",
                    "last_validated": "2026-03-15T10:30:00Z",
                    "source_session": "s1",
                },
                "pattern": {
                    "description": "x",
                    "trigger": "y",
                    "action": "z",
                },
                "confidence": {
                    "score": 0.5,
                    "validations": 0,
                    "contradictions": 0,
                    "status": "candidate",
                },
            }),
            "instinct",
        )
        assert not result.valid


class TestLearningConfigSchema:
    def test_valid_full_config(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("config.yaml", {
                "apiVersion": "aes/v1",
                "kind": "LearningConfig",
                "extraction": {
                    "enabled": True,
                    "auto_extract": True,
                    "min_session_length": 5,
                    "max_candidates_per_session": 3,
                },
                "confidence": {
                    "initial_score": 0.4,
                    "promotion_threshold": 0.6,
                    "promotion_min_validations": 3,
                    "publish_threshold": 0.8,
                    "publish_min_validations": 5,
                    "decay_rate_per_week": 0.01,
                    "min_score": 0.3,
                },
                "context_loading": {
                    "max_instincts_in_context": 10,
                    "sort_by": "confidence_score",
                    "token_budget": 2000,
                    "format": "compact",
                },
            }),
            "learning-config",
        )
        assert result.valid, result.errors

    def test_minimal_config(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("config.yaml", {
                "apiVersion": "aes/v1",
                "kind": "LearningConfig",
            }),
            "learning-config",
        )
        assert result.valid, result.errors

    def test_invalid_format_enum(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("config.yaml", {
                "apiVersion": "aes/v1",
                "kind": "LearningConfig",
                "context_loading": {
                    "format": "verbose",
                },
            }),
            "learning-config",
        )
        assert not result.valid

    def test_invalid_sort_by(self, tmp_yaml):
        result = validate_file(
            tmp_yaml("config.yaml", {
                "apiVersion": "aes/v1",
                "kind": "LearningConfig",
                "context_loading": {
                    "sort_by": "random",
                },
            }),
            "learning-config",
        )
        assert not result.valid


class TestInstinctsInAgentDir:
    def test_instincts_validated_in_agent_dir(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text(yaml.dump({
            "aes": "1.4",
            "name": "test-project",
            "version": "0.1.0",
            "description": "Test project",
            "agent": {"instructions": "instructions.md"},
        }))
        (agent_dir / "instructions.md").write_text("# Test")

        instincts_dir = agent_dir / "learning" / "instincts" / "active"
        instincts_dir.mkdir(parents=True)
        (instincts_dir / "test.instinct.yaml").write_text(yaml.dump({
            "apiVersion": "aes/v1",
            "kind": "Instinct",
            "metadata": {
                "id": "test",
                "created_at": "2026-03-15T10:30:00Z",
                "last_validated": "2026-03-15T10:30:00Z",
                "source_session": "s1",
            },
            "pattern": {
                "description": "A pattern",
                "trigger": "When X",
                "action": "Do Y",
            },
            "confidence": {
                "score": 0.8,
                "validations": 5,
                "contradictions": 0,
                "status": "active",
            },
        }))

        results = validate_agent_dir(agent_dir)
        instinct_results = [r for r in results if r.schema_type == "instinct"]
        assert len(instinct_results) == 1
        assert instinct_results[0].valid

    def test_active_instinct_below_min_score_warns(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text(yaml.dump({
            "aes": "1.4",
            "name": "test",
            "version": "0.1.0",
            "description": "Test",
            "agent": {"instructions": "instructions.md"},
        }))
        (agent_dir / "instructions.md").write_text("# Test")

        instincts_dir = agent_dir / "learning" / "instincts" / "active"
        instincts_dir.mkdir(parents=True)
        (instincts_dir / "low.instinct.yaml").write_text(yaml.dump({
            "apiVersion": "aes/v1",
            "kind": "Instinct",
            "metadata": {
                "id": "low-confidence",
                "created_at": "2026-03-15T10:30:00Z",
                "last_validated": "2026-03-15T10:30:00Z",
                "source_session": "s1",
            },
            "pattern": {
                "description": "x",
                "trigger": "y",
                "action": "z",
            },
            "confidence": {
                "score": 0.1,
                "validations": 1,
                "contradictions": 5,
                "min_score": 0.3,
                "status": "active",
            },
        }))

        results = validate_agent_dir(agent_dir)
        warnings = [
            r for r in results
            if r.schema_type == "instinct" and r.valid and r.errors
        ]
        assert any("below" in str(w.errors) for w in warnings)
