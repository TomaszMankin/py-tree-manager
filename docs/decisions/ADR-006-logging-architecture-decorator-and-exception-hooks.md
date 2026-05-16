---
id: ADR-006
title: Logging architecture — decorator-based journey log, dual exception hooks (sys.excepthook + wx.App.OnExceptionInMainLoop), file-lock self-recovery, 14-day cleanup
kind: tech
decision_type: architecture
status: accepted
date: 2026-05-09
author: architect
sprint: sprint-11
supersedes: (none)
amended: 2026-05-09 (same day, revision pass — see §0 Changelog)
iterates_with_user: false
related:
  - PRD-005 (scope contract)
  - ADR-007 (severity model + log-line format — companion ADR)
sources:
  - .pipeline/decisions/PRD-005-diagnostic-logging-foundation.md
  - .pipeline/JOURNAL.md 2026-05-09 orchestrator entry "PM defaults review"
  - .pipeline/1-architecture/discovery/kb-wxpython-exception-hooks-snapshot.md
  - .pipeline/1-architecture/discovery/kb-wxpython-gotchas-localized-elderly-ui-snapshot.md
  - https://docs.wxpython.org/wx.AppConsole.html
  - https://docs.wxpython.org/events_overview.html
  - https://wiki.wxpython.org/CustomExceptionHandling
  - https://www.blog.pythonlibrary.org/2014/03/14/wxpython-catching-exceptions-from-anywhere/
  - https://docs.python.org/3/library/sys.html#sys.excepthook
---

# ADR-006 — Logging architecture

> Companion to ADR-007 (severity model + log-line format). Read together.

## 0. Changelog

- **2026-05-09 (initial)** — first issue.
- **2026-05-09 (same-day amendment, this revision)** — two changes per
  orchestrator dispatch and JOURNAL line 1213+:
  1. **Added §3.10 `log_error()` manual API** for caught-and-handled
     exceptions inside frames'/services' inner `try-except polish_dialog`
     handlers. Closes the gap §6.2 of ADR-007 flagged: existing inner
     except blocks swallow exceptions before the decorator's outer
     except can log them, which left ~10 catch sites silent in the
     exception log. User's stance shifted from "demo phase, errors
     don't matter" to "production-on-father's-machine, I need
     visibility on every error". The decorator path is unchanged; this
     adds a parallel manual write path with `source=manual`
     attribution.
  2. **Amended §3.6 cleanup-failure path** — instead of silent-pass
     (original deviation from PRD-005's "log to journey + continue"
     literal) OR journey-log-noise (the PRD literal), cleanup failures
     now emit ONE `INFO-CLEANUP` line to today's exception log per
     failed file. Journey log stays a pure user-action narrative;
     exception log is the diagnostics-about-diagnostics surface. User
     selected this Option C middle path during 2026-05-09 design review.

## 1. Context

PRD-005 locks WHAT gets logged, with what retention, and at what shape.
This ADR locks HOW the logging machinery wires into the wxPython app:
the decorator API, the dual exception-hook integration, the file-lock
self-recovery contract, the cleanup mechanism, and the bootstrap order.

Per the PM-default review (JOURNAL 2026-05-09), four user-locked
decisions feed this ADR:

- **Severity**: INFO / ERROR / CRITICAL only. (See ADR-007.)
- **Storage**: plain-text per-day files at `<root>/logs/`.
- **Person context**: every line carries `[Person: <name>]`; placeholder
  `[Person: -]` when no frame is loaded.
- **Both exception hooks** wired (`sys.excepthook` AND
  `wx.App.OnExceptionInMainLoop`) — user said "do both".
- **Decorator implementation**: user said "whichever works and is easier
  to maintain and/or extend"; PM recommended sentinel attribute on
  frame; this ADR ratifies that recommendation.

## 2. Decision (one paragraph)

A new module `helpers/logger.py` exposes (a) two file-backed loggers
(`journey` and `exceptions`), (b) a `@log_user_action(verb)` decorator
applied to UI handlers in `frames/add_person_frame.py`, (c) bootstrap
helpers `init_logging()` and `cleanup_old_logs(retention_days=14)`, and
(d) hook-installer functions `install_python_excepthook()` and base
class `LoggingApp(wx.App)` that overrides `OnExceptionInMainLoop`. A
sentinel attribute `self._current_person_label` on `AddPersonFrame`,
maintained at every person-load / person-clear site, supplies the
decorator with the `[Person: ...]` field. File-write contention is
handled by suffix-and-retry (`__1.log`, `__2.log`, ..., cap `__99`,
then drop to stderr). Logger-internal errors are swallowed; the app
never crashes on logging failure.

## 3. Components

### 3.1 New module — `helpers/logger.py`

Public surface (Sprint 11 will refine names; these are the contract):

```python
# Constants
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"             # for [timestamp] field
LOG_FILE_DATE_FORMAT = "%Y-%m-%d"                 # for filename prefix
LOG_RETENTION_DAYS = 14
LOG_LOCK_RETRY_CAP = 99
PERSON_PLACEHOLDER = "-"                          # PM-locked default

# Bootstrap (called from PyTreeManagerApp.OnInit)
def init_logging(root_folder: Optional[Path]) -> None: ...
def cleanup_old_logs(retention_days: int = LOG_RETENTION_DAYS) -> None: ...

# Hook installers (called from main.py before wx.App is constructed
# AND from inside LoggingApp.OnExceptionInMainLoop respectively)
def install_python_excepthook() -> None: ...
class LoggingApp(wx.App):
    def OnExceptionInMainLoop(self) -> bool: ...

# Decorator applied to UI handler methods
def log_user_action(action_verb: str) -> Callable: ...

# Manual ERROR API — for caught-and-handled exceptions (added 2026-05-09
# amendment, see §3.10). Distinct from the decorator's outer-except path:
# the decorator catches AT THE BOUNDARY; log_error() is called BEFORE
# re-handling within an inner except.
def log_error(exc: BaseException, context: Optional[str] = None) -> None: ...

# Person-context helpers — frame calls these on every state change
def set_current_person_label(frame: wx.Frame, label: str) -> None: ...
def clear_current_person_label(frame: wx.Frame) -> None: ...

# Internal write paths — exposed for tests, not for callers
def _emit_info(person_label: str, action_verb: str) -> None: ...
def _emit_error(person_label: str, handler_name: str,
                exctype, value, tb, extra_data: Optional[dict] = None) -> None: ...
def _emit_critical(person_label: str, exctype, value, tb,
                   source: str) -> None: ...
def _emit_cleanup_failure(log_file: Path, exc: BaseException) -> None: ...  # added 2026-05-09 amendment per §3.6
def _open_for_append_with_lock_retry(target_path: Path) -> Optional[TextIO]: ...
def _today_exceptions_log_path() -> Path: ...     # used by log_error and _emit_cleanup_failure
def _today_journey_log_path() -> Path: ...        # used by _emit_info
```

