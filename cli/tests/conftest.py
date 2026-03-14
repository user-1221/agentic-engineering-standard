"""Shared fixtures for AES CLI tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _force_english_locale(monkeypatch):
    """Ensure tests always run in English regardless of user config."""
    monkeypatch.setenv("AES_LANG", "en")
    # Reset the i18n module state so it picks up the env var
    from aes.i18n import init_locale
    init_locale("en")
