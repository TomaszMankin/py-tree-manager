---
id: ADR-007
title: Severity model + log-line format — INFO/ERROR/CRITICAL semantics, line-shape grammar, ERROR vs CRITICAL distinction in code
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
  - ADR-006 (logging architecture — companion ADR)
sources:
  - .pipeline/decisions/PRD-005-diagnostic-logging-foundation.md
  - .pipeline/JOURNAL.md 2026-05-09 orchestrator entry "PM defaults review"
  - .pipeline/decisions/ADR-006-logging-architecture-decorator-and-exception-hooks.md
  - https://docs.python.org/3/library/traceback.html#traceback.format_exception
---

# ADR-007 — Severity model + log-line format

> Companion to ADR-006 (logging architecture). Read together.

## 0. Changelog

- **2026-05-09 (initial)** — first issue.
- **2026-05-09 (same-day amendment, this revision)** — three changes
  per orchestrator dispatch and JOURNAL line 1213+:
  1. **Added `INFO-CLEANUP` severity tag** to the enumeration (§3 + new
     §4.5). Used only by the cleanup subsystem when it cannot delete a
     retention-expired log file. Lives in the exception log so the
     journey log stays a pure user-action narrative. Cleanup-failure
     volume is bounded (one per failed file per session, 14-day window
     means at most a handful per startup).
  2. **Added `[source=...]` field to ERROR lines** (§4.2 grammar update).
     Distinguishes ERROR-from-decorator-outer-except (the original
     "we caught it before re-raise" path) from ERROR-from-manual-call
     (the new ADR-006 §3.10 `log_error()` API). Field values:
     `decorator` | `manual`. Lets Tomasz `grep '[source=manual]'` to
     isolate inner-caught-and-handled errors from
     decorator-caught-and-re-raised errors.
  3. **§5.1 + §6.2 updated** — caught-and-handled exceptions are no
     longer invisible. The §5.1 trade-off "no manual ERROR API" is
     superseded; ADR-006 §3.10 introduces `log_error()` and Sprint 11's
     catch-site sweep populates the existing inner-except sites with
     calls. The §6.2 KeyError-in-compute_membership trace is rewritten
     to show the manual ERROR line.

## 1. Context

PRD-005 locks the three-level severity model (INFO/ERROR/CRITICAL). The
PM-default review (JOURNAL 2026-05-09) leaves the **artifact line shape**
as ADR territory:

- The exact byte-level grammar of an INFO line and an ERROR/CRITICAL line.
- How the timestamp, severity tag, person field, handler-name field,
  exception class, and traceback are assembled.
- How ERROR and CRITICAL are *distinguished in code* (which code path
  produces which severity).
- How a real concrete failure (Polish-character path issue, KeyError in
  `compute_membership`) walks through this model.

ADR-006 §3.3 already includes worked examples; this ADR is the
canonical reference for the line-shape contract.

## 2. Decision (one paragraph)

INFO lines: single-line `[ts] [INFO] [Person: <label>] User clicked
'<verb>'`. ERROR lines: header line `[ts] [ERROR] [Person: <label>]
handler=<name> <ExcClass>: <one-line message>`, optional `payload: <repr>`
line for save-handlers, then the indented traceback. CRITICAL lines:
identical to ERROR but `[CRITICAL]` and `source=<excepthook|wx-mainloop>`
field instead of `handler=<name>`. ERROR is produced by the decorator's
`except Exception:` arm (the "we caught it before re-raise" record);
CRITICAL is produced by `sys.excepthook` and
`wx.App.OnExceptionInMainLoop` (the "process is terminating" record).
Both routes write to the same `<date>__exceptions.log` file. INFO writes
to the separate `<date>__journey.log`.

## 3. Severity contract — what produces which level

| Severity | Producer | Code path | Example trigger |
|---|---|---|---|
| INFO | `@log_user_action(verb)` decorator, entry side | Step 2 of decorator (see ADR-006 §3.3) | Every UI handler invocation. |
| INFO-CLEANUP | `_emit_cleanup_failure(...)` inside `cleanup_old_logs` | Per-file failure branch (see ADR-006 §3.6, amended 2026-05-09) | A retention-expired `*.log` file could not be deleted (locked, permission denied, etc.). Lives in **exception log** despite the INFO prefix — see §4.5. |
| ERROR (decorator) | `@log_user_action(verb)` decorator, outer except arm | Step 4 of decorator (see ADR-006 §3.3) | An exception escapes the wrapped handler's inner try/excepts (or the handler has none). The decorator catches, logs ERROR with `[source=decorator]`, re-raises. |
| ERROR (manual) | `log_error(exc, context)` (see ADR-006 §3.10, added 2026-05-09) | Caller's inner `except` block before recovery | A handler caught an exception, wants to recover (show dialog + return), but also wants visibility in the exception log. Logs ERROR with `[source=manual]` and a `context=` field; does NOT re-raise. |
| CRITICAL | `sys.excepthook` *or* `wx.App.OnExceptionInMainLoop` (whichever fires) | `_emit_critical(...)` in either hook | Uncaught exception that escapes all decorators (i.e., the same exception that was just logged ERROR by the decorator now bubbles up — see §4.3). Or: an exception during app startup before any handler is wired. |

