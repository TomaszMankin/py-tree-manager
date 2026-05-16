---
id: ADR-014
title: Self-replace update_helper mechanism — .bat helper with retry-on-lock and silent relaunch
kind: tech
decision_type: architecture
status: accepted
date: 2026-05-12
author: architect
sprint: sprint-15
supersedes: (none)
iterates_with_user: false   # mechanism is operational; the .bat content can be refined without involving the user
related:
  - ADR-012 (CI bundles the .bat helper alongside the .exe in dist/)
  - ADR-013 (consumer-side; calls download_and_apply_update which this ADR implements)
sources:
  - JOURNAL 2026-05-12 — user-locked decision #3 (in-place self-replace via helper that waits, swaps, relaunches)
  - https://andreasrohner.at/posts/Programming/C%23/A-platform-independent-way-for-a-C%23-program-to-update-itself/ — canonical write-up of the .bat-helper self-replace pattern with retry-on-lock; cited in WebSearch result for the dispatch
  - https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/timeout — `timeout` command syntax (used in the helper for the wait loop)
  - https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/move — `move` overwrites the destination by default on Windows
  - https://docs.python.org/3/library/subprocess.html#subprocess.CREATE_NO_WINDOW — `CREATE_NO_WINDOW` flag (0x08000000) suppresses the console window when spawning a child .bat from Python
  - https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecutea — `ShellExecuteW` SW_HIDE option (alternative spawn path; not used here in favor of subprocess)
  - https://docs.python.org/3/library/urllib.request.html#urllib.request.urlretrieve — `urlretrieve` documented; deprecated wrapper; we use `urlopen` + manual write for a controlled timeout
---

# ADR-014 — Self-replace update_helper mechanism

## 0. Changelog

- **2026-05-12 (initial)** — first issue. Resolves user-locked decision
  #3 from Sprint 15 dispatch. `.bat` helper chosen over `update_helper.exe`
  per the dispatch's "lean toward `.bat`" steer.

## 1. Context

ADR-013 stops at "user clicked Yes; we have an `UpdateInfo`". This ADR
implements `download_and_apply_update(update_info: UpdateInfo) -> None`.

The Windows constraint:

> A running `.exe` file is locked by the OS. The running process
> cannot rename or delete itself. The replacement must be done by
> a separate process that starts AFTER the running process exits.

The pattern: ship a small `.bat` helper alongside the main `.exe`.
When an update is approved, the running app:

1. Downloads the new `.exe` to a sibling file (`py-tree-manager.exe.new`).
2. Launches the helper `.bat` (hidden, fire-and-forget).
3. Exits.

The helper:

4. Waits for the parent process to actually release the file lock.
5. Renames `py-tree-manager.exe.new` over `py-tree-manager.exe`.
6. Relaunches `py-tree-manager.exe`.
7. Self-deletes (optional; we leave it on disk — see §3.6).

The father sees: app blinks closed → app comes back, now showing the
new version in its About dialog. One click; zero technical steps.

## 2. Decision

Three artifacts:

- **`update.bat`** — the helper. Shipped by PyInstaller as a sidecar
  via `--add-data .pipelines/update.bat;.` flag in ADR-012. Lives next to
  `py-tree-manager.exe` in `dist/` and on the father's machine.
- **`src/helpers/update_helper.py`** function `download_and_apply_update`
  (declared in ADR-013 §2.1; implemented here).
- **One Sprint 15 test file** at `src/tests/helpers/test_update_helper_download.py`
  for L0 tests that don't need a real running parent (download +
  helper-launch validation; the actual replace + relaunch is L2 user
  smoke).

### 2.1 `update.bat` content (exact)

