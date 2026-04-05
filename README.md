# maintenance

Automated macOS maintenance CLI. Runs weekly via `brew services` to keep your dev environment clean.

## Install

```bash
brew install calvindotsg/tap/maintenance
brew services start maintenance  # Monday 12 PM weekly
```

## Tasks

| Task | What it does |
|------|-------------|
| gcloud | Update Google Cloud SDK components |
| pnpm | Remove unreferenced packages from content-addressable store |
| uv | Remove unused Python package cache entries |
| fisher | Update Fish shell plugins |
| mo_clean | Remove system/user caches, logs, dev tool caches (sudo) |
| mo_optimize | DNS, Spotlight, LaunchServices, fonts, Dock, Bluetooth (sudo) |
| mo_purge | Remove old project artifacts: node_modules, .venv, target/ |
| brew_bundle | Remove packages not listed in Brewfile |

Tasks auto-detect installed tools. Missing tools are skipped.

## Usage

```bash
maintenance run              # Run all tasks
maintenance run --dry-run    # Preview without executing
maintenance run --debug      # Verbose output
maintenance setup            # Print sudoers rules for this machine
maintenance status           # Show brew service status
maintenance logs             # View last 20 log lines
maintenance logs -f          # Follow logs
maintenance --version        # Show version
```

## Configuration

Copy the example config:

```bash
mkdir -p ~/.config/maintenance
cp "$(brew --prefix)/share/maintenance/config.example.toml" ~/.config/maintenance/config.toml
```

All tasks default to enabled. Set any to `false` to disable:

```toml
[tasks]
gcloud = false       # Skip gcloud updates
mo_optimize = false  # Skip system optimization

[paths]
brewfile = "~/.config/Brewfile"
```

Environment variables override the config file:

```bash
MAINTENANCE_GCLOUD=false maintenance run
```

| Variable | Default | Description |
|----------|---------|-------------|
| `MAINTENANCE_GCLOUD` | `true` | Update gcloud components |
| `MAINTENANCE_PNPM` | `true` | Prune pnpm store |
| `MAINTENANCE_UV` | `true` | Prune uv cache |
| `MAINTENANCE_FISHER` | `true` | Update Fish plugins |
| `MAINTENANCE_MO_CLEAN` | `true` | Clean caches (requires sudo) |
| `MAINTENANCE_MO_OPTIMIZE` | `true` | Optimize macOS (requires sudo) |
| `MAINTENANCE_MO_PURGE` | `true` | Remove project artifacts |
| `MAINTENANCE_BREW_BUNDLE` | `true` | Brewfile cleanup |
| `MAINTENANCE_BREWFILE` | auto-detect | Path to Brewfile |

## Prerequisites

`mo_clean` and `mo_optimize` require passwordless sudo for the `mo` binary:

```bash
maintenance setup | sudo tee /etc/sudoers.d/maintenance && sudo chmod 0440 /etc/sudoers.d/maintenance
sudo visudo -c
```

## License

MIT