**Manual ERROR API** (added 2026-05-09 amendment): per ADR-006 §3.10,
`log_error(exc, context)` is the sanctioned way to record a
caught-and-handled exception that the caller has decided to recover
from (typically followed by `polish_dialog` + `return`). Distinct from
the decorator's outer except path:

- **Decorator path** = "the handler had no inner protection (or its
  inner protection was narrower than what fired); the wrapper caught
  it; we log ERROR and re-raise". Re-raise → CRITICAL via hook → app
  terminates.
- **Manual path** = "the handler had an inner `try-except` that
  recovers; we log ERROR but do NOT re-raise; app continues". No
  CRITICAL, no termination.

The two paths are indistinguishable on the line shape EXCEPT for the
new `[source=...]` field. `grep '[source=decorator]'` finds
caught-by-wrapper events (every one of these has a matching CRITICAL);
`grep '[source=manual]'` finds caught-by-inner-handler events (no
CRITICAL).

There remains **no public API to "log a CRITICAL manually"**. CRITICAL
is reserved for the hook layer (the "process is terminating" record).
A handler that catches an exception and chooses to recover writes
`log_error`, not "log_critical" — by definition, choosing to recover
means it isn't critical.

> **PRD-005 contract update**: PRD-005 originally locked "no API to
> 'log an ERROR manually'". As of the 2026-05-09 amendment, this is
> relaxed in lockstep — the manual ERROR API exists at exactly one
> entry point (`log_error`), the severity boundaries are still crisp
> (the function is named for what it does and only writes ERROR; no
> free-form severity-as-string parameter), and the user's stance shift
> from "demo, errors don't matter" to "production, I need visibility on
> every error" is the rationale. See PRD-005 changelog.

## 4. Line-shape grammar

### 4.1 INFO line — single-line

Grammar (ABNF-ish):

```
INFO_LINE = "[" TS "] [INFO] [Person: " PERSON "] User clicked '" VERB "'\n"
TS        = "%Y-%m-%d %H:%M:%S"   ; e.g. 2026-05-09 14:32:11
PERSON    = "-" | "New" | "Draft" | "Draft, " NAME | NAME
NAME      = UTF-8-bytes          ; person's full_name; never quoted
VERB      = ASCII-or-UTF-8       ; e.g. "Save person", "Refresh Drzewo"
```

Concrete examples:

```
[2026-05-09 09:00:00] [INFO] [Person: -] App started, version 0.10.0, log_dir C:\Users\Father\AppData\Local\PyTreeManager\logs
[2026-05-09 09:00:14] [INFO] [Person: -] User clicked 'Pick root folder'
[2026-05-09 09:00:31] [INFO] [Person: -] User clicked 'Open person for edit'
[2026-05-09 09:00:33] [INFO] [Person: Anna Staluszka] User clicked 'Refresh Drzewo'
[2026-05-09 09:01:02] [INFO] [Person: New] User clicked 'Save person (new)'
[2026-05-09 09:01:18] [INFO] [Person: Draft, Adam K] User clicked 'Save draft'
```

The "App started" first-line shape is a special case — the decorator
isn't involved; `init_logging()` writes it directly. Same line shape
(INFO + person `-`) for consistency.

### 4.2 ERROR line — multi-line block

Grammar (amended 2026-05-09 — added `[source=...]` field; manual path
swaps `handler=<name>` for `context=<string>`):

```
ERROR_BLOCK    = HEADER "\n" [PAYLOAD "\n"] TRACEBACK
HEADER         = HEADER_DECORATOR | HEADER_MANUAL
HEADER_DECORATOR = "[" TS "] [ERROR] [Person: " PERSON "] [source=decorator] handler=" HANDLER_NAME " " EXC_CLASS ": " ONE_LINE_MSG
HEADER_MANUAL    = "[" TS "] [ERROR] [Person: " PERSON "] [source=manual] [context=" FREE_TEXT "] " EXC_CLASS ": " ONE_LINE_MSG
PAYLOAD        = "  payload: " PYTHON_REPR_DICT
TRACEBACK      = traceback.format_exception(...) joined by "\n", indented 2 spaces
```

The HEADER fits on one line (single-line greppable). PAYLOAD only
appears for the **decorator path**, and only if the handler is in the
save-handler whitelist (`{on_save_click, on_save_edit_click,
on_save_draft_click}`). The manual path does NOT auto-collect payload —
if the caller wants to encode payload-like context, they pack it into
the `context=` string.