```batch
@echo off
REM update.bat — py-tree-manager self-replace helper. See ADR-014.
REM
REM Args:
REM   %1 = full path to py-tree-manager.exe (the file being replaced)
REM   %2 = full path to the downloaded .new file (will be moved over %1)
REM   %3 = parent PID (we wait until this PID exits before swapping)
REM
REM Strategy: poll up to ~30 seconds for the parent to release the lock,
REM then atomically replace, then relaunch.

setlocal

set "TARGET=%~1"
set "SOURCE=%~2"
set "PARENT_PID=%~3"

REM --- Step 1: wait for parent process to exit (max ~30 s) ---
set /a TRIES=0
:WAIT_PARENT
tasklist /FI "PID eq %PARENT_PID%" 2>NUL | find "%PARENT_PID%" >NUL
if errorlevel 1 goto PARENT_GONE
set /a TRIES+=1
if %TRIES% GEQ 30 goto FORCE_RETRY
timeout /t 1 /nobreak >NUL
goto WAIT_PARENT

:PARENT_GONE
REM Parent confirmed gone. Even so, the file lock may linger one tick.
timeout /t 1 /nobreak >NUL

:FORCE_RETRY
REM --- Step 2: try to replace; retry on file-lock for up to ~30 s ---
set /a RETRY=0
:DO_MOVE
move /Y "%SOURCE%" "%TARGET%" >NUL 2>&1
if not errorlevel 1 goto MOVED
set /a RETRY+=1
if %RETRY% GEQ 30 goto FAIL
timeout /t 1 /nobreak >NUL
goto DO_MOVE

:MOVED
REM --- Step 3: relaunch the app ---
start "" "%TARGET%"
endlocal
exit /b 0

:FAIL
REM Move failed after 30 retries. Leave .new in place; the next launch
REM of the OLD .exe will see ADR-013 detect the same version again and
REM re-attempt. Don't delete .new; user may inspect.
endlocal
exit /b 1
```

Notes on the helper:

- **No console window**: when spawned from Python via `subprocess.Popen`
  with `creationflags=subprocess.CREATE_NO_WINDOW` (per the
  CREATE_NO_WINDOW docs URL in `sources:`), the `cmd.exe` interpreter
  that runs the `.bat` is hidden. The `@echo off` first line also
  silences command echo (defensive; with CREATE_NO_WINDOW it's
  invisible anyway).
- **`timeout /t 1 /nobreak`** waits one second without printing the
  countdown. Output redirected to `>NUL` for further silence.
- **`tasklist /FI "PID eq ..."`** polls whether the parent is still
  running. `find` returns errorlevel 1 if the PID isn't in the
  filtered tasklist output → parent gone → break the loop.
- **Two-phase wait**: 30 seconds waiting for the PID to disappear, then
  30 more seconds retrying the move if the lock persists. Total worst
  case ~60 seconds before giving up. Practical case: parent exits in
  <1 second; the first move succeeds.
- **`move /Y`** overwrites the destination without prompting.
  Documented at the move-command URL in `sources:`.
- **`start "" "%TARGET%"`** launches the new exe and returns
  immediately. The empty `""` is the title argument (a `start`-command
  quirk: with a quoted target, it interprets the first quoted string
  as the window title).
- **No self-delete**. The `.bat` stays on disk. Self-deleting is
  possible (`del /F "%~f0" & exit`) but adds complexity for negligible
  benefit (~500 bytes). Sprint-N+ if anyone ever asks.

### 2.2 `download_and_apply_update` implementation

