"""Tests for task execution."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from maintenance.config import Config
from maintenance.tasks import run_task, strip_ansi


def test_strip_ansi_removes_color_codes():
    assert strip_ansi("\x1b[0;32m✓\x1b[0m test") == "✓ test"


def test_strip_ansi_preserves_plain_text():
    assert strip_ansi("no colors here") == "no colors here"


def test_run_task_skips_disabled():
    config = Config()
    config.tasks["gcloud"] = False
    result = run_task("gcloud", ["gcloud", "update"], config=config)
    assert result is False


@patch("maintenance.tasks.shutil.which", return_value=None)
def test_run_task_skips_missing_command(mock_which):
    config = Config()
    result = run_task("gcloud", ["gcloud", "update"], config=config)
    assert result is False


def test_run_task_dry_run_does_not_execute():
    config = Config()
    with patch("maintenance.tasks.shutil.which", return_value="/usr/bin/gcloud"):
        result = run_task("gcloud", ["gcloud", "update"], config=config, dry_run=True)
    assert result is True


@patch("maintenance.tasks.subprocess.run")
@patch("maintenance.tasks.shutil.which", return_value="/usr/bin/echo")
def test_run_task_executes_command(mock_which, mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="done", stderr="")
    config = Config()
    result = run_task("gcloud", ["echo", "test"], config=config)
    assert result is True
    mock_run.assert_called_once()
