#!/usr/bin/env python3
"""Bump AES versions across the repository."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def bump_cli(version: str, *, dry_run: bool = False) -> list[str]:
    """Bump CLI version in pyproject.toml and __init__.py."""
    changes: list[str] = []

    # cli/pyproject.toml
    pyproject = REPO_ROOT / "cli" / "pyproject.toml"
    text = pyproject.read_text()
    new_text = re.sub(
        r'^version = ".*"',
        f'version = "{version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if text != new_text:
        if not dry_run:
            pyproject.write_text(new_text)
        changes.append(f"  cli/pyproject.toml: version -> {version}")

    # cli/aes/__init__.py
    init_py = REPO_ROOT / "cli" / "aes" / "__init__.py"
    text = init_py.read_text()
    new_text = re.sub(
        r'^__version__ = ".*"',
        f'__version__ = "{version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if text != new_text:
        if not dry_run:
            init_py.write_text(new_text)
        changes.append(f"  cli/aes/__init__.py: __version__ -> {version}")

    return changes


def bump_spec(version: str, *, dry_run: bool = False) -> list[str]:
    """Bump spec version in README, schemas, examples, templates, scaffolds."""
    changes: list[str] = []
    major = version.split(".")[0]

    # spec/README.md header
    readme = REPO_ROOT / "spec" / "README.md"
    text = readme.read_text()
    new_text = re.sub(
        r"^# Agentic Engineering Standard \(AES\) v\d+\.\d+",
        f"# Agentic Engineering Standard (AES) v{version}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if text != new_text:
        if not dry_run:
            readme.write_text(new_text)
        changes.append(f"  spec/README.md: header -> v{version}")

    # Schema $id URLs — update major version component
    for schema_file in sorted((REPO_ROOT / "schemas").glob("*.json")):
        text = schema_file.read_text()
        new_text = re.sub(
            r'("https://aes\.dev/schemas/[^/]+/)v\d+"',
            rf"\1v{major}\"",
            text,
        )
        if text != new_text:
            if not dry_run:
                schema_file.write_text(new_text)
            changes.append(f"  schemas/{schema_file.name}: $id -> v{major}")

    # aes: "X.Y" in example and template manifests
    manifest_files = sorted(
        list((REPO_ROOT / "examples").rglob("agent.yaml"))
        + list((REPO_ROOT / "templates").rglob("agent.yaml"))
    )
    for f in manifest_files:
        text = f.read_text()
        new_text = re.sub(
            r'^aes: "\d+\.\d+"',
            f'aes: "{version}"',
            text,
            flags=re.MULTILINE,
        )
        if text != new_text:
            if not dry_run:
                f.write_text(new_text)
            changes.append(f"  {f.relative_to(REPO_ROOT)}: aes -> {version}")

    # Scaffold templates — aes: and aes_* version fields
    scaffold_dir = REPO_ROOT / "cli" / "aes" / "scaffold"
    version_patterns = [
        (r'aes: "\d+\.\d+"', f'aes: "{version}"'),
        (r'aes_skill: "\d+\.\d+"', f'aes_skill: "{version}"'),
        (r'aes_workflow: "\d+\.\d+"', f'aes_workflow: "{version}"'),
        (r'aes_permissions: "\d+\.\d+"', f'aes_permissions: "{version}"'),
    ]
    for jinja_file in sorted(scaffold_dir.glob("*.jinja")):
        text = jinja_file.read_text()
        new_text = text
        for pattern, replacement in version_patterns:
            new_text = re.sub(pattern, replacement, new_text)
        if text != new_text:
            if not dry_run:
                jinja_file.write_text(new_text)
            rel = jinja_file.relative_to(REPO_ROOT)
            changes.append(f"  {rel}: aes versions -> {version}")

    return changes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bump AES versions across the repository"
    )
    parser.add_argument("--cli", metavar="VERSION", help="CLI version (e.g., 0.2.0)")
    parser.add_argument("--spec", metavar="VERSION", help="Spec version (e.g., 1.1)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without writing"
    )
    args = parser.parse_args()

    if not args.cli and not args.spec:
        parser.error("Provide --cli VERSION, --spec VERSION, or both")

    if args.cli and not re.match(r"^\d+\.\d+\.\d+$", args.cli):
        parser.error(f"CLI version must be semver (e.g., 0.2.0), got: {args.cli}")
    if args.spec and not re.match(r"^\d+\.\d+$", args.spec):
        parser.error(f"Spec version must be X.Y (e.g., 1.1), got: {args.spec}")

    if args.dry_run:
        print("[dry-run] No files will be modified.\n")

    tags: list[str] = []

    if args.cli:
        print(f"Bumping CLI to {args.cli}:")
        changes = bump_cli(args.cli, dry_run=args.dry_run)
        if changes:
            for c in changes:
                print(c)
        else:
            print("  (no changes)")
        tags.append(f"cli-v{args.cli}")

    if args.spec:
        print(f"\nBumping spec to {args.spec}:")
        changes = bump_spec(args.spec, dry_run=args.dry_run)
        if changes:
            for c in changes:
                print(c)
        else:
            print("  (no changes)")
        tags.append(f"spec-v{args.spec}")

    print("\n--- After committing, create tags: ---")
    for tag in tags:
        print(f'  git tag -a {tag} -m "Release {tag}"')
    print("  git push && git push --tags")


if __name__ == "__main__":
    main()
