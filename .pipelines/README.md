# .pipelines/

CI and release scaffolding for py-tree-manager. GitHub Actions runs from a
self-hosted Windows runner; everything in here either runs on the runner or
ships inside the built `.exe`.

## Layout

| Path                          | Purpose                                                                |
|-------------------------------|------------------------------------------------------------------------|
| `ci/bump-version.ps1`         | Patch-bump pyproject.toml, commit `[skip ci]`, tag, push to origin.    |
| `ci/rename-artifact.ps1`      | Rename PyInstaller output to versioned filename.                       |
| `ci/pii-check.ps1`            | Scan tracked files for personal data + stale references on every PR.   |
| `update.bat`                  | Self-replace helper bundled into the `.exe` via PyInstaller `--add-data`. |
| `local-runner-schema.yaml`    | Self-hosted runner registration / config reference.                    |

Workflow YAMLs that invoke these scripts live at `.github/workflows/`:

- `pr-build.yml` — builds prerelease `.exe` on every PR
- `release.yml`  — bumps version, builds, publishes GitHub Release on push to `main`
- `pii-check.yml` — runs `pii-check.ps1` on every PR

## Testing the PowerShell scripts locally

### Syntax-only parse check

Surfaces braces, dollar-quote, and pipeline errors without running the body:

```powershell
$errors = $null
[Management.Automation.Language.Parser]::ParseFile(
    '.pipelines/ci/bump-version.ps1', [ref]$null, [ref]$errors)
if ($errors) { $errors | ForEach-Object { Write-Host $_ } }
```

### Run pii-check.ps1 against the working tree

```powershell
.\.pipelines\ci\pii-check.ps1
```

Exits 0 if clean, 1 if any FAIL-group pattern matched. Useful before opening
a PR — same script the CI runs.

### Sacrificial branch

Push to a throwaway branch and open a PR. `pr-build.yml` will produce a
prerelease asset visible at `https://github.com/TomaszMankin/py-tree-manager/releases`
tagged `v<base>-pr-<num>-<sha7>`. `release.yml` only fires on push to `main`
so a feature branch is safe.

For the full release-flow rehearsal see `docs/RELEASE.md`.
