"""Registry client — fetch index, resolve versions, download packages."""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Default registry URL (R2/S3 public bucket)
REGISTRY_URL = os.environ.get("AES_REGISTRY_URL", "https://registry.aes-official.com")
INDEX_PATH = "index.json"
PACKAGES_PATH = "packages"


def _parse_version(v: str) -> Tuple[int, int, int]:
    """Parse a semver string into (major, minor, patch)."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", v)
    if not match:
        raise ValueError(f"Invalid semver: {v}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _version_matches(version: str, spec: str) -> bool:
    """Check if *version* satisfies *spec*.

    Supports: exact "1.2.3", caret "^1.2.0", tilde "~1.2.0",
    minimum ">=1.0.0", wildcard "*".
    """
    if spec == "*":
        return True

    ver = _parse_version(version)

    if spec.startswith("^"):
        base = _parse_version(spec[1:])
        # >=base, <next_major (or <next_minor if major==0)
        if base[0] == 0:
            ceiling = (0, base[1] + 1, 0)
        else:
            ceiling = (base[0] + 1, 0, 0)
        return base <= ver < ceiling

    if spec.startswith("~"):
        base = _parse_version(spec[1:])
        ceiling = (base[0], base[1] + 1, 0)
        return base <= ver < ceiling

    if spec.startswith(">="):
        base = _parse_version(spec[2:])
        return ver >= base

    if spec.startswith(">"):
        base = _parse_version(spec[1:])
        return ver > base

    if spec.startswith("<="):
        base = _parse_version(spec[2:])
        return ver <= base

    if spec.startswith("<"):
        base = _parse_version(spec[1:])
        return ver < base

    # Exact match
    return ver == _parse_version(spec)


def resolve_version(spec: str, available: List[str]) -> Optional[str]:
    """Find the best (highest) version matching *spec*."""
    matches = [v for v in available if _version_matches(v, spec)]
    if not matches:
        return None
    matches.sort(key=_parse_version)
    return matches[-1]


_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


def parse_registry_source(source: str) -> Tuple[str, str]:
    """Parse ``aes-hub/deploy@^1.2.0`` into (name, version_spec).

    Returns (name, "*") if no version constraint given.
    Raises ValueError if name is invalid.
    """
    # Strip prefix
    name_ver = source
    if "/" in name_ver:
        name_ver = name_ver.split("/", 1)[1]

    if "@" in name_ver:
        name, version_spec = name_ver.split("@", 1)
    else:
        name = name_ver
        version_spec = "*"

    if not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid package name {name!r}: must be 1-64 lowercase chars "
            "starting with a letter (a-z, 0-9, _, -)"
        )

    return name, version_spec


def fetch_index(registry_url: Optional[str] = None) -> dict:
    """Fetch and parse the registry ``index.json``."""
    base = registry_url or os.environ.get("AES_REGISTRY_URL", REGISTRY_URL)
    url = f"{base.rstrip('/')}/{INDEX_PATH}"

    req = urllib.request.Request(url)
    token = os.environ.get("AES_REGISTRY_KEY")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def download_package(
    name: str,
    version: str,
    sha256_expected: str,
    dest: Path,
    registry_url: Optional[str] = None,
) -> Path:
    """Download a tarball from the registry and verify its sha256.

    Returns the local path to the downloaded file.
    """
    base = registry_url or os.environ.get("AES_REGISTRY_URL", REGISTRY_URL)
    url = f"{base.rstrip('/')}/{PACKAGES_PATH}/{name}/{version}.tar.gz"

    tarball_path = dest / f"{name}-{version}.tar.gz"

    req = urllib.request.Request(url)
    token = os.environ.get("AES_REGISTRY_KEY")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()

    actual_sha = hashlib.sha256(data).hexdigest()
    if actual_sha != sha256_expected:
        raise ValueError(
            f"SHA256 mismatch for {name}@{version}: "
            f"expected {sha256_expected[:16]}..., got {actual_sha[:16]}..."
        )

    tarball_path.write_bytes(data)
    return tarball_path


def upload_package(
    tarball_path: Path,
    name: str,
    version: str,
    description: str,
    tags: Optional[List[str]] = None,
    registry_url: Optional[str] = None,
    pkg_type: str = "skill",
    visibility: str = "public",
) -> dict:
    """Upload a tarball and update the registry index.

    Returns the updated index entry for this package.
    """
    base = registry_url or os.environ.get("AES_REGISTRY_URL", REGISTRY_URL)
    token = os.environ.get("AES_REGISTRY_KEY")
    if not token:
        raise RuntimeError(
            "AES_REGISTRY_KEY environment variable is required for publishing. "
            "Set it to your registry API token."
        )

    tarball_data = tarball_path.read_bytes()
    sha = hashlib.sha256(tarball_data).hexdigest()

    # Upload tarball
    upload_url = f"{base.rstrip('/')}/{PACKAGES_PATH}/{name}/{version}.tar.gz"
    req = urllib.request.Request(upload_url, data=tarball_data, method="PUT")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/gzip")
    try:
        urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            raise RuntimeError(
                f"Version {version} of '{name}' already exists in the registry. "
                "Bump the version in your skill manifest and try again."
            ) from None
        raise

    # Fetch current index
    try:
        index = fetch_index(registry_url)
    except (urllib.error.URLError, urllib.error.HTTPError):
        index = {"packages": {}}

    # Update index
    packages = index.setdefault("packages", {})
    pkg = packages.setdefault(name, {
        "description": description,
        "latest": version,
        "versions": {},
    })
    pkg["description"] = description
    pkg["type"] = pkg_type
    pkg["visibility"] = visibility
    if tags:
        pkg["tags"] = tags

    from datetime import datetime, timezone
    pkg["versions"][version] = {
        "url": f"{PACKAGES_PATH}/{name}/{version}.tar.gz",
        "sha256": sha,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }

    # Update "latest" if this version is higher
    try:
        if _parse_version(version) >= _parse_version(pkg.get("latest", "0.0.0")):
            pkg["latest"] = version
    except ValueError:
        pkg["latest"] = version

    # Upload updated index
    index_data = json.dumps(index, indent=2).encode()
    index_url = f"{base.rstrip('/')}/{INDEX_PATH}"
    req = urllib.request.Request(index_url, data=index_data, method="PUT")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    urllib.request.urlopen(req, timeout=30)

    return pkg


def search_packages(
    query: str = "",
    tag: Optional[str] = None,
    domain: Optional[str] = None,
    index: Optional[dict] = None,
    registry_url: Optional[str] = None,
    pkg_type: Optional[str] = None,
) -> List[Dict[str, object]]:
    """Search the registry index for matching packages.

    Returns list of dicts with: name, description, latest, tags, type.
    """
    if index is None:
        index = fetch_index(registry_url)

    results = []
    for name, pkg in index.get("packages", {}).items():
        # Type filter (packages without type default to "skill")
        if pkg_type:
            if pkg.get("type", "skill") != pkg_type:
                continue

        # Keyword filter
        if query:
            q = query.lower()
            haystack = f"{name} {pkg.get('description', '')}".lower()
            if q not in haystack:
                continue

        # Tag filter
        if tag:
            pkg_tags = pkg.get("tags", [])
            if tag.lower() not in [t.lower() for t in pkg_tags]:
                continue

        # Domain filter (convention: domain is a tag)
        if domain:
            pkg_tags = pkg.get("tags", [])
            if domain.lower() not in [t.lower() for t in pkg_tags]:
                continue

        # Compute latest_published_at from the latest version entry
        latest_ver = pkg.get("latest", "")
        latest_info = pkg.get("versions", {}).get(latest_ver, {})
        latest_published_at = latest_info.get("published_at", "")

        results.append({
            "name": name,
            "description": pkg.get("description", ""),
            "latest": pkg.get("latest", "?"),
            "tags": pkg.get("tags", []),
            "type": pkg.get("type", "skill"),
            "versions": list(pkg.get("versions", {}).keys()),
            "version_count": len(pkg.get("versions", {})),
            "latest_published_at": latest_published_at,
        })

    return results
