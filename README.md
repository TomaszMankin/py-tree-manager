# py-tree-manager

A Python/wxPython desktop application for managing a family tree stored as a flat folder structure on Windows. Single-user, Polish UI. This is a bridge app that reads and writes `me.json` files produced by the predecessor C# system, letting the user manage people, relationships, and shortcuts until a future server-backed system is ready.

## Tech stack

- Python 3.10+ (tested on 3.13)
- wxPython 4.x (GUI)
- pywin32 (Windows shell shortcuts via `IShellLinkW`)
- pytest

## Install

```
git clone https://github.com/TomaszMankin/py-tree-manager.git
cd py-tree-manager
python -m venv env
env\Scripts\activate
pip install -e ".[dev]"
```

Dependencies are declared in `pyproject.toml`. `pywin32` is required for `.lnk` shortcut creation; if you see `ModuleNotFoundError: No module named 'win32com'` on first launch, re-run the install.

## Run

```
python main.py
```

On first launch the app will ask for a root folder. Point it at a folder that contains (or will contain) a `Lista osób/` directory.

## Test

```
python -m pytest
```

Tests under `tests/integration/` require real pywin32 and run automatically when it is installed. They are skipped cleanly otherwise. Service and helper tests under `tests/services/`, `tests/helpers/`, `tests/frames/` run in all environments via a `win32com.client` stub.

## On-disk layout once configured

```
<root>/                             User-chosen folder
  Lista osób/<Person>/me.json       Canonical person records
  Drzewo/                           Auto-generated hourglass-selection shortcuts
  Rody/                             Auto-generated surname branch shortcuts
  Poczekalnia/<uuid>.json           Draft persons not yet promoted to the tree
  .PyTreeManager/
    settings.json                   App settings
    logs/YYYY-MM-DD__*.log          Per-day diagnostic logs

%LOCALAPPDATA%\PyTreeManager\
  last_root.txt                     1-line pointer to <root> (only file outside <root>/)
```

See `docs/architecture.md` for the full module map, data flow, and design highlights.

## How to release

Every merge to `main` triggers `.github/workflows/release.yml` which auto-increments the patch version, tags the commit, builds a `.exe`, and publishes a GitHub Release marked as `--latest`. The app self-updates on next launch using the `update.bat` helper.

For the full release flow (self-hosted runner setup, manual minor/major bumps, rollback, AV exclusion advice): see **`docs/RELEASE.md`**.

The pipeline configuration lives in `.github/workflows/` (three workflows: `pr-build.yml`, `release.yml`, `pii-check.yml`). Helper PowerShell scripts are under `.pipelines/ci/`. CI authenticates via the auto-issued `GITHUB_TOKEN` — no PAT or repository secret is required.

## Where to read more

- `docs/architecture.md` — single-page module map + data flow + on-disk layout + design highlights + glossary
- `docs/decisions/INDEX.md` — full ADR index
- `docs/RELEASE.md` — release flow, runner setup, AV-exclusion advice
- `SETUP.md` — email notification configuration (Gmail app password), log file locations, root folder setup
