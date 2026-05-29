---
id: ADR-018
title: Inno Setup installer with fixed per-user location, shortcuts, and update-path observability
kind: tech
decision_type: architecture
status: proposed
date: 2026-05-29
author: architect
sprint: sprint-20
supersedes: (none)
amends: ADR-013, ADR-014
iterates_with_user: true   # install location + shortcut naming are UX-facing; expect 1-2 user rounds
related:
  - ADR-013 (update detection — OnInit wiring point gains observability here)
  - ADR-014 (self-replace .bat — install location must be writable; relaunch path now fixed)
  - ADR-015 (GitHub Releases — release.yml gains an installer artifact alongside the raw .exe)
  - "WPF migration design (docs/superpowers/specs/2026-05-23-wpf-migration-design.md) — long-term home uses Velopack + Inno Setup; this ADR is the minimal bridge equivalent"
sources:
  - https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm — PrivilegesRequired=lowest enables per-user install touching per-user areas on any Windows version (verified current UI 2026-05-29)
  - https://jrsoftware.org/ishelp/topic_consts.htm — Inno Setup directory constants ({autopf}, {localappdata}, {userdesktop}, {autoprograms})
  - https://ahmedsyntax.com/creating-professional-installers-inno-setup/ — 2026 walkthrough: [Setup]/[Files]/[Icons]/[Run]/[Tasks] structure for PyInstaller onefile + Start Menu + Desktop shortcut
  - https://github.com/pyinstaller/pyinstaller/issues/5905 — PyInstaller onefile wrapped by Inno Setup pattern confirmation
  - C:/Repositories/py-tree-manager/src/helpers/logger.py lines 601-662 (LoggingApp.OnInit — update-check wiring point; gains INFO log lines here)
  - C:/Repositories/py-tree-manager/src/helpers/update_helper.py (check_for_update + download_and_apply_update — log lines added; relaunch path unchanged)
  - "Issue #24 attached logs (2026-05-29 journey + exceptions) — ZERO update-path trace; confirms observability gap"
---

# ADR-018 — Installer with fixed location + update-path observability

## 0. Changelog

- **2026-05-29 (initial, proposed)** — resolves #14 (installer / shortcuts /
  no-leftovers) and the distribution half of #24 (new version not detected).
  Pairs with `decision-needed.md` D-1 (install location). One open user
  decision gates §2.1; rest of ADR holds regardless.

## 1. Context

Two GitHub issues, one root cause.

**#14** — father gets two app copies in two places after an update; confusing.
**#24** — father stuck on 1.0.0 while 1.0.4 is latest; no update prompt.

Today's distribution model (ADR-014 + ADR-015): a self-contained PyInstaller
`--onefile` `.exe`. The father double-clicks a bare `.exe` that sits wherever
it was copied. No installer, no Desktop shortcut, no Start Menu entry, no fixed
location. The self-replace `update.bat` only swaps the `.exe` it was launched
FROM (`sys.executable`).