The `context=` field in the manual path is OMITTED entirely (not even
the field name) when the caller passes `context=None`:

```
[ts] [ERROR] [Person: X] [source=manual] RuntimeError: foo
```

vs

```
[ts] [ERROR] [Person: X] [source=manual] [context=Refresh Drzewo failed] RuntimeError: foo
```

TRACEBACK is the standard Python traceback (decorator and manual paths
both indent 2 spaces; same shape).

Concrete example, **decorator path** (Worked Example C from ADR-006 —
KeyError escapes `on_save_click`):

```
[2026-05-09 14:40:22] [ERROR] [Person: New] [source=decorator] handler=on_save_click KeyError: 'uid-cafef00d'
  payload: {'first_name': 'Adam', 'other_first_names': '', 'last_name': 'Kowalski', 'sex': 'M', 'parents_id': ['uid-aaa', 'uid-bbb'], 'children_id': [], ...}
  Traceback (most recent call last):
    File "frames/add_person_frame.py", line 883, in on_save_click
      self._tree_service.save_person_and_add_to_tree(person_data)
    File "services/tree_service.py", line 412, in save_person_and_add_to_tree
      parent_folder = self._cached_people[parent_uid]
  KeyError: 'uid-cafef00d'
```

Concrete example, **manual path** (the post-amendment shape of
`_on_refresh_drzewo_click` line 1437 catch site):

```
[2026-05-09 14:32:11] [ERROR] [Person: Anna Staluszka] [source=manual] [context=Refresh Drzewo: rebuild_drzewo failed] RuntimeError: Korzeń nie istnieje
  Traceback (most recent call last):
    File "frames/add_person_frame.py", line 1436, in _on_refresh_drzewo_click
      written, log = self._tree_service.rebuild_drzewo()
    File "services/tree_service.py", line ..., in rebuild_drzewo
      ...
  RuntimeError: Korzeń nie istnieje
```

Both end in today's `__exceptions.log`. `grep '[source=manual]'` surfaces
the second; `grep '[source=decorator]'` surfaces the first.

Notes on the line shape:

- HEADER is single-line so `grep "[ERROR]"` finds the entry.
- `EXC_CLASS: ONE_LINE_MSG` reuses Python's standard `repr(exc)` style.
  If `str(value)` contains newlines, they are replaced with `\n` literal
  (escaped) so the header stays single-line.
- PAYLOAD uses `repr(dict)` not JSON. Polish characters survive (Python
  3 `repr` is Unicode-clean). Keys appear in insertion order.
- TRACEBACK is indented 2 spaces. This is to make the header visually
  distinct in `tail -f` and to keep grep filters working
  (`grep -v '^  '` shows only headers).

### 4.3 CRITICAL line — multi-line block

Identical to ERROR except the severity tag is `[CRITICAL]` and the
`handler=<name>` field is replaced by `source=<...>`:

```
CRITICAL_BLOCK = HEADER "\n" TRACEBACK
HEADER         = "[" TS "] [CRITICAL] [Person: " PERSON "] source=" SOURCE " " EXC_CLASS ": " ONE_LINE_MSG
SOURCE         = "sys.excepthook" | "wx.App.OnExceptionInMainLoop"
```

(No PAYLOAD line — CRITICAL doesn't have a save-handler context to dump.
The exception triple has the traceback, which already contains the
function names.)

Concrete example (the same KeyError as Example C, after re-raise):

```
[2026-05-09 14:40:22] [CRITICAL] [Person: New] source=wx.App.OnExceptionInMainLoop KeyError: 'uid-cafef00d'
  Traceback (most recent call last):
    File "frames/add_person_frame.py", line 883, in on_save_click
      self._tree_service.save_person_and_add_to_tree(person_data)
    File "services/tree_service.py", line 412, in save_person_and_add_to_tree
      parent_folder = self._cached_people[parent_uid]
  KeyError: 'uid-cafef00d'
```

Note: the timestamp may differ from the ERROR line by a few milliseconds
because the decorator captures one timestamp and the hook captures another.
That's fine — both are wall-clock at write time, not "the moment the
exception was raised". For grouping ERROR + CRITICAL pairs, Tomasz
reads by handler name + traceback shape, not millisecond timestamp
matching.

### 4.4 File assignment

| Severity | File |
|---|---|
| INFO | `<logdir>/<YYYY-MM-DD>__journey.log` |
| INFO-CLEANUP | `<logdir>/<YYYY-MM-DD>__exceptions.log` (despite the INFO prefix; see §4.5) |
| ERROR (decorator) | `<logdir>/<YYYY-MM-DD>__exceptions.log` |
| ERROR (manual) | `<logdir>/<YYYY-MM-DD>__exceptions.log` |
| CRITICAL | `<logdir>/<YYYY-MM-DD>__exceptions.log` (same file as ERROR; severity tag distinguishes) |

