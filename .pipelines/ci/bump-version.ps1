# Resolves the next release version from pyproject.toml + existing tags.
# Patches pyproject.toml in-place so PyInstaller --copy-metadata embeds
# the correct version. Does NOT commit; the patch is workflow-local.
# Tag creation is delegated to `gh release create` downstream (tags are
# not gated by the main-branch ruleset, so no bypass needed).

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$pyprojectPath = "pyproject.toml"
$content = Get-Content -Path $pyprojectPath -Raw

if ($content -notmatch '(?m)^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"') {
    throw "Could not parse version in pyproject.toml."
}

$major = [int]$matches[1]
$minor = [int]$matches[2]
$basePatch = [int]$matches[3]

# Find max patch among existing tags for this major.minor line.
$tags = git tag --list "v$major.$minor.*"
$maxPatch = -1
foreach ($t in $tags) {
    if ($t -match "^v$major\.$minor\.(\d+)$") {
        $p = [int]$matches[1]
        if ($p -gt $maxPatch) { $maxPatch = $p }
    }
}

if ($maxPatch -lt 0) {
    # No prior tag in this line — first release of this major.minor.
    $newPatch = $basePatch
} else {
    $newPatch = $maxPatch + 1
}
$newVersion = "$major.$minor.$newPatch"

# In-place patch; not committed.
$patched = $content -replace '(?m)^version\s*=\s*"\d+\.\d+\.\d+"', "version = `"$newVersion`""
Set-Content -Path $pyprojectPath -Value $patched -NoNewline

"new_version=$newVersion" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
Write-Host "Resolved release version: $newVersion (tag will be v$newVersion)"