The module owns its own state — global module-level variables for the
two file paths (today's journey + today's exceptions) and a thread-lock
for the rare-but-possible concurrent write (wxPython is single-threaded
in our app, but `wx.Timer` callbacks Sprint 12 introduces will use the
same logger). This is `helpers/logger.py` only; nothing else in the
codebase imports the file paths directly.

### 3.2 Sentinel attribute on `AddPersonFrame`

Per PM recommendation, ratified here.

```python
class AddPersonFrame(wx.Frame):
    def __init__(self, parent):
        super().__init__(...)
        # Sentinel for the journey-log decorator. Set by every site that
        # loads, clears, or transitions person context. Default placeholder
        # at construction time before any person is loaded.
        self._current_person_label: str = "-"
        # ... rest of __init__
```

The decorator reads `getattr(self, '_current_person_label', '-')`. The
`getattr` default `'-'` makes the decorator robust to any frame that
doesn't set the sentinel (future frames the user may add — e.g., the
root-person picker dialog, when its handlers grow). Falls back gracefully.

**Sites that set the sentinel** (Sprint 11 implementation must touch
every one — see sprint plan):

| Site | New value | Reason |
|---|---|---|
| `__init__` | `"-"` | No person loaded yet. |
| `_reset_to_add_mode` | `"New"` | Add-new mode. |
| `_load_person_for_edit` (after success) | `<full_name>` from `person_data` | Edit-tree mode. |
| `on_load_draft_click` (after success) | `f"Draft, {first_last}"` or `"Draft"` if no name yet | Edit-draft mode. |
| `on_save_click` (after success, before `_reset_to_add_mode` runs) | (no explicit set; `_reset_to_add_mode` flips to `"New"`) | Auto-cascade. |
| `on_save_edit_click` (after success) | unchanged (still editing the same person) | No transition. |

Helper `set_current_person_label(self, label)` and
`clear_current_person_label(self)` exist as one-liners for the frame to
call at the sites above. The frame doesn't import the loggers directly —
just these label-management helpers — keeping the contract narrow.

### 3.3 The `@log_user_action` decorator

#### Pseudocode

```python
def log_user_action(action_verb: str) -> Callable:
    """Decorator factory. Wraps a UI handler so:
       - on entry: emits one INFO journey-log line.
       - on exception: emits one ERROR exceptions-log line, then re-raises.
       - on normal return: returns the wrapped function's return value.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Step 1: read person label off the frame (best-effort)
            person_label = getattr(self, '_current_person_label', '-')

            # Step 2: emit INFO journey line; failure here is silent
            try:
                _emit_info(person_label, action_verb)
            except Exception:
                pass  # Logger NEVER crashes the app

            # Step 3: invoke wrapped handler
            try:
                return func(self, *args, **kwargs)
            except Exception:
                exctype, value, tb = sys.exc_info()
                # Step 4: emit ERROR exception line; failure here is silent
                try:
                    _emit_error(
                        person_label=person_label,
                        handler_name=func.__name__,
                        exctype=exctype, value=value, tb=tb,
                        extra_data=_collect_save_payload_if_save_handler(self, func.__name__),
                    )
                except Exception:
                    pass  # Logger NEVER crashes the app
                raise   # Re-raise; caller's try/except (if any) decides next.
        return wrapper
    return decorator
```

#### Worked example A — `_on_refresh_drzewo_click`, person already loaded

Setup: user has loaded "Anna Staluszka" (so
`self._current_person_label == "Anna Staluszka"`), then clicks "Odśwież
drzewo" menu item. The handler succeeds.

Source-code shape after Sprint 11:

```python
@log_user_action("Refresh Drzewo")
def _on_refresh_drzewo_click(self, event: wx.Event) -> None:
    if not self._tree_service._file_service.get_drzewo_root_uuid():
        polish_dialog(self, "Najpierw wybierz osobę-korzeń drzewa...", ...)
        return
    try:
        written, log = self._tree_service.rebuild_drzewo()
    except Exception as e:
        polish_dialog(self, f"Nie udało się odświeżyć drzewa.\n\n{e}", ...)
        return
    polish_dialog(self, f"Drzewo odświeżone: {written} skrótów.", ...)
```

Trace through the wrapper pseudocode:

1. `person_label` = `"Anna Staluszka"` (from `getattr`).
2. `_emit_info("Anna Staluszka", "Refresh Drzewo")` → appends to today's
   journey.log:
   ```
   [2026-05-09 14:32:11] [INFO] [Person: Anna Staluszka] User clicked 'Refresh Drzewo'
   ```
3. `func(self, event)` runs and returns `None` normally.
4. No exception → wrapper returns `None`.

**Net log output**: one INFO line in `2026-05-09__journey.log`. Nothing
in `__exceptions.log`. App proceeds.

#### Worked example B — `_on_new_person_click`, no person loaded

Setup: app has just started. User picks "Plik → Nowa osoba" from menu.
Frame's `_current_person_label` is `"-"` (set in `__init__`).

Source-code shape after Sprint 11:

```python
@log_user_action("Reset to add-new mode")
def _on_new_person_click(self, event: wx.Event) -> None:
    if self._is_dirty:
        result = polish_dialog(self, "Masz niezapisane zmiany...", ...)
        if result != wx.ID_YES:
            return
    self._reset_to_add_mode()
```

Trace:

1. `person_label` = `"-"`.
2. `_emit_info("-", "Reset to add-new mode")` appends:
   ```
   [2026-05-09 09:12:03] [INFO] [Person: -] User clicked 'Reset to add-new mode'
   ```
3. `func(self, event)` runs. Inside, `_reset_to_add_mode()` calls
   `set_current_person_label(self, "New")` near the end, so the *next*
   handler invocation will see `"New"` as the label.
4. Wrapper returns `None`.

**Net log output**: one INFO line with `[Person: -]`. Subsequent handler
invocations on the same frame would emit `[Person: New]` until the user
either loads or saves a person.

#### Worked example C — `on_save_click`, exception escapes

Setup: user has filled the form for a new person, clicks "Zapisz".
`self._current_person_label == "New"`. The save raises an uncaught
`KeyError` somewhere inside `_tree_service.save_person_and_add_to_tree`
(say a `cached_people` lookup returns `None` and a downstream attribute
access blows up — exact mechanism not material for this trace).

