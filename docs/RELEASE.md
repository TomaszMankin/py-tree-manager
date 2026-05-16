# Release process

py-tree-manager builds and distributes via **GitHub Actions** and **GitHub Releases**.
Source-of-truth repo: `https://github.com/TomaszMankin/py-tree-manager` (public).

## Routine flow (every merge to `main`)

1. `.github/workflows/release.yml` fires on push to `main`.
2. The `install-and-test` job runs `pytest` (skipped if the head commit message contains `[skip ci]`).
3. The `build-and-release` job:
   - Runs `.pipelines/ci/bump-version.ps1`, which patch-bumps `pyproject.toml`
     (X.Y.Z → X.Y.Z+1), commits with `[skip ci]`, tags `vX.Y.Z+1`, and pushes
     both commit and tag back to `origin/main`.
   - Runs PyInstaller (`--onefile --windowed --copy-metadata --add-data update.bat`).
   - Renames the artifact to `dist/py-tree-manager-X.Y.Z+1.exe`.
   - Publishes a GitHub Release tagged `vX.Y.Z+1` with the `.exe` as an asset,
     marked `--latest`.
4. The bump-commit push re-triggers `release.yml`, but the `install-and-test`
   gate short-circuits on the `[skip ci]` marker, so the workflow is a no-op.
   No infinite loop.
5. The in-app updater on the father's machine polls
   `https://api.github.com/repos/TomaszMankin/py-tree-manager/releases/latest`
   on next launch, sees the new `tag_name`, prompts in Polish, downloads the
   asset, runs `update.bat`, exits, and re-launches the new version.

## Pull request builds

Every push to a PR branch triggers `.github/workflows/pr-build.yml`:

- Runs `pytest`.
- Derives a per-commit version string: `<base>-pr-<pr-num>-<sha7>`.
- Builds the `.exe` with that version embedded.
- Publishes a GitHub Release tagged `v<base>-pr-<pr-num>-<sha7>` with
  `--prerelease`.

Prereleases are excluded from `/releases/latest` by GitHub, so the in-app
updater never offers them. Manual download from the Releases page only.

The PR build also triggers `.github/workflows/pii-check.yml`, which scans the
working tree for stale Bitbucket references, hardcoded personal paths, and
process breadcrumbs that should not ship to a public repo. Fails the PR if any
match.

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
collaborators" → **Require approval for all outside collaborators**. This
prevents fork PRs from running code on the self-hosted runner without an
explicit approval step.

### 3. Confirm pwsh 7 is installed on the runner machine

```powershell
pwsh --version
```

If missing: `winget install Microsoft.PowerShell`. GitHub Actions defaults
the shell to pwsh 7 on Windows runners when available.

### 4. First-time install on the father's machine

After the first successful `release.yml` run on `main`:

1. Download `py-tree-manager-X.Y.Z.exe` from the Releases page.
2. Copy to a **writable** folder on the father's machine — Desktop or
   `Documents`, NOT `C:\Program Files\`. UAC blocks the `move /Y` in
   `update.bat` if the `.exe` lives in a protected folder.
3. Add the folder to the antivirus exclusion list (some AV products flag the
   self-replace pattern as ransomware-adjacent). On Windows Defender:
   Settings → Virus & threat protection → Manage settings → Add or remove
   exclusions → Add a folder.
4. Double-click to launch. The bundled `update.bat` extracts to the same
   folder on first run. From then on every launch auto-checks for updates.

## Manual minor or major bump

Patch is auto-bumped on every merge. For a deliberate minor/major bump, edit
`pyproject.toml` on a feature branch:

```toml
version = "1.1.0"
```

Merge. The pipeline then patch-bumps to `1.1.1` and publishes that. If you
want `1.1.0` as the exact released version, bump to `1.0.999` (or whatever
the predecessor is) just before merging — patch bump produces `1.1.0`.

## Hot-fixing a broken release

Bump `pyproject.toml` manually on a feature branch, merge. Next auto-bump
increments from your manual version.

## Skipping CI on an emergency push

Include `[skip ci]` in the commit message.

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
| `release.yml` fires twice on a merge | `[skip ci]` token missing from the bump commit | Inspect the bump commit message; should contain `[skip ci]` literally |
| `.exe` shows version `0.0.0` in the About dialog | `pip install -e .[dev]` did not run before PyInstaller | Check workflow log; the "Install dependencies (post-bump)" step is required |
| Father's app prompts repeatedly for the same version | `skipped_update_version` was not saved | Check `<root>/.PyTreeManager/settings.json` for the key after declining |
| App starts but no update prompt despite a newer release | Network error (offline, GitHub unreachable) | Expected — offline = silent skip per design |
| `update.bat` exits with code 1 after 30 retries | UAC + `.exe` in a write-protected folder | Move the `.exe` to a personal folder (Desktop, Documents) |
| Self-hosted runner is offline | Laptop is off | Power on; the workflow queue resumes |
| PII check fails on a PR | A scan pattern matched against changed files | See `.pipelines/ci/pii-check.ps1`. Either fix the offending content or update the script's exclusion list |