```python
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

DOWNLOAD_TIMEOUT_SECONDS = 600  # 10 minutes; .exe is ~30 MB
DOWNLOAD_CHUNK_BYTES = 64 * 1024


def download_and_apply_update(update_info: UpdateInfo) -> None:
    """Download the new .exe, launch the helper .bat, exit the app.

    On any error before launching the helper: log and return (app stays
    running, user can retry on next launch — same skipped_version path).
    On successful helper launch: call sys.exit(0) — control transfers
    to the helper.
    """

    if not getattr(sys, "frozen", False):
        # Dev mode (python main.py). Self-replace is meaningless here;
        # log + skip. Father's machine always runs the frozen .exe.
        log_info_dev_mode_update_skipped()
        return

    # sys.executable in frozen mode is the path to py-tree-manager.exe
    exe_path = Path(sys.executable).resolve()
    exe_dir = exe_path.parent
    new_exe_path = exe_path.with_suffix(".exe.new")
    bat_path = exe_dir / "update.bat"

    if not bat_path.exists():
        # Helper missing — refuse to proceed (cannot self-replace).
        # Log + return; user keeps old version.
        log_error_missing_update_helper(bat_path)
        return

    # --- Step 1: download to .exe.new ---
    try:
        _download_to(update_info.download_url, new_exe_path,
                     timeout=DOWNLOAD_TIMEOUT_SECONDS)
    except Exception as e:
        # Best-effort cleanup of partial file
        try:
            if new_exe_path.exists():
                new_exe_path.unlink()
        except OSError:
            pass
        log_error_download_failed(update_info.download_url, e)
        return

    # --- Step 2: launch helper ---
    parent_pid = os.getpid()
    try:
        subprocess.Popen(
            ["cmd.exe", "/c", str(bat_path),
             str(exe_path), str(new_exe_path), str(parent_pid)],
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            close_fds=True,
        )
    except Exception as e:
        # Helper didn't even launch — leave .new in place for inspection;
        # user keeps running old version this session.
        log_error_helper_launch_failed(e)
        return

    # --- Step 3: exit cleanly ---
    log_info_update_handoff(update_info.latest_version)
    sys.exit(0)


def _download_to(url: str, dest: Path, *, timeout: float) -> None:
    """Stream the URL to a file via urllib.request. Honors timeout."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        with open(dest, "wb") as f:
            while True:
                chunk = response.read(DOWNLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                f.write(chunk)
```

### 2.3 PyInstaller bundling

ADR-012 §2.1 already shows the PyInstaller invocation. For Sprint 15
the invocation extends to include the helper:

```
python -m PyInstaller --onefile --windowed ^
  --name py-tree-manager ^
  --copy-metadata py-tree-manager ^
  --add-data ".pipelines/update.bat;." ^
  main.py
```

The `--add-data ".pipelines/update.bat;."` flag bundles the file. For `--onefile`,
PyInstaller extracts bundled data files into a temp directory at
launch (`sys._MEIPASS`) — but `update.bat` MUST live alongside the
running `.exe`, not in `_MEIPASS` (which gets cleaned up).

**Therefore**: a small one-shot bootstrap step runs on every launch
to copy `update.bat` from `_MEIPASS` to `exe_dir` if it's missing:

```python
# In main.py or LoggingApp.OnInit, BEFORE the update_helper check:
def _ensure_update_helper_present() -> None:
    if not getattr(sys, "frozen", False):
        return  # dev mode; helper not needed
    exe_dir = Path(sys.executable).resolve().parent
    target = exe_dir / "update.bat"
    if target.exists():
        return
    bundled = Path(sys._MEIPASS) / "update.bat"
    if bundled.exists():
        try:
            shutil.copy2(str(bundled), str(target))
        except OSError:
            pass  # not fatal; update_helper check will detect missing helper
```

This runs once per launch; the copy is a no-op after the first run.

## 3. Behavior matrix

| Scenario | Outcome | App state after |
|---|---|---|
| Happy path: download OK, helper launches, parent exits, move succeeds, relaunch fires | New version running | Updated |
| Download fails (network drops mid-stream) | `download_and_apply_update` returns; app keeps running on old version | Unchanged; user can retry on next launch (skipped_version NOT written — user said Yes, not No) |
| `update.bat` not on disk (developer ran a build without `--add-data` and shipped that .exe) | `download_and_apply_update` returns immediately; app keeps running | Unchanged |
| Helper launches but parent never exits (sys.exit(0) hangs because wx mainloop is busy) | Helper times out after 30 s waiting for PID; then 30 s retrying move; gives up; .new stays on disk | Unchanged; .new orphaned next to .exe |
| Helper moves but relaunch fails (security software blocks `start`) | New .exe exists but is not running; user double-clicks it; it works | Updated, after one manual click |
| Disk full during download | `_download_to` raises OSError; partial .new cleaned up; app keeps running | Unchanged |
| User has UAC enabled, .exe lives in a write-protected folder | `move /Y` fails (Access Denied) → 30 retries → FAIL exit 1 | Unchanged; .new orphaned; user must move manually or run app from a writable folder. Documented: father's machine should run the app from Desktop or a personal folder, not Program Files. |

## 4. Pre-implementor parity check

### 4.1 Example ↔ pseudocode parity

§2.1 (.bat content) and §2.2 (Python helper-launch) traced together:

1. Python passes `subprocess.Popen([..., str(exe_path), str(new_exe_path), str(parent_pid)])`.
2. The .bat reads `%1 = exe_path`, `%2 = new_exe_path`, `%3 = parent_pid`.
3. The .bat's `%TARGET% = %1 = exe_path` and `move /Y "%SOURCE%" "%TARGET%"`
   = `move /Y new_exe_path exe_path`.

So `.new` moves OVER the old `.exe`. Correct: source = new, target = old.
MATCHES.

If Python had passed `str(new_exe_path)` as %1 (swap order), the
helper would move `exe_path` over `new_exe_path` — silent reverse
bug. **Implementor: keep the argument order locked. Add a unit test
that asserts the argv order.** Sprint 15 carry-forward note for the
reviewer: argv order is load-bearing.

### 4.2 PID lifecycle

The helper polls the parent PID. PIDs can be recycled on Windows
(usually after process exit, a window of seconds). If the PID is
reused by an unrelated process during the helper's poll, the helper
would wait until THAT process exits. **Mitigation**: parent's
`sys.exit(0)` typically completes in <1 second, well before any PID
recycling. The 30-second per-phase timeout caps the worst case.
Documented; not a halt criterion.

### 4.3 `sys.frozen` and `sys._MEIPASS` correctness

`sys.frozen` is set to `True` by PyInstaller's bootloader. Verified
in PyInstaller docs (cited in ADR-012 sources). `sys._MEIPASS` is the
runtime temp-extracted resources dir; only set in `--onefile` frozen
mode. The `_ensure_update_helper_present` function's
`Path(sys._MEIPASS)` reference would NameError in dev mode — guarded
by the `getattr(sys, "frozen", False)` early return.

## 5. Alternatives considered

### 5.1 Tiny `update_helper.exe` instead of `.bat`

Pros: no `cmd.exe` console window flash (CREATE_NO_WINDOW is
documented to suppress the window but a brief redraw can occur on
some Windows versions).

Cons:
- Second PyInstaller build (or a separate one-file Python script
  frozen with PyInstaller). Adds CI complexity.
- The `.exe` would need to be self-replacable too (if `update_helper.exe`
  needs an update, who updates it?). Solvable but adds layers.
- Father's machine doesn't care about a 100ms console window flash.

**Rejected** per dispatch's "lean toward .bat".

### 5.2 PowerShell script instead of .bat

`update.ps1` would have richer error handling and proper exception
semantics. But:
- ExecutionPolicy on father's machine may be Restricted by default.
- Requires `powershell -ExecutionPolicy Bypass -File update.ps1` which
  is an extra surface; SmartScreen and AV may flag.
- `.bat` is the OS-native, lowest-friction option.

**Rejected** on the AV-friendliness argument.

### 5.3 Use `os.rename` from the dying parent + subprocess for the relaunch

Doesn't work. Windows holds the file lock on `sys.executable` even
during the `sys.exit(0)` call. The parent process cannot rename its
own running binary, period.

**Rejected** on Windows-correctness.

### 5.4 Download to %TEMP%, helper copies into place

