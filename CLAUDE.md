# CLAUDE.md

## Quick Commands

| Command | Purpose |
|---------|---------|
| `uv sync` | Install dependencies |
| `uv run ruff check src/ tests/` | Lint |
| `uv run ruff format src/ tests/` | Format |
| `uv run pytest` | Run tests |
| `uv run pytest --cov` | Run tests with coverage |
| `uv run maintenance run --dry-run` | Test CLI without side effects |

## Architecture

```
cli.py  → Typer app, subcommand dispatch, signal handling, logging setup
tasks.py → run_task() helper, run_all_tasks() orchestrator, ANSI stripping
config.py → TOML loading (tomllib), env var overrides, Brewfile discovery
```

Entry point: `maintenance.cli:app` (registered in pyproject.toml `[project.scripts]`).

## Key Patterns

- **Auto-detection**: `shutil.which(cmd)` checks if a tool is installed before running. Missing tools are skipped, not errors.
- **Graceful failure**: Each task wrapped in try/except. Individual failures log a warning and continue to the next task. The CLI always exits 0 unless interrupted (130).
- **ANSI stripping**: Mole emits color codes even without TTY. `re.sub(r'\x1b\[[0-9;]*m', '', output)` strips them from captured output.
- **sudo + HOME**: `sudo -n` with full path `$BREW_PREFIX/bin/mo`. Sudoers `env_keep += "HOME"` preserves user's home directory (otherwise `HOME=/var/root` and mole misses user caches).
- **fisher needs `--interactive`**: Fisher uses `$last_pid` for job control which fails in non-interactive shells ([fisher#608](https://github.com/jorgebucaran/fisher/issues/608)).
- **Task ordering**: `brew_bundle` runs last because `mo_clean` internally runs `brew autoremove`. Running bundle cleanup after avoids the [cascading removal bug](https://github.com/homebrew/brew/issues/21350).
- **Brew prefix detection**: `subprocess.run(["brew", "--prefix"])` with architecture fallback. Portable across Apple Silicon and Intel.
- **Missed schedules**: launchd catches up after sleep (coalesced). Powered off → skipped until next Monday.

## Non-Obvious Constraints

- `gcloud-cli` is a Homebrew cask, not a formula — can't be a formula dependency. Auto-detected at runtime.
- `mo_purge` uses permanent `rm -rf` with no age threshold. All matching patterns (node_modules, .venv, target/) in configured scan paths are deleted.
- `mo_optimize` security fixes are auto-skipped in non-TTY contexts (read_key returns QUIT). Safe operations still run.
- NOPASSWD in sudoers bypasses PAM entirely — no interaction with Touch ID (pam_tid) setup.
- `check_touchid` is already whitelisted in mole's optimize whitelist, preventing false positive security fix suggestions.

## Release Process

Automated via release-please:

1. Commit changes using conventional commits, push to main
2. release-please creates a release PR (bumps version in `pyproject.toml`, updates CHANGELOG.md)
3. Merge the release PR → GitHub release + tag created
4. Update `homebrew-tap` formula: compute new sha256, update `Formula/maintenance.rb`
