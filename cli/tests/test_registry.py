"""Tests for aes.registry — version resolution and index parsing."""

from __future__ import annotations

import json
import os
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from aes.registry import (
    _parse_version,
    _version_matches,
    resolve_version,
    parse_registry_source,
    search_packages,
    upload_package,
)


# ---------------------------------------------------------------------------
# Version parsing
# ---------------------------------------------------------------------------

class TestParseVersion:
    def test_basic(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_with_prerelease(self):
        # Should still extract major.minor.patch
        assert _parse_version("1.2.3-beta") == (1, 2, 3)

    def test_invalid(self):
        with pytest.raises(ValueError):
            _parse_version("not-a-version")


# ---------------------------------------------------------------------------
# Version matching
# ---------------------------------------------------------------------------

class TestVersionMatches:
    def test_exact(self):
        assert _version_matches("1.2.3", "1.2.3")
        assert not _version_matches("1.2.4", "1.2.3")

    def test_wildcard(self):
        assert _version_matches("0.0.1", "*")
        assert _version_matches("99.99.99", "*")

    def test_caret(self):
        # ^1.2.0: >=1.2.0, <2.0.0
        assert _version_matches("1.2.0", "^1.2.0")
        assert _version_matches("1.9.9", "^1.2.0")
        assert not _version_matches("2.0.0", "^1.2.0")
        assert not _version_matches("1.1.9", "^1.2.0")

    def test_caret_zero_major(self):
        # ^0.2.0: >=0.2.0, <0.3.0
        assert _version_matches("0.2.0", "^0.2.0")
        assert _version_matches("0.2.9", "^0.2.0")
        assert not _version_matches("0.3.0", "^0.2.0")

    def test_tilde(self):
        # ~1.2.0: >=1.2.0, <1.3.0
        assert _version_matches("1.2.0", "~1.2.0")
        assert _version_matches("1.2.9", "~1.2.0")
        assert not _version_matches("1.3.0", "~1.2.0")
        assert not _version_matches("1.1.9", "~1.2.0")

    def test_gte(self):
        assert _version_matches("1.0.0", ">=1.0.0")
        assert _version_matches("2.0.0", ">=1.0.0")
        assert not _version_matches("0.9.9", ">=1.0.0")

    def test_gt(self):
        assert _version_matches("1.0.1", ">1.0.0")
        assert not _version_matches("1.0.0", ">1.0.0")

    def test_lte(self):
        assert _version_matches("1.0.0", "<=1.0.0")
        assert not _version_matches("1.0.1", "<=1.0.0")

    def test_lt(self):
        assert _version_matches("0.9.9", "<1.0.0")
        assert not _version_matches("1.0.0", "<1.0.0")


# ---------------------------------------------------------------------------
# Version resolution
# ---------------------------------------------------------------------------

class TestResolveVersion:
    VERSIONS = ["1.0.0", "1.1.0", "1.2.0", "2.0.0", "2.1.0"]

    def test_exact(self):
        assert resolve_version("1.1.0", self.VERSIONS) == "1.1.0"

    def test_caret(self):
        assert resolve_version("^1.0.0", self.VERSIONS) == "1.2.0"

    def test_tilde(self):
        assert resolve_version("~1.0.0", self.VERSIONS) == "1.0.0"

    def test_gte(self):
        assert resolve_version(">=2.0.0", self.VERSIONS) == "2.1.0"

    def test_wildcard(self):
        assert resolve_version("*", self.VERSIONS) == "2.1.0"

    def test_no_match(self):
        assert resolve_version("3.0.0", self.VERSIONS) is None

    def test_empty_list(self):
        assert resolve_version("*", []) is None


# ---------------------------------------------------------------------------
# Source parsing
# ---------------------------------------------------------------------------

class TestParseRegistrySource:
    def test_full(self):
        name, spec = parse_registry_source("aes-hub/deploy@^1.2.0")
        assert name == "deploy"
        assert spec == "^1.2.0"

    def test_no_version(self):
        name, spec = parse_registry_source("aes-hub/deploy")
        assert name == "deploy"
        assert spec == "*"

    def test_bare_name(self):
        name, spec = parse_registry_source("deploy@1.0.0")
        assert name == "deploy"
        assert spec == "1.0.0"


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class TestSearch:
    INDEX = {
        "packages": {
            "deploy": {
                "description": "Deploy the app",
                "latest": "1.0.0",
                "tags": ["devops", "deployment"],
                "versions": {"1.0.0": {}},
            },
            "train": {
                "description": "Train ML models",
                "latest": "2.0.0",
                "tags": ["ml", "training"],
                "versions": {"1.0.0": {}, "2.0.0": {}},
            },
            "scaffold": {
                "description": "Scaffold web features",
                "latest": "1.0.0",
                "tags": ["web"],
                "versions": {"1.0.0": {}},
            },
        }
    }

    def test_keyword_search(self):
        results = search_packages(query="deploy", index=self.INDEX)
        assert len(results) == 1
        assert results[0]["name"] == "deploy"

    def test_tag_filter(self):
        results = search_packages(tag="ml", index=self.INDEX)
        assert len(results) == 1
        assert results[0]["name"] == "train"

    def test_domain_filter(self):
        results = search_packages(domain="web", index=self.INDEX)
        assert len(results) == 1
        assert results[0]["name"] == "scaffold"

    def test_empty_query_returns_all(self):
        results = search_packages(index=self.INDEX)
        assert len(results) == 3

    def test_no_match(self):
        results = search_packages(query="nonexistent", index=self.INDEX)
        assert len(results) == 0


class TestSearchType:
    """Tests for pkg_type filter in search_packages."""

    INDEX = {
        "packages": {
            "deploy": {
                "description": "Deploy skill",
                "type": "skill",
                "latest": "1.0.0",
                "versions": {"1.0.0": {}},
            },
            "ml-pipeline": {
                "description": "ML template",
                "type": "template",
                "latest": "2.0.0",
                "tags": ["ml"],
                "versions": {"2.0.0": {}},
            },
            "old-skill": {
                "description": "Legacy skill without type field",
                "latest": "1.0.0",
                "versions": {"1.0.0": {}},
            },
        }
    }

    def test_filter_skills(self):
        results = search_packages(pkg_type="skill", index=self.INDEX)
        names = {r["name"] for r in results}
        assert "deploy" in names
        assert "old-skill" in names  # defaults to skill
        assert "ml-pipeline" not in names

    def test_filter_templates(self):
        results = search_packages(pkg_type="template", index=self.INDEX)
        assert len(results) == 1
        assert results[0]["name"] == "ml-pipeline"

    def test_no_filter_returns_all(self):
        results = search_packages(index=self.INDEX)
        assert len(results) == 3

    def test_type_included_in_results(self):
        results = search_packages(index=self.INDEX)
        by_name = {r["name"]: r for r in results}
        assert by_name["deploy"]["type"] == "skill"
        assert by_name["ml-pipeline"]["type"] == "template"
        assert by_name["old-skill"]["type"] == "skill"  # default


# ---------------------------------------------------------------------------
# Upload — HTTP error handling
# ---------------------------------------------------------------------------

class TestUploadPackage:
    """Tests for upload_package — especially duplicate (409) handling."""

    def test_409_raises_friendly_error(self, tmp_path):
        tarball = tmp_path / "deploy-1.0.0.tar.gz"
        tarball.write_bytes(b"fake tarball content")

        err_409 = urllib.error.HTTPError(
            url="https://registry.aes-official.com/packages/deploy/1.0.0.tar.gz",
            code=409,
            msg="Conflict",
            hdrs={},
            fp=None,
        )

        with patch.dict(os.environ, {"AES_REGISTRY_KEY": "test-token"}):
            with patch("aes.registry.urllib.request.urlopen", side_effect=err_409):
                with pytest.raises(RuntimeError, match=r"Version 1\.0\.0 of 'deploy' already exists"):
                    upload_package(
                        tarball_path=tarball,
                        name="deploy",
                        version="1.0.0",
                        description="Deploy skill",
                    )

    def test_upload_includes_visibility(self, tmp_path):
        tarball = tmp_path / "deploy-1.0.0.tar.gz"
        tarball.write_bytes(b"fake tarball content")

        calls = []
        def mock_urlopen(req, **kwargs):
            calls.append(req)
            method = req.get_method()
            url = req.full_url
            # First call is PUT package, second is GET index, third is PUT index
            if method == "PUT" and "index.json" in url:
                return MagicMock()
            if method == "PUT":
                return MagicMock()
            # GET index — return empty index
            resp = MagicMock()
            resp.read.return_value = b'{"packages":{}}'
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch.dict(os.environ, {"AES_REGISTRY_KEY": "test-token"}):
            with patch("aes.registry.urllib.request.urlopen", side_effect=mock_urlopen):
                result = upload_package(
                    tarball_path=tarball,
                    name="deploy",
                    version="1.0.0",
                    description="Deploy skill",
                    visibility="private",
                )

        assert result["visibility"] == "private"

    def test_upload_default_visibility_is_public(self, tmp_path):
        tarball = tmp_path / "deploy-1.0.0.tar.gz"
        tarball.write_bytes(b"fake tarball content")

        def mock_urlopen(req, **kwargs):
            method = req.get_method()
            url = req.full_url
            if method == "PUT" and "index.json" in url:
                return MagicMock()
            if method == "PUT":
                return MagicMock()
            resp = MagicMock()
            resp.read.return_value = b'{"packages":{}}'
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch.dict(os.environ, {"AES_REGISTRY_KEY": "test-token"}):
            with patch("aes.registry.urllib.request.urlopen", side_effect=mock_urlopen):
                result = upload_package(
                    tarball_path=tarball,
                    name="deploy",
                    version="1.0.0",
                    description="Deploy skill",
                )

        assert result["visibility"] == "public"

    def test_500_still_raises_error(self, tmp_path):
        tarball = tmp_path / "deploy-1.0.0.tar.gz"
        tarball.write_bytes(b"fake tarball content")

        err_500 = urllib.error.HTTPError(
            url="https://registry.aes-official.com/packages/deploy/1.0.0.tar.gz",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )

        with patch.dict(os.environ, {"AES_REGISTRY_KEY": "test-token"}):
            with patch("aes.registry.urllib.request.urlopen", side_effect=err_500):
                with pytest.raises(RuntimeError, match="HTTP 500"):
                    upload_package(
                        tarball_path=tarball,
                        name="deploy",
                        version="1.0.0",
                        description="Deploy skill",
                    )
