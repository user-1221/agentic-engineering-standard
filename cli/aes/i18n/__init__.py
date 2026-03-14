"""Internationalization support for AES CLI."""

from __future__ import annotations

import os
from typing import Optional

# Module-level state
_current_locale: str = "en"
_translations: dict = {}


def init_locale(locale: Optional[str] = None) -> str:
    """Initialize i18n from saved config or given locale. Returns active locale."""
    global _current_locale, _translations

    if locale is None:
        # Check env var first
        env_lang = os.environ.get("AES_LANG")
        if env_lang and env_lang in ("en", "ja"):
            locale = env_lang
        else:
            from aes.global_config import get_locale
            locale = get_locale() or "en"

    _current_locale = locale

    if locale == "ja":
        from aes.i18n.ja import MESSAGES
        _translations = MESSAGES
    else:
        _translations = {}

    return _current_locale


def t(key: str, **kwargs: object) -> str:
    """Translate a message key, with optional format arguments.

    Falls back to English if the key is not in the current locale.
    Falls back to the key itself if not in English either.
    """
    from aes.i18n._messages import MESSAGES as EN_MESSAGES

    template = _translations.get(key)
    if template is None:
        template = EN_MESSAGES.get(key, key)

    if kwargs:
        return template.format(**kwargs)
    return template


def get_current_locale() -> str:
    """Return the currently active locale."""
    return _current_locale
