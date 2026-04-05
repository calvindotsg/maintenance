"""Maintenance task definitions and execution."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from maintenance.config import Config
from maintenance.output import TaskResult

logger = logging.getLogger("maintenance")

ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def get_brew_prefix() -> str:
    """Detect Homebrew prefix (portable: Apple Silicon /opt/homebrew, Intel /usr/local)."""
    brew = shutil.which("brew")
    if brew:
        try:
            result = subprocess.run(
                [brew, "--prefix"], capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
    return "/opt/homebrew" if os.uname().machine == "arm64" else "/usr/local"


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    return ANSI_PATTERN.sub("", text)


def run_task(
    name: str,
    cmd: list[str],
    *,
    config: Config,
    dry_run: bool = False,
    needs_sudo: bool = False,
) -> TaskResult:
    """Execute a maintenance task with auto-detection and graceful failure."""
    task_key = name.lower().replace(" ", "_")

    if not config.is_enabled(task_key):
        logger.info("SKIP: %s (disabled in config)", name)
        return TaskResult(name, "skipped", reason="disabled")

    # Check if the primary command exists
    primary_cmd = cmd[0] if not needs_sudo else cmd[2]  # skip sudo -n
    if not shutil.which(primary_cmd):
        logger.info("SKIP: %s (%s not installed)", name, primary_cmd)
        return TaskResult(name, "skipped", reason="not installed")

    if dry_run:
        logger.info("DRY-RUN: would run %s", name)
        return TaskResult(name, "ok", reason="dry-run")

    logger.info("Running %s...", name)
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        duration = time.monotonic() - start
        output = strip_ansi(result.stdout + result.stderr).strip()
        if output:
            for line in output.splitlines():
                logger.debug("  %s", line)
        if result.returncode != 0:
            logger.warning("%s exited with code %d", name, result.returncode)
            return TaskResult(
                name, "failed", reason=f"exit code {result.returncode}", duration=duration
            )
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        logger.warning("%s timed out after 300s", name)
        return TaskResult(name, "failed", reason="timed out", duration=duration)
    except subprocess.CalledProcessError as e:
        duration = time.monotonic() - start
        logger.warning("%s failed: %s", name, strip_ansi(e.stderr or str(e)))
        return TaskResult(name, "failed", reason=str(e), duration=duration)

    return TaskResult(name, "ok", duration=duration)


def run_all_tasks(*, config: Config, dry_run: bool = False) -> list[TaskResult]:
    """Run all maintenance tasks in order. Returns list of task results."""
    brew_prefix = get_brew_prefix()
    mo_bin = f"{brew_prefix}/bin/mo"
    results: list[TaskResult] = []

    tasks = [
        ("gcloud", ["gcloud", "components", "update", "--quiet"]),
        ("pnpm", ["pnpm", "store", "prune"]),
        ("uv", ["uv", "cache", "prune"]),
        # --interactive: fisher needs job control (jorgebucaran/fisher#608)
        ("fisher", ["fish", "--interactive", "-c", "fisher update"]),
    ]

    for name, cmd in tasks:
        results.append(run_task(name, cmd, config=config, dry_run=dry_run))

    # sudo tasks: env_keep in sudoers preserves HOME (not /var/root)
    sudo_tasks = [
        ("mo_clean", [mo_bin, "clean"]),
        ("mo_optimize", [mo_bin, "optimize"]),
    ]
    for name, cmd in sudo_tasks:
        results.append(
            run_task(
                name,
                ["sudo", "-n"] + cmd,
                config=config,
                dry_run=dry_run,
                needs_sudo=True,
            )
        )

    # mo purge: no sudo, permanent rm -rf, no age threshold
    results.append(run_task("mo_purge", [mo_bin, "purge"], config=config, dry_run=dry_run))

    # brew bundle cleanup: runs last (mo clean runs autoremove — homebrew/brew#21350)
    if config.is_enabled("brew_bundle"):
        if not config.brewfile or not Path(config.brewfile).is_file():
            logger.info("SKIP: brew_bundle (no Brewfile found)")
            results.append(TaskResult("brew_bundle", "skipped", reason="no Brewfile found"))
        elif dry_run:
            logger.info("DRY-RUN: would run brew_bundle")
            results.append(TaskResult("brew_bundle", "ok", reason="dry-run"))
        else:
            results.append(
                run_task(
                    "brew_bundle",
                    ["brew", "bundle", "cleanup", "--force", f"--file={config.brewfile}"],
                    config=config,
                    dry_run=False,
                )
            )
    else:
        logger.info("SKIP: brew_bundle (disabled in config)")
        results.append(TaskResult("brew_bundle", "skipped", reason="disabled"))

    return results
