---
id: ADR-012
title: CI pipeline architecture — Windows self-hosted Bitbucket runner, version-bump-on-merge, Bitbucket Downloads distribution
kind: tech
decision_type: architecture
status: superseded-by ADR-015
date: 2026-05-12
author: architect
sprint: sprint-15
supersedes: (none)
superseded_by: ADR-015 (2026-05-17 — hosting + CI moved to GitHub Actions / GitHub Releases)
iterates_with_user: false   # mechanics are user-locked; only label values / variable names may flex
related:
  - ADR-013 (version embedding + in-app update detection; consumes `latest.json` produced by this pipeline)
  - ADR-014 (self-replace update_helper mechanism; ships the `.bat` helper this pipeline bundles into `dist/`)
  - PRD-007 (release engineering umbrella; this ADR resolves Stream B + part of Stream C against the user-locked decisions captured in the Sprint 15 dispatch)
sources:
  - JOURNAL 2026-05-12 — user-locked decisions block in Sprint 15 dispatch (Windows self-hosted runner; Bitbucket Downloads on public repo; auto-patch-bump on merge to main; pyproject.toml = source of truth at 1.0.0; no embedded credentials)
  - https://support.atlassian.com/bitbucket-cloud/docs/set-up-runners-for-windows/ — Windows runner prerequisites (OpenJDK 11, Git 2.35+, PowerShell 5+, Windows 10+ / Server 2019+, 8 GB RAM; runs in PowerShell directly, no Docker)
  - https://support.atlassian.com/bitbucket-cloud/docs/configure-your-runner-in-bitbucket-pipelines-yml/ — `runs-on: ['self.hosted', 'windows']` is mandatory; omitting `windows` makes the scheduler assume Linux Docker
  - https://support.atlassian.com/bitbucket-cloud/kb/how-to-write-push-commits-to-a-repository-from-a-windows-runner/ — OAuth client_credentials + `git remote set-url origin "https://x-token-auth:$token@bitbucket.org/..."` is the documented pattern for committing back from a Windows runner; `[skip ci]` in commit message prevents recursion
  - https://developer.atlassian.com/cloud/bitbucket/rest/api-group-downloads/ — `POST /2.0/repositories/{workspace}/{slug}/downloads` with `-F files=@filename`; same-name upload overwrites (community-confirmed pattern at https://community.atlassian.com/forums/Bitbucket-questions/Bitbucket-REST-API-Post-File-Something-went-wrong/qaq-p/2135007)
  - https://support.atlassian.com/bitbucket-cloud/docs/app-password-permissions/ — `repository:write` scope required for git push; alternative is a Repository Access Token (more granular, recommended for CI)
  - https://support.atlassian.com/bitbucket-cloud/kb/bitbucket-cloud-pipelines-set-up-runners-for-windows-as-a-windows-service/ — runner-as-service is third-party (WinSW / NSSM); the user is handling this out-of-band per dispatch
  - .gitignore line 36 (`.pipelines/` already excluded — distinct from `.pipeline/` agent state)
---

# ADR-012 — CI pipeline architecture (Windows self-hosted runner, auto-version-bump, Bitbucket Downloads)

> This ADR resolves Stream B + part of Stream C of PRD-007 against the
> user-locked decisions captured in the Sprint 15 dispatch JOURNAL entry
> (2026-05-12). All five locked decisions are treated as inputs, not
> options.

## 0. Changelog

- **2026-05-12 (initial)** — first issue. Five user-locked decisions
  taken as inputs (Windows self-hosted runner; Bitbucket Downloads on
  public repo; auto-patch-bump on merge to main; pyproject.toml source
  of truth at 1.0.0; no embedded credentials).

## 1. Context

The app must reach Tomasz's father's machine without manual file
transfer. Sprint 13 Phase B (deferred from PRD-007) is the path of
least resistance: CI builds a `.exe`, hosts it on a publicly-readable
URL, the running app on the father's machine fetches a small JSON
manifest, prompts on a new version, and self-replaces.

Two questions had to close before this ADR could write itself:

