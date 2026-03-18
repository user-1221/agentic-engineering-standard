"""Sync target adapters for AI coding tools."""

from __future__ import annotations

from typing import Dict, Type

from aes.targets._base import AgentContext, GeneratedFile, SyncPlan, SyncTarget
from aes.targets.claude import ClaudeTarget
from aes.targets.copilot import CopilotTarget
from aes.targets.cursor import CursorTarget
from aes.targets.openclaw import OpenClawTarget
from aes.targets.windsurf import WindsurfTarget

TARGETS: Dict[str, Type[SyncTarget]] = {
    "claude": ClaudeTarget,
    "cursor": CursorTarget,
    "copilot": CopilotTarget,
    "windsurf": WindsurfTarget,
    "openclaw": OpenClawTarget,
}

TARGET_NAMES = list(TARGETS.keys())

__all__ = [
    "TARGETS",
    "TARGET_NAMES",
    "AgentContext",
    "GeneratedFile",
    "SyncPlan",
    "SyncTarget",
]
