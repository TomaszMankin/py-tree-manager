---
id: ADR-017
title: Picker exclusion lifecycle — set_selected_people MUST fire on_change_callback on every state mutation
kind: tech
decision_type: architecture
status: accepted
date: 2026-05-19
author: architect
sprint: sprint-18
supersedes: (none)
extends: ADR-011 (form + mode reset contract did not specify picker-internal exclusion lifecycle)
iterates_with_user: false
related:
  - ADR-011 (context-menu state machine — _reset_to_add_mode invokes the picker setter that this ADR fixes)
sources:
  - C:/Repositories/py-tree-manager/src/frames/controls/multi_person_picker_control.py lines 175-193 (`set_selected_people` — current early-return on empty list is the bug site)
  - C:/Repositories/py-tree-manager/src/frames/controls/multi_person_picker_control.py lines 93-96 (`set_excluded_people` — the symmetric setter; fires `on_search` and is consistent with the callback-on-every-mutation contract)
  - C:/Repositories/py-tree-manager/src/frames/controls/multi_person_picker_control.py lines 125-148 (`on_add` — wires `on_change_callback` after mutation; reference pattern)
  - C:/Repositories/py-tree-manager/src/frames/controls/multi_person_picker_control.py lines 149-166 (`on_remove` — wires `on_change_callback` after mutation; reference pattern)
  - C:/Repositories/py-tree-manager/src/frames/add_person_frame.py lines 178-203 (`update_all_picker_exclusions` — gathers selections across four pickers, calls `set_excluded_people` on each)
  - C:/Repositories/py-tree-manager/src/frames/add_person_frame.py lines 1129-1132 (`_on_picker_change` — replacement callback installed by `_wire_dirty_tracking`; calls `update_all_picker_exclusions` then sets dirty)
  - C:/Repositories/py-tree-manager/src/frames/add_person_frame.py lines 1175-1198 (`_wire_dirty_tracking` — overwrites `on_change_callback` with `_on_picker_change` for all four pickers)
  - C:/Repositories/py-tree-manager/src/frames/add_person_frame.py lines 1619-1675 (`_reset_to_add_mode` — calls `set_selected_people([])` on all four pickers; symptom site of issue #19)
  - https://github.com/TomaszMankin/py-tree-manager/issues/19 — user-reported bug, comments + attached logs
---

# ADR-017 — Picker exclusion lifecycle

> Companion to ADR-011. Defines the callback semantics that `MultiPersonPickerControl` must honour so frame-level cross-picker exclusion state cannot decouple from picker-level selection state.

## 1. Context

### 1.1 The bug (user-reported issue #19, 2026-05-17)

Four `MultiPersonPickerControl` instances on `AddPersonFrame` (parents, children, spouses, siblings). Each picker holds a private `excluded_people_uuids` list set by the frame via `set_excluded_people()`. The frame's `update_all_picker_exclusions` (lines 178-203) gathers all four pickers' current selections and pushes the cross-set into each picker — so a person already chosen as a spouse in the spouse picker is filtered out of the parents / children / siblings pickers' search results.

`update_all_picker_exclusions` is invoked through one path only: each picker's `on_change_callback`. At construction the callback is set to `update_all_picker_exclusions` directly; later, `_wire_dirty_tracking` overwrites it with `_on_picker_change` which calls `update_all_picker_exclusions` and then sets `_is_dirty = True`.

When the user saves a person and the form resets, `_reset_to_add_mode` (frame line 1619) clears each picker via `self.<role>_picker.set_selected_people([])`. The current implementation of `set_selected_people` (control line 175):

```python
def set_selected_people(self, ids: List[str]) -> None:
    self.selected_list.Clear()
    self.selected_people_uuids.clear()

    if not ids or len(ids) == 0:
        return                       # <-- early-return; on_change_callback NEVER fires

    for id in ids:
        ...
    self.on_search(None)
    if self.on_change_callback is not None:
        self.on_change_callback()
```

The early-return short-circuits `on_change_callback`. Consequence: the four pickers' `selected_people_uuids` are now all empty, but each picker's `excluded_people_uuids` still holds the *previous* person's cross-set. The next person's `on_search` filters those stale UUIDs out — so the person the user just saved (who had been selected in, say, the spouses picker when the previous form was active) now appears missing from the parents, children, and siblings pickers, but visible in the spouses picker. Exactly the symptom in the issue's three screenshots.

### 1.2 Why this is a contract gap, not a contradiction

ADR-011 §2.3 covers form-field reset and mode transition. It does not specify what `set_selected_people([])` is supposed to do, nor what guarantees picker callers can rely on around exclusion lifecycle. The control's own behaviour is silently inconsistent: `set_selected_people` with a non-empty list fires the callback; the same method with an empty list does not. Two callers in the codebase invoke this method:

- `_reset_to_add_mode` (frame line 1664-1667) — four times with `[]`
- `_fill_form_from_draft` paths via `set_selected_people(relationships['parent_ids'])` etc. — with populated lists

The first triggers the bug. The second does not, because the for-loop runs and the callback fires.

### 1.3 The repro path traced through real state

User journey from issue #19 (roles only — names omitted per PII rule):

1. Start app. Mode = NEW. All four pickers empty. `excluded_people_uuids` empty everywhere.
2. Fill in person-A. Click `Zapisz osobę i dodaj do drzewa`. Save succeeds → `_reset_to_add_mode` runs → pickers cleared via `set_selected_people([])` four times, each early-returning → exclusions are still all empty (which is *correct* by accident at this step because no exclusions had been set yet).
3. Fill in person-B (spouse of A). User picks A in the spouses picker → spouses_picker's `on_add` runs → `_on_picker_change` fires → `update_all_picker_exclusions` sets the *other three pickers'* `excluded_people_uuids = [A_uuid]`.
4. Click `Zapisz osobę i dodaj do drzewa`. Save succeeds → `_reset_to_add_mode` runs → pickers cleared via `set_selected_people([])` four times, each early-returning → spouses_picker.selected_people_uuids = []; parents_picker / children_picker / siblings_picker still have `excluded_people_uuids = [A_uuid]`. **Stale state survives reset.**
5. Fill in person-C (parent of A). User searches A in parents_picker. `on_search` filters by `selected | excluded` = `{} | {A_uuid}` = `{A_uuid}`. A is excluded → not visible. Bug.

The spouses picker (where A was last selected) shows A correctly, because that picker's `excluded_people_uuids` was never set to include A (you cannot exclude a selection from itself). The other three pickers carry the stale exclusion. This matches the user's observation: "person appears missing from 3 of 4 pickers but visible in the one role they were last assigned."

## 2. Decision

### 2.1 The picker-callback contract

`MultiPersonPickerControl.on_change_callback`, when not None, MUST fire on every state mutation that changes either `selected_people_uuids` or the visible `selected_list`. This is the contract callers (the frame) depend on. The mutation paths are:

| Path | Current callback fires? | After this ADR |
|---|---|---|
| `on_add` (user clicks Add or double-clicks results) | yes (line 146) | yes — unchanged |
| `on_remove` (user clicks Remove or double-clicks selection) | yes (line 164) | yes — unchanged |
| `set_selected_people(ids)` with non-empty list | yes (line 192) | yes — unchanged |
| `set_selected_people([])` (or `None`) | **no — bug** | yes — fix below |
| `set_excluded_people(excluded)` | n/a (this mutates exclusion, not selection — does not fire `on_change_callback`; this is correct and intentional — exclusion change is *caused by* a selection change in another picker, firing it from here would recurse) | unchanged |
| `reload_people(new_people)` | no (line 195-205) | no — see §2.4; intentional |

### 2.2 The fix — Option C: callback fix in control + defensive call in frame

Two changes:

**Change 1 (canonical fix, picker contract restored).** In `multi_person_picker_control.py`, `set_selected_people` no longer early-returns. The method always falls through to the callback site:

```python
def set_selected_people(self, ids: List[str]) -> None:
    self.selected_list.Clear()
    self.selected_people_uuids.clear()

    # Validate every id is known to this picker BEFORE mutating selected_list.
    # Raise early so a partial-population state cannot leak out.
    if ids:
        for person_id in ids:
            if person_id not in self.all_people:
                raise RuntimeError(
                    f"Person with id <{person_id}> has not been found in the tree."
                )
        for person_id in ids:
            self.selected_people_uuids.append(person_id)
            self.selected_list.Append(self.all_people[person_id], person_id)

    # Refresh visible results regardless of whether ids was empty — selection
    # state has changed, so the available-results view may now include people
    # who were previously selected and need to reappear.
    self.on_search(None)

    # Fire callback unconditionally — selection state changed, callers depend
    # on the contract that any mutation through this method emits a change event.
    # Empty-list case included: callers like _reset_to_add_mode rely on this to
    # re-run cross-picker exclusion recomputation across the four-picker set.
    if self.on_change_callback is not None:
        self.on_change_callback()
```

Behaviour deltas vs current code:

- Empty-list path now runs `on_search(None)` (refreshes available-results view — empty selection means all non-excluded people should be visible). Previously the visible list was untouched on the empty path; cosmetically the rebuild is invisible because the list was about to be re-populated by the next form-fill anyway, but semantically it's correct.
- Empty-list path now fires `on_change_callback`. This is the bug fix.
- Validation moved BEFORE mutation. Today's code mutates `selected_people_uuids` and `selected_list` in the loop and then raises mid-loop if a bad id arrives, leaving the picker in a partial state. Pre-validation is the correct invariant.

**Change 2 (defense in depth, frame).** In `add_person_frame.py`, `_reset_to_add_mode` calls `update_all_picker_exclusions()` explicitly after the four `set_selected_people([])` calls and before the `_apply_menu_mode(MenuMode.NEW)` line:

```python
# Relationship pickers
self.parents_picker.set_selected_people([])
self.children_picker.set_selected_people([])
self.spouses_picker.set_selected_people([])
self.siblings_picker.set_selected_people([])

# Defensive: even with the Change 1 fix above, explicitly recompute exclusions
# so this method's correctness does not depend on the picker firing four
# callbacks in sequence. Idempotent — calling after the picker callbacks have
# already recomputed exclusions is a no-op-equivalent (recomputes the same
# empty cross-set).
self.update_all_picker_exclusions()
```

### 2.3 Why both changes (rationale)

| | Change 1 only | Change 2 only | Both (chosen) |
|---|---|---|---|
| Fixes #19 symptom | yes | yes | yes |
| Picker contract honest (callback fires on every mutation) | yes | no — bug remains for any other caller of `set_selected_people([])` | yes |
| `_reset_to_add_mode` independent of picker-internal contract | no — bug returns if the picker contract is broken again later | yes | yes |
| Cost | ~10 LOC + 4 picker tests | 1 LOC + 1 frame test | ~11 LOC + 5 tests |
| Idempotency overhead | none | one extra `update_all_picker_exclusions` call per reset (four pickers × `set_excluded_people` × constant-time `on_search` rebuild ≈ ms) | same as Change 2 alone |

Change 1 restores the picker's invariant. Change 2 makes the frame's reset path self-contained. Together they pass the audit question "is the reset correct regardless of whether each picker's callback fires?" — answer: yes, because `update_all_picker_exclusions` is invoked at least once unconditionally. The Change-2 idempotency cost is negligible (four set_excluded_people calls with empty cross-sets, four trivial on_search rebuilds, no I/O).

**Alt-1 (Change 1 only)**: rejected — leaves `_reset_to_add_mode`'s correctness coupled to the picker callback firing. Any future picker refactor that drops the callback wiring (e.g. switching to a Qt-style signal connect) reintroduces #19.

**Alt-2 (Change 2 only)**: rejected — leaves the picker contract dishonest. Any future caller of `set_selected_people([])` (e.g. a "clear pickers" button, batch-reset across multiple frames) silently inherits the same bug.

**Alt-3 (refactor: pickers expose a `clear()` method separate from `set_selected_people`)**: rejected for this sprint. The current method already covers both cases; splitting it introduces an API change with ripple effects on the four `_fill_form_from_draft` paths and two `_load_person_for_edit` paths, none of which are broken today. File as a Sprint-19+ refactor candidate if a future control inventory makes it worth doing.

### 2.4 `reload_people` is intentionally callback-free

`reload_people(new_people)` is called after a person is added to the tree so all four pickers see the updated `all_people` dictionary. It does not change `selected_people_uuids`, so firing the callback would trigger a spurious exclusion recompute (against unchanged selection state). Verdict: `reload_people` keeps its current "no callback" behaviour. Documented here so a future maintainer doesn't accidentally "fix" symmetry by adding a callback fire to it.

### 2.5 Defensive call ordering inside `_reset_to_add_mode`

The defensive `update_all_picker_exclusions()` call (Change 2) MUST go AFTER the four `set_selected_people([])` calls and BEFORE `_apply_menu_mode(MenuMode.NEW)`. Reasons:

- After the setters: at this point all four pickers have empty `selected_people_uuids`. `update_all_picker_exclusions` reads from `get_selected_people()` on each picker (frame lines 186-189), so the gathered cross-sets are correctly empty. Running it before the setters would push the *previous* form's selections back as exclusions.
- Before `_apply_menu_mode`: not load-bearing — `_apply_menu_mode` is purely about menu-item enable/disable + mode visuals, no picker interaction. But keeping the picker-related work clustered before the mode flip preserves visual coherence (form is fully reset before the menu/colour transition).

The existing `_is_dirty = False` line (line 1675) MUST remain last — `update_all_picker_exclusions` → `set_excluded_people` → `on_search` does NOT fire the picker's `on_change_callback` (intentional, see §2.1 table), so it does not set `_is_dirty = True`. But the four `set_selected_people([])` calls above DO fire the callback (after Change 1), which DOES call `_on_picker_change` (the dirty-track replacement installed at frame line 1198) → sets `_is_dirty = True`. The last-line `_is_dirty = False` discards those synthetic dirty events — same role as today, comment in the docstring at line 1626 stays accurate.

## 3. Test strategy

All L0; no wx mainloop required. Pickers can be constructed with a stub `parent` and asserted directly.

### 3.1 New file: `src/tests/L0/frames/test_multi_person_picker_control.py`

Tests target the control in isolation, with `wx.Frame(None)` as parent.

| # | Test | Asserts |
|---|---|---|
| 1 | `test_set_selected_people_empty_fires_callback` | callback invoked exactly once when called with `[]`. THIS IS THE BUG-REGRESSION TEST. Must fail against current `main`. |
| 2 | `test_set_selected_people_empty_clears_internal_state` | `selected_people_uuids == []` and `selected_list.GetCount() == 0` after empty call |
| 3 | `test_set_selected_people_nonempty_fires_callback` | callback invoked exactly once when called with `["uid-1", "uid-2"]` |
| 4 | `test_set_selected_people_nonempty_populates_lists` | `selected_people_uuids == ["uid-1", "uid-2"]` and `selected_list.GetCount() == 2` |
| 5 | `test_set_selected_people_unknown_id_raises_before_mutation` | passing an id not in `all_people` raises `RuntimeError` AND `selected_people_uuids` is unchanged from its pre-call state (pre-validation invariant) |
| 6 | `test_set_selected_people_no_callback_when_callback_none` | constructing with `on_change_callback=None` and calling `set_selected_people([])` does not raise (None-safety) |
| 7 | `test_reload_people_does_not_fire_callback` | locks §2.4 — `reload_people` is intentionally callback-free |

Test 1 is the failing-then-passing regression marker. Reviewer's Halt-A grep should confirm it exists and verifies the callback fires on the empty path.

### 3.2 Modify in place: `src/tests/L0/frames/test_add_person_frame_transitions.py`

Add one test to lock the Change-2 defensive call:

| # | Test | Asserts |
|---|---|---|
| 8 | `test_reset_to_add_mode_clears_exclusions_across_all_four_pickers` | Setup: real `AddPersonFrame` with stub `all_people` containing three uuids X/Y/Z. Programmatically populate the spouse picker via `set_selected_people([X])` (callback fires → exclusions push X into other three pickers' `excluded_people_uuids`). Pre-assert `parents_picker.excluded_people_uuids == [X]`. Call `_reset_to_add_mode()`. Assert all four pickers have `selected_people_uuids == []` AND `excluded_people_uuids == []`. THIS LOCKS THE FIX END-TO-END. |

If the picker fix (Change 1) is reverted but the frame fix (Change 2) is kept, test 8 still passes — Change-2 covers it independently. If the frame fix is reverted but the picker fix is kept, test 8 also still passes — Change-1's callback firing triggers `_on_picker_change` which calls `update_all_picker_exclusions`. Test 8 thus locks the *behaviour* without coupling the assertion to which of the two changes is responsible. Defense in depth verified.

### 3.3 L1 integration test — NOT added this sprint

The bug surfaces during a multi-person creation sequence (3+ persons across 3+ form sessions). An L1 test for this would require driving the full wx event loop through three saves + three new-person clicks, which the project's L1 fixture set does not currently support headlessly (verified by Sprint 11 carry-forward item 2 — wxpython-headless not in the project yet). The unit-level coverage in §3.1 + §3.2 locks the algorithm; the multi-person scenario is covered by the user's manual smoke (halt criterion H-Sprint-A).

### 3.4 Halt criteria

| ID | Criterion | Verification |
|---|---|---|
| H-Sprint-A | User runs the issue #19 repro on a real tree and confirms person-A appears in person-C's parents picker after person-B has been saved | manual smoke; user-driven |
| H-Sprint-B | All 7 new picker tests + 1 new frame test pass; existing 264+ test count grows to 272+ with zero pre-existing test regressions | pytest run |
| H-Sprint-C | Grep `set_selected_people` in `multi_person_picker_control.py` — no `return` statement appears between the method signature and the callback-fire line | source-text grep |
| H-Sprint-D | Grep `update_all_picker_exclusions` in `add_person_frame.py` — appears at least twice (once in the `_reset_to_add_mode` body, once in `_on_picker_change`); the `_reset_to_add_mode` call is positioned between the four `set_selected_people([])` calls and the `_apply_menu_mode(MenuMode.NEW)` line | source-text grep |
| H-Sprint-E | The logger.py post-migration import fix lands: grep `from helpers.update_helper import UpdateHelper` in `src/helpers/logger.py` returns zero hits; grep `from src.helpers.update_helper import UpdateHelper` returns two hits (lines 608, 635) | source-text grep |

## 4. Out of scope for this ADR

- ADR-011's existing form-reset spec (mode flip, field clear, dirty reset) — unchanged.
- The picker's add/remove UX behaviour — unchanged.
- `set_excluded_people` callback semantics — intentionally callback-free (see §2.1 rationale).
- The broken-import bug at `src/helpers/logger.py:608` and `:635` — included in Sprint 18 file-touch list per user's 2026-05-17 directive, but does not require its own ADR (one-line import path fix, post-migration cleanup, not a design decision). Sprint plan tracks the fix; no ADR coverage needed.

## 5. Citations

All line numbers verified at HEAD of `main` post-PR-21-merge (2026-05-19). Re-verify after any touch to `multi_person_picker_control.py` or `add_person_frame.py` lines 178-203 / 1619-1675.

GitHub issue source: https://github.com/TomaszMankin/py-tree-manager/issues/19 — comments and the three attached screenshots (PII-stripped here per project rule).
