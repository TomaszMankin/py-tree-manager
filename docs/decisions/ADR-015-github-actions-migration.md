---
id: ADR-015
title: Migrate hosting + CI from Bitbucket Pipelines to GitHub Actions + GitHub Releases
kind: tech
decision_type: architecture
status: accepted
date: 2026-05-17
author: architect
supersedes: ADR-012
amends: ADR-013
related:
  - ADR-012 (CI pipeline — Bitbucket-era, fully superseded)
  - ADR-013 (in-app update detection — URL + JSON shape redefined here)
  - ADR-014 (self-replace updater mechanism — fully preserved)
sources:
  - https://docs.github.com/en/rest/releases/releases — GitHub Releases REST API schema (tag_name, name, body, draft, prerelease, published_at, assets[])
  - https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token — permissions block for contents:write
  - https://cli.github.com/manual/gh_release_create — gh release create flags including --prerelease, --latest, --target
  - https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency — workflow concurrency cancel-in-progress
  - https://docs.github.com/actions/security-guides/automatic-token-authentication — GITHUB_TOKEN auto-issuance + scope semantics
---

# ADR-015 — Migrate hosting + CI from Bitbucket to GitHub Actions + GitHub Releases

## 0. Changelog

- **2026-05-17 (initial)** — supersedes ADR-012 entirely; amends ADR-013 URL + JSON parsing.

## 1. Context

Bitbucket Cloud's Free plan paywalls the Downloads REST API: any `POST /2.0/repositories/{slug}/downloads` from a Free workspace returns HTTP 402 "A workspace on a Free plan does not support uploading or downloading files." This was discovered after Sprint 15 shipped with a fully working Windows self-hosted Bitbucket runner, version-bump pipeline, and PyInstaller `.exe` build — only the binary distribution leg was paywalled.

Four practical options were evaluated:
1. Upgrade Bitbucket to a paid plan — recurring cost for a zero-revenue family-tree app; rejected on cost.
2. Keep source on Bitbucket, host binaries on GitHub Releases (split-host) — adds a second account + token, two control planes.
3. Keep source on Bitbucket, host binaries on Cloudflare R2 / Backblaze B2 — adds a third service, no integration with the source repo.
4. Migrate source + CI + binaries to GitHub — single ecosystem, all free, but loses Bitbucket private-repo posture.

The user chose option 4 on 2026-05-17. Fresh-start migration (no git history transferred); the Bitbucket repository remains as a private historical archive.

## 2. Decision

GitHub Releases for binary hosting, GitHub Actions for CI, both at `https://github.com/TomaszMankin/py-tree-manager` (public, fresh repo).

### 2.1 Two workflow files

- `.github/workflows/pr-build.yml` — `pull_request` event. Builds the `.exe`, publishes as a **prerelease** with `--prerelease` flag and version tag `v<base>-pr-<num>-<sha7>`. Concurrency-cancels previous runs on the same PR. Invisible to `/releases/latest`.
- `.github/workflows/release.yml` — `push` to `main` (gated by `if: !contains(github.event.head_commit.message, '[skip ci]')`). Bumps `pyproject.toml` patch version, commits with `[skip ci]`, tags `vX.Y.Z+1`, pushes commit + tag, builds the `.exe`, publishes as the **latest** release with `--latest`.

Two files rather than one with conditionals: per user preference, each YAML stays short and per-concern.

### 2.2 GITHUB_TOKEN auto-issuance

Every workflow run receives `GITHUB_TOKEN` automatically (`${{ secrets.GITHUB_TOKEN }}` or `${{ github.token }}`). With `permissions: contents: write` declared at workflow scope, the token is sufficient for:
- `git push` to `origin/main` from inside the workflow (via `actions/checkout@v4` configuring the credential helper)
- Tag push to `origin`
- `gh release create` against the same repo

No PAT, no Repository Secret, no OAuth consumer. The pre-Sprint-15 OAuth client_credentials grant is fully retired.

### 2.3 In-app updater data contract

The custom `latest.json` schema is **dropped entirely**. The in-app updater (`src/helpers/update_helper.py`) now polls:

```
GET https://api.github.com/repos/TomaszMankin/py-tree-manager/releases/latest
Accept: application/vnd.github+json
User-Agent: py-tree-manager-updater
```

Response shape (relevant fields):

```json
{
  "tag_name": "v1.0.1",
  "published_at": "2026-05-17T10:30:00Z",
  "draft": false,
  "prerelease": false,
  "assets": [
    {
      "name": "py-tree-manager-1.0.1.exe",
      "browser_download_url": "https://github.com/TomaszMankin/py-tree-manager/releases/download/v1.0.1/py-tree-manager-1.0.1.exe",
      "size": 12345678
    }
  ]
}
```

The endpoint excludes draft and prerelease entries by definition — PR builds cannot leak to the updater path even if accidentally tagged as `--latest`. Parsing:

- `latest_version` = `tag_name.lstrip("v")` (so `"v1.0.1"` → `"1.0.1"`).
- `published_at` carries forward as the display timestamp.
- `download_url` is selected from `assets[]` by exact-name match `py-tree-manager-<version>.exe`, with a defensive fallback to "single `.exe` asset" when name doesn't match.
- `min_supported_version` field is **dropped** (was speculative scaffolding never operationally used).

### 2.4 Self-hosted Windows runner reuse

The same self-hosted runner machine that served the Bitbucket pipeline serves GitHub Actions. The runner registers via repo Settings → Actions → Runners with a Windows installer. Workflows declare `runs-on: [self-hosted, Windows]`.

GitHub Actions on Windows runners defaults `shell:` to `pwsh` (PowerShell 7) when pwsh is on PATH — Windows PowerShell 5.1 is no longer the default. The PS 5.1 portability traps that bit Sprint 15 (`Join-Path` multi-arg, em-dash UTF-8 reading, `Invoke-RestMethod -Form`) are no longer a concern.

### 2.5 Fork-PR security gate

Public repo + self-hosted runner is a known security surface: forks can open PRs that run code on the runner. Mitigation: repo Settings → Actions → General → "Fork pull request workflows from outside collaborators" → **"Require approval for all outside collaborators"**. With this setting on, fork-PR workflows pause for explicit maintainer approval before running.

For a single-developer repo with no expected external contributors, the practical impact is zero ongoing friction.

## 3. Code touch list

| File | Action |
|---|---|
| `.github/workflows/pr-build.yml` | NEW |
| `.github/workflows/release.yml` | NEW |
| `.pipelines/ci/bump-version.ps1` | REWRITE — drop OAuth, drop Bitbucket env vars, drop handoff file, drop PR-branch path |
| `.pipelines/ci/rename-artifact.ps1` | TRIM — drop latest.json generation |
| `.pipelines/ci/upload-downloads.ps1` | DELETE |
| `bitbucket-pipelines.yml` | DELETE |
| `.pipelines/update.bat` | UNCHANGED |
| `src/helpers/update_helper.py` | REWRITE — URL constant, JSON parsing, asset selection |
| `src/helpers/update_info.py` | TRIM — drop `min_supported_version`, rename `released_at` → `published_at` |
| `src/tests/helpers/test_update_helper.py` | UPDATE — new payload shape, new asset-selection tests |
| `docs/decisions/ADR-012` | AMEND front-matter (status → superseded-by ADR-015) |
| `docs/decisions/ADR-013` | AMEND front-matter (amended-by ADR-015) |
| `docs/decisions/INDEX.md` | ADD ADR-015 row, update ADR-012 status |
| `docs/RELEASE.md` | REWRITE for GitHub flow |
| `.gitignore` | TRIM — drop `.pipelines/ci/.version-bumped-to` (no longer produced) |
| `requirements.txt`, `requirements-dev.txt` | DELETE — superseded by `[project.optional-dependencies].dev` in pyproject.toml |
| `qt_mockup/` | DELETE — unused Qt evaluation prototype (ADR-002), preserved in archive |

## 4. Alternatives considered

### 4.1 Stay on Bitbucket, upgrade to a paid plan

Bitbucket Standard is $3/user/month and unlocks Downloads. Recurring cost for a personal project; rejected.

### 4.2 Split-host (source on Bitbucket, binaries on GitHub Releases)