**Evidence (issue #24 attached logs, 2026-05-29):**

- App self-reports v1.0.0; GitHub `/releases/latest` returns v1.0.4 with asset
  `py-tree-manager-1.0.4.exe` (verified live). `check_for_update` parse logic is
  correct against that payload — detection logic is NOT the bug.
- The journey log (full session, many launches) contains ZERO update-path
  trace: no "update available", no "no update", no "update check failed".
  The OnInit update block (logger.py 634-651) is wrapped in `try/except` that
  logs ONLY on exception. Success and "no-update" paths emit nothing.
- Therefore from logs we CANNOT tell whether the check ran, returned None, or
  the father launched a stale 1.0.0 copy that lives in a different folder than
  the one a prior update wrote to.

Two failure modes are jointly consistent with the evidence, and the
distribution model permits BOTH:

1. **Stale-copy launch (most likely, ties #14)** — a prior update downloaded
   and swapped a `.exe` in folder X; the father's Desktop/taskbar pin points at
   an OLD `.exe` in folder Y. He keeps opening Y → forever 1.0.0.
2. **Offline-at-launch** — `check_for_update` returns None silently (by design).
   No way to distinguish from #1 without logging.

## 2. Decision

Three coordinated changes. The installer kills the multi-copy class of bug;
the observability change makes future "no update" reports diagnosable in one
log read; the updater relaunch is reconciled with the fixed location.

### 2.1 Inno Setup installer — fixed per-user location + shortcuts

Ship an `.exe` **installer** built by Inno Setup, wrapping the PyInstaller
onefile `.exe`. The installer:

- Installs the app `.exe` to **one fixed location** (exact dir = `decision-needed.md` D-1).
- Creates a **Desktop shortcut** and a **Start Menu** entry (searchable).
- Registers an **uninstaller** (Add/Remove Programs) — clean removal, no leftovers.
- On reinstall/upgrade over an existing install, overwrites the SAME location
  (no second copy).

`[Setup]` uses `PrivilegesRequired=lowest` (per-user; no UAC; install dir must
be user-writable so `update.bat`'s `move /Y` keeps working). Sections used:
`[Setup]`, `[Files]`, `[Icons]` (`{autodesktop}` + `{autoprograms}`), `[Run]`
(offer launch-on-finish), `[Tasks]` (optional desktop-icon toggle).

**Install location is user-decidable** (D-1). Two candidates:

| Option | Location | Pro | Con |
|---|---|---|---|
| **A — conventional** | `{localappdata}\Programs\PyTreeManager\` | standard, writable, survives tree-folder moves, AV-friendly | not the tree folder (#14 AC text says "the user-selected folder where the app builds the tree") |
| **B — issue-literal** | `<tree-root>\.PyTreeManager\app\` | matches #14 AC wording literally; app sits with its data | tree root not known at install time (chosen later, in-app); installer cannot place the exe there |

Architect note: Option B is **mechanically blocked at install time** — the
tree root is selected INSIDE the app on first run, long after the installer has
finished. An installer cannot put the `.exe` somewhere the user hasn't chosen
yet. So #14's literal wording ("put it in the tree folder") cannot be honored
by a classic installer. Recommended framing for the user: Option A for the
binary + shortcuts; the tree data stays wherever the user points it (unchanged
ADR-010 `.PyTreeManager` under `<root>`). Final call is the user's — see D-1.

### 2.2 Update-path observability (the diagnosable half of #24)

The OnInit update block (logger.py ~634-651) and `update_helper` gain INFO
log lines on EVERY branch so a future "no update happened" report is
one-log-read diagnosable. New lines (Polish-free; these are diagnostic INFO,
not user-facing — per ADR-007 INFO lines are developer-facing):

| Branch | New INFO line (developer-facing English) |
|---|---|
| check entered | `Update check: current=<v> skipped=<v-or-none> url=<api-url>` |
| network/parse failure inside check_for_update | `Update check: no result (network/parse) — staying on <current>` |
| no newer version | `Update check: up to date (latest=<v> current=<v>)` |
| newer found, prompting | `Update check: newer version <latest> available; prompting user` |
| user accepted | `Update: user accepted <latest>; entering download_and_apply` |
| dev-mode no-op (frozen False) | `Update: dev mode (not frozen) — self-replace skipped` |
| helper .bat missing | `Update: update.bat not found at <path> — cannot self-replace` |
| download failed | `Update: download failed for <url>` |
| handoff to .bat | `Update: launching update.bat; exiting for swap` |
| user declined | `Update: user declined <latest>; remembered as skipped` |

These are written via the existing logger `log_*`/journey-INFO path (implementor
picks the exact existing API — `log_info`-equivalent; grep the logger surface).
Each line is wrapped so logging failure never crashes the update path. The
existing top-level `try/except` that logs on exception STAYS as the safety net.

**Why this is load-bearing, not gold-plating**: issue #24's own logs are the
proof. With these lines, the next father report tells us immediately whether
(a) he's offline, (b) he's launching a stale copy (no check line at all because
he launched a 1.0.0 binary that predates this change), or (c) the prompt fired
and he declined. Without them we are guessing, exactly as now.

### 2.3 Updater relaunch reconciled with fixed location

ADR-014's `download_and_apply_update` swaps `sys.executable` in place and
relaunches it. With the installer placing the `.exe` at a fixed writable
location (§2.1 Option A), the existing self-replace mechanism is **already
correct** — `sys.executable` IS the fixed-location `.exe`, the swap happens
there, and the Desktop/Start-Menu shortcuts point at that same path so they
keep working after the swap (a shortcut targets a path, not an inode).

No change to `update.bat` argv order or logic. One reconciliation item: the
installer must NOT lay down a shortcut to a versioned filename
(`py-tree-manager-1.0.4.exe`) — the shortcut and the on-disk binary must use a
**stable, version-less filename** (e.g. `PyTreeManager.exe`) so that after a
self-replace the shortcut still resolves. See §3.1.

### 2.4 Stable binary filename

Today the release asset is `py-tree-manager-<version>.exe` and the self-replace
swaps `sys.executable` (whatever it was named) — fragile if a shortcut encodes
the version. Decision: the INSTALLED binary is always named **`PyTreeManager.exe`**
(version-less, stable). The installer renames the versioned release asset to
`PyTreeManager.exe` on install. `update.bat` already swaps `.new` over
`sys.executable` by path, so it swaps `PyTreeManager.exe` → stays stable.
`update_helper.download_and_apply_update` writes `<exe>.exe.new` next to
`sys.executable` — also stable. The versioned name survives ONLY as the GitHub
release asset (so humans can tell releases apart on the Releases page).

## 3. Behavior matrix

| Scenario | Before (today) | After this ADR |
|---|---|---|
| First install | copy bare .exe somewhere; no shortcut | run installer → fixed location + Desktop + Start Menu + uninstaller |
| Father searches Start Menu for the app | not found | found (`{autoprograms}` entry) |
| Update applied | .exe swapped at launch-folder; Desktop pin may point elsewhere → stale copy | .exe swapped at fixed location; shortcuts target that path → always current |
| "No update prompt" report | logs silent; undiagnosable | log shows exactly which branch fired |
| Uninstall | manual delete; leftovers possible | Add/Remove Programs removes binary + shortcuts; tree data untouched |
| Tree data on update | untouched (ADR-014) | untouched (unchanged) |

## 4. Pre-implementor parity check

### 4.1 Example ↔ pseudocode parity (observability table ↔ OnInit code)

Traced §2.2 table against logger.py 634-651 control flow:

- `info = check_for_update(...)` → if `info is None` we cannot today tell
  "no-update" from "network-fail" because both return None. **Resolution**:
  the "no result (network/parse)" vs "up to date" distinction CANNOT be made by
  the OnInit caller (both are `None`). Therefore those two lines (rows 2 and 3)
  must be emitted INSIDE `check_for_update` itself, not in OnInit — `check_for_update`
  is the only place that knows which one happened. Implementor: rows 2-3 go in
  `update_helper.check_for_update`; rows 1, 4-10 go in OnInit. This is a real
  example↔code gap the parity check caught — without it the implementor would
  try to emit both from OnInit and could only ever emit one.
- `check_for_update` is documented wx-free (ADR-013 §2.1). Adding a logger
  import there is fine — logger is wx-free at import (logger.py §580 comment).

### 4.2 Self-replace path still correct under fixed-location install

`download_and_apply_update` (update_helper.py 210-243): `exe_path =
Path(sys.executable).resolve()`; `new_exe_path = exe_path.with_suffix(".exe.new")`;
launches `update.bat exe_path new_exe_path pid`. With the installed binary at a
fixed writable location named `PyTreeManager.exe`, `sys.executable` resolves to
exactly that. The `.new` lands beside it; `move /Y` swaps it; `start "" target`
relaunches the same path. Shortcuts (target = path) keep working. MATCHES — no
logic change needed.

### 4.3 PrivilegesRequired vs update.bat move

`PrivilegesRequired=lowest` installs to a per-user, user-writable dir.
`update.bat`'s `move /Y` (ADR-014) requires write access to the install dir.
Per-user install dir IS writable by the running user. Consistent. (The old
ADR-014 §3 risk "UAC + write-protected folder" is RETIRED by choosing a per-user
location — document the retirement, don't re-litigate it.)

## 5. Alternatives considered

### 5.1 Keep bare .exe, just add observability (no installer)

Fixes the diagnosability of #24 but NOT the structural cause: the father can
still have N copies and launch the wrong one. #14 explicitly asks for shortcuts
+ no-leftovers. Rejected — leaves the root cause standing.

### 5.2 MSIX / Windows App SDK packaging

Modern, sandboxed, auto-update via the Store or sideload. But: code-signing
cert required for sideload trust, far heavier toolchain, sandboxed file access
fights the "app reads/writes a user-chosen tree folder anywhere on disk" core
behavior. Massive over-build for a single-elderly-user bridge app. Rejected on
project posture.

### 5.3 Velopack (the WPF rewrite's choice) for the Python app too

Velopack is the chosen updater/installer for the .NET rewrite. It has a Python
story but it's .NET-first; wiring it into a PyInstaller onefile is more
integration than the existing `update.bat` mechanism, which already works.
Given the WPF rewrite is the long-term home, investing in Velopack for the
soon-to-be-retired Python app is wasted effort. Rejected — reuse the working
`update.bat` (ADR-014) + a thin Inno wrapper.

### 5.4 Install to {autopf} (Program Files) with elevation

Program Files is the "proper" location but is write-protected → `update.bat`'s
in-place swap fails (the exact ADR-014 §3 UAC risk + the RELEASE.md
troubleshooting row). Would force either elevation-on-every-update or a
fundamentally different updater. Rejected — per-user writable location keeps
the existing simple updater valid.

### 5.5 Self-update via re-running the installer (download installer, run silent)

Instead of swapping the bare `.exe`, download the new INSTALLER and run it
`/SILENT`. Cleaner upgrade semantics (installer handles shortcuts/uninstall
registration). But requires the release to publish an installer asset AND the
updater to fetch+run it, and the running app to exit cleanly for the silent
installer to overwrite. More moving parts than the proven `update.bat` swap.
**Deferred, not rejected** — noted as the natural next step if the bare-swap
proves fragile in practice (Sprint-21+ candidate). For Sprint 20: installer for
first-install; existing `update.bat` swap for subsequent updates.

## 6. Risks

### Risk 1 — Installer asset not yet produced by release.yml

The CI today builds only the bare `.exe`. Adding an Inno Setup compile step
requires Inno Setup (`iscc.exe`) on the self-hosted runner. **Mitigation**:
Sprint 20 plan step installs Inno Setup on the runner + adds the `iscc` compile
step; the installer `.iss` script is committed. If the runner can't get Inno
Setup, the installer can be compiled locally by the user as a one-time manual
step (documented fallback in RELEASE.md).

### Risk 2 — Existing 1.0.0 install won't auto-migrate to the installer

The father's current bare-.exe 1.0.0 won't magically become an installed app.
**Mitigation**: this is a one-time manual reinstall — user runs the new
installer once on the father's machine; thereafter updates flow normally.
Document in RELEASE.md "migrating an existing bare-.exe install".

### Risk 3 — Antivirus flags the unsigned installer

Unsigned installers trip SmartScreen. **Mitigation**: same as today's unsigned
.exe (RELEASE.md already documents the AV exclusion + SmartScreen "More info →
Run anyway"). Code-signing is out of scope (no cert; single-user app).

### Risk 4 — Observability INFO lines leak a personal path

The diagnostic lines include `url` and `<path>` (update.bat path). The API url
is public; the .exe path could contain the username. **Mitigation**: pii-check
gate already scans for hardcoded personal paths in SOURCE; runtime log content
is in `<root>/.PyTreeManager/logs` (user's own disk), not committed. The father
attaches logs deliberately. Acceptable; no source-level PII added.

## 7. Halt criteria

(H-A) Installer produces a working install: app launches from the fixed
location; Desktop shortcut present; Start Menu search finds it; uninstaller in
Add/Remove Programs. User smoke on a real Windows machine.

(H-B) After a simulated update (bump version, publish, relaunch), the app shows
the new version AND the Desktop shortcut still launches the current binary (no
stale copy). User smoke.

(H-C) Observability: launch with network up against a newer release → log shows
"newer version available; prompting". Launch offline → log shows "no result
(network/parse)". Launch on latest → log shows "up to date". Three distinct
lines, automatable at L0 by asserting the log calls fire on mocked branches.

(H-D) Uninstall removes binary + both shortcuts; `<root>` tree data is NOT
touched (the installer never wrote there).

## 8. Test plan

| Layer | What | Mock | Asserts |
|---|---|---|---|
| L0 | check_for_update emits "up to date" line | mock urlopen → latest==current | log call fired with up-to-date message |
| L0 | check_for_update emits "no result" line | mock urlopen → URLError | log call fired with no-result message; returns None |
| L0 | OnInit-equivalent emits "newer available" | mock check_for_update → UpdateInfo | log call fired with prompting message |
| L0 | download_and_apply emits dev-mode line | sys.frozen False | log call fired; returns without Popen |
| L0 | download_and_apply emits handoff line | frozen True, bat exists, download ok, mock Popen | handoff log fired before sys.exit |
| L2 | installer install/uninstall/upgrade | real Windows machine | H-A, H-B, H-D — manual smoke, documented in RELEASE.md |

L0 lines added to `src/tests/L0/helpers/test_update_helper*.py`. L2 is the
release/install rehearsal (no headless installer test on free-tier CI).

## 9. Sources

(See front-matter `sources:` block.)
