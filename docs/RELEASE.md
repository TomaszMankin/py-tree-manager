# Release process

py-tree-manager builds and distributes via **GitHub Actions** and **GitHub Releases**.
Source-of-truth repo: `https://github.com/TomaszMankin/py-tree-manager` (public).

## Routine flow (every merge to `main`)

1. `.github/workflows/release.yml` fires on push to `main`.
2. The `install-and-test` job runs `pytest`.
3. The `build-and-release` job:
   - Runs `.pipelines/ci/bump-version.ps1`, which reads `pyproject.toml`'s base
     version (`X.Y.Z`) plus existing tags matching `vX.Y.*`. Picks the next
     patch (max-tag-patch + 1, or `Z` if no tag in this line yet). Patches
     `pyproject.toml` in-place — **workflow-local, never committed**.
   - Runs PyInstaller (`--onefile --windowed --copy-metadata --add-data update.bat`).
   - Renames the artifact to `dist/py-tree-manager-X.Y.<resolved>.exe`.
   - `gh release create vX.Y.<resolved> ... --latest --target <merge-sha>` —
     creates the tag and publishes the release. Tags are not gated by the
     main-branch ruleset, so no bypass needed.
4. The in-app updater on the father's machine polls
   `https://api.github.com/repos/TomaszMankin/py-tree-manager/releases/latest`
   on next launch, sees the new `tag_name`, prompts in Polish, downloads the
   asset, runs `update.bat`, exits, and re-launches the new version.

## Pull request builds

Every push to a PR branch triggers `.github/workflows/pr-build.yml`:

- Runs `pytest`.
- Derives a PEP 440-compliant per-commit version: `<base>.dev<pr-num>+<sha7>`
  (e.g. `1.0.0.dev3+a1b2c3d`). `.dev` sorts strictly below the base release.
- Builds the `.exe` with that version embedded.
- Publishes a GitHub Release tagged `v<base>.dev<pr-num>+<sha7>` with `--prerelease`.

Prereleases are excluded from `/releases/latest` by GitHub, so the in-app
updater never offers them. Manual download from the Releases page only.

The PR also triggers `.github/workflows/pii-check.yml`, which scans for stale
Bitbucket references, hardcoded personal paths, process breadcrumbs, and
diagnostic leftovers. Fails the PR if any match.

## One-time setup

### 1. Register the self-hosted runner

Repo → Settings → Actions → Runners → **New self-hosted runner** → Windows.
Follow the PowerShell snippet GitHub provides. Confirm labels include
`self-hosted` and `Windows`. Install as a Windows service so it auto-starts:

```powershell
./svc.cmd install
./svc.cmd start
```

### 2. Enable fork-PR approval gate

Repo → Settings → Actions → General → "Fork pull request workflows from outside
collaborators" → **Require approval for all outside collaborators**.

### 3. Install Python system-wide on the runner machine

The runner service runs as `NT AUTHORITY\NETWORK SERVICE` by default, which
cannot read user-scoped Python installs. Install Python so the service sees it:

```powershell
winget install --id Python.Python.3.11 --scope machine --override "InstallAllUsers=1 PrependPath=1"
Restart-Service "<runner service name>"
```

Confirm with `(Get-Command python).Source` from a fresh shell — should resolve to
`C:\Program Files\Python311\python.exe`.

### 4. First-time install on the father's machine

After the first successful `release.yml` run on `main`:

