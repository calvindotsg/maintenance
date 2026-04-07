"""macOS notifications via terminal-notifier (preferred) or osascript (fallback)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from maintenance.output import TaskResult

logger = logging.getLogger("maintenance")


def notify(
    title: str,
    message: str,
    *,
    subtitle: str = "",
    sound: str = "Submarine",
    activate_bundle_id: str = "",
    open_url: str = "",
) -> bool:
    """Send a macOS notification. Uses terminal-notifier if available, osascript fallback."""
    if shutil.which("terminal-notifier"):
        cmd = ["terminal-notifier", "-title", title, "-message", message, "-group", "maintenance"]
        if subtitle:
            cmd += ["-subtitle", subtitle]
        if sound:
            cmd += ["-sound", sound]
        if activate_bundle_id:
            cmd += ["-activate", activate_bundle_id]
        if open_url:
            cmd += ["-open", open_url]
        try:
            subprocess.run(cmd, timeout=5, capture_output=True, stdin=subprocess.DEVNULL)
            return True
        except Exception:
            logger.debug("terminal-notifier failed, trying osascript")

    # osascript fallback
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


def detect_terminal_bundle_id() -> str:
    """Detect the current terminal app's bundle ID for notification click activation."""
    cmux_id = os.environ.get("CMUX_BUNDLE_ID")
    if cmux_id:
        return cmux_id
    ghostty_plist = Path("/Applications/Ghostty.app/Contents/Info.plist")
    if ghostty_plist.is_file():
        try:
            result = subprocess.run(
                ["defaults", "read", str(ghostty_plist), "CFBundleIdentifier"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
    return "com.apple.Terminal"


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