Workable but adds: a GitHub PAT in Bitbucket Repository variables, two control planes for code review vs releases, two accounts to manage. The user chose full migration on the grounds that the Atlassian-specific advantages (free private repos, free pipelines) no longer outweigh the operational tax of running two ecosystems.

### 4.3 Cloudflare R2 or Backblaze B2 for binaries

S3-compatible object storage with generous free tiers and no egress fees. Pros: full control, custom domain, no platform vendor lock. Cons: adds a third service, requires bucket setup + access keys, no integration with the source repo's PR or issue flow. Rejected on cost-of-coordination grounds.

### 4.4 Single workflow file with `if:` branches for PR vs main

Mechanically possible; rejected on user preference. Two separate per-concern files are easier to read, diff, and edit.

### 4.5 Third-party release-asset GitHub Action (e.g. `softprops/action-gh-release`)

A popular community action wraps `gh release create` with convenience features (auto-changelog, prerelease toggle, etc.). Rejected in favour of `gh release create` directly — it's first-party, ships with the runner image, has no third-party version pin to maintain, and the workflow is already this short.

### 4.6 Keep `latest.json` as fallback for some hybrid period

The user's existing v1.0.0 installs — if any existed — would not see the new GitHub Releases endpoint until updated. Since the user's father has no install yet (clean state confirmed 2026-05-17), there's nothing to support backward-compatibly. Rejected on YAGNI.

## 5. Consequences

### Positive

- Free public hosting + free unlimited Actions minutes on public repos
- Updater keys on a documented public REST API; no schema to maintain
- Prerelease/release distinction enforced server-side by GitHub
- pwsh 7 default on Windows runners eliminates the PS 5.1 portability traps
- `GITHUB_TOKEN` auto-issuance removes all credential-plumbing complexity

### Negative

- Bitbucket history is private-archived, not transferred. Acceptable per user preference.
- Source code is now public on GitHub. The user confirmed no PII concerns at the current commit (PII audit performed pre-commit).
- Single-developer repo + public + self-hosted runner requires the fork-PR approval gate.

### Neutral

- `update.bat` and the in-app self-replace mechanism (ADR-014) are unchanged.
- Father-machine `.exe` URL changes from `bitbucket.org/...` to `github.com/...`. No effect — no existing install.

## 6. Risks

### Risk 1 — Self-hosted runner downtime

The runner is on the user's laptop. If offline when a merge to main lands, the workflow queues until the runner comes online. Same behaviour as the Bitbucket era. Not a halt criterion.

### Risk 2 — GitHub API rate-limit on the updater poll

Unauthenticated GitHub API calls are rate-limited to 60 requests per hour per IP. The updater polls once per app launch; the father launches the app a handful of times per day at most. Not a real risk.

### Risk 3 — Fork-PR runs code on the self-hosted runner

Mitigated by the "Require approval for all outside collaborators" repo setting. Documented in `docs/RELEASE.md` setup section.

### Risk 4 — `gh release create` race on concurrent main pushes

Mitigated by the bump-commit `[skip ci]` gate: the only way two release workflows could run concurrently is if two different commits with non-`[skip ci]` messages land in quick succession. Unlikely on a single-developer repo; would manifest as one of the two tag-push commands failing on conflict, with the other succeeding. Acceptable.

## 7. Test plan

- L0 unit tests in `src/tests/helpers/test_update_helper.py` covering the new payload shape, asset selection, and existing version-comparison robustness. 44 tests in this file.
- L1 smoke test: first PR after migration must produce a prerelease visible at `https://github.com/TomaszMankin/py-tree-manager/releases`. Asset name must match `py-tree-manager-<base>-pr-1-<sha7>.exe`.
- L2 smoke test: merge the first PR. Verify `release.yml` bumps 1.0.0 → 1.0.1, tags `v1.0.1`, publishes as the `--latest` release. Verify `curl -s https://api.github.com/repos/TomaszMankin/py-tree-manager/releases/latest` returns `tag_name: "v1.0.1"` with the asset URL.
- L3 manual: download v1.0.1 to a Windows machine, install on father's Desktop folder, confirm the app launches and self-update triggers on next bump.

## 8. Sources

(See front-matter `sources:` block.)
