"""Task result dataclass and output formatting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskResult:
    """Result of a single maintenance task."""

    name: str
    status: str  # "ok", "skipped", "failed"
    reason: str = ""  # "disabled", "not installed", "exit code 1", "timed out"
    duration: float = 0  # seconds elapsed
