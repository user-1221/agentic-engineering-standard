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
                "1.0.0": {"url": "packages/deploy/1.0.0.tar.gz", "sha256": "abc"},
                "1.1.0": {"url": "packages/deploy/1.1.0.tar.gz", "sha256": "def"},
            },
        },
        "train": {
            "description": "Train ML models with Optuna",
            "latest": "2.0.0",
            "type": "skill",
            "tags": ["ml", "training"],
            "versions": {
                "2.0.0": {"url": "packages/train/2.0.0.tar.gz", "sha256": "ghi"},
            },
        },
        "ml-pipeline": {
            "description": "Complete ML pipeline template",
            "latest": "2.1.0",
            "type": "template",
            "tags": ["ml"],
            "versions": {
                "2.1.0": {"url": "packages/ml-pipeline/2.1.0.tar.gz", "sha256": "jkl"},
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
