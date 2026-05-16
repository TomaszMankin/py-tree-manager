# rename-artifact.ps1
# Renames the PyInstaller artifact to include the version string.
#
# Input: $env:BUMPED_VERSION (set by the release.yml workflow as a step
# output from bump-version.ps1).
#
# Action: dist/py-tree-manager.exe -> dist/py-tree-manager-<version>.exe

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$version = $env:BUMPED_VERSION
if ([string]::IsNullOrWhiteSpace($version)) {
    throw "BUMPED_VERSION env var is not set."
}
# Defensive trim — env vars on Windows shells occasionally arrive
# wrapped in literal "..." quotes.
$version = $version.Trim().Trim('"', "'")

$src = "dist/py-tree-manager.exe"
$dst = "dist/py-tree-manager-$version.exe"

if (-not (Test-Path $src)) {
    throw "Source artifact not found: $src"
}

Move-Item -Path $src -Destination $dst -Force
Write-Host "Renamed artifact: $src -> $dst"