Same complexity as the chosen approach but the download target is
%TEMP% instead of the .exe directory. Pros: cleaner if the .exe dir
is write-protected (but then the move would fail too). Cons: a stray
file in %TEMP% if the helper fails. The chosen approach (.new sibling)
makes orphan detection easy ("there's a .new next to the .exe; the
last update didn't finish").

**Rejected** on orphan-detection clarity.

### 5.5 Apply update on app shutdown instead of immediately

E.g., download in the background, swap when the user closes the app.
More complex; requires the wx app to detect "an update is pending"
state across the whole session. Pure UX benefit (no perceived
shutdown blink) for a once-per-version event.

**Rejected** on cost/benefit; revisit if father reports the blink is
annoying.

### 5.6 Atomic file replacement via `MoveFileEx` with `MOVEFILE_DELAY_UNTIL_REBOOT`

Windows API for "move this file at next reboot, atomically, even if
locked now". Would let the parent enqueue its own replacement before
exiting.

**Rejected**: requires reboot to take effect. Father wouldn't see the
update until next reboot, which could be days. The whole point is
"one click → updated now".

## 6. Halt criteria

(H-A) Build pipeline produces a working `.exe` that launches the actual
app on father's machine class. Real-pywin32 in CI catches the obvious
smoke; verify on Tomasz's machine before declaring done.

(H-D) Helper script must survive Windows file locks: the running `.exe`
is locked while alive; the helper retries until parent exits. The
30-second wait phase + 30-second retry phase covers the realistic
worst case.

Plus, specific to this ADR:

(H-D2) **Argv order parity**: Python passes `(exe_path, new_exe_path,
parent_pid)` and the helper reads `%1, %2, %3` in the same order. A
unit test asserts the subprocess.Popen argv list shape.

(H-D3) **Brief console flash regression check**: after build, run
`py-tree-manager.exe`, trigger a fake update flow (mock manifest with
`download_url` pointing at a local file or a small self-served URL),
confirm no visible console window during the helper launch. User-smoke,
not CI-automated.

## 7. Test plan

| Layer | What | Mock | Asserts |
|---|---|---|---|
| L0 | `_download_to` happy path | `urlopen` returns a fake response with known bytes | Destination file contains the bytes |
| L0 | `_download_to` timeout | `urlopen` raises `socket.timeout` | Exception propagates; caller (`download_and_apply_update`) catches |
| L0 | `_download_to` partial write cleaned up on error | `urlopen` returns response that raises mid-stream | Caller deletes partial .new; tested via dest path absence after the failed call |
| L0 | `download_and_apply_update` skips in dev mode | `sys.frozen = False` | Function returns without calling Popen |
| L0 | `download_and_apply_update` skips when helper missing | `sys.frozen = True`, but `update.bat` doesn't exist in `exe_dir` | Function returns without calling Popen |
| L0 | `download_and_apply_update` argv order | Mock `subprocess.Popen` (capture call args); `sys.frozen = True`; helper exists; download succeeds | Argv = `["cmd.exe", "/c", bat_path, exe_path, new_exe_path, parent_pid]` in this exact order |
| L0 | `_ensure_update_helper_present` copies from `_MEIPASS` | Set `sys.frozen = True`, set `sys._MEIPASS` to a tmpdir containing `update.bat`, point `sys.executable` at another tmpdir | `update.bat` exists in `sys.executable.parent` after the call |
| L2 | Live self-replace | Father's machine; real download; real swap; real relaunch | New version running; About dialog shows new version. Manual smoke, documented in `RELEASE.md`. |

L0 tests live at `src/tests/helpers/test_update_helper_download.py`.
L2 is the release rehearsal.

## 8. Risks

### Risk 1 — Antivirus quarantines the .bat or the .new file

Some AV products flag scripted self-replacement as ransomware-adjacent
behavior. **Mitigation**: father's machine should have the app's
folder in the AV exclusion list. Document in `RELEASE.md`.

### Risk 2 — `cmd.exe` window briefly visible despite CREATE_NO_WINDOW

On some Windows configurations the flag is honored unevenly. Worst
case: a 100ms flash. Acceptable. If father reports it as scary,
upgrade to a `pythonw`-launched update_helper.exe in a follow-up sprint.

### Risk 3 — User clicks the .new file by mistake

`py-tree-manager.exe.new` has `.new` extension; Windows doesn't know
how to run it. The user-confusion surface is "a file named .new
appeared next to the .exe" — solvable by leaving the helper alone
(the .new is gone after a successful swap; orphaned .new is the
failure-mode visible artifact).

### Risk 4 — Subprocess inheritance keeps file handles open

`close_fds=True` in the Popen call prevents the child from inheriting
the parent's file handles. The .exe lock is held by the OS at the
process level, not at the handle level — `close_fds` doesn't address
the lock directly, but it does prevent the child holding open log
files that would prevent log rotation. Defensive.

### Risk 5 — `sys.exit(0)` doesn't fully unwind wxPython

In wx, `sys.exit()` from inside an event handler can be caught by the
event loop's exception machinery. Worst case the app sticks around
for a moment longer than intended. The helper's 30-second wait
absorbs this. Not a halt criterion.

## 9. Sources

(See front-matter `sources:` block.)
