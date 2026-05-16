---
id: ADR-001
title: Use IShellLink + IPersistFile directly for .lnk creation (not WScript.Shell)
kind: tech
status: accepted
date: 2026-05-02
author: architect
sprint: sprint-04
---

## Context

End-to-end manual smoke test on 2026-05-02 surfaced a real bug:
`ShortcutHelper.create_shortcut()` fails with HRESULT 0x80070003
(`ERROR_PATH_NOT_FOUND`) when the .lnk path contains characters outside the
system's active ANSI codepage (cp1252 on the user's EN-locale Windows install).
Specifically: Polish-language characters `ń`, `ł`, `ż` (Latin Extended-A) trip
the bug; `ó` (which exists in cp1252 at 0xF3) does not. The on-disk folder
names use proper UTF-8; the mangling happens **inside the COM call**, not on
disk.

This is an uncaught **pre-existing bug**, not a regression: per
`.pipeline/0-vision/seed-knowledge/phases.md` ledger and the JOURNAL trace,
T1.2 (save-with-relationships) and T2.7-T2.10 / RT1-RT7 were all deferred or
run only against ASCII-only synthetic paths. The Sprint 03 real-pywin32
integration test in `tests/integration/test_shortcut_real_pywin32.py` PASSED —
but with `tmp_path / "shortcut.lnk"` (ASCII-only). The pywin32 binding shipped
in Sprint 03 is not at fault; the *interface* the helper uses is.

`helpers/shortcut_helper.py` uses `win32com.client.Dispatch("WScript.Shell")`,
which returns a `WshShortcut` IDispatch object whose Save method routes through
the ANSI variant of the underlying Shell Link API. Non-cp1252 characters get
best-effort substituted in the ANSI round-trip; the resulting path no longer
exists on disk; the kernel returns `ERROR_PATH_NOT_FOUND`.

The product target user is the user's elderly Polish-speaking father. Polish
characters in folder names are not an edge case — they are the norm. This must
be fixed before Sprint 04 closes.

## Decision

Replace the body of `helpers.shortcut_helper.ShortcutHelper.create_shortcut()`
to bypass `WScript.Shell` and call `IShellLink` + `IPersistFile` directly:

```python
import pythoncom
from win32com.shell import shell

link = pythoncom.CoCreateInstance(
    shell.CLSID_ShellLink,
    None,
    pythoncom.CLSCTX_INPROC_SERVER,
    shell.IID_IShellLink,  # GUID 000214F9 == the W variant; pywin32 marshals str as LPCOLESTR
)
link.SetPath(target_path)
link.QueryInterface(pythoncom.IID_IPersistFile).Save(shortcut_path, 0)
```

Public signature, validation logic (lines 57-71), and exception types stay
unchanged. The `IWshShortcut` Protocol type-hint can stay or be removed — it's
no longer load-bearing because we don't use the IDispatch path; leave for
documentation continuity (this sprint's scope is the fix, not type-hint
cleanup).

`remove_shortcut()` is unaffected — it doesn't touch COM, just `Path.unlink()`.

The fix is ~10 LOC. Validation and error handling stay identical. No new
dependency: pywin32 is already a Sprint 03 dep and the `win32com.shell`
submodule + `pythoncom` are part of the same wheel.

## Alternatives considered

- **Option B — `pylnk3` library**: rejected. (1) Adds a new dep when pywin32
  is already required for `wxPython`-adjacent COM calls elsewhere in the app
  (and is now installed per Sprint 03). (2) Re-implements the binary .lnk
  format in pure Python; more surface area to trust than the official Shell
  API. (3) Reportedly misses Shell-handled subtleties (icon caching, link
  tracking). What would change my mind: pywin32 fails to install on a future
  target machine, OR a Microsoft Shell-API regression makes the wide-char path
  unreliable. Neither is current.
- **Option C — wait for upstream pywin32 fix**: rejected. The bug is in
  `WScript.Shell` itself (a Windows Script Host scripting-era object dating
  from Win9x), not in pywin32's wrapper. There is no upstream "fix" available;
  Microsoft's documented workaround for Unicode on the scripting layer is
  Shell.Application or the direct IShellLink path. What would change my mind:
  Microsoft ships a Unicode-aware replacement for `WshShortcut` in a future
  WSH update. Not on any roadmap.
