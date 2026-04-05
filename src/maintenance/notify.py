"""macOS notifications via osascript."""

from __future__ import annotations

import logging
import subprocess

from maintenance.output import TaskResult

logger = logging.getLogger("maintenance")


def notify(
    title: str,
    message: str,
    *,
    subtitle: str = "",
    sound: str = "Submarine",
) -> bool:
    """Send a macOS notification via osascript. Returns True if delivered."""
    script = f'display notification "{message}" with title "{title}"'
    if subtitle:
        script += f' subtitle "{subtitle}"'
    if sound:
        script += f' sound name "{sound}"'
    try:
        subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            timeout=5,
            capture_output=True,
        )
        return True
    except Exception:
        logger.debug("Notification delivery failed")
        return False


def format_summary(results: list[TaskResult]) -> tuple[str, str, str]:
    """Build notification (title, message, subtitle) from task results."""
    ok = [r for r in results if r.status == "ok" and r.reason != "dry-run"]
    skipped = [r for r in results if r.status == "skipped"]
    failed = [r for r in results if r.status == "failed"]

    if failed:
        title = f"Maintenance: {len(failed)} failed"
        parts = []
        if ok:
            parts.append(f"{len(ok)} ran")
        if skipped:
            parts.append(f"{len(skipped)} skipped")
        message = ", ".join(parts) if parts else "No tasks ran"
        subtitle = ", ".join(r.name for r in failed)
    else:
        title = "Maintenance complete"
        parts = []
        if ok:
            parts.append(f"{len(ok)} ran")
        if skipped:
            parts.append(f"{len(skipped)} skipped")
        message = ", ".join(parts) if parts else "No tasks ran"
        subtitle = ""

    return title, message, subtitle