1. **Where does the CI run?** Bitbucket Cloud's hosted runners are
   Linux-only for the free tier and would require `pywin32` stubs +
   no real PyInstaller-on-Windows verification. The user has reconfigured
   his Docker-based Linux runner to a **Windows-native self-hosted
   runner** (installed as a Windows service via third-party wrapper —
   out of this ADR's scope; user handles operationally).
2. **Where does the binary live?** The user picked **Bitbucket Downloads
   on the same repo** and made the repo **public** for anonymous-readable
   downloads from his father's machine. No second repo. No embedded
   credentials in the `.exe`.

This ADR specifies the pipeline structure, the auto-version-bump
mechanism, the Downloads upload sequence, and the secret-handling
boundary. It does NOT specify: the `.exe` runtime's version-detection
logic (ADR-013) or the self-replace mechanism (ADR-014).

## 2. Decision

A single `bitbucket-pipelines.yml` at repo root. Two pipeline trees:

- **`pipelines.default`** — every commit on any branch except `main`.
  Three steps: install, test, validation-build. Artifact discarded.
- **`pipelines.branches.main`** — only on merge to `main`. Five steps:
  install, test, version-bump-and-tag, build, upload-to-downloads.

Both run on `runs-on: ['self.hosted', 'windows']` per the Atlassian
docs at the runner-config URL in `sources:`.

### 2.1 Pipeline yaml structure (high-level)

```yaml
image: atlassian/default-image:3  # ignored on self-hosted runners; harmless to include

definitions:
  steps:
    - step: &install-and-test
        name: Install + test
        runs-on:
          - 'self.hosted'
          - 'windows'
        script:
          - python -m pip install --upgrade pip
          - python -m pip install -r requirements.txt -r requirements-dev.txt
          - python -m pytest

    - step: &validation-build
        name: Validation build (artifact discarded)
        runs-on:
          - 'self.hosted'
          - 'windows'
        script:
          - python -m pip install pyinstaller
          - python -m PyInstaller --onefile --windowed --name py-tree-manager --copy-metadata py-tree-manager main.py

pipelines:
  default:
    - step: *install-and-test
    - step: *validation-build

  branches:
    main:
      - step: *install-and-test
      - step:
          name: Bump version, tag, build, upload
          runs-on:
            - 'self.hosted'
            - 'windows'
          script:
            - powershell -ExecutionPolicy Bypass -File .pipelines/ci/bump-version.ps1
            - python -m pip install pyinstaller
            - python -m PyInstaller --onefile --windowed --name py-tree-manager --copy-metadata py-tree-manager main.py
            - powershell -ExecutionPolicy Bypass -File .pipelines/ci/rename-artifact.ps1
            - powershell -ExecutionPolicy Bypass -File .pipelines/ci/upload-downloads.ps1
```

Two design notes on the YAML:

- **YAML anchors (`&install-and-test`, `*install-and-test`)** dedupe
  the install+test step between default and main pipelines. The same
  step runs on every branch including main; on main, the extra steps
  follow.
- **`atlassian/default-image:3`** is set at top-level for completeness
  but is ignored by self-hosted runners (which use the host PowerShell
  directly per the runner-docs URL). Documented to prevent a reviewer
  thinking it's load-bearing.

### 2.2 Pipeline variables (set in Repository Settings → Pipelines → Repository variables)

| Name | Scope | Used by | Notes |
|---|---|---|---|
| `BITBUCKET_BOT_CLIENT_ID` | Secured | `.pipelines/ci/bump-version.ps1` (git push); `.pipelines/ci/upload-downloads.ps1` (auth) | OAuth consumer Client ID. Created in Workspace settings → OAuth consumers, scoped to `repository:write` + `repository:admin` (admin needed for Downloads write per the Atlassian app-password docs URL). |
| `BITBUCKET_BOT_CLIENT_SECRET` | Secured | same | OAuth consumer secret. |
| `BITBUCKET_REPO_OWNER` | Built-in | scripts | Bitbucket-injected: `Duch003`. |
| `BITBUCKET_REPO_SLUG` | Built-in | scripts | Bitbucket-injected: `py-tree-manager`. |
| `BITBUCKET_COMMIT` | Built-in | scripts (optional, for the release commit body) | Bitbucket-injected. |

**Why OAuth client_credentials and not a personal app password**: the
referenced Atlassian KB article for "write/push commits from a Windows
runner" uses the OAuth client_credentials grant pattern directly; it
yields a short-lived bearer token via the
`https://bitbucket.org/site/oauth2/access_token` endpoint, and that
same token works for both `git push` and the Downloads REST API.
Repository Access Tokens are also valid; the user can switch by
swapping which variable is set without touching the YAML.

### 2.3 The three PowerShell helpers (under `.pipelines/ci/`)

To keep the YAML readable and to make the pipeline locally rehearsable
(Tomasz can run any of these scripts in a PowerShell prompt against a
local clone), the three main-only steps are extracted into scripts at
`.pipelines/ci/`:

**`.pipelines/ci/bump-version.ps1`** — steps 6 + 7 of the dispatch's spec:

1. Read `[project] version = "..."` from `pyproject.toml` via a tiny regex
   (no `tomllib` parsing needed — the field is single-line by convention).
2. Split into `major.minor.patch`. Increment `patch`.
3. Write back. Verify by re-reading.
4. Acquire OAuth bearer token (see §2.4 below).
5. `git config user.name "Bitbucket Pipelines"`
6. `git config user.email "bitbucket-pipelines@bitbucket.org"`
7. `git remote set-url origin "https://x-token-auth:$token@bitbucket.org/$env:BITBUCKET_REPO_OWNER/$env:BITBUCKET_REPO_SLUG.git"`
8. `git add pyproject.toml`
9. `git commit -m "chore(release): bump version to $newVersion [skip ci]"`
   — the `[skip ci]` token prevents the pipeline from triggering itself
   (Bitbucket honors this token; verified via the Atlassian push-back KB URL).
10. `git tag "v$newVersion"`
11. `git push origin HEAD:main`
12. `git push origin "v$newVersion"`
13. Write `$newVersion` to `.pipelines/ci/.version-bumped-to` so the next step can read it
    without re-parsing `pyproject.toml`.

**`.pipelines/ci/rename-artifact.ps1`** — step 8 of dispatch's spec:

1. Read `.pipelines/ci/.version-bumped-to`.
2. `Move-Item dist\py-tree-manager.exe dist\py-tree-manager-$version.exe`
3. Write `dist\latest.json` (schema in ADR-013 §3).

**`.pipelines/ci/upload-downloads.ps1`** — step 9 of dispatch's spec:

1. Read version.
2. Acquire bearer token (same OAuth flow as `bump-version.ps1`).
3. `Invoke-RestMethod -Method Post -Uri "https://api.bitbucket.org/2.0/repositories/$env:BITBUCKET_REPO_OWNER/$env:BITBUCKET_REPO_SLUG/downloads" -Headers @{ Authorization = "Bearer $token" } -Form @{ files = Get-Item "dist\py-tree-manager-$version.exe" }`
4. Same call with `files = Get-Item "dist\latest.json"`.
5. On 200/201, log success; on non-2xx, fail the pipeline.

**Why two POSTs not one**: `multipart/form-data` supports multiple
files in one request, but `Invoke-RestMethod -Form` in PowerShell 5+
serializes one file per call. Two requests is simpler and the failure
mode (one upload succeeds, the other doesn't) is acceptable: the next
merge-to-main re-uploads `latest.json` either way.

### 2.4 OAuth bearer-token acquisition (shared snippet)

Both `bump-version.ps1` and `upload-downloads.ps1` need this. Sourced
verbatim from the Atlassian push-back KB URL in `sources:`:

```powershell
function Get-BitbucketBearerToken {
    $body = @{ "grant_type" = "client_credentials" }
    $authHeader = 'Basic ' + [Convert]::ToBase64String(
        [Text.Encoding]::ASCII.GetBytes("$($env:BITBUCKET_BOT_CLIENT_ID):$($env:BITBUCKET_BOT_CLIENT_SECRET)")
    )
    $response = Invoke-RestMethod `
        -Uri 'https://bitbucket.org/site/oauth2/access_token' `
        -Method Post `
        -Body $body `
        -Headers @{ Authorization = $authHeader }
    return $response.access_token
}
```

The token lifetime is ~2 hours (per the Atlassian OAuth docs at the
push-back KB URL), so acquiring a fresh token per pipeline step is
safe.

### 2.5 Distribution layout on Bitbucket Downloads

After the first main-pipeline run, the Downloads area at
`https://bitbucket.org/Duch003/py-tree-manager/downloads/` contains:

```
py-tree-manager-1.0.1.exe       <-- versioned, accumulates over time
latest.json                     <-- overwritten on each release
```

After ten releases, it contains ten `.exe` files plus one `latest.json`.
**The accumulation is intentional**: the user (or a future Tomasz)
can roll back manually by editing `latest.json.download_url` to point at
an older versioned `.exe`. ADR-013 reads the URL out of `latest.json`,
not by string-templating from `latest_version` — so older builds remain
reachable without a code change.

The first release's manual upload (`py-tree-manager-1.0.0.exe`) is a
one-time Sprint 15 task done by Tomasz from his dev box; the pipeline
takes over from `1.0.1` onward.

## 3. Worked example — first commit → first merge → second release

Assume current `pyproject.toml`:

```toml
[project]
name = "py-tree-manager"
version = "1.0.0"
```

**Day 1 — Tomasz pushes a feature branch `feat/some-fix`**:

- `pipelines.default` fires.
- Step 1: `pip install` succeeds.
- Step 2: `pytest` runs, 210+ tests green. Halt-A baseline preserved.
- Step 3: PyInstaller builds `dist\py-tree-manager.exe`. Artifact discarded
  (no Downloads write). Build success is the only success signal.

**Day 1 — Tomasz merges `feat/some-fix` to `main`**:

- `pipelines.branches.main` fires.
- Steps 1-2: identical to default.
- Step 3 (`bump-version.ps1`): reads `1.0.0`, increments to `1.0.1`,
  writes back, commits with `[skip ci]`, tags `v1.0.1`, pushes both.
  The `[skip ci]` token in the commit prevents the push from
  re-triggering the pipeline (would otherwise infinite-loop).
- Step 4 (`PyInstaller`): builds `dist\py-tree-manager.exe`.
- Step 5 (`rename-artifact.ps1`): renames to
  `dist\py-tree-manager-1.0.1.exe`, writes `dist\latest.json`:
  ```json
  {
    "latest_version": "1.0.1",
    "download_url": "https://bitbucket.org/Duch003/py-tree-manager/downloads/py-tree-manager-1.0.1.exe",
    "released_at": "2026-05-13T14:32:00Z",
    "min_supported_version": "1.0.0"
  }
  ```
- Step 6 (`upload-downloads.ps1`): two POSTs to the Downloads endpoint.
  Both succeed.

**Day 1 — father's machine, app already running version `1.0.0`**:

- (Out of this ADR's scope — see ADR-013 §4.) On next launch the app
  fetches `latest.json`, compares `1.0.1 > 1.0.0`, prompts, downloads
  `py-tree-manager-1.0.1.exe`, ADR-014 takes over.

## 4. Code touch list

| File | Action |
|---|---|
| `bitbucket-pipelines.yml` | NEW. ~50 LOC. |
| `.pipelines/ci/bump-version.ps1` | NEW. ~70 LOC. |
| `.pipelines/ci/rename-artifact.ps1` | NEW. ~30 LOC (writes `latest.json` — schema delegated to ADR-013 §3). |
| `.pipelines/ci/upload-downloads.ps1` | NEW. ~40 LOC. |
| `pyproject.toml` | NEW. Minimal: `[project] name = "py-tree-manager" version = "1.0.0"` plus `[build-system] requires = ["setuptools>=68"] build-backend = "setuptools.build_meta"` and a `requires-python = ">=3.11"`. ~20 LOC. |
| `requirements.txt` | EXTEND. Add `packaging>=23.0` (for `packaging.version.parse` — robust semver compare per ADR-013 §3.4). |
| `requirements-dev.txt` | EXTEND. Add `pyinstaller>=6.0`. |
| `.gitignore` | EXTEND. Add `dist/` (already there at line 7 — no-op verified) and `.pipelines/ci/.version-bumped-to`. |
| `docs/decisions/INDEX.md` | EXTEND. Add ADR-012/013/014 rows. |

Total: 5 new files + 3 edits. Estimated ~220 LOC.

## 5. Alternatives considered

### 5.1 Bitbucket Cloud-hosted Linux runner with pywin32 stubs

Free-tier minute limits aside, this would mean:

- `pywin32` is unavailable on Linux; tests would need shims/stubs (Sprint
  03's `tests/conftest.py` already has some, but they're not comprehensive
  for the `shortcut_helper.py` Unicode-clean shortcut creation that
  ADR-001 specifies).
- PyInstaller on Linux produces a Linux ELF, not a Windows `.exe`. Would
  require cross-compilation (Wine + PyInstaller), which is fragile and
  off-mainstream.

Rejected: the user-locked decision explicitly removes this path. Captured
for posterity.

### 5.2 GitHub Actions windows-latest runner instead of Bitbucket self-hosted

Would work technically (free tier: 2000 min/month for public repos,
unlimited for `windows-latest` on public repos with caveats) but requires
migrating the repo from Bitbucket to GitHub, which is out of scope per
PRD-007 §"Decisions revisitable later". Documented as a future option if
the self-hosted runner becomes burdensome.

### 5.3 Separate "releases" repo for the binary

Common GitHub pattern: one repo for source, one for releases (avoids
shipping the .exe binary in the source repo's clone tarball). On
Bitbucket Downloads, the binaries don't pollute clones (they live in
the Downloads area, not under `dist/` in the repo). The two-repo
pattern adds no value here.

Rejected. Single-repo distribution is simpler and the user explicitly
chose it.

### 5.4 GitHub Releases + asset upload (cross-platform tooling like `gh` CLI)

Would require `gh` to be installed on the Windows self-hosted runner.
The Atlassian-native Downloads endpoint is one curl/Invoke-RestMethod
call. The dependency on `gh` is a poor trade for a Bitbucket-hosted
project.

Rejected on Occam.

### 5.5 Tag-triggered pipeline (only build/release on `git tag v*`)

Instead of bumping on every merge to main, the pipeline would only fire
on a manual tag push. This is what most mature OSS projects do. But:

- The user wants every merge to main to produce a downloadable release
  (per the dispatch text: "CI auto-increments the patch on every merge
  to main"). This matches the bridge-app posture: every fix should
  reach the father's machine without ceremony.
- Tag-triggered would re-introduce a manual step ("Tomasz remembers to
  push a tag") that the bridge-app posture explicitly wants to remove.

Rejected per user-locked decision #4.

### 5.6 Version-as-Python-constant (no `pyproject.toml`)

Old-style: `src/__version__.py` with `__version__ = "1.0.0"`, no
pyproject.toml at all. Works for the runtime read, but:

- The user's locked decision #4 names `pyproject.toml` as the source of
  truth.
- PyInstaller's `--copy-metadata` (ADR-013 §3.2) requires the package
  to be installable, which requires `pyproject.toml`.
- `pyproject.toml` is the modern Python packaging standard (PEP 621).

Rejected per user-locked decision #4.

## 6. Risks + halt criteria

### Risk 1 — Pipeline infinite-loop on version bump

The version-bump step pushes a commit to `main`. Without mitigation,
that commit re-triggers `pipelines.branches.main`, which bumps the
version again, etc.

**Mitigation**: `[skip ci]` token in the commit message. Bitbucket
honors this token unconditionally (per the push-back KB URL).
**Halt criterion**: a second main-pipeline run must NOT trigger within
5 minutes of a successful version bump. Verifiable in the Pipelines UI.

### Risk 2 — OAuth credentials leak in pipeline logs

PowerShell's default `Write-Verbose` on `Invoke-RestMethod` could log
the Authorization header. Mitigation: use `-ErrorAction Stop` only
(no `-Verbose`), and never `Write-Host $token`. Implementor's
checklist: grep the helper scripts for `$token` outside the
`Authorization` header context — should be zero hits.

### Risk 3 — Bitbucket Downloads same-name upload behavior

The Atlassian docs at the api-group-downloads URL say POST overwrites
existing files of the same name. This is the behavior `latest.json`
relies on (every release overwrites). If Atlassian changes this
behavior, `latest.json` could either fail-on-conflict (HTTP 409) or
silently accumulate sibling files.

**Mitigation**: if the upload returns non-2xx, the pipeline fails loud
(`Invoke-RestMethod` raises on 4xx/5xx by default). The `.exe` uploads
are versioned filenames so they never collide. **Halt criterion**:
first release rehearsal must confirm `latest.json` is overwritten not
appended.

### Risk 4 — Runner downtime during user push

The user's Windows machine hosts the runner. If it's offline when
Tomasz merges, the pipeline queues per the Atlassian runner docs URL.
The release simply delays until the machine is online. **Not a halt
criterion** — the queue is correct behavior.

### Risk 5 — `pywin32` resolution under PyInstaller

`pywin32==311` registers post-install hooks (`pywin32_postinstall.py`)
that wire up COM registrations. PyInstaller historically has issues
collecting `pythoncom*.dll` and `pywintypes*.dll`. The `--onefile`
flag plus the `--copy-metadata py-tree-manager` flag should suffice
because `pywin32` is also pulled via the package's
`importlib.metadata` graph. **Halt criterion**: the validation build's
resulting `.exe` must launch on a clean Windows VM AND successfully
exercise `shortcut_helper.py` (the only `pywin32`-heavy module). This
is user-smoke, not CI-automated.

### Risk 6 — Pipeline minutes consumed on self-hosted runner

Self-hosted runners do NOT consume Bitbucket Cloud's free-tier build
minutes (per the Atlassian Pipelines pricing docs — runners are billed
separately, and self-hosted is free). **Not a halt criterion**.

## 7. Decisions revisitable later

- **OAuth vs Repository Access Token**: the YAML reads from
  `BITBUCKET_BOT_CLIENT_ID` + `BITBUCKET_BOT_CLIENT_SECRET`. If the user
  prefers a Repository Access Token (more granular, no separate OAuth
  consumer registration), swap which variables are set in Repository
  Settings — no YAML change needed.
- **`[skip ci]` discipline**: if Bitbucket ever removes this token's
  effect, the version-bump push would infinite-loop. Mitigation
  fallback: skip the auto-push entirely; require manual tag-push to
  release. ~30 minutes of refactor.
- **Single `latest.json` vs per-channel manifests** (e.g.,
  `latest-stable.json` + `latest-beta.json`): out of scope. The user
  has one channel. If a beta channel is ever wanted, add a second
  manifest and a second upload step.
- **Code signing**: explicitly out of scope per dispatch's "what you
  must NOT do". SmartScreen warnings on first run accepted.

## 8. Test plan

Tests for this ADR's deliverables are mostly **out-of-band of pytest**
because they exercise the runner + Bitbucket API + git. The test
strategy is:

| Layer | What | How | Where |
|---|---|---|---|
| L0 | `bump-version.ps1` version-parse logic | Pure regex / string-manip; copy-paste the regex into a tiny `tests/ci/test_version_regex.py` that uses Python's `re` to verify it against `1.0.0`, `1.0.10`, `2.5.99`, malformed inputs. | `src/tests/ci/` (new dir) |
| L0 | `latest.json` schema produced by `rename-artifact.ps1` | Run the script in a tmpdir; assert resulting JSON parses + has the four required keys + ISO-8601 timestamp. | `src/tests/ci/test_latest_json_shape.py` |
| L1 | End-to-end main-pipeline run | First release rehearsal: push a no-op commit to main, watch the pipeline. Verify: version bumped 1.0.0 → 1.0.1, tag v1.0.1 exists, `dist/py-tree-manager-1.0.1.exe` uploaded, `latest.json` overwritten. | Manual, documented in `RELEASE.md`. |
| L2 | Pipeline infinite-loop protection | After the version-bump push, watch for 5 minutes — confirm no second pipeline run triggers. | Manual, same release rehearsal. |
| L3 | Father's-machine smoke | `.exe` from Downloads runs on a Windows machine that does NOT have Python installed. | Manual, documented in `RELEASE.md`. |

## 9. Anti-overengineering check

This ADR specs:
- 1 YAML file
- 3 PowerShell scripts (each ~30-70 LOC)
- 1 new `pyproject.toml` (~20 LOC)
- 3 dependency-list edits

That's it. No build-cache machinery, no parallel-step optimization, no
matrix builds, no artifact-promotion gates. The bridge-app posture
applies: simpler is better; this is single-user release engineering.

The only "sophistication" is the YAML anchor pattern (`&install-and-test`
+ `*install-and-test`) to dedupe one step between two pipelines.
Justified by the fact that pytest+install runs on both default AND
main pipelines.

## 10. Sources

(See front-matter `sources:` block. All cited inline in §2 and §5.)
