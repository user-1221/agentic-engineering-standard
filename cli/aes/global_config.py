"""Global user configuration (~/.aes/config.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

_CONFIG_DIR = Path.home() / ".aes"
_CONFIG_FILE = _CONFIG_DIR / "config.yaml"


def load_global_config() -> dict:
    """Load ~/.aes/config.yaml. Returns empty dict if not found."""
    if not _CONFIG_FILE.exists():
        return {}
    with open(_CONFIG_FILE) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def save_global_config(config: dict) -> None:
    """Write config to ~/.aes/config.yaml, creating dir if needed."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def get_locale() -> Optional[str]:
    """Return configured locale or None."""
    return load_global_config().get("locale")


def set_locale(locale: str) -> None:
    """Persist locale to global config."""
    config = load_global_config()
    config["locale"] = locale
    save_global_config(config)