ERROR (both flavors), CRITICAL, and INFO-CLEANUP share `__exceptions.log`.
PRD-005 §"What gets logged — exceptions log" specifies the file for the
exception data; the same file is the natural home for
diagnostics-about-diagnostics (cleanup failures) since both are
"non-user-action" data Tomasz reads when something looks wrong. Tomasz
filters with `grep '[ERROR]'`, `grep '[CRITICAL]'`,
`grep '[INFO-CLEANUP]'`, or `grep '[source=manual]'` to slice the file.

### 4.5 INFO-CLEANUP line — single-line (added 2026-05-09 amendment)

The cleanup subsystem (ADR-006 §3.6, the 14-day sweep on `OnInit`)
emits one `INFO-CLEANUP` line per failed-to-delete file. Lives in the
exception log so the journey log stays a pure user-action narrative.

Grammar:

```
INFO_CLEANUP_LINE = "[" TS "] [INFO-CLEANUP] [Person: " PERSON "] Cleanup: failed to delete " PATH ": " REASON "\n"
PATH              = absolute Path of the file the cleanup tried to delete
REASON            = ExcClass + ": " + str(exc)  ; one line, newlines escaped
```

Concrete example:

```
[2026-05-09 09:01:14] [INFO-CLEANUP] [Person: -] Cleanup: failed to delete C:\Users\Father\AppData\Local\PyTreeManager\logs\2026-04-25__journey.log: PermissionError: [WinError 32] The process cannot access the file because it is being used by another process
```

PERSON is typically `-` because cleanup runs early in `OnInit` (before
any frame loads), but it reads `_last_known_person_label` like every
other writer — if a future startup-time change happens to set the
label first, the line will reflect it. Single-line, no traceback (the
exception class + message is enough; cleanup-failure is not the kind of
defect that needs a stack walk to diagnose — it's a Windows file-lock
or NTFS permission story, not a code path).

**Semantic**: "diagnostics-about-diagnostics". Used only by the cleanup
subsystem when it cannot delete a retention-expired log file. NOT
escalated by Sprint 12's email channel (per PRD-006 in Sprint 12 — only
ERROR + CRITICAL are eligible; this is bounded noise we don't want
emailed). NOT counted as an ERROR for any grep-based "did anything go
wrong this session" check.

**Volume bound**: at most a handful per startup. The 14-day sweep
inspects at most ~28 files per directory (2 logs × 14 days), and only
files whose mtime indicates expiry are touched. Cleanup failures are
rare (the most likely cause is a previous app-instance still holding
the file open, which resolves on next session). Bounded by design.

## 5. ERROR vs CRITICAL — code-side distinction

This section answers the dispatch's spec-out requirement:
> "ERROR vs CRITICAL distinction in code: ERROR = `try: ... except:
> log_error(); show_user_notification(); continue`. CRITICAL = `except:
> log_critical(); raise`. Spell out which exceptions get which."

The reality is slightly different from the dispatch wording — the
decorator does NOT call `show_user_notification`; the original handler's
own try/except does that. Let me spell out the actual flow:

### 5.1 ERROR path — caught-and-handled (manual API, post-amendment)

> **Amended 2026-05-09**: original §5.1 said "inner-caught exceptions do
> not produce an ERROR line in this design". User review reversed that
> trade-off; Sprint 11 ships with `log_error()` (ADR-006 §3.10) AND a
> catch-site sweep (sprint-11 plan Item 8) that populates every existing
> inner `except polish_dialog` site with a `log_error` call. The
> revised §5.1 below describes the post-amendment flow.

A handler with its own internal `try-except` catches a recoverable
exception, calls `logger.log_error(exc, context="...")` BEFORE its
existing dialog/return path, and continues. Example: `on_save_click`
catches `ValueError` from `_resolve_relationship_paths` (lines 869-872
in current code; Sprint 11 sweep adds the `log_error` call):

```python
@log_user_action("Save person (new)")
def on_save_click(self, event: wx.Event) -> None:
    # ...
    try:
        self._resolve_relationship_paths(person_data)
    except ValueError as e:
        logger.log_error(e, context="Save person (new): resolve_relationship_paths failed")
        polish_dialog(self, str(e), "Błąd danych", wx.OK | wx.ICON_ERROR)
        return  # Handled, no re-raise; decorator never sees it.
    # ...
