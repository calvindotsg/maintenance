"""Tests for macOS notifications."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from maintenance.notify import format_summary, notify
from maintenance.output import TaskResult


def test_notify_sends_osascript():
    with patch("maintenance.notify.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = notify("Title", "Message")
    assert result is True
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "/usr/bin/osascript"
    script = cmd[2]
    assert "display notification" in script
    assert '"Message"' in script
    assert '"Title"' in script


def test_notify_includes_subtitle():
    with patch("maintenance.notify.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        notify("T", "M", subtitle="sub")
    script = mock_run.call_args[0][0][2]
    assert "subtitle" in script
    assert '"sub"' in script


def test_notify_includes_sound():
    with patch("maintenance.notify.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        notify("T", "M", sound="Glass")
    script = mock_run.call_args[0][0][2]
    assert "sound name" in script
    assert '"Glass"' in script


def test_notify_omits_sound_when_empty():
    with patch("maintenance.notify.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        notify("T", "M", sound="")
    script = mock_run.call_args[0][0][2]
    assert "sound name" not in script


def test_notify_returns_false_on_exception():
    with patch("maintenance.notify.subprocess.run", side_effect=Exception("fail")):
        result = notify("T", "M")
    assert result is False


def test_notify_returns_false_on_timeout():
    import subprocess
    err = subprocess.TimeoutExpired(cmd="osascript", timeout=5)
    with patch("maintenance.notify.subprocess.run", side_effect=err):
        result = notify("T", "M")
    assert result is False


def test_format_summary_all_ok():
    results = [TaskResult("gcloud", "ok", duration=2.0), TaskResult("pnpm", "ok", duration=1.0)]
    title, message, subtitle = format_summary(results)
    assert title == "Maintenance complete"
    assert "2 ran" in message
    assert subtitle == ""


def test_format_summary_mixed():
    results = [
        TaskResult("gcloud", "ok"),
        TaskResult("uv", "skipped", reason="not installed"),
    ]
    title, message, subtitle = format_summary(results)
    assert title == "Maintenance complete"
    assert "1 ran" in message
    assert "1 skipped" in message


def test_format_summary_with_failure():
    results = [
        TaskResult("gcloud", "ok"),
        TaskResult("mo_clean", "failed", reason="exit code 1"),
        TaskResult("uv", "skipped", reason="not installed"),
    ]
    title, message, subtitle = format_summary(results)
    assert "1 failed" in title
    assert "1 ran" in message
    assert "mo_clean" in subtitle


def test_format_summary_excludes_dry_run_from_ok():
    results = [TaskResult("gcloud", "ok", reason="dry-run")]
    title, message, subtitle = format_summary(results)
    assert "No tasks ran" in message
