# pii-check.ps1
# Scans the working tree for stale Bitbucket references, hardcoded personal
# paths, process breadcrumbs in production code, and leftover diagnostic
# strings. Runs on every PR via .github/workflows/pii-check.yml.
#
# Exit codes:
#   0 - clean (no fail-group matches)
#   1 - one or more fail-group patterns matched; lines printed to stdout
#
# Pattern groups:
#   - FAIL: stale Bitbucket references (must not appear anywhere)
#   - FAIL: hardcoded personal Windows paths (must not appear in code)
#   - FAIL: process breadcrumbs (ADR-/Sprint-/PRD-/etc.) in production code
#           only (docs/decisions/ is allowed)
#   - FAIL: diagnostic leftovers (sha256[:16] fingerprints, etc.)
#   - WARN: real-name patterns (logged but do not fail the run)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..' '..')
Set-Location $repoRoot

# ---------------------------------------------------------------------------
# Collect tracked files via git (only tracked content is scanned; build
# outputs, .git, gitignored dirs are skipped automatically).
# ---------------------------------------------------------------------------
$trackedRaw = git ls-files
if ($LASTEXITCODE -ne 0) {
    Write-Error "git ls-files failed (exit $LASTEXITCODE)."
    exit 2
}
$tracked = $trackedRaw -split "`n" | Where-Object { $_ -ne "" }

Write-Host "PII check scanning $($tracked.Count) tracked files..."

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Test-PathMatch {
    param([string]$RelPath, [string[]]$Patterns)
    foreach ($p in $Patterns) {
        if ($RelPath -like $p) { return $true }
    }
    return $false
}

function Invoke-Scan {
    param(
        [string]$GroupName,
        [string]$Regex,
        [string[]]$IncludePathGlobs,
        [string[]]$ExcludePathGlobs,
        [switch]$WarnOnly
    )
    $hits = @()
    foreach ($f in $tracked) {
        # Path filters
        if ($IncludePathGlobs -and -not (Test-PathMatch $f $IncludePathGlobs)) { continue }
        if ($ExcludePathGlobs -and (Test-PathMatch $f $ExcludePathGlobs)) { continue }

        # Only scan text-readable files; skip binaries by extension
        $ext = [IO.Path]::GetExtension($f).ToLowerInvariant()
        if ($ext -in @('.png', '.jpg', '.jpeg', '.gif', '.ico', '.exe', '.dll',
                       '.pyd', '.zip', '.lnk', '.pdf')) { continue }

        $full = Join-Path $repoRoot $f
        if (-not (Test-Path $full)) { continue }
        try {
            $matches = Select-String -Path $full -Pattern $Regex -AllMatches `
                -ErrorAction SilentlyContinue
        } catch { continue }
        foreach ($m in $matches) {
            $hits += [pscustomobject]@{
                File = $f
                Line = $m.LineNumber
                Text = $m.Line.Trim()
            }
        }
    }

    if ($hits.Count -gt 0) {
        $label = if ($WarnOnly) { "WARN" } else { "FAIL" }
        Write-Host ""
        Write-Host "[$label] Group: $GroupName ($($hits.Count) match(es))"
        foreach ($h in $hits) {
            Write-Host "  $($h.File):$($h.Line)  $($h.Text)"
        }
    }
    return $hits.Count
}

# ---------------------------------------------------------------------------
# Pattern groups
# ---------------------------------------------------------------------------
$failCount = 0
$warnCount = 0

# 1. Stale Bitbucket references — must not appear in live code or live docs.
#    Allowed: docs/decisions/* (ADRs are historical decision records; ADR-012
#    documents the superseded Bitbucket design, ADR-015 documents the migration
#    AWAY from Bitbucket, ADR-013 has historical pseudocode now amended).
$failCount += Invoke-Scan -GroupName "stale-bitbucket-references" `
    -Regex 'bitbucket\.org|x-token-auth|BITBUCKET_BOT_|Duch003/py-tree-manager' `
    -ExcludePathGlobs @('docs/decisions/*', '.pipelines/ci/pii-check.ps1')

# 2. Hardcoded personal Windows paths (must not appear anywhere, including
#    ADRs — the user's actual disk paths are personal data, not historical
#    decisions).
$failCount += Invoke-Scan -GroupName "hardcoded-personal-paths" `
    -Regex 'C:\\Users\\Duch003|C:\\Sorted tree|C:\\Repositories\\py-tree-manager' `
    -ExcludePathGlobs @('.pipelines/ci/pii-check.ps1')

# 3. Process breadcrumbs in production code (ADR-NNN / Sprint-NN / PRD-NNN /
#    KB-NNN / Halt-X). Allowed in docs/decisions/. Forbidden in src/, tests,
#    .pipelines/, .github/.
$failCount += Invoke-Scan -GroupName "process-breadcrumbs-in-code" `
    -Regex 'ADR-\d{3}|Sprint-\d{2}|PRD-\d{3}|KB-\d{3}|Halt-[A-Z0-9]' `
    -IncludePathGlobs @('src/*', '.pipelines/*', '.github/*', 'main.py') `
    -ExcludePathGlobs @('.pipelines/ci/pii-check.ps1')

# 4. Diagnostic leftovers from prior OAuth debugging.
$failCount += Invoke-Scan -GroupName "diagnostic-leftovers" `
    -Regex 'BEB573A71EE76F12|sha256\[:16\]|DB01CCFF3253FF4B|client_credentials' `
    -ExcludePathGlobs @('docs/decisions/*', '.pipelines/ci/pii-check.ps1')

# 5. WARN-only: real names that might be personal. Skipped in ADRs (which can
#    reference the user) and in this script.
$warnCount += Invoke-Scan -GroupName "real-names" `
    -Regex 'Mańkin|tomasz\.mankin' `
    -ExcludePathGlobs @('docs/decisions/*', '.pipelines/ci/pii-check.ps1') `
    -WarnOnly

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "PII check complete."
Write-Host "  FAIL matches: $failCount"
Write-Host "  WARN matches: $warnCount"

if ($failCount -gt 0) {
    Write-Host ""
    Write-Host "Fix the FAIL hits above or update the exclusion list in"
    Write-Host ".pipelines/ci/pii-check.ps1 if a hit is a documented false positive."
    exit 1
}

Write-Host "OK - no fail-group matches."
exit 0