Source-code shape after Sprint 11:

```python
@log_user_action("Save person (new)")
def on_save_click(self, event: wx.Event) -> None:
    errors = self._validate_form()
    if errors:
        polish_dialog(self, "\n".join(errors), ...)
        return
    person_data = PersonDataWrapper(self._collect_all_data_to_dict())
    try:
        self._resolve_relationship_paths(person_data)
    except ValueError as e:
        polish_dialog(self, str(e), ...)
        return
    # ... preflight etc. ...
    self._tree_service.save_person_and_add_to_tree(person_data)  # ← KeyError here
    # ... never reached ...
```

Trace:

1. `person_label` = `"New"`.
2. `_emit_info("New", "Save person (new)")` appends:
   ```
   [2026-05-09 14:40:22] [INFO] [Person: New] User clicked 'Save person (new)'
   ```
3. `func(self, event)` runs. Validation passes. `_collect_all_data_to_dict`
   returns the form payload. `save_person_and_add_to_tree` raises
   `KeyError('uid-xxx')`.
4. Wrapper catches at the bare `except Exception:`. `sys.exc_info()` gives
   `(KeyError, KeyError('uid-xxx'), <tb>)`.
5. `_collect_save_payload_if_save_handler(self, 'on_save_click')` returns
   the `_collect_all_data_to_dict()` snapshot (only for handlers whose
   name matches a small whitelist — `on_save_click`, `on_save_edit_click`,
   `on_save_draft_click`).
6. `_emit_error(...)` appends to today's exceptions.log:
   ```
   [2026-05-09 14:40:22] [ERROR] [Person: New] handler=on_save_click KeyError: 'uid-xxx'
     payload: {'first_name': 'Adam', 'last_name': 'Kowalski', 'sex': 'M', ...}
     Traceback (most recent call last):
       File "frames/add_person_frame.py", line 883, in on_save_click
         self._tree_service.save_person_and_add_to_tree(person_data)
       File "services/tree_service.py", line ..., in save_person_and_add_to_tree
         ...
     KeyError: 'uid-xxx'
   ```
7. Wrapper re-raises the `KeyError`.
8. The exception escapes the handler. wxPython's C++ event dispatch
   catches it at the language boundary and calls
   `wx.App.OnExceptionInMainLoop` (see §4 below).

**Net log output**: one INFO line, one ERROR line (with traceback), and
then a CRITICAL line from the exception-hook layer if no inner try/except
caught the exception before re-raise. The user-visible behavior depends
on whether the original `on_save_click` had an outer try/except — in the
current code it does NOT around `save_person_and_add_to_tree` (line 883),
so the exception escapes. **The decorator's ERROR line is the
"caught-by-decorator" record; the CRITICAL line is the
"app-is-terminating" record.** Both are valuable; both fire.