```

Outcome:
1. INFO line on entry (decorator step 2).
2. **ERROR line with `[source=manual]`** in today's exception log (the
   new `log_error` call).
3. User sees the `polish_dialog`. App continues.
4. No CRITICAL — the exception is caught by the inner except; never
   reaches the decorator's outer except; never escapes to the hook layer.

The decorator's outer except is still a backstop — it only fires when
the inner except either doesn't exist or fires a narrower class than
the inner protects against.

#### Distinction from §5.2 (decorator-caught)

| Path | Trigger | What happens |
|---|---|---|
| §5.1 manual | Inner `except` catches; calls `log_error`; recovers | INFO + ERROR(`source=manual`); app continues; no CRITICAL |
| §5.2 decorator | No inner except OR inner except too narrow; outer wrapper catches | INFO + ERROR(`source=decorator`); decorator re-raises; CRITICAL via hook; app terminates |

#### Why both paths exist (the rationale captured for future readers)

The original ADR-007 took the position that ERROR was a property of "how
the line was produced", with the decorator's outer except being the
sole producer. The user's stance during Sprint 11 design review shifted
the requirement from "demo phase, errors don't matter" to "production
on father's machine, I need visibility on every error". Caught-and-handled
exceptions are EXACTLY the class of error that's most likely to recur
(if it crashed, the user sees the dialog and tells the developer; if
it's caught, the user shrugs and moves on, and no one knows). The
manual API closes the gap.

**Severity boundaries are still crisp** (the original concern):
`log_error` only writes ERROR; there is no free-form severity-as-string
parameter; CRITICAL remains hook-only. The relaxation is in *who can
write ERROR* (now: decorator + `log_error`), not in *how severity is
chosen*.

### 5.2 ERROR path via decorator (caught by outer wrapper)

A handler that has NO inner try/except around the failing line, OR an
inner try/except that catches a narrower exception class than what
actually fires, escapes the inner protection. The decorator's outer
wrapper catches the escaped exception, emits ERROR, re-raises.

Example: `on_save_click` line 883 — `save_person_and_add_to_tree(...)`
is NOT inside a try/except in the current code (line 882-884 is bare).
A `KeyError` from there escapes to the decorator. ERROR fires.

Then the re-raise propagates to wxPython, which calls
`OnExceptionInMainLoop`. CRITICAL fires.

### 5.3 CRITICAL path (uncaught)

CRITICAL is always written from the hook layer (`sys.excepthook` or
`OnExceptionInMainLoop`). The decorator does NOT emit CRITICAL — its
job is bounded at "log + re-raise". The hook layer's job is bounded at
"log + decide whether to terminate".

This means a single uncaught exception produces:

1. INFO line on handler entry (decorator step 2).
2. ERROR line in `__exceptions.log` (decorator step 4).
3. CRITICAL line in `__exceptions.log` (`OnExceptionInMainLoop` step).

Three lines, all attributable. Tomasz reads:
- Journey log → sees what the user did.
- Exceptions log → sees the ERROR with payload + traceback (the
  diagnostic gold) AND the CRITICAL line (proof the app exited because
  of this).

### 5.4 What if the original handler IS already in a try/except?

The decorator does not interfere. The inner try/except runs first:
- If it catches: inner code's `polish_dialog` runs; `return`; decorator's
  outer except is NOT entered; no ERROR or CRITICAL line. INFO remains.
- If it does not catch (or re-raises): decorator's outer except runs;
  ERROR line; re-raise; CRITICAL via hook.

This is the "ERROR vs CRITICAL distinction in code" answer the dispatch
asked for, expressed precisely.

## 6. Worked examples (full traces)

### 6.1 Worked example — Polish-character path issue

**Setup**: user is on a freshly-installed Windows machine with username
`Łukasz`. User picks `<root> = C:\Users\Łukasz\Drzewo`. App tries to
save a person; the save fails because some downstream COM call doesn't
handle the path encoding correctly.

**Specific failure**: `save_person_and_add_to_tree` calls
`shortcut_helper.create_shortcut(target_path=...)`. The IShellLink path
should handle Unicode (per ADR-001), but suppose for argument's sake
that an unrelated `os.makedirs` call inside the save flow fails:

```python
# Inside services/file_service.py
os.makedirs(folder_path, exist_ok=True)
# OSError: [WinError 123] The filename, directory name, or volume label syntax is incorrect: '...\\Łukasz\\Drzewo\\...'
```

**Trace**:

1. User clicks "Zapisz". `_current_person_label == "New"`.
2. **Decorator INFO**: journey.log gets:
   ```
   [2026-05-09 16:14:02] [INFO] [Person: New] User clicked 'Save person (new)'
   ```
3. `on_save_click` runs. Validation, collect, resolve, preflight all
   pass. `save_person_and_add_to_tree` called at line 883. NOT inside
   inner try/except.
4. Deep stack: `os.makedirs` raises `OSError`.
5. **Decorator ERROR**: exceptions.log gets:
   ```
   [2026-05-09 16:14:02] [ERROR] [Person: New] handler=on_save_click OSError: [WinError 123] The filename, directory name, or volume label syntax is incorrect: 'C:\\Users\\Łukasz\\Drzewo\\Anna Kowalski\\me.json'
     payload: {'first_name': 'Anna', 'last_name': 'Kowalski', 'sex': 'F', ...}
     Traceback (most recent call last):
       File "frames/add_person_frame.py", line 883, in on_save_click
         self._tree_service.save_person_and_add_to_tree(person_data)
       ...
       File "services/file_service.py", line 215, in _create_person_folder
         os.makedirs(folder_path, exist_ok=True)
     OSError: [WinError 123] The filename...
   ```
6. Decorator re-raises.
7. wxPython catches at boundary; calls `OnExceptionInMainLoop`.
8. **CRITICAL**: exceptions.log gets:
   ```
   [2026-05-09 16:14:02] [CRITICAL] [Person: New] source=wx.App.OnExceptionInMainLoop OSError: [WinError 123] The filename...
     Traceback (most recent call last):
       ...
   ```
9. App terminates. User sees the wx top-level dialog (or just the window
   closing, depending on wx version).

**What Tomasz reads** (sent by father via "send error report" red button
in Sprint 12; for Sprint 11, walked through reading the file directly):
- INFO line says father clicked Save with a new person.
- ERROR line names the person being saved (`payload`), the exact
  exception class + message (path encoding issue at WinError 123), and
  the line where it fired (`os.makedirs`).
- CRITICAL line confirms the app exited because of this.

Diagnostic gold for "what was the user doing, what specifically went
wrong, why did the app close".

### 6.2 Worked example — KeyError in `compute_membership` (post-amendment)

> **Amended 2026-05-09**: this example previously demonstrated the gap
> ("no ERROR line because the inner except swallowed the exception").
> User review closed the gap; the trace below is the post-amendment
> flow with `log_error()` (ADR-006 §3.10) wired into the catch site.

**Setup**: father clicks "Odśwież drzewo". `_current_person_label ==
"Anna Staluszka"` (loaded from a recent edit). The Drzewo root is set.
`rebuild_drzewo` calls `compute_membership(root_uuid)` which fails on a
stale `cached_people` lookup.

**Specific failure**: `cached_people` was populated at frame-init time,
but a person was added (and the cache wasn't refreshed) between init
and the click. `compute_membership` tries to look up a uid that's
missing.

**Code shape** (post-Sprint-11 catch-site sweep, lines 1435-1444):

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

**Trace**:

1. User clicks "Odśwież drzewo". `_current_person_label ==
   "Anna Staluszka"`.
2. **INFO** (decorator step 2): journey.log gets:
   ```
   [2026-05-09 16:20:11] [INFO] [Person: Anna Staluszka] User clicked 'Refresh Drzewo'
   ```
3. `_on_refresh_drzewo_click` runs. The `try` block at line 1435 calls
   `rebuild_drzewo()`.
4. `rebuild_drzewo` calls `compute_membership` which raises
   `KeyError('uid-zzz')`.
5. The handler's INNER `except` (line 1437) catches it. The new first
   line of the except body calls `log_error(e, context="...")`.
6. **`log_error` writes ERROR (manual)**: exceptions.log gets:
   ```
   [2026-05-09 16:20:11] [ERROR] [Person: Anna Staluszka] [source=manual] [context=Refresh Drzewo: rebuild_drzewo failed] KeyError: 'uid-zzz'
     Traceback (most recent call last):
       File "frames/add_person_frame.py", line 1436, in _on_refresh_drzewo_click
         written, log = self._tree_service.rebuild_drzewo()
       File "services/tree_service.py", line ..., in rebuild_drzewo
         membership = compute_membership(root_uuid)
       File "services/drzewo_service.py", line ..., in compute_membership
         person = cached_people[uid]
     KeyError: 'uid-zzz'
   ```
7. The decorator's outer except is NOT reached (inner except handled
   and didn't re-raise). No CRITICAL.
8. User sees the Polish dialog with the KeyError repr in it.
9. App continues. `_on_refresh_drzewo_click` returns normally.

**What Tomasz reads**:
- Journey log: "User clicked 'Refresh Drzewo'" — establishes the user
  intent and the time.
- Exception log: ERROR line with `[source=manual]`, the
  `[context=...]` framing, the exception class+message, and the full
  traceback through `compute_membership`. Diagnostic gold.

**No more trade-off.** Pre-amendment §5.1 said this case left
"NO trail in the exception log". Post-amendment, it leaves an ERROR
line attributable to the catch site, with the same diagnostic content
as the decorator path's ERROR line (minus the `payload:` line, which is
decorator-path-only — but the `context=` field carries the
caller-supplied framing in its place).

**Architect note for Implementor**: the `log_error` call MUST come
BEFORE the `polish_dialog` call. Order matters because (a) the
exception object `e` is still captured at this point, (b) if
`polish_dialog` somehow itself raises (extremely unlikely, but a
defensive concern), the log_error has already happened. The pattern
is: log first, recover second.

### 6.3 Worked example — exception during app startup

**Setup**: app is launched but `wx` import fails (broken venv). This
fires before the wx event loop, before `OnExceptionInMainLoop` exists.

**Trace**:

1. `main.py` line 1 imports `wx`. ImportError.
2. `sys.excepthook` is NOT yet installed (we install it at line 6 of
   the new `main.py` — *after* wx is imported, because `LoggingApp`
   needs `wx`). Python's default excepthook prints to stderr.
3. Process exits with no log line.

**Mitigation**: this is unavoidable for the `import wx` failure
specifically — there's no way to install our hook before importing wx.
For ANY OTHER import-time failure (`from frames.add_person_frame import
AddPersonFrame`, etc.), we can install the Python hook before the
heavyweight imports:

```python
# main.py — Sprint 11 shape
import sys
from helpers.logger import install_python_excepthook  # cheap, no wx

