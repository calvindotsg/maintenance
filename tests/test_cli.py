"""Tests for CLI commands."""

from __future__ import annotations

from typer.testing import CliRunner

from maintenance.cli import app

runner = CliRunner()


def test_help_exits_zero():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "maintenance" in result.output.lower()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0


def test_setup_outputs_sudoers():
    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 0
    assert "NOPASSWD" in result.output
    assert "env_keep" in result.output
    assert "mo clean" in result.output
    assert "mo optimize" in result.output


def test_run_dry_run():
    result = runner.invoke(app, ["run", "--dry-run"])
    assert result.exit_code == 0