> **Note on ADR-007 severity-level ambiguity for this case.** This
> example illustrates that a *single* uncaught exception produces both
> an ERROR log line (decorator's catch) and a CRITICAL log line
> (`OnExceptionInMainLoop`'s catch). This is intentional and documented
> in ADR-007 §4.3. The decorator catches, logs ERROR, re-raises;
> `OnExceptionInMainLoop` catches the re-raised exception and logs
> CRITICAL because the app is about to terminate. Tomasz reads both
> files; the duplication is "ERROR explains the handler context (with
> save payload); CRITICAL records the actual termination event with
> source attribution".

#### Decorator semantics — return values, async, threads

- **Return value**: `wrapper` returns whatever `func` returned. wx event
  handlers conventionally return `None`, but if a future handler returns
  `wx.ID_OK` or similar, the decorator preserves it.
- **Re-raise on exception**: yes, always. The decorator's job is to
  observe + log; not to swallow. Swallowing would interfere with
  `OnExceptionInMainLoop` and with any try/except the original handler
  may already have around its own internals.
- **Async / threaded handlers**: out of scope for current codebase (no
  `asyncio` usage; no `threading.Thread`). If a future Sprint 12 timer
  callback (`wx.Timer.Notify`) is decorated, the decorator works the
  same way — `wx.Timer` callbacks run on the wx main loop thread, so no
  threading hazard. If a future thread-spawning handler appears, the
  decorator must be applied to the **callable that runs on the wx
  thread**, not to the thread target — a thread target's exceptions
  don't propagate to wx event dispatch and would not reach
  `OnExceptionInMainLoop`. Documented for future reference.

### 3.4 Dual exception-hook integration

#### `sys.excepthook` — Python-side global hook

Installed in `main.py` BEFORE `wx.App` is constructed. Catches:
- Crashes during `wx.App.__init__` / `OnInit`.
- Crashes after `MainLoop()` returns (shutdown).
- Crashes in any thread the app spawns (none today; future-proof).

Pseudocode:

```python
# main.py
import sys
import wx
from helpers.logger import (init_logging, install_python_excepthook,
                            LoggingApp, _emit_critical)

install_python_excepthook()  # FIRST, before LoggingApp() runs

if __name__ == "__main__":
    app = LoggingApp(False)  # subclass of wx.App; OnInit calls init_logging
    app.MainLoop()


# helpers/logger.py
def install_python_excepthook() -> None:
    def _hook(exctype, value, tb):
        try:
            person_label = _read_global_person_label()  # best-effort, defaults '-'
            _emit_critical(person_label, exctype, value, tb,
                           source="sys.excepthook")
        except Exception:
            pass
        # Chain to default so stderr behavior is preserved.
        sys.__excepthook__(exctype, value, tb)
    sys.excepthook = _hook
```

`_read_global_person_label()` is a defensive helper. The Python hook
runs at top-frame level; it does not have a `self` to read the sentinel
from. Two possibilities:

- **Option A**: a module-level `_last_known_person_label` updated by
  `set_current_person_label` whenever the frame's sentinel changes.
  Cheap, single source of truth, single-threaded-safe.
- **Option B**: walk `wx.GetTopLevelWindows()` and read
  `_current_person_label` off the first frame. More indirect, more
  failure surface.

**Picked Option A.** `set_current_person_label(frame, label)` updates
both `frame._current_person_label` AND
`helpers.logger._last_known_person_label`. Sprint 11 implementation:
3-line helper. Fall-back is `"-"` if never set.

#### `wx.App.OnExceptionInMainLoop` — wx-side event-loop hook

Catches exceptions that escape Python event handlers back into wx C++
event dispatch (the *common* case for "user clicked X and it crashed").
Per the events_overview docs ("If an exception is thrown in event
handler, wx.App.OnExceptionInMainLoop is called"), this is the canonical
wxPython 4.x hook for this case.

Pseudocode:

```python
class LoggingApp(wx.App):
    def OnInit(self) -> bool:
        # Determine root_folder if known; init_logging falls back to
        # %LOCALAPPDATA% if root_folder is None.
        from frames.add_person_frame import AddPersonFrame
        # We can't ask for root_folder before AddPersonFrame is created
        # (root-folder picker runs inside its __init__), so call
        # init_logging() with None first; AddPersonFrame.__init__ will
        # call init_logging again (idempotent) once it has the root.
        init_logging(root_folder=None)
        cleanup_old_logs()  # 14-day sweep on startup
        frame = AddPersonFrame(None)
        frame.Show()
        return True

    def OnExceptionInMainLoop(self) -> bool:
        exctype, value, tb = sys.exc_info()
        try:
            person_label = _read_global_person_label()
            _emit_critical(person_label, exctype, value, tb,
                           source="wx.App.OnExceptionInMainLoop")
        except Exception:
            pass
        return False  # Exit the loop and terminate.
```

Return `False` is deliberate: an uncaught exception means the app's
state is no longer trustworthy; we don't swallow-and-continue. Caught
exceptions inside handlers (which we DO survive) are ERROR not
CRITICAL — see ADR-007.

#### What each catches that the other doesn't (recap)

This is the "concrete failure modes" requirement from the dispatch.

| Failure mode | Caught by `sys.excepthook` | Caught by `OnExceptionInMainLoop` |
|---|---|---|
| Syntax error in startup import (`import wx` succeeds, then `import frames.add_person_frame` raises) | yes — happens before LoggingApp() | no — main loop hasn't started |
| `RuntimeError("Root folder has to be selected or set.")` raised from `AddPersonFrame.__init__` (line 52) when user cancels the root picker | yes — Python init phase, no event loop yet | no — handler never registered |
| Uncaught `KeyError` in `_on_save_person_click` after the user clicks "Zapisz" (Worked Example C) | unreliable; may or may not bubble across the C++/Python boundary | yes — this is the canonical case |
| Exception in `wx.Timer.Notify` callback (Sprint 12 introduces these) | unreliable | yes |
| `ImportError` raised at module-import time (e.g., `import wx` fails because pip env is broken) | yes | no — wx isn't initialized |

The "do both" decision (user-locked) covers all five rows. Either alone
leaves a hole.

### 3.5 File-lock self-recovery

Path: `<root>/logs/2026-05-09__journey.log` (or `__exceptions.log`).
Same scheme for both. PRD-005 specifies `__N.log` numeric suffix; this
ADR pins the cap at 99.

Pseudocode for `_open_for_append_with_lock_retry`:

```python
def _open_for_append_with_lock_retry(target_path: Path) -> Optional[TextIO]:
    """Open target_path for UTF-8 append. On Windows lock contention,
    retry with __1.log, __2.log, ... up to LOG_LOCK_RETRY_CAP=99.
    Returns the file handle, or None if all attempts fail (in which
    case caller falls back to stderr — never crashes the app).
    """
    base = target_path.parent / target_path.stem      # e.g. .../2026-05-09__journey
    suffix = target_path.suffix                        # '.log'

    # Attempt 0: the un-suffixed canonical path.
    candidates = [target_path]
    # Attempts 1..99: __1.log, __2.log, ..., __99.log
    candidates.extend(
        Path(f"{base}__{i}{suffix}") for i in range(1, LOG_LOCK_RETRY_CAP + 1)
    )

    for candidate in candidates:
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            return candidate.open("a", encoding="utf-8", newline="")
        except (PermissionError, OSError):
            continue
        except Exception:
            # Truly unexpected — bail to stderr fallback rather than
            # propagate to caller (logger NEVER crashes the app).
            break

    # All attempts failed. Emit one warning to stderr (best-effort) and
    # return None so the emit_X function knows to skip the write.
    try:
        sys.stderr.write(
            f"[logger] could not open {target_path} or any __1..__99 suffix; "
            f"this log line is dropped\n"
        )
    except Exception:
        pass
    return None
```

#### Race-condition analysis (PRD-005 + dispatch requirement)

If two log calls hit a locked file simultaneously, what happens? Today
this is NOT a real scenario — `AddPersonFrame` is single-threaded; all
handlers and `wx.Timer.Notify` callbacks run on the same wx event loop
thread, and each emit-call is sequential. So:

1. Single-threaded today: no real race. Sequential calls retry sequentially.
2. Sprint 12 introduces `wx.Timer` retry-the-pending-email loop. Still
   single-threaded (timers fire on the wx event thread).
3. Hypothetical future: two app instances opened simultaneously by the
   user. Each has its own process. Process P1 has `journey.log` open
   for append; process P2 starts, tries to open the same file, gets
   `PermissionError` on Windows (file shared-write semantics). P2 falls
   through to `__1.log` and writes there. Result: one day's log split
   across `journey.log` (P1's lines) and `journey__1.log` (P2's lines).
   Both are readable; `cat journey.log journey__1.log` gives interleaved
   chronology. Documented as expected behavior; not a bug.

### 3.6 14-day cleanup

Run from `LoggingApp.OnInit` (after `init_logging`, before `AddPersonFrame`
is constructed). Walks `<root>/logs/` and `%LOCALAPPDATA%/PyTreeManager/logs/`
(both possible log roots — see §3.7), deletes `*.log` files older than
14 days by `mtime`.

Pseudocode (amended 2026-05-09 — failure branch now writes one
`INFO-CLEANUP` line to today's exception log per failed file rather than
silent-passing; rest of behavior unchanged):

```python
def cleanup_old_logs(retention_days: int = 14) -> None:
    cutoff = time.time() - (retention_days * 86400)
    candidate_dirs = []
    if _root_log_dir is not None:
        candidate_dirs.append(_root_log_dir)
    candidate_dirs.append(_localappdata_log_dir())
    for log_dir in candidate_dirs:
        if not log_dir.exists():
            continue
        try:
            for log_file in log_dir.glob("*.log"):
                try:
                    if log_file.stat().st_mtime < cutoff:
                        log_file.unlink()
                except (PermissionError, FileNotFoundError, OSError) as e:
                    # Best-effort: failed-to-delete files stay around an
                    # extra day. Emit one INFO-CLEANUP line to today's
                    # exception log so Tomasz sees that cleanup tried
                    # and failed (production-posture visibility).
                    try:
                        _emit_cleanup_failure(log_file, e)
                    except Exception:
                        pass  # Logger NEVER crashes the app.
                    continue
        except Exception:
            # Even directory iteration failure is silent — we cannot log
            # to a directory we cannot iterate. The app continues.
            continue


def _emit_cleanup_failure(log_file: Path, exc: BaseException) -> None:
    """Write ONE INFO-CLEANUP line to today's exception log for a
    cleanup-delete failure. Distinct severity tag (per ADR-007 §3) so
    Tomasz can `grep '[INFO-CLEANUP]'` to isolate cleanup-noise from
    real ERROR/CRITICAL.

    Format (per ADR-007 §4.5):
      [2026-05-09 09:01:14] [INFO-CLEANUP] [Person: -] Cleanup: failed to delete <path>: <reason>
    """
    ts = time.strftime(LOG_DATE_FORMAT)
    person = _last_known_person_label or PERSON_PLACEHOLDER
    reason = f"{type(exc).__name__}: {exc}"
    line = (
        f"[{ts}] [INFO-CLEANUP] [Person: {person}] "
        f"Cleanup: failed to delete {log_file}: {reason}\n"
    )
    target = _today_exceptions_log_path()
    fh = _open_for_append_with_lock_retry(target)
    if fh is None:
        return
    try:
        fh.write(line)
    finally:
        fh.close()
```

**Self-recovery contract**: every failure path is `continue` or the bare
`except Exception`. Cleanup NEVER crashes the app (PRD-005 prime
directive). The new `_emit_cleanup_failure` writer is itself wrapped in
the caller's `try/except Exception: pass` — if the cleanup-failure logger
ALSO fails (e.g., exception log is locked by 99 suffixes), the original
delete failure is silently dropped. Acceptable: cleanup is best-effort by
design and cleanup-of-cleanup-of-cleanup recursion is not a meaningful
guarantee to chase.

**Cleanup never writes to the journey log.** PRD-005's literal text said
"log to journey + continue"; this ADR (post-amendment) routes cleanup
failures to the **exception log** with the `INFO-CLEANUP` tag instead.
Rationale: the journey log is the user-action breadcrumb (the trail
Tomasz reads to reconstruct "what was the user doing right before the
bad thing"); cleanup-failure noise on it would drown the user-action
signal. The exception log is already the diagnostics surface; adding
diagnostics-about-diagnostics there is on-character. PRD-005 is amended
in lockstep; see PRD-005 changelog.

> **History** (kept for traceability of the design path): the original
> ADR-006 §3.6 silent-pass was a deviation from PRD-005 literal. User
> review (2026-05-09) preferred the middle path — neither silent nor
> journey-log-noise — and selected the `INFO-CLEANUP` →
> exception-log routing now codified above. The `verbose: bool = False`
> v2 flag the original deviation flagged is not introduced; the
> `INFO-CLEANUP` route IS the verbose mode, always on.

### 3.7 Bootstrap order

Per the dispatch's question "which logger initializes first?":

1. **`main.py` line 1-N**: imports.
2. **`install_python_excepthook()`** is called immediately. Hook is now
   live; any subsequent crash up to and through `MainLoop()` returning
   reaches it.
3. **`LoggingApp(False)`** is constructed. wxPython initializes; `OnInit`
   runs.
4. **Inside `OnInit`**:
   1. `init_logging(root_folder=None)` — opens `%LOCALAPPDATA%/.../logs/`
      as the active log dir (root not yet known). Logs the **session
      start** line:
      ```
      [2026-05-09 09:00:00] [INFO] [Person: -] App started, version 0.10.0, log_dir %LOCALAPPDATA%\PyTreeManager\logs
      ```
   2. `cleanup_old_logs()` — 14-day sweep on the active log dir.
   3. `AddPersonFrame(None)` is constructed. Its `__init__` sets
      `self._current_person_label = "-"`, then calls
      `tree_service.is_root_location_set()`. If root is not set, the
      folder picker dialog runs; once root is set,
      `init_logging(root_folder=<root>)` is called again (idempotent —
      flushes the active log dir to `<root>/logs/` and emits a "log dir
      relocated" line).
   4. `frame.Show()`.
5. **`app.MainLoop()`** enters. From here on, exceptions go through
   `OnExceptionInMainLoop`.

The first log line of every session is the "App started" INFO line.
This is the breadcrumb that says "the session began at HH:MM:SS"; if a
crash is reported later, the journey log read top-down starts from this
line.

**Idempotency of `init_logging`**: callable any number of times. First
call: open the determined log dir. Subsequent calls with a different
log dir: flush state, re-point. Subsequent calls with the same log dir:
no-op. This handles the AddPersonFrame-relocates-log-dir case naturally.

### 3.8 Pre-root fallback to `%LOCALAPPDATA%`

Per PRD-005, if `<root>` is not yet picked, logs go to
`%LOCALAPPDATA%/PyTreeManager/logs/`. Implementation:

```python
def _localappdata_log_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "PyTreeManager" / "logs"
    # LOCALAPPDATA unset (almost never on Windows; defensive)
    return Path(tempfile.gettempdir()) / "PyTreeManager" / "logs"
```

The `tempfile.gettempdir()` fallback survives unusual Windows setups
where `LOCALAPPDATA` is unset. PRD-005 flags this as
decision-revisitable; we keep it.

### 3.9a `log_error()` manual API (added 2026-05-09 amendment)

The decorator catches AT THE BOUNDARY (the wrapped handler's outer
frame). Before that boundary, an inner `try-except` block can catch and
recover — `frames/add_person_frame.py` has 10 such sites today (see
sprint plan Item 8). For all of them, the existing flow is:

```python
try:
    self._tree_service.rebuild_drzewo()
except Exception as e:
    polish_dialog(self, f"Nie udało się odświeżyć drzewa.\n\n{e}", ...)
    return
```

The exception never escapes to the decorator's outer except, so under
the original ADR-006 there is **no ERROR line in the exception log**.
ADR-007 §6.2 flagged this gap; user review confirmed it is unacceptable
in production posture (father's-machine, no remote-debug fallback).

**Resolution**: a parallel manual write path. The handler keeps its
existing `try-except polish_dialog return` shape and adds ONE line:
`logger.log_error(exc, context="...")` BEFORE the dialog. Existing
behavior (dialog content, return path, user-visible flow) is unchanged.

#### Signature

```python
def log_error(exc: BaseException, context: Optional[str] = None) -> None:
    """Write ONE ERROR line to today's exception log.

    Use INSIDE an inner `except` block that catches and recovers from an
    exception (typically followed by `polish_dialog` and `return`). The
    decorator's outer except handles uncaught exceptions; this helper
    handles the caught-and-handled case.

    Args:
        exc: the caught exception instance (the `e` in `except ... as e`).
        context: optional caller-supplied "what was happening" string.
            E.g., "Refresh Drzewo failed during rebuild" or "Save
            person, error during write to me.json". One line. Free-form.

    Output line shape (single ERROR block per ADR-007 §4.2,
    HEADER_MANUAL grammar):
      [ts] [ERROR] [Person: <label>] [source=manual] [context=<context>] <ExcClass>: <one-line msg>
        Traceback (most recent call last):
          ...
    When context is None, the [context=...] field is OMITTED entirely:
      [ts] [ERROR] [Person: <label>] [source=manual] <ExcClass>: <one-line msg>

    Person label: read from helpers.logger._last_known_person_label
    (the same module-level state the decorator and hooks read; updated
    by set_current_person_label). No `self` available at the call site
    — the function reads from module state, not from a frame attribute.

    Self-recovery: log_error MUST NOT raise. Wrap the entire body in
    try/except Exception; on any internal failure, fall through silently.
    The caller already has its own except path running; we will not
    mask a real error with a logger error.
    """
```

#### Pseudocode

```python
def log_error(exc: BaseException, context: Optional[str] = None) -> None:
    try:
        person_label = _read_global_person_label()  # falls back to "-"
        # Build header. Use type(exc).__name__ + str(exc) one-line.
        exc_class = type(exc).__name__
        one_line_msg = str(exc).replace("\n", "\\n").replace("\r", "\\r")
        ts = time.strftime(LOG_DATE_FORMAT)

        # Per ADR-007 §4.2 HEADER_MANUAL grammar: bracketed context
        # field, OMITTED entirely when caller passes context=None.
        ctx_field = f"[context={context}] " if context else ""
        header = (
            f"[{ts}] [ERROR] [Person: {person_label}] [source=manual] "
            f"{ctx_field}{exc_class}: {one_line_msg}\n"
        )

        # Traceback. Prefer traceback.format_exception(exc) (Python 3.10+
        # signature accepts the exception instance directly); fall back to
        # the (etype, value, tb) signature if older Python is in use.
        try:
            tb_lines = traceback.format_exception(exc)
        except TypeError:
            tb_lines = traceback.format_exception(
                type(exc), exc, exc.__traceback__
            )
        tb_block = "".join(tb_lines)
        tb_block_indented = "\n".join("  " + line for line in tb_block.splitlines())

        body = header + tb_block_indented + "\n"

        target = _today_exceptions_log_path()
        fh = _open_for_append_with_lock_retry(target)
        if fh is None:
            return  # Lock-cap exhausted; logger is best-effort.
        try:
            fh.write(body)
        finally:
            fh.close()
    except Exception:
        # Logger NEVER crashes the app. The caller's except path runs
        # regardless; we do not want a logger bug to mask a real bug.
        return
```

#### Worked example — `_on_refresh_drzewo_click` (lines 1425-1444)

This is the canonical case. The inner except at line 1437-1444 catches
any exception from `rebuild_drzewo()` and shows a Polish dialog. Today,
nothing reaches the exception log.

**Before amendment** (current code, lines 1435-1444):

```python
try:
    written, log = self._tree_service.rebuild_drzewo()
except Exception as e:
    polish_dialog(
        self,
        f"Nie udało się odświeżyć drzewa.\n\n{e}",
        "Błąd",
        wx.OK | wx.ICON_ERROR,
    )
    return
```

**After amendment** (Sprint 11 catch-site sweep, Item 8):

```python
try:
    written, log = self._tree_service.rebuild_drzewo()
except Exception as e:
    logger.log_error(e, context="Refresh Drzewo: rebuild_drzewo failed")
    polish_dialog(
        self,
        f"Nie udało się odświeżyć drzewa.\n\n{e}",
        "Błąd",
        wx.OK | wx.ICON_ERROR,
    )
    return
```

One added line. Dialog text, dialog title, button mask, return behavior
all unchanged.

#### Resulting log lines (worked trace)

Setup: user has loaded "Anna Staluszka" (so
`_last_known_person_label == "Anna Staluszka"`); clicks "Odśwież drzewo";
`rebuild_drzewo()` raises `RuntimeError("Korzeń nie istnieje")` for some
internal reason.

1. **Decorator INFO** (entry-side; `@log_user_action("Refresh Drzewo")`
   on the handler). `<today>__journey.log` gets:
   ```
   [2026-05-09 14:32:11] [INFO] [Person: Anna Staluszka] User clicked 'Refresh Drzewo'
   ```
2. **Manual ERROR** (from `log_error(e, context="...")` inside the inner
   except). `<today>__exceptions.log` gets:
   ```
   [2026-05-09 14:32:11] [ERROR] [Person: Anna Staluszka] [source=manual] [context=Refresh Drzewo: rebuild_drzewo failed] RuntimeError: Korzeń nie istnieje
     Traceback (most recent call last):
       File "frames/add_person_frame.py", line 1436, in _on_refresh_drzewo_click
         written, log = self._tree_service.rebuild_drzewo()
       File "services/tree_service.py", line ..., in rebuild_drzewo
         ...
     RuntimeError: Korzeń nie istnieje
   ```
3. **No CRITICAL line.** The exception is caught by the inner except;
   it never escapes to the decorator's outer except, never escapes to
   `OnExceptionInMainLoop`. The app continues.
4. The user sees the Polish dialog with the RuntimeError message.

**Net log output**: one INFO line in journey.log, one ERROR line in
exceptions.log with `[source=manual]` attribution, app continues.

#### Distinction from the decorator's ERROR path

| Aspect | Decorator (`source=decorator`) | Manual (`source=manual`) |
|---|---|---|
| Where the catch happens | Outer wrapper around the entire handler | Inner `except` inside the handler body |
| What the caller does next | Re-raises (decorator step 4 then `raise`); exception escapes to wxPython, triggers CRITICAL too | Continues (caller's recovery path runs: dialog, return, etc.) |
| Net log lines | 1 INFO + 1 ERROR + 1 CRITICAL | 1 INFO + 1 ERROR (NO CRITICAL — the app didn't terminate) |
| Has `context=` field | No (decorator doesn't get a free-form caller string) | Yes — caller passes `context="..."` to frame the situation |
| `payload:` line | Yes for save-handlers (whitelist) | No (the manual API doesn't auto-collect payload; if the caller wants payload, include it in `context=`) |

`grep '[source=decorator]'` filters to "the app caught it at the
boundary"; `grep '[source=manual]'` filters to "an inner handler
caught it and chose to keep running". Useful for triage.

#### Self-recovery — the `MUST NOT raise` contract

The function body is enclosed in `try/except Exception: return`. Every
internal failure mode is silenced:
- Exception log path unresolvable: `_today_exceptions_log_path()` itself
  is wrapped; if the active log dir is `None`, the helper returns a
  `Path` to `%LOCALAPPDATA%`.
- Lock-retry exhausted (`fh is None`): early `return`. The line is
  dropped.
- `traceback.format_exception` raises (very rare): caught by the outer
  `try/except`.
- Unicode encode error on `fh.write` (extremely rare with UTF-8): caught
  by the outer `try/except`.

**Why "must not raise" is critical**: the caller is already in an
exception-handling path. The pattern is:

```python
try:
    do_thing()
except Exception as e:
    logger.log_error(e, context="...")  # MUST not raise
    polish_dialog(self, str(e), ...)    # MUST run
    return
```

If `log_error` raised, control jumps out before the dialog runs and the
user gets nothing — worse, the new exception masks the original `e`.
The caller's recovery flow is sacrosanct; logging is observability,
not control flow.

### 3.9 `.gitignore` updates

Append to `.gitignore`:

```
# Diagnostic logs (Sprint 11+; logs are personal data, never committed)
logs/
# Sprint 12 introduces the offline-email queue; gitignored from day 1.
logs/pending/
```

(The `logs/pending/` line is added in Sprint 11 even though Sprint 12
populates the directory. Keeping the gitignore single-PR-per-sprint is
not worth the cost of someone forgetting the line in Sprint 12.)

The `<root>/logs/` literal pattern in PRD-005 is matched by the
non-anchored `logs/` glob in `.gitignore` because the user runs the app
from a working directory where `<root>` is configured separately and the
repo's `.gitignore` is anchored at repo root. The `logs/` directory in
the repo would only exist if a developer runs the test suite with the
repo as `<root>` — in which case it should still be ignored. Safe.

## 4. Alternatives considered

### 4.1 Decorator API mechanism (PRD-005 Architect-detail flag)

Three options on the table per PRD-005 §"Person-context capture
(architect-detail)":

**Option 1 — sentinel attribute on frame** (`self._current_person_label`).
**Picked.** Justification:
- The frame already owns the relevant state — `self.unique_identifier`,
  `self._is_edit_mode`, `self._original_name` all live on `self`. A
  label sentinel fits the existing mental model.
- Single-threaded wxPython: no race. No thread-local complication.
- Trivially debuggable: `print(self._current_person_label)` in any
  handler shows the current value.
- One-line `getattr(self, '_current_person_label', '-')` in the
  decorator. Robust to frames that don't set the sentinel.
- Six setter sites in the existing codebase (see §3.2 table). All are
  in `add_person_frame.py`. Mechanical.

**Option 2 — `contextvars.ContextVar`**. Rejected. ContextVar is the
right answer for `asyncio` or threading where a single global wouldn't
work. We have neither. Adds a layer of indirection (an extra import,
a `set` / `get` ceremony at every transition) for zero benefit.

**Option 3 — explicit `context: PersonContext` parameter**. Rejected.
Invasive: every handler signature changes from `(self, event)` to
`(self, event, context)`. Worse: `wx.Bind(EVT_MENU, handler)` doesn't
support extra positional args without partials. The cost-benefit is
strongly negative.

### 4.2 Use Python's stdlib `logging` module as the journey-log backend

Rejected as the **artifact format owner** (PRD-005 already locked plain
text + custom shape). May still be used **internally** as a thin file
handle — `logging.getLogger("journey")` with a `FileHandler` and a
custom `Formatter` could match the `[ts] [SEV] [Person: X] msg` shape.
Implementation choice deferred to Sprint 11 — if `logging.Formatter` is
cleaner than direct `file.write()`, use it. This ADR locks the artifact
shape, not the writer mechanism.

### 4.3 `traceback.print_exc()` to a single `app.log` instead of split files

Rejected. PRD-005 explicitly splits journey.log (low-signal-high-volume,
INFO only) from exceptions.log (high-signal-low-volume, ERROR + CRITICAL).
The split is on Tomasz's read pattern — he greps `[ERROR]` or tail-f
`exceptions.log` to monitor failures, and reads journey.log linearly to
reconstruct user actions before a failure. Mixing them costs grep on
every read.

### 4.4 Single global `try/except` wrapping `app.MainLoop()` instead of `OnExceptionInMainLoop`

This is the pre-Phoenix wxPython pattern (still seen in 2014-era
tutorials). Rejected for current code:
- `OnExceptionInMainLoop` is the documented Phoenix way and is more
  precisely scoped (wraps a single event dispatch, not the entire loop).
- `try/except app.MainLoop()` only catches exceptions that the event
  loop fails to handle internally — by Phoenix architecture, that's
  exactly what `OnExceptionInMainLoop` is for.
- The global `try/except` would still need a way to write to the log
  before re-raising. We'd be reinventing `OnExceptionInMainLoop` worse.

### 4.5 Per-handler `try/except` with manual ERROR logging (no decorator)

Rejected. This is the "literal" PRD-005 reading of "try/except
wrappers". Issues:
- Every handler needs the same boilerplate. Six handlers today, more
  added in future. Drift inevitable.
- Decorator is the wxPython community-recommended pattern (Robin Dunn,
  2014).
- The decorator IS a try/except wrapper — just one written once.

## 5. Pre-Implementor self-check (architect, 2026-05-09)

Per Sprint 09 retro lesson — example ↔ pseudocode parity check:

**Worked Example A** (`_on_refresh_drzewo_click`, person loaded):
- Pseudocode step 1 reads `getattr(self, '_current_person_label', '-')`.
  In Example A, `self._current_person_label == "Anna Staluszka"`. Trace
  produces `person_label = "Anna Staluszka"`. ✓
- Pseudocode step 2 calls `_emit_info("Anna Staluszka", "Refresh
  Drzewo")`. The expected log line shape is `[ts] [INFO] [Person: <name>]
  User clicked '<verb>'` — produced. ✓
- Pseudocode step 3 invokes `func(self, event)`. In Example A the
  function returns `None`. Wrapper returns `None`. ✓

**Worked Example B** (`_on_new_person_click`, no person loaded):
- `person_label = "-"` from `getattr` default since `__init__` set it
  to `"-"`. ✓
- INFO line produced with `[Person: -]`. ✓
- `_reset_to_add_mode()` calls `set_current_person_label(self, "New")`
  internally — verified against §3.2 table: yes, `_reset_to_add_mode`
  IS in the setter-sites list. ✓

**Worked Example C** (`on_save_click`, KeyError escapes):
- `person_label = "New"` (set by previous `_reset_to_add_mode` or by
  `_on_new_person_click`'s cascade). ✓
- INFO line emitted. ✓
- `_collect_save_payload_if_save_handler` returns the form payload.
  This helper has a whitelist `{on_save_click, on_save_edit_click,
  on_save_draft_click}` and a fallback that calls
  `self._collect_all_data_to_dict()`. Verified: the existing handlers
  at lines 852, 915, 1176 are exactly the whitelist. ✓
- ERROR line written with traceback + payload. ✓
- Wrapper re-raises. wxPython C++ event dispatch catches; calls
  `OnExceptionInMainLoop`. CRITICAL line written.
- ✓ — both ERROR and CRITICAL fire; this is documented as expected
  behavior (the note above Worked Example C's net output).

**Cross-check — `set_current_person_label` setter sites table (§3.2):**

| Site | New value | Verified against code? |
|---|---|---|
| `__init__` | `"-"` | New code (Sprint 11 adds the line) |
| `_reset_to_add_mode` | `"New"` | New code; site exists at line 1294 |
| `_load_person_for_edit` | `<full_name>` | Site exists at line 1240; sets `self._original_name` at line 1256 — same load point |
| `on_load_draft_click` | `f"Draft, {first_last}"` or `"Draft"` | Site exists at line 1196; loads via `_fill_form_from_draft` |

All four sites are real and in the right place. ✓

**Failure-mode end-to-end trace** (dispatch self-read item #2):

Scenario: father clicks "Zapisz" → `on_save_click` runs → KeyError
escapes from `save_person_and_add_to_tree`.

1. **Journey log (before exception)**: one INFO line —
   `[2026-05-09 14:40:22] [INFO] [Person: New] User clicked 'Save person (new)'`
2. **Decorator catches**: `_emit_error` writes one ERROR line (with
   payload + traceback) to today's exceptions.log.
3. **Decorator re-raises**: KeyError propagates out of `wrapper`.
4. **wxPython event dispatch**: catches at the Python/C++ boundary.
   Calls `LoggingApp.OnExceptionInMainLoop`.
5. **OnExceptionInMainLoop**: `sys.exc_info()` returns the same
   `(KeyError, ..., tb)`. `_emit_critical(...)` writes one CRITICAL line
   to today's exceptions.log. Returns `False`.
6. **wx event loop exits**. Process unwinds.
7. **`sys.excepthook`**: depending on how wxPython terminates the
   process, may or may not fire on the way out. If it does, a second
   CRITICAL line is written. Acceptable redundancy.
8. **What user sees**: app window closes. (Today's behavior is "app
   prints the exception and re-raises in `main.py`'s top-level
   try/except"; that gets replaced by the new hooks.)
9. **App continues?** No — uncaught exception means termination. This
   matches PRD-005's CRITICAL definition.

End-to-end coverage: journey log shows what the user did right before;
exceptions log shows the ERROR with payload; CRITICAL line records the
process-exit. Tomasz reads three pieces of evidence to reconstruct.

**Halt criterion match**: Sprint 11 plan's halt criteria include
"`sys.excepthook` doesn't fire on a forced uncaught exception in test"
— this trace shows that BOTH hooks should fire in this scenario. The
halt criterion is a spec match.

## 6. Consequences

**Positive:**
- All UI handler invocations leave a trail. Tomasz can reconstruct any
  session.
- Both exception hook points cover the disjoint failure surfaces;
  no uncaught exception escapes silent.
- Decorator is the smallest possible API — one annotation per handler.
- File-lock self-recovery means logs survive multi-process or
  antivirus-scan contention without dropping lines (within the 99-suffix cap).
- Logger is a single small module (`helpers/logger.py`); easy to test
  in isolation.

**Negative:**
- A single uncaught exception produces 2-3 log lines (INFO entry +
  decorator's ERROR + OnExceptionInMainLoop's CRITICAL). Acceptable
  redundancy; documented.
- The sentinel attribute requires discipline at every person-state
  transition. Six sites today; we'll add a Sprint-11 carry-forward to
  audit any new frame that adds a 7th transition site.
- `wx.App.OnExceptionInMainLoop` requires subclassing `wx.App`. Today's
  `main.py` uses `wx.App(False)` directly; Sprint 11 changes that to
  `LoggingApp(False)`.

**Neutral:**
- `helpers/logger.py` is the single import surface for the rest of the
  codebase. `frames/` imports `log_user_action` and
  `set_current_person_label`. `services/` does NOT import the logger
  (services aren't decorated; PRD-005 + dispatch confirm).

## 7. Out of scope

- Email escalation (Sprint 12; PRD-006).
- The "Wyślij raport o błędzie" red button (Sprint 12).
- Rate limiting on email send (user accepted no-rate-limit).
- PII scrub inside log lines (PRD-005 explicit: PII inside logs is
  intentional; gitignore enforces the boundary).
- Sweeping existing `print` calls in the codebase (Sprint 13+ if useful;
  out for now).
- Decorating service-layer methods (`drzewo_service`, `rody_service`,
  etc.) — explicitly out per dispatch.

## 8. Sources

- `PRD-005-diagnostic-logging-foundation.md` — scope contract.
- JOURNAL 2026-05-09 orchestrator entry "PM defaults review" — locked
  user decisions for Sprint 11 (do-both, sentinel, person placeholder).
- `1-architecture/discovery/kb-wxpython-exception-hooks-snapshot.md` —
  research synthesis for the dual-hook integration.
- `1-architecture/discovery/kb-wxpython-gotchas-localized-elderly-ui-snapshot.md` —
  Gotcha 4 (`event.Skip()` discipline) and the decorator's interaction
  with wx event propagation.
- https://docs.wxpython.org/wx.AppConsole.html — wxPython 4.x AppConsole
  surface.
- https://docs.wxpython.org/events_overview.html — "If an exception is
  thrown in event handler, wx.App.OnExceptionInMainLoop is called".
- https://wiki.wxpython.org/CustomExceptionHandling — historical pattern
  (older, still partially valid).
- https://www.blog.pythonlibrary.org/2014/03/14/wxpython-catching-exceptions-from-anywhere/ —
  Robin Dunn's decorator pattern (origin of the `exception_logger` shape
  this ADR extends).
- https://docs.python.org/3/library/sys.html#sys.excepthook — Python
  stdlib hook contract.
- `frames/add_person_frame.py` lines 36-115, 852-1475, 1240-1352 —
  existing handler surface and person-state transition sites referenced
  by §3.2's setter table.
- `main.py` — current entry point that this ADR's bootstrap order
  modifies (lines 4-10, the `wx.App(False)` block).
