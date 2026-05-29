---
id: ADR-019
title: Folder-selection guards — forbidden root names and person-folder me.json pre-check
kind: tech
decision_type: architecture
status: proposed
date: 2026-05-29
author: architect
sprint: sprint-20
supersedes: (none)
iterates_with_user: true   # Polish dialog wording is UX-facing; expect refinement
related:
  - ADR-010 (runtime data + root selection — root picker is one guarded site)
  - ADR-004/ADR-016 (forbidden folder names already skipped during SCAN; this extends the same list to root SELECTION)
sources:
  - C:/Repositories/py-tree-manager/src/services/file_service.py lines 177-182 (_forbidden_locations list — single source of truth, reused here)
  - C:/Repositories/py-tree-manager/src/frames/add_person_frame.py lines 1505-1539 (on_open_person_click + _load_person_for_edit — person-folder picker)
  - "Issue #24 attached exceptions log (2026-05-29) — repeated FileNotFoundError 'Wybrany folder nie zawiera pliku me.json.' at add_person_frame.py:1527"
  - "Issue #24 user comment 2026-05-29 — 'block user from selecting other not-allowed folders'"
---

# ADR-019 — Folder-selection guards

## 0. Changelog

- **2026-05-29 (initial, proposed)** — two related guards bundled: (1)
  forbidden root-folder names rejected at SELECTION (existing scope), (2)
  person-folder picker validates `me.json` presence before load (scope
  amendment to issue #24, 2026-05-29 dispatch).

## 1. Context

Two folder-picker validation gaps surfaced together.

**Guard A — forbidden root names (existing scope).** `_forbidden_locations`
(file_service.py 177-182: `"Pozostałe nieuporządkowane"`, `"Rutowscy - dane
ogólne"`, `"Do ustalenia"`, `"Wspólne"`) are skipped during the cached-people
SCAN, but nothing stops the user from SELECTING one of those folders as the
tree ROOT. Selecting one as root would scan garbage / non-person folders.

**Guard B — person-folder missing me.json (issue #24 amendment).** The
person-folder picker (`on_open_person_click` → `_load_person_for_edit`) lets the
user pick ANY folder. If the folder lacks `me.json`, `_load_person_for_edit`
raises `FileNotFoundError("Wybrany folder nie zawiera pliku me.json.")`
(add_person_frame.py:1527). The outer handler catches it and shows the raw
exception text in a dialog (line 1520). The father hit this REPEATEDLY (5+
times in the 2026-05-29 log) — every misclick produced a logged ERROR + a
dialog showing a developer-flavored message. Functionally caught, but: it
pollutes the exceptions log with non-bugs, and the error path is reactive
(raise-then-catch) rather than a friendly pre-check.

## 2. Decision

### 2.1 Guard A — reject forbidden names at root selection

Where the user picks the tree root (the root picker — ADR-010; grep
`DirDialog` / `_on_pick_*root*` in add_person_frame.py and the root-selection
path in file_service `set_root_folder`), after the folder is chosen and BEFORE
it is committed as root:

- If the selected folder's **basename** is in `_forbidden_locations`, show a
  Polish dialog and abort (do not set it as root).
- Reuse `FileService._forbidden_locations` as the single source of truth — do
  NOT duplicate the list. Expose it if needed (it's already an instance attr;
  implementor grep for the cleanest access — a module-level constant or a
  `@property` is acceptable if the list needs to be read before a FileService
  exists).

Polish dialog (iterates_with_user — wording may refine):

> Title: `Nieprawidłowy folder`
> Body: `Ten folder nie może być folderem głównym drzewa. Wybierz inny folder.`

Codepoints: ł U+0142 ("główny"), ó U+00F3 ("głównym"), none others needed.
(Implementor: enumerate + verify each codepoint per the Polish-label parity rule.)

### 2.2 Guard B — me.json pre-check in person-folder picker

In `on_open_person_click` (add_person_frame.py:1505), AFTER the folder is picked
and BEFORE calling `_load_person_for_edit`:

```python
# after: folder_path = dialog.GetPath(); dialog.Destroy()
me_json = os.path.join(folder_path, "me.json")   # or Path(folder_path) / "me.json"
if not os.path.exists(me_json):
    polish_dialog(
        self,
        "Wybrany folder nie zawiera pliku osoby. Wybierz inny folder.",
        "Nieprawidłowy folder",
        wx.OK | wx.ICON_WARNING,
    )
    return   # do NOT call _load_person_for_edit; nothing is loaded
# else: proceed as today
self._load_person_for_edit(folder_path)
```

The existing `raise FileNotFoundError(...)` at `_load_person_for_edit:1527` and
the outer `except Exception` (1518-1520) **STAY as a safety net** — they are no
longer the primary guard but they catch the race where `me.json` is deleted
between the pre-check and the load. The pre-check means the COMMON misclick path
(picking a non-person folder) no longer raises, no longer logs an ERROR, and
shows a friendly message instead of the exception string.

Polish dialog body (iterates_with_user): `"Wybrany folder nie zawiera pliku
osoby. Wybierz inny folder."` Codepoints: ó U+00F3 ("osoby" — actually 'o',
no diacritic; "Wybrany" none; recheck — none of ę/ń/ł/ó/ś/ż/ą appear except
possibly none). Implementor: enumerate the final string and verify; if zero
diacritics, that is fine, assert accordingly. Title `"Nieprawidłowy folder"`
contains ł U+0142 and ó U+00F3.

**Why WARNING not ERROR icon**: a misclick is not an error; it is user input
the app gently corrects. `wx.ICON_WARNING` reads as "try again", not "something
broke".

## 3. Behavior matrix

| User action | Before | After |
|---|---|---|
| Pick a forbidden folder as root | accepted; scans garbage | dialog "nie może być folderem głównym"; root unchanged |
| Pick a non-person folder to edit | FileNotFoundError raised → logged ERROR → raw-text dialog | friendly WARNING dialog; no log ERROR; nothing loaded |
| Pick a valid person folder to edit | loads | loads (unchanged) |
| me.json deleted mid-pick (race) | FileNotFoundError → dialog | pre-check passes, load raises, safety-net catch shows dialog (unchanged path) |

## 4. Pre-implementor parity check

### 4.1 _forbidden_locations access (attribute chain)

The list lives at `file_service.py:177-182` as `self._forbidden_locations`
(instance attr set in `__init__`). The root picker may run before/around a
FileService instance. **Implementor MUST grep** the root-selection site to find
whether a FileService instance is in hand. If yes, read
`fs._forbidden_locations`. If the list is needed before any FileService exists,
lift it to a module-level constant `FORBIDDEN_LOCATIONS` in file_service.py and
reference the same constant from `__init__` — DO NOT copy the four strings into
a second place. Single source of truth (the four names already appear in
CLAUDE.md domain-reference; the CODE list is canonical).

### 4.2 polish_dialog signature

Guard B pseudocode calls `polish_dialog(self, body, title, flags)`. Verified
against existing call sites in add_person_frame.py (e.g. 1472-1477, 1496-1503):
signature is `polish_dialog(parent, message, caption, style)`. MATCHES.
Implementor: confirm the exact param order at the import site before use.

### 4.3 os vs pathlib

`_load_person_for_edit` already uses `Path(folder_path) / "me.json"` (line
1525). The dispatch amendment says `os.path.exists(os.path.join(...))`. Either
works; for consistency with the surrounding method the implementor MAY use
`Path(folder_path) / "me.json"` + `.exists()`. Not load-bearing; pick one,
test it.

## 5. Alternatives considered

### 5.1 Guard B: keep raise-then-catch, just soften the message

Change the FileNotFoundError text to be friendlier and let the existing catch
show it. Less code. But: still logs an ERROR for every misclick (log noise —
the #24 log shows 5+ such lines), and conflates "user misclicked" with "real
error" in the exceptions log. Rejected — the dispatch explicitly wants a
pre-check that aborts gracefully without raising.

### 5.2 Guard A: skip forbidden roots silently (auto-scan, ignore the folder)

Selecting a forbidden folder could just scan and find zero people (the folder
gets skipped). But the user would see an empty tree with no explanation.
Rejected — explicit rejection dialog is clearer for an elderly user.

### 5.3 Validate me.json CONTENT (not just existence) in the pre-check

Check that me.json parses + has a UUID, not just that it exists. But
`_load_person_for_edit` already raises a friendly `ValueError("Nie można
odczytać danych osoby...")` (line 1533) for corrupt content, caught by the
safety net. Adding content validation to the pre-check duplicates that.
Rejected — existence pre-check + existing content safety-net is the right split.

## 6. Risks

### Risk 1 — _forbidden_locations basename match is case/whitespace sensitive

`folder.name in self._forbidden_locations` is exact-string. A trailing space or
case difference in a real folder name would miss. **Mitigation**: the scan path
(file_service.py:368) already uses the same exact-match; Guard A is consistent
with existing behavior — no NEW inconsistency introduced. Not a halt criterion.

### Risk 2 — Guard A site may not exist as a single clean function

The root-selection flow spans dialog + set_root_folder. **Mitigation**:
implementor grep locates the commit point; the guard goes immediately after
`GetPath()` at the dialog site (same shape as Guard B), before any
set_root_folder call. Documented as an implementor-locate step.

## 7. Halt criteria

(H-A) Pick a forbidden-named folder as root → rejection dialog; root not
changed. L0: mock the picker to return a forbidden basename, assert no
set_root_folder call + dialog fired.

(H-B) Pick a folder without me.json to edit → WARNING dialog; `_load_person_for_edit`
NOT called; no ERROR logged. L0: mock DirDialog/GetPath + os.path.exists→False,
assert dialog fired and load not invoked.

(H-C) Pick a valid person folder → loads as today (regression guard).

## 8. Test plan

| Layer | What | Mock | Asserts |
|---|---|---|---|
| L0 | Guard B: missing me.json aborts | DirDialog→OK, GetPath→folder, exists→False, mock polish_dialog + _load_person_for_edit | dialog called once; _load_person_for_edit NOT called |
| L0 | Guard B: present me.json loads | exists→True, mock _load_person_for_edit | _load_person_for_edit called once |
| L0 | Guard A: forbidden root rejected | picker→forbidden basename, mock set_root + dialog | set_root NOT called; dialog called |
| L0 | Guard A: normal root accepted | picker→ordinary basename | proceeds to set_root |
| L0 | _forbidden_locations single-source | import the constant/attr | the four canonical names present; no second literal list in frame |

L0 tests in `src/tests/L0/frames/` (Guard B + A frame sites) and
`src/tests/L0/services/` (single-source assertion if lifted to constant).

## 9. Sources

(See front-matter `sources:` block.)
