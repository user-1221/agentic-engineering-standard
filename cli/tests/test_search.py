"""Tests for aes search command."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from aes.__main__ import cli


MOCK_INDEX = {
    "packages": {
        "deploy": {
            "description": "Deploy the app",
            "latest": "1.1.0",
            "type": "skill",
            "tags": ["devops"],
            "versions": {
                "1.0.0": {"url": "packages/deploy/1.0.0.tar.gz", "sha256": "abc", "published_at": "2025-01-15T10:00:00Z"},
                "1.1.0": {"url": "packages/deploy/1.1.0.tar.gz", "sha256": "def", "published_at": "2025-06-01T12:00:00Z"},
            },
        },
        "train": {
            "description": "Train ML models with Optuna",
            "latest": "2.0.0",
            "type": "skill",
            "tags": ["ml", "training"],
            "versions": {
                "2.0.0": {"url": "packages/train/2.0.0.tar.gz", "sha256": "ghi", "published_at": "2025-09-20T08:00:00Z"},
            },
        },
        "ml-pipeline": {
            "description": "Complete ML pipeline template",
            "latest": "2.1.0",
            "type": "template",
            "tags": ["ml"],
            "versions": {
                "2.1.0": {"url": "packages/ml-pipeline/2.1.0.tar.gz", "sha256": "jkl", "published_at": "2025-03-10T00:00:00Z"},
            },
        },
    }
}


def _mock_fetch_index(*args, **kwargs):
    return MOCK_INDEX


class TestSearchCommand:

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_all(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search"])
        assert result.exit_code == 0, result.output
        assert "deploy" in result.output
        assert "train" in result.output
        assert "ml-pipeline" in result.output
        assert "3 package(s)" in result.output

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_keyword(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "train"])
        assert result.exit_code == 0, result.output
        assert "train" in result.output
        assert "1 package(s)" in result.output

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_tag(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--tag", "ml"])
        assert result.exit_code == 0, result.output
        assert "train" in result.output
        assert "deploy" not in result.output.split("AES Registry")[1]  # not in table

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_no_results(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "nonexistent"])
        assert result.exit_code == 0, result.output
        assert "No packages" in result.output

    @patch("aes.commands.search.fetch_index", side_effect=Exception("Network error"))
    def test_search_fetch_failure(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search"])
        assert result.exit_code != 0
        assert "Failed to fetch" in result.output

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_type_skill(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--type", "skill"])
        assert result.exit_code == 0, result.output
        assert "deploy" in result.output
        assert "train" in result.output
        assert "2 package(s)" in result.output

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_type_template(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--type", "template"])
        assert result.exit_code == 0, result.output
        assert "ml-pipeline" in result.output
        assert "1 package(s)" in result.output

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_type_column_in_output(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search"])
        assert result.exit_code == 0, result.output
        assert "Type" in result.output  # column header
        assert "skill" in result.output
        assert "template" in result.output

    # --- New: sort, limit, verbose ---

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_sort_by_name(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--sort-by", "name"])
        assert result.exit_code == 0, result.output
        # Default sort is alphabetical; deploy < ml-pipeline < train
        lines = result.output.split("\n")
        pkg_lines = [l for l in lines if "deploy" in l or "train" in l or "ml-pipeline" in l]
        assert len(pkg_lines) == 3

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_sort_by_latest(self, mock_fetch) -> None:
        """Sort by published_at descending — train (Sep) > deploy (Jun) > ml-pipeline (Mar)."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--sort-by", "latest"])
        assert result.exit_code == 0, result.output
        # train was published most recently (2025-09), should appear first in table
        train_pos = result.output.find("Train ML models")
        deploy_pos = result.output.find("Deploy the app")
        ml_pos = result.output.find("Complete ML pipeline")
        assert train_pos < deploy_pos < ml_pos

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_sort_by_version(self, mock_fetch) -> None:
        """Sort by semver descending — ml-pipeline 2.1.0 > train 2.0.0 > deploy 1.1.0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--sort-by", "version"])
        assert result.exit_code == 0, result.output
        ml_pos = result.output.find("Complete ML pipeline")
        train_pos = result.output.find("Train ML models")
        deploy_pos = result.output.find("Deploy the app")
        assert ml_pos < train_pos < deploy_pos

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_limit(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--limit", "1"])
        assert result.exit_code == 0, result.output
        assert "1 of 3 package(s)" in result.output

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_limit_larger_than_results(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--limit", "100"])
        assert result.exit_code == 0, result.output
        assert "3 package(s) found" in result.output

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_verbose(self, mock_fetch) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "-v"])
        assert result.exit_code == 0, result.output
        assert "Versions" in result.output  # extra column header
        assert "Published" in result.output  # extra column header

    @patch("aes.commands.search.fetch_index", side_effect=_mock_fetch_index)
    def test_search_sort_and_limit_combined(self, mock_fetch) -> None:
        """--sort-by version --limit 2: top 2 by semver = ml-pipeline 2.1.0, train 2.0.0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--sort-by", "version", "--limit", "2"])
        assert result.exit_code == 0, result.output
        assert "2 of 3 package(s)" in result.output
        assert "ml-pipeline" in result.output
        assert "train" in result.output
        # deploy (1.1.0) should be excluded
        # Check it's not in the table body (after header)
        table_body = result.output.split("AES Registry")[1]
        assert "Deploy the app" not in table_body
