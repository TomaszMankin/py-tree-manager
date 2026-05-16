# bump-version.ps1
# Patch-bumps the version in pyproject.toml, commits with [skip ci],
# tags, and pushes both commit and tag to origin/main.
#
# Auth: actions/checkout@v4 configures the local git credential helper
# with the workflow's auto-issued GITHUB_TOKEN. No PAT, no Repository
# Secret, no manual credential plumbing.
#
# Output: emits "new_version=X.Y.Z" to $env:GITHUB_OUTPUT for downstream
# steps (rename + release publish).

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# ---------------------------------------------------------------------------
# 1. Read current version
# ---------------------------------------------------------------------------
$pyprojectPath = "pyproject.toml"
$content = Get-Content -Path $pyprojectPath -Raw

if ($content -notmatch '(?m)^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"') {
    throw "Could not parse version (expected X.Y.Z) in $pyprojectPath."
}

$major = [int]$matches[1]
$minor = [int]$matches[2]
$patch = [int]$matches[3] + 1
$newVersion = "$major.$minor.$patch"
$oldMatch  = $matches[0]

# ---------------------------------------------------------------------------
# 2. Write back
# ---------------------------------------------------------------------------
$patched = $content -replace '(?m)^version\s*=\s*"\d+\.\d+\.\d+"', "version = `"$newVersion`""
Set-Content -Path $pyprojectPath -Value $patched -NoNewline

Write-Host "Bumped version: $oldMatch -> version = `"$newVersion`""

# ---------------------------------------------------------------------------
# 3. Configure git identity for the bot commit
# ---------------------------------------------------------------------------
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

# ---------------------------------------------------------------------------
# 4. Commit, tag, push
# ---------------------------------------------------------------------------
# [skip ci] in the commit message prevents the resulting push from
# re-triggering this workflow (the if: gate on install-and-test honours it).
git add $pyprojectPath
git commit -m "[skip ci] bump version to $newVersion"
if ($LASTEXITCODE -ne 0) { throw "git commit failed (exit $LASTEXITCODE)." }

git tag "v$newVersion"
if ($LASTEXITCODE -ne 0) { throw "git tag failed (exit $LASTEXITCODE)." }

git push origin HEAD:main
if ($LASTEXITCODE -ne 0) { throw "git push (main) failed (exit $LASTEXITCODE)." }

git push origin "v$newVersion"
if ($LASTEXITCODE -ne 0) { throw "git push (tag) failed (exit $LASTEXITCODE)." }

# ---------------------------------------------------------------------------
# 5. Emit step output for downstream steps
# ---------------------------------------------------------------------------
"new_version=$newVersion" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8

Write-Host "Pushed commit + tag v$newVersion to origin/main."