install_python_excepthook()

import wx
from helpers.logger import init_logging, LoggingApp
from frames.add_person_frame import AddPersonFrame
# ... rest ...
```

**But wait** — `helpers.logger` itself imports `wx` for `LoggingApp`.
We split: `install_python_excepthook` lives at module scope; the
`LoggingApp` class is a deferred import via `_get_logging_app()` factory.
Or, `install_python_excepthook` lives in a `helpers/_python_excepthook.py`
sub-module that does NOT import wx, with `helpers.logger` doing the wx
imports separately. Implementor's call on the exact split. The
*contract* is: `install_python_excepthook` must be importable and
callable before `import wx`.

If `import wx` itself fails — that's the one case neither hook
catches. The user sees "ModuleNotFoundError: wx" on stderr. The fallback
is the OS event log (Windows) or `2>&1` redirection if the user runs
from a console. PRD-005 doesn't require we cover this; we don't.

## 7. Alternatives considered

### 7.1 4-level severity (DEBUG/INFO/WARN/ERROR)

Rejected per PRD-005. Three levels are sufficient and the user
explicitly introduced the 3-level model. DEBUG would invite log noise;
WARN would invite "what's the difference between WARN and ERROR" arguments.

### 7.2 JSON-lines or logfmt format instead of bracketed plain text

Rejected per PRD-005 ("Plain text") and per the user's "5-min ship"
constraint. The `[ts] [SEV] [Person: X]` shape grep-friendly,
tail-f-friendly, copy-pasteable into chat. JSON-lines requires Tomasz
to pipe through `jq`; logfmt requires a parser. Plain text wins on
"open in Notepad++ and read".

### 7.3 Single combined log file (`<date>.log`) with all severities

Rejected per PRD-005 ("Two log files per day"). The journey log is
high-volume and the exception log is high-signal. Splitting saves grep
on every read; mixing costs grep on every read.

### 7.4 ISO-8601 timestamp with microsecond precision

Rejected for default. `[2026-05-09 14:32:11]` is a second-precision
human-readable shape. Microseconds add noise without diagnostic value
for human-paced UI events. If Sprint N introduces async or timer-driven
events that fire faster than 1Hz, revisit.

### 7.5 Localized severity tags (`[BŁĄD]` instead of `[ERROR]`)

Rejected. The reader is Tomasz (English-fluent; codes Python in
English). Polish severity tags would force a grep+sed pipeline and
break the muscle memory of every other Python developer who might read
the file. The Polish-language constraint is for father-facing UI text,
not Tomasz-facing diagnostic artifacts.

## 8. Pre-Implementor self-check (architect, 2026-05-09)

Per Sprint 09 retro lesson — example ↔ pseudocode parity check:

**Worked example 6.1 (Polish path)**:
- §4.2 grammar matches the example: HEADER + PAYLOAD + TRACEBACK
  produced. ✓
- §5.2 "no inner try/except → decorator catches" matches: line 883 of
  `on_save_click` is bare. ✓
- §3 table maps OSError to ERROR (decorator's except arm): trace shows
  decorator step 4 fires. ✓
- §3 table maps re-raised OSError to CRITICAL via
  `OnExceptionInMainLoop`: trace shows that hook fires after re-raise.
  ✓
- ERROR + CRITICAL lines share the same exceptions.log per §4.4: trace
  writes both to that file. ✓

**Worked example 6.2 (KeyError in compute_membership, caught inner)**:
- §5.1 contract: inner try/except catches → decorator's outer except
  not reached → no ERROR line. Trace produces INFO only. ✓
- §3 table consistent: ERROR producer is "decorator's except arm"; if
  the arm doesn't fire, no ERROR. ✓

**Worked example 6.3 (import-time failure)**:
- §3.7 of ADR-006 specifies install order: hook BEFORE wx imports.
  Trace shows that contract being honored. ✓
- §6.3 acknowledges `import wx` failure as unrecoverable (hook not yet
  installed). Documented limit. ✓

**Cross-check — file assignment table (§4.4) vs filename grammar**:
- INFO → `<date>__journey.log`. Filename matches PRD-005 §"Storage"
  example `2026-05-09__journey.log`. ✓
- ERROR + CRITICAL → `<date>__exceptions.log`. Filename matches PRD-005
  example. ✓

**Cross-check — `payload` whitelist (§4.2) vs ADR-006 §3.3 helper**:
ADR-006 §3.3 step 5 references `_collect_save_payload_if_save_handler`
with whitelist `{on_save_click, on_save_edit_click, on_save_draft_click}`.
This ADR §4.2 says "PAYLOAD only appears if the handler is in the
save-handler whitelist". Same set. ✓

**Cross-check — line-shape examples vs grammar in §4**:
- Example "[2026-05-09 09:00:00] [INFO] [Person: -] App started, version 0.10.0..."
  vs grammar `INFO_LINE = "[" TS "] [INFO] [Person: " PERSON "] User clicked '" VERB "'"`.
  The grammar says "User clicked '<verb>'" but the App-started line says
  "App started, version...". **MISMATCH** flagged.
  - Resolution: §4.1 already labels "App started" as a special case
    written by `init_logging()` directly. Grammar should accept "App
    started, version <V>, log_dir <D>" as a special-case payload alongside
    the "User clicked '<verb>'" common-case payload. The relaxed grammar:
    ```
    INFO_LINE_PAYLOAD = "User clicked '" VERB "'" | "App started, " STARTUP_DETAILS
    ```
  - This is added to §4.1 (see grammar revision below in §9 Errata).

## 9. Errata / clarifications added during self-check

§4.1 grammar revised to accept the App-started payload alongside the
canonical `User clicked '<verb>'` payload. The non-User-clicked
payloads are limited to:

- `App started, version <V>, log_dir <D>` — written by `init_logging()`.
- (Future, Sprint 12+) any other "session-event" lines added by the
  hook layer or timer.

Implementor: when adding new INFO line-payloads, update §4.1 grammar
in this ADR with a one-line amendment (under `iterates_with_user:
false`, an Architect-only amendment is fine).

## 10. Consequences

**Positive:**
- Crisp severity boundaries; no "what level should this be?" debates.
- Three lines per uncaught exception (INFO entry + ERROR with payload +
  CRITICAL termination) gives Tomasz overlapping evidence.
- Plain-text grammar is grep-friendly, tail-friendly,
  copy-paste-friendly.
- Two-file split (journey vs exceptions) saves grep on every read.

**Negative:**
- Caught-and-handled exceptions inside handlers (the common
  `try-except polish_dialog return` pattern) leave NO trail in the
  exception log. Trade-off accepted per §5.1; revisitable in a future
  sprint if it bites.
- One uncaught exception produces 2-3 log lines (sometimes more if
  `sys.excepthook` also fires after `OnExceptionInMainLoop`). Acceptable
  redundancy.
- The "App started" line is a special case in the grammar. One-line
  amendment risk if someone adds another special case without updating
  §4.1.

**Neutral:**
- ERROR and CRITICAL share `__exceptions.log`. Tomasz uses
  `grep "[CRITICAL]"` to filter terminations from caught-by-decorator
  events.

## 11. Out of scope

- Email escalation (Sprint 12).
- Manual `log_error` / `log_critical` API for handlers (deferred —
  caught-and-handled exceptions don't log; revisit if it bites).
- Structured logging / JSON-lines (deferred per PRD-005).
- DEBUG / WARN / TRACE severities (deferred per PRD-005).

## 12. Sources

- `PRD-005-diagnostic-logging-foundation.md` §"Severity model",
  §"What gets logged — exceptions log", §"Storage".
- `ADR-006-logging-architecture-decorator-and-exception-hooks.md`
  §3.3 (worked examples) and §3.4 (hook integration); this ADR pins
  the line-shape grammar that ADR-006's worked examples produce.
- JOURNAL 2026-05-09 orchestrator entry "PM defaults review" — locked
  user decisions for Sprint 11.
- https://docs.python.org/3/library/traceback.html#traceback.format_exception —
  standard traceback format reused for the TRACEBACK section.
- `frames/add_person_frame.py` lines 852-913 (on_save_click), 915-1175
  (on_save_edit_click), 1176-1191 (on_save_draft_click), 1196-1221
  (on_load_draft_click), 1223-1238 (on_open_person_click), 1354-1366
  (_on_new_person_click), 1372-1423 (_on_pick_drzewo_root_click),
  1425-1449 (_on_refresh_drzewo_click), 1451-1475
  (_on_refresh_rody_click), 819-851 (on_maiden_name_toggle,
  on_is_dead_toggle), 1053-1057 (_on_field_dirty), 1059-1129
  (_on_picker_change), 1130-1175 (_on_close), 1192-1195 (on_exit_click)
  — the complete handler surface this ADR's ERROR examples are drawn
  from.
