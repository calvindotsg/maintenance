"""Tests for macOS notifications."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mac_upkeep.notify import detect_terminal_bundle_id, format_summary, notify
from mac_upkeep.output import TaskResult


def test_notify_sends_osascript_when_no_terminal_notifier():
    with (
        patch("mac_upkeep.notify.shutil.which", return_value=None),
        patch("mac_upkeep.notify.subprocess.run") as mock_run,
    ):
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
    with (
        patch("mac_upkeep.notify.shutil.which", return_value=None),
        patch("mac_upkeep.notify.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        notify("T", "M", subtitle="sub")
    script = mock_run.call_args[0][0][2]
    assert "subtitle" in script
    assert '"sub"' in script


def test_notify_includes_sound():
    with (
        patch("mac_upkeep.notify.shutil.which", return_value=None),
        patch("mac_upkeep.notify.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        notify("T", "M", sound="Glass")
    script = mock_run.call_args[0][0][2]
    assert "sound name" in script
    assert '"Glass"' in script


def test_notify_omits_sound_when_empty():
    with (
        patch("mac_upkeep.notify.shutil.which", return_value=None),
        patch("mac_upkeep.notify.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        notify("T", "M", sound="")
    script = mock_run.call_args[0][0][2]
    assert "sound name" not in script


def test_notify_returns_false_on_exception():
    with (
        patch("mac_upkeep.notify.shutil.which", return_value=None),
        patch("mac_upkeep.notify.subprocess.run", side_effect=Exception("fail")),
    ):
        result = notify("T", "M")
    assert result is False


def test_notify_returns_false_on_timeout():
    import subprocess

    err = subprocess.TimeoutExpired(cmd="osascript", timeout=5)
    with (
        patch("mac_upkeep.notify.shutil.which", return_value=None),
        patch("mac_upkeep.notify.subprocess.run", side_effect=err),
    ):
        result = notify("T", "M")
    assert result is False


def test_format_summary_all_ok():
    results = [TaskResult("gcloud", "ok", duration=2.0), TaskResult("pnpm", "ok", duration=1.0)]
    title, message, subtitle = format_summary(results)
    assert title == "mac-upkeep complete"
    assert "2 ran" in message
    assert subtitle == ""


def test_format_summary_mixed():
    results = [
        TaskResult("gcloud", "ok"),
        TaskResult("uv", "skipped", reason="not installed"),
    ]
    title, message, subtitle = format_summary(results)
    assert title == "mac-upkeep complete"
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


# --- terminal-notifier tests ---


def test_notify_uses_terminal_notifier():
    with (
        patch("mac_upkeep.notify.shutil.which", return_value="/usr/local/bin/terminal-notifier"),
        patch("mac_upkeep.notify.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        result = notify(
            "Title",
            "Message",
            activate_bundle_id="com.test.app",
            open_url="file:///tmp/test.log",
        )
    assert result is True
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "terminal-notifier"
    assert "-title" in cmd
    assert "-activate" in cmd
    assert "com.test.app" in cmd
    assert "-open" in cmd
    assert "file:///tmp/test.log" in cmd
    assert "-group" in cmd
    assert "mac-upkeep" in cmd


def test_notify_terminal_notifier_includes_group():
    with (
        patch("mac_upkeep.notify.shutil.which", return_value="/usr/local/bin/terminal-notifier"),
        patch("mac_upkeep.notify.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        notify("T", "M")
    cmd = mock_run.call_args[0][0]
    idx = cmd.index("-group")
    assert cmd[idx + 1] == "mac-upkeep"


def test_notify_falls_back_to_osascript_on_terminal_notifier_failure():
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("terminal-notifier failed")
        return MagicMock(returncode=0)

    with (
        patch("mac_upkeep.notify.shutil.which", return_value="/usr/local/bin/terminal-notifier"),
        patch("mac_upkeep.notify.subprocess.run", side_effect=side_effect),
    ):
        result = notify("T", "M")
    assert result is True
    assert call_count == 2


# --- Bundle ID detection tests ---


def test_detect_bundle_id_cmux(monkeypatch):
    monkeypatch.setenv("CMUX_BUNDLE_ID", "com.cmuxterm.app")
    assert detect_terminal_bundle_id() == "com.cmuxterm.app"


def test_detect_bundle_id_ghostty():
    with (
        patch.dict("os.environ", {}, clear=False),
        patch("mac_upkeep.notify.Path") as mock_path,
        patch("mac_upkeep.notify.subprocess.run") as mock_run,
    ):
        # Remove CMUX_BUNDLE_ID if present
        import os

        os.environ.pop("CMUX_BUNDLE_ID", None)
        mock_path.return_value.is_file.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="com.mitchellh.ghostty\n")
        result = detect_terminal_bundle_id()
    assert result == "com.mitchellh.ghostty"


def test_detect_bundle_id_fallback(monkeypatch):
    monkeypatch.delenv("CMUX_BUNDLE_ID", raising=False)
    with patch("mac_upkeep.notify.Path") as mock_path:
        mock_path.return_value.is_file.return_value = False
        result = detect_terminal_bundle_id()
    assert result == "com.apple.Terminal"