- **Option D — Shell.Application COM object**: rejected as more indirection
  with no benefit over Option A. The ITPro Today workaround for VBScript users
  uses Shell.Application because VBScript can't easily do CoCreateInstance;
  Python with pywin32 can, so Option A is more direct.
- **Option E — pre-create the .lnk via `WScript.Shell` against a temp ASCII
  path, then rename**: rejected as a hack. Doesn't solve the TargetPath
  problem (the target also contains Polish characters).

## Consequences

- **Positive**: Polish (and any non-cp1252) characters in both the .lnk path
  and the target path now work correctly. The fix is mechanical and
  well-documented; the snapshot at
  `1-architecture/discovery/kb-pattern-pywin32-shell-link-unicode-snapshot.md`
  is a promotion candidate to a real cross-project KB note after Sprint 04
  ships.
- **Positive**: The new code path is the canonical Microsoft + Tim Golden
  pattern. Cited authoritatively. Future readers don't have to trace why
  `WScript.Shell` was abandoned.
- **Negative**: The integration-test conftest stub at
  `tests/integration/conftest.py` mirrors the OLD `WScript.Shell` shape. The
  Sprint-02 root `tests/conftest.py` stub also mirrors the old shape (used by
  service-layer tests that call into `ShortcutHelper`). Both stubs need to be
  taught the new shape (a fake `pythoncom.CoCreateInstance` + a fake
  `IShellLink` + a fake `IPersistFile`) — OR taught to monkey-patch
  `helpers.shortcut_helper.ShortcutHelper.create_shortcut` directly, which is
  simpler. The implementation plan calls out which path to take.
- **Negative**: Slightly more imports in `shortcut_helper.py` (`pythoncom`,
  `win32com.shell.shell`). Both ship with pywin32; no new dep.
- **Neutral**: The `IWshShortcut` Protocol type hint at the top of the file
  becomes orphaned (we no longer use `WScript.Shell`'s shortcut object). Not
  worth removing this sprint — leave for a future cleanup.

## Revisit when

- A future requirement needs `.lnk` features beyond `SetPath` (icon, working
  dir, hotkey, args, description). The IShellLink interface exposes all of
  these via additional `Set*` calls; no architecture change. Add as needed.
- pywin32 is dropped as a dependency (e.g. switch to a non-COM toolkit). At
  that point pylnk3 becomes the natural replacement.
- The user's Windows install changes locale such that the active codepage IS
  cp1250 (Polish) — at which point `ą`/`ć`/`ę`/etc. would survive ANSI but
  some other locale's chars wouldn't. The wide-char path is correct for ALL
  locales, so this doesn't actually change the decision; it just means the
  bug would have a different signature on a Polish-locale machine.

## Sources

- `.pipeline/1-architecture/discovery/kb-pattern-pywin32-shell-link-unicode-snapshot.md`
  (architect's snapshot, 2026-05-02 — primary citation; full mechanism +
  reference implementation + test contract)
- python-list, Martin v. Löwis on IShellLinkA vs IShellLinkW:
  https://python-list.python.narkive.com/ckA3gUEu/unicode-aware-file-shortcuts-in-windows
- Microsoft Learn, "Shell Links" (CreateLink C example shows the
  `MultiByteToWideChar(CP_ACP, ...)` round-trip):
  https://learn.microsoft.com/en-us/windows/win32/shell/links
- Tim Golden, "Create a shortcut" (canonical Python pattern):
  https://timgolden.me.uk/python/win32_how_do_i/create-a-shortcut.html
- Tim Golden, pywin32 docs, "win32com.shell and Windows Shell Links":
  https://timgolden.me.uk/pywin32-docs/win32com.shell_and_Windows_Shell_Links.html
- Local verification on this machine, 2026-05-02:
  pywin32 311 exposes `shell.IID_IShellLink`, `shell.CLSID_ShellLink`, and
  `shell.IID_IShellLinkW` (all confirmed via `hasattr`).
- Bug-evidence trail in `.pipeline/JOURNAL.md` 2026-05-03 orchestrator entry
  (HRESULT 0x80070003, disk verified UTF-8, T1.2/RT-deferred history).