1. Download `py-tree-manager-X.Y.Z.exe` from the Releases page.
2. Copy to a **writable** folder on the father's machine — Desktop or
   `Documents`, NOT `C:\Program Files\`. UAC blocks the `move /Y` in
   `update.bat` if the `.exe` lives in a protected folder.
3. Add the folder to the antivirus exclusion list (some AV products flag the
   self-replace pattern as ransomware-adjacent).
4. Double-click to launch. The bundled `update.bat` extracts to the same
   folder on first run. From then on every launch auto-checks for updates.

## Installer — first install and migration guide (sprint-20, ADR-018)

### First install via installer (new machines)

Starting with the first release that includes an installer:

1. Download `PyTreeManager-Setup-X.Y.Z.exe` from the Releases page.
2. Double-click — no UAC prompt (per-user install, `PrivilegesRequired=lowest`).
3. App installs to `%LOCALAPPDATA%\Programs\PyTreeManager\PyTreeManager.exe`.
4. A Desktop shortcut and a Start Menu entry are created automatically.
5. Click "Uruchom PyTreeManager" on the final installer screen, or use the Desktop shortcut.
6. On first launch, pick the tree-root folder. A `PyTreeManager.lnk` shortcut is placed in
   the root folder for quick access (frozen/installed mode only).

### Migrating an existing bare-.exe install

If the father already has a bare `py-tree-manager-X.Y.Z.exe` on his Desktop
(pre-installer distribution):

1. Download and run `PyTreeManager-Setup-X.Y.Z.exe`.
2. The installer places the app at the fixed location and creates proper shortcuts.
3. Delete the old bare `.exe` from the Desktop (or wherever it was).
4. Going forward, updates flow automatically via the in-app updater (`update.bat`).
   The Desktop shortcut targets the fixed location, so it stays valid after every update.

### Manual Inno Setup compile (if iscc absent on the runner)

The CI runner must have Inno Setup installed with `iscc.exe` on the System PATH.
If it is missing, `release.yml` will warn and skip the installer step; the raw `.exe`
is still published.

To compile the installer manually on the developer machine:

1. Install Inno Setup 6 from https://jrsoftware.org/isdl.php
2. In a PowerShell terminal:
   ```powershell
   # From the repo root, after PyInstaller has produced dist\PyTreeManager.exe:
   iscc /DMyAppVersion=1.0.5 installer\py-tree-manager.iss
   # Output: installer_output\PyTreeManager-Setup-1.0.5.exe
   ```
3. Upload the resulting installer manually to the GitHub Release if needed.

To install Inno Setup on the self-hosted runner (one-time):

```powershell
winget install --id JRSoftware.InnoSetup --scope machine
# Then restart the runner service so it picks up the updated PATH:
Restart-Service '<runner-service-name>'
```

## Manual minor or major bump

Patch is auto-resolved from existing tags. For a deliberate minor or major
bump, edit `pyproject.toml` on a feature branch:

```toml
version = "1.1.0"
```

Merge. The pipeline sees no existing `v1.1.*` tags, picks `1.1.0` (the
pyproject value) as the first release in this line, then `1.1.1`, `1.1.2`...
on subsequent merges.

## Hot-fixing a broken release

Open a PR with the fix. Merge. The next patch number above the broken release
is auto-resolved and published.

## Rollback

GitHub Releases keeps every published release. To roll back:

1. On `github.com/TomaszMankin/py-tree-manager/releases`, find the older
   release you want to mark as `--latest`.
2. Edit it, check "Set as the latest release", save. The previous "latest" is
   demoted automatically.
3. Father's app polls `/releases/latest` on next launch and offers what the
   `--latest` flag now points to.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `.exe` shows version `0.0.0` in the About dialog | `pip install -e .[dev]` did not run before PyInstaller, or pyproject.toml patch failed | Check workflow log; "Install dependencies (after version patch)" step is required |
| Father's app prompts repeatedly for the same version | `skipped_update_version` was not saved | Check `<root>/.PyTreeManager/settings.json` for the key after declining |
| App starts but no update prompt despite a newer release | Network error (offline, GitHub unreachable) | Expected — offline = silent skip per design |
| `update.bat` exits with code 1 after 30 retries | UAC + `.exe` in a write-protected folder | Move the `.exe` to a personal folder (Desktop, Documents) |
| Self-hosted runner is offline | Laptop is off | Power on; the workflow queue resumes |
| PII check fails on a PR | A scan pattern matched against changed files | Fix the offending content or update `.pipelines/ci/pii-check.ps1` exclusions |
| Release publish fails with "tag already exists" | Tag for the resolved version is already present (e.g. you manually pushed one) | Bump pyproject.toml past the existing tag and re-merge |
