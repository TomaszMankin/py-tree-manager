---
id: ADR-011
title: Context-menu state machine, three-section menu structure, and draft-update semantics
kind: tech
decision_type: architecture
status: accepted
date: 2026-05-11
author: architect
sprint: sprint-14
supersedes: (none)
iterates_with_user: true   # the section structure / Polish labels emerged from in-chat AskUserQuestion; expect 1-2 follow-up refinements
related:
  - ADR-005 (mode background palette — modes drive both bg-color AND menu enable/disable from Sprint 14 onward)
  - ADR-006 (logging architecture — INFO-CLEANUP severity reused for delete-fails-on-promote path)
  - ADR-007 (severity model — INFO-CLEANUP line shape per §4.5)
sources:
  - C:/Repositories/py-tree-manager/frames/add_person_frame.py lines 795-839 (current single-section menu; build site)
  - C:/Repositories/py-tree-manager/frames/add_person_frame.py lines 1287-1315 (`on_load_draft_click` — the root of the duplicate-file bug; does NOT restore `self.unique_identifier` from the loaded draft)
  - C:/Repositories/py-tree-manager/frames/add_person_frame.py lines 1336-1365 (`_load_person_for_edit` — DOES restore `self.unique_identifier`; the reference pattern the draft path is missing)
  - C:/Repositories/py-tree-manager/frames/add_person_frame.py lines 1264-1280 (`on_save_draft_click` — uses `_collect_all_data_to_dict` → `self.unique_identifier`; today writes a fresh UUID when one is loaded)
  - C:/Repositories/py-tree-manager/frames/add_person_frame.py lines 920-928 (`on_save_click` — existing draft-cleanup pattern after new-person save; uses `self.unique_identifier` as the filename key — reused verbatim for promote-disposes-draft)
  - C:/Repositories/py-tree-manager/frames/add_person_frame.py lines 1641-1648 (`_collect_all_data_to_dict` — reads `self.unique_identifier` into the dict payload)
  - C:/Repositories/py-tree-manager/services/tree_service.py lines 47-55 (`save_person_draft` — writes to `<poczekalnia>/<uid>.json`; the path key is the data's `get_unique_identifier()`)
  - C:/Repositories/py-tree-manager/services/file_service.py lines 371-399 (`get_poczekalnia_path` + `scan_drafts_location` — the draft folder contract)
  - C:/Repositories/py-tree-manager/helpers/logger.py lines 248-271 (`_emit_cleanup_failure` — internal INFO-CLEANUP writer; this ADR lifts it to a public helper)
  - C:/Repositories/py-tree-manager/.pipeline/JOURNAL.md 2026-05-11 — user-locked decisions captured in chat (three AskUserQuestion answers)
---

# ADR-011 — Context-menu state machine + three-section menu + draft-update semantics

> User-facing menu UX. `iterates_with_user: true` — the section structure and Polish labels are expected to refine over 1-2 follow-up user-feedback rounds.

## 1. Context

### 1.1 The bug (user-reported 2026-05-11)

> "When I open a person draft and edit it, I can't save it. I can only click 'Zapisz osobę bez dodawania do drzewa', which creates a duplicate entry in draft people."

**Root cause** (traced against `frames/add_person_frame.py` at HEAD):

There is no "update existing draft" menu action. When a draft is loaded:

- `on_load_draft_click` (lines 1287-1315) calls `_fill_form_from_draft(data)` to populate fields and `_apply_mode_visuals('edit-draft')` to flip the header strip — but it **does not** copy `person_data.get_unique_identifier()` into `self.unique_identifier`. By contrast, `_load_person_for_edit` (line 1350) DOES this for tree people.
- When the user clicks "Zapisz osobę bez dodawania do drzewa", `on_save_draft_click` (lines 1264-1280) calls `_collect_all_data_to_dict` which reads `self.unique_identifier` (lines 1644-1647). Because `on_load_draft_click` never overwrote it, `self.unique_identifier` is still the **launch-time fresh UUID** assigned in `__init__` at line 123.
- `save_person_draft` (`tree_service.py` lines 48-55) writes to `<poczekalnia>/<get_unique_identifier()>.json`. With a fresh UUID, that is a **new** file. The original draft `<orig-uuid>.json` is untouched. Result: two files for the same person — the duplicate the user sees.

There are therefore **two** design gaps:

1. **Data layer**: the load-draft path does not propagate the draft's persisted UUID back into frame state.
2. **UX layer**: there is no menu action whose contract is "overwrite the currently loaded draft." The only available save action under a loaded draft is "save as new draft" — which is correct for new-mode but wrong as the sole option in edit-draft mode.

### 1.2 Why a state machine

Today the menu is a flat 8-item list under one "Plik" submenu. Enable/disable state is partial: only `_save_edit_item` is dynamically toggled (lines 809, 1361, 1442) and it is keyed to a private boolean `self._is_edit_mode` that does not distinguish "editing tree person" from "editing draft." The user-facing consequence:

- "Zapisz osobę i dodaj do drzewa" stays enabled in edit-tree mode and edit-draft mode → invites an accidental click that creates a second tree record from a loaded person.
- "Zapisz osobę bez dodawania do drzewa" stays enabled in edit-draft mode → the bug above.
- The menu gives no visual grouping by intent: new-person actions, tree-person management, draft management are interleaved.

The user-proposed restructure (locked in chat 2026-05-11) introduces an **explicit three-mode state machine** that maps cleanly to three menu sections separated by horizontal separators. Each section's mutating actions are enabled only in the matching mode. Load actions and configuration actions stay always-enabled across all modes.

### 1.3 User-locked decisions (from chat 2026-05-11 — do NOT re-litigate)

1. **Promote-disposes-draft**: when a loaded draft is promoted to the tree, the draft file is deleted.
2. **No tree → draft fork in Sprint 14.** Section 2 has no "save tree person as a new draft" action. Parked for future "person degradation" feature.
3. **Idle-state saves are enabled.** App launches into mode=new; Section 1 saves are enabled even on an empty form. No "idle" state in the state machine.

## 2. Decision

### 2.1 State machine — three modes only

```
                            ┌──────────────────────────────────┐
                            │             NEW                  │
                            │  (default on launch;             │
                            │   reset after any successful     │
                            │   save in any mode;              │
                            │   "Nowa osoba" click)            │
                            └─────┬──────────────────────┬─────┘
                                  │                      │
                  ┌───────────────┘                      └───────────────┐
                  │                                                      │
       "Edytuj osobę z drzewa"                                "Wczytaj szkic osoby"
       (user picks tree person)                               (user picks draft)
                  │                                                      │
                  ▼                                                      ▼
        ┌─────────────────┐                                   ┌──────────────────┐
        │   EDIT_TREE     │                                   │   EDIT_DRAFT     │
        │                 │                                   │                  │
        │  any successful │                                   │  any successful  │
        │  save  ────────────────────► back to NEW ◄────────────────  save       │
        └─────────────────┘                                   └──────────────────┘
```

**No "idle" state.** App boot lands in `NEW` directly. Per user decision #3, Section 1 saves are enabled on a blank form on launch — user explicitly chose this is acceptable.

### 2.2 Three-section menu structure (locked Polish labels)

The single "Plik" menu retains its top-level position. Inside, three sections separated by `wx.Menu.AppendSeparator()` calls. Sections grouped by **intent**, not by save/load:

**Section 1 — New-person creation:**

| Label (exact) | Codepoints to grep | Always-enabled? | Mode-enabled |
|---|---|---|---|
| `Nowa osoba` | (none) | yes | all |
| `Zapisz osobę i dodaj do drzewa` | ę (U+0119), ą (U+0105) | no | NEW only |
| `Zapisz osobę jako szkic` | ę (U+0119) | no | NEW only |

**Section 2 — In-tree people management:**

| Label (exact) | Codepoints to grep | Always-enabled? | Mode-enabled |
|---|---|---|---|
| `Edytuj osobę z drzewa` | ę (U+0119) | yes | all |
| `Ustaw osobę-korzeń drzewa` | ę (U+0119), ń (U+0144) [note: not on user's listed codepoints — see §2.6] | yes | all |
| `Zapisz zmiany dla osoby na drzewie` | (none) | no | EDIT_TREE only |

**Section 3 — Drafts management:**

| Label (exact) | Codepoints to grep | Always-enabled? | Mode-enabled |
|---|---|---|---|
| `Wczytaj szkic osoby` | (none) | yes | all |
| `Zaktualizuj szkic osoby` | (none) | no | EDIT_DRAFT only |
| `Dodaj szkic osoby do drzewa` | (none) | no | EDIT_DRAFT only |

**Plus** the existing always-enabled items that survive at the bottom of the menu (between separators or below Section 3):

- `Odśwież drzewo`, `Odśwież rody` — load/build actions, always-enabled, no mode tie
- `Wyjdź` — under its own separator at the very bottom, as today

### 2.3 Mode-transition wiring (exact)

| Trigger | Resulting mode | Side effect |
|---|---|---|
| `__init__` complete | NEW | `_apply_mode_visuals('add-new')` already called at line 140; mode-state initializer runs to `NEW` |
| Click `Nowa osoba` (with dirty-guard dialog if `_is_dirty`) | NEW | form cleared via `_reset_to_add_mode` |
| Click `Edytuj osobę z drzewa` → user picks tree folder → load succeeds | EDIT_TREE | `_load_person_for_edit` already sets bg + title; mode flipped at end of that method |
| Click `Wczytaj szkic osoby` → user picks draft → load succeeds | EDIT_DRAFT | `on_load_draft_click` updated to ALSO restore `self.unique_identifier` (§3.1) |
| Click any Section 1 save (`Zapisz osobę i dodaj do drzewa`, `Zapisz osobę jako szkic`) → success | NEW (form cleared) | matches current behavior in `on_save_click` line 933 |
| Click `Zapisz zmiany dla osoby na drzewie` (in EDIT_TREE) → success | NEW (form cleared) | **behavior change**: today `on_save_edit_click` leaves the frame in EDIT_TREE (line 997 re-applies `'edit-tree'`); this ADR resets to NEW per user-locked "any successful save → mode resets to NEW with cleared form" |
| Click `Zaktualizuj szkic osoby` (in EDIT_DRAFT) → success | NEW (form cleared) | new behavior — see §3.1 |
| Click `Dodaj szkic osoby do drzewa` (in EDIT_DRAFT) → success | NEW (form cleared) | new behavior — see §3.2 |

### 2.4 Enable/disable matrix (the load-bearing contract)

| Action | NEW | EDIT_TREE | EDIT_DRAFT |
|---|---|---|---|
| Nowa osoba | enabled | enabled | enabled |
| Zapisz osobę i dodaj do drzewa | **enabled** | disabled | disabled |
| Zapisz osobę jako szkic | **enabled** | disabled | disabled |
| Edytuj osobę z drzewa | enabled | enabled | enabled |
| Ustaw osobę-korzeń drzewa | enabled | enabled | enabled |
| Zapisz zmiany dla osoby na drzewie | disabled | **enabled** | disabled |
| Wczytaj szkic osoby | enabled | enabled | enabled |
| Zaktualizuj szkic osoby | disabled | disabled | **enabled** |
| Dodaj szkic osoby do drzewa | disabled | disabled | **enabled** |
| Odśwież drzewo | enabled | enabled | enabled |
| Odśwież rody | enabled | enabled | enabled |
| Wyjdź | enabled | enabled | enabled |

### 2.5 Code-level data structure

A `MenuMode` enum and a single `_menu_mode` attribute on `AddPersonFrame`:

```python
from enum import Enum

class MenuMode(Enum):
    NEW = "new"
    EDIT_TREE = "edit-tree"
    EDIT_DRAFT = "edit-draft"
```

The frame holds **two** menu-item references per mode-gated item (the wx `MenuItem` handles returned by `Menu.Append`) and a single `_apply_menu_mode(mode: MenuMode)` method that walks the matrix in §2.4 and toggles each one via `menu_bar.Enable(item.GetId(), bool)`. The existing partial state (`self._save_edit_item` reference at line 807, the conditional enable at lines 1361/1442) collapses into the new `_apply_menu_mode`.

`_menu_mode` is the **single source of truth** going forward. The legacy `self._is_edit_mode` boolean (set at lines 126, 1359, 1406) becomes redundant — Sprint 14 either deletes it or aliases it to `_menu_mode == EDIT_TREE`. Decision: **alias for one release, delete in a follow-up sprint.** Rationale: avoids a cascade of unrelated test/grep churn; the alias is a one-line `@property` and is trivially safe.

`_apply_mode_visuals(mode_str)` (already exists, line 1370) is called from `_apply_menu_mode` as the second half of the same transition — bg-color + header strip + menu enable always change together. This co-locates ADR-005's visual contract with ADR-011's menu contract.

### 2.6 Note on the diacritic-codepoint list

The dispatch's listed codepoints are: ś (U+015B), ż (U+017C), ł (U+0142), ó (U+00F3), ą (U+0105), ę (U+0119). After labelling each action above I see **none of the eight Section labels use ś, ż, ł, or ó.** The only diacritics in the eight strings are:

- ę (U+0119) in "osobę", "korzeń"-adjacent labels (wait — that's ń)
- ą (U+0105) in "dodaj do drzewa" wait — no, that's "do drzewa", no ą there. Let me re-list:

Actually re-grepping the eight labels for diacritics:

- `Nowa osoba` — none
- `Zapisz osobę i dodaj do drzewa` — ę
- `Zapisz osobę jako szkic` — ę
- `Edytuj osobę z drzewa` — ę
- `Ustaw osobę-korzeń drzewa` — ę, **ń** (U+0144) — note `ń` is NOT in the dispatch's listed codepoints
- `Zapisz zmiany dla osoby na drzewie` — none
- `Wczytaj szkic osoby` — none
- `Zaktualizuj szkic osoby` — none
- `Dodaj szkic osoby do drzewa` — none

**Surface to reviewer**: only ę (U+0119) appears in the eight new labels, plus ń (U+0144) in "Ustaw osobę-korzeń drzewa" which is NOT in the dispatch's listed codepoint set. ń **must also be grep-verified**. The dispatch's other listed codepoints (ś, ż, ł, ó, ą) are not present in any of these eight strings — verifying them in the new menu code will produce zero matches, which is the expected outcome. Reviewer should grep ę (U+0119) and ń (U+0144) and check both are correct.

The Plik-menu items that survive verbatim from Sprint 13 (`Odśwież drzewo`, `Odśwież rody`, `Wyjdź`) use ś (U+015B) and ż (U+017C) — already correct, do not touch.

## 3. Specific code-level contracts

### 3.1 Bug fix: load-draft must restore UUID; new "Zaktualizuj szkic osoby" handler

**Change to `on_load_draft_click`** (insert after line 1310 `self._is_dirty = False`, before `self._apply_mode_visuals('edit-draft')`):

```python
# ADR-011 §3.1: restore the loaded draft's UUID into frame state so subsequent
# saves overwrite the same file. Without this, _collect_all_data_to_dict() reads
# self.unique_identifier (set in __init__) and Zaktualizuj writes a NEW file.
self.unique_identifier = PersonDataWrapper(data).get_unique_identifier() or self.unique_identifier
# Persist the draft's filesystem path so the update handler can verify it later.
# This mirrors the (self.location, self.unique_identifier) pair used by edit-tree mode.
self._loaded_draft_path: str = path
```

`self._loaded_draft_path` is a new frame attribute. Initialize in `__init__` to `None` (next to `self.location = ''` at line 122). Reset to `None` inside `_reset_to_add_mode` (next to `self.location = ''` at line 1404).

**New handler `on_update_draft_click`** (mirrors `on_save_draft_click` but uses the stored path):

```python
@log_user_action("Update draft")
def on_update_draft_click(self, event: wx.Event) -> None:
    """Overwrite the currently loaded draft file in place.

    Pre-condition: self._menu_mode == MenuMode.EDIT_DRAFT (enforced via menu enable).
    Pre-condition: self._loaded_draft_path is a real file inside <poczekalnia>.

    The draft's UUID was restored into self.unique_identifier in on_load_draft_click,
    so save_person_draft writes back to <poczekalnia>/<self.unique_identifier>.json
    — the SAME file the user loaded. No new UUID is generated anywhere on this path.
    """
    try:
        data_dump = PersonDataWrapper(self._collect_all_data_to_dict())
        # Defensive parity check: data's UUID should equal the frame's UUID should
        # equal the loaded-path basename. Drift here means upstream state was lost.
        # On mismatch we still save (user intent is "update what I'm looking at")
        # but log_error a context line so it surfaces in the journey log.
        expected_uid = data_dump.get_unique_identifier()
        path_uid = Path(self._loaded_draft_path).stem if self._loaded_draft_path else None
        if path_uid and expected_uid and path_uid != expected_uid:
            log_error(
                RuntimeError(
                    f"Draft UUID drift: path={path_uid} data={expected_uid}"
                ),
                context="Update draft: UUID drift detected; overwriting by data UUID",
            )
        self._tree_service.save_person_draft(data_dump)
    except Exception as e:
        log_error(e, context="Update draft: write failed")
        polish_dialog(
            self,
            f"Nie udało się zaktualizować szkicu.\n\n{e}",
            "Błąd zapisu szkicu",
            wx.OK | wx.ICON_ERROR,
        )
        return
    self._is_dirty = False
    polish_dialog(self, "Szkic zaktualizowany.", "Zapisano", wx.OK | wx.ICON_INFORMATION)
    self._reset_to_add_mode()  # per §2.3: any successful save → mode resets to NEW
```

**Why `save_person_draft` works unchanged**: looking at `tree_service.py` lines 48-55, the method already uses `person_draft.get_unique_identifier()` as the filename key. Once `self.unique_identifier` is correctly the loaded draft's UUID (fix above), the same service method overwrites the correct file. No service-layer change needed.

### 3.2 Promote-disposes-draft: "Dodaj szkic osoby do drzewa" handler

Today's "Zapisz osobę i dodaj do drzewa" handler (`on_save_click` lines 876-940) **already** has the draft-cleanup pattern at lines 920-928. Re-using it verbatim for the new "Dodaj szkic osoby do drzewa" handler:

```python
@log_user_action("Promote draft to tree")
def on_promote_draft_click(self, event: wx.Event) -> None:
    """Promote the currently loaded draft to a full tree person and delete the draft file.

    Pre-condition: self._menu_mode == MenuMode.EDIT_DRAFT (enforced via menu enable).

    Steps:
      1. Validate + resolve + preflight (same as on_save_click).
      2. save_person_and_add_to_tree (creates the tree person folder under Lista osób/).
      3. Delete the draft file at <poczekalnia>/<self.unique_identifier>.json.
         If delete fails: log INFO-CLEANUP line and continue silently — the tree
         person is canonical; the orphan draft is harmless.
      4. Reset to NEW mode.
    """
    # Steps 1-2 are copy-paste from on_save_click; refactor to a shared helper or
    # keep duplicated — implementor's call. Recommended: keep duplicated to avoid
    # breaking the on_save_click happy-path that 159 existing tests cover.
    errors = self._validate_form()
    if errors:
        polish_dialog(self, "\n".join(errors), "Błąd walidacji", wx.OK | wx.ICON_WARNING)
        return
    person_data = PersonDataWrapper(self._collect_all_data_to_dict())
    try:
        self._resolve_relationship_paths(person_data)
    except ValueError as e:
        log_error(e, context="Promote draft: resolve_relationship_paths failed")
        polish_dialog(self, str(e), "Błąd danych", wx.OK | wx.ICON_ERROR)
        return
    try:
        self._preflight_checks(person_data)
    except (FileNotFoundError, IOError) as e:
        polish_dialog(self, str(e), "Błąd dostępu do pliku", wx.OK | wx.ICON_ERROR)
        return
    try:
        self._tree_service.save_person_and_add_to_tree(person_data)
    except Exception as e:
        log_error(e, context="Promote draft: save_person_and_add_to_tree failed")
        polish_dialog(self, f"Nie udało się zapisać osoby.\n\n{e}", "Błąd zapisu", wx.OK | wx.ICON_ERROR)
        return

    # Step 3: delete the loaded draft (user-locked decision #1: promote disposes draft)
    draft_path = self._tree_service._file_service.get_poczekalnia_path() / f"{self.unique_identifier}.json"
    try:
        if draft_path.exists():
            draft_path.unlink()
    except (OSError, RuntimeError) as cleanup_exc:
        # Non-fatal — the tree person is canonical. Log INFO-CLEANUP and continue.
        # ADR-007 §4.5 line shape. Lifting the existing _emit_cleanup_failure helper
        # to a public log_cleanup_failure() API — see §3.4.
        from helpers.logger import log_cleanup_failure
        log_cleanup_failure(draft_path, cleanup_exc)

    person_name_for_msg = person_data.get_person_name()
    self._refresh_people_list()
    self._reset_to_add_mode()
    polish_dialog(
        self,
        f"Osoba \"{person_name_for_msg}\" została pomyślnie dodana do drzewa "
        "(szkic został usunięty).\n\n"
        "Formularz został wyczyszczony — możesz dodać kolejną osobę.",
        "Zapisano",
        wx.OK | wx.ICON_INFORMATION,
    )
```

**Note on existing `on_save_click` at lines 920-928**: that block already deletes a draft file matching the current `self.unique_identifier`. In **NEW mode**, `self.unique_identifier` is the launch-time fresh UUID; no draft file matches; the `if draft_path.exists()` check is a no-op — safe. The block stays unchanged. The new `on_promote_draft_click` is a sibling, not a replacement.

### 3.3 Forward-compat hook for "person degradation" (tree → draft fork)

User parked this feature explicitly. Leave a single comment block at the Section 2 menu-construction site:

```python
# Section 2 — In-tree people management
section2_save = file_menu.Append(wx.ID_ANY, "Zapisz zmiany dla osoby na drzewie")
self.Bind(wx.EVT_MENU, self.on_save_edit_click, section2_save)
# FUTURE (parked 2026-05-11): "person degradation" — a fourth Section 2 item
# "Zapisz osobę z drzewa jako szkic" that copies the tree person's me.json into
# Poczekalnia/ under a fresh UUID and switches mode to EDIT_DRAFT for further
# editing. Out of scope for Sprint 14 per user lock. When implementing: enable
# only in EDIT_TREE mode; the state-machine matrix in ADR-011 §2.4 gains one row.
```

No code, no test, no enum value. Just the comment.

### 3.4 Promote `_emit_cleanup_failure` to a public helper

Currently `helpers/logger.py` line 248 has a module-private `_emit_cleanup_failure(log_file: Path, exc: BaseException) -> None` used by `cleanup_old_logs`. The §3.2 promote-fails-on-delete path needs the same line shape. **Two options:**

- **Option A**: lift the helper to a public name `log_cleanup_failure(target: Path, exc: BaseException)`. One-line rename + add it to the module's exported names. Update the two existing call sites in `cleanup_old_logs`.
- **Option B**: call `log_error(exc, context="Cleanup: failed to delete <path>")`. Writes an `[ERROR]` line, not `[INFO-CLEANUP]`. Semantically wrong: cleanup-failure is informational, not an error.

**Decision: Option A.** Rationale: the INFO-CLEANUP severity already exists in ADR-007 §4.5 and is used for exactly this case (best-effort delete failed, user impact = none). Promoting the helper to public is a one-line change and keeps severity semantics honest. The renamed parameter goes from `log_file: Path` to `target: Path` since it now covers both old logs and orphan drafts.

### 3.5 Idempotency / re-entrancy of Section 1 saves in NEW mode

Per user decision #3, Section 1 saves are enabled on a blank form. Concrete behavior:

- Click "Zapisz osobę i dodaj do drzewa" with all fields blank → `_validate_form` returns `[]` (line 1007 — empty list, no validation yet) → `_collect_all_data_to_dict` produces a person with `first_name="(nieznane)"`, `last_name="(nieznane)"`, full_name `"(nieznane) (nieznane)"` (line 1585/1594 fallbacks). `save_person_and_add_to_tree` creates a folder named `(nieznane) (nieznane)` under `Lista osób/`.
- Click "Zapisz osobę jako szkic" with all fields blank → writes `<poczekalnia>/<self.unique_identifier>.json` with all `(nieznane)` fields.
- 100 such clicks → 100 such files. User explicitly accepted this.

**No additional guard logic.** Validation as a future feature is a PRD-shaped item, not ADR-011 scope.

## 4. Alternatives considered

### 4.1 Alt-1: Fix the bug only, leave the menu structure flat

Diff: add `on_update_draft_click` + the load-time UUID restoration. Skip the 3-section restructure, skip the state machine, leave the existing partial mode toggling intact.

Rejected because: it fixes the immediate symptom but leaves the structural defect (no clear mapping from "what mode am I in" to "which actions are legal"). The user explicitly redesigned the menu in the chat. Implementing only the bug fix would force a second visit for the same code locus within weeks.

### 4.2 Alt-2: Per-field dirty tracking + save-button enable/disable

Diff: drive save-action enable state from `self._is_dirty` rather than from `_menu_mode`. Section 1 saves disabled when form is empty + clean.

Rejected because: user explicitly chose against this. Quote (chat 2026-05-11): "technically we can open the app and save 100 empty files for now, regardless of this making sense or not." Adding per-field validation is a future PRD scope item, not a Sprint 14 architecture decision.

### 4.3 Alt-3: Submit a `MenuRouter` class that owns the matrix declaratively

Diff: introduce `frames/menu_router.py` with a 9×3 declarative table + a single `route(mode)` method. The frame holds an instance and delegates all enable/disable through it.

Rejected because: M-class project, S-class sprint. A 12-row dict literal on the frame plus a `_apply_menu_mode` method is sufficient. A separate router class is justified only when the matrix grows to ~25+ rows or when multiple frames need shared mode logic — neither is true today. **Forward-compat note**: if the "person degradation" feature lands (§3.3) plus 2-3 more mode-gated actions, the dict literal becomes hard to read; that's the natural trigger for a follow-up extraction sprint.

### 4.4 Alt-4: Use wx.UpdateUIEvent for menu state instead of explicit `_apply_menu_mode` calls

Diff: bind `wx.EVT_UPDATE_UI` on each mode-gated menu item; the handler reads `self._menu_mode` and calls `event.Enable(bool)`. Lets wxPython drive the polling.

Rejected because: harder to test. `wx.EVT_UPDATE_UI` fires on idle, which is unreachable in a no-mainloop unit-test fixture. The explicit `_apply_menu_mode(mode)` call after each transition is trivially testable: assert that calling it twice with the same mode is idempotent and that each mode toggles the matrix correctly. Halt-D's "no wx mainloop required" rests on this.

### 4.5 Alt-5: Replace `self._is_edit_mode` with `_menu_mode` immediately + sweep all references

Diff: in Sprint 14, every read of `self._is_edit_mode` becomes a read of `self._menu_mode == MenuMode.EDIT_TREE`. Net deletion ~3 lines + test churn.

Rejected for **this sprint** because: cascade of small changes across `_load_person_for_edit`, `_reset_to_add_mode`, `on_save_edit_click` for marginal benefit. The alias-via-property approach (§2.5) is one line, behaviorally identical, and lets the implementor focus on the state machine + bug fix. **Follow-up sprint candidate** — file as Sprint 15 carry-forward.

## 5. Worked example: the regression-test trace

Setup (simulating the user's report):

1. Tree root at `C:/Sorted tree/`. `Poczekalnia/` empty.
2. User clicks `Nowa osoba`. Mode = NEW. `self.unique_identifier = X` (some fresh UUID).
3. User fills in "Jan", "Kowalski". Clicks `Zapisz osobę jako szkic`.
   - `on_save_draft_click` → `save_person_draft(data with UID=X)` → writes `<poczekalnia>/X.json`. Mode → NEW (reset).
   - **State at end**: `Poczekalnia/X.json` exists, frame `self.unique_identifier = X2` (fresh, post-reset).
4. User clicks `Wczytaj szkic osoby`. Picker shows one draft (Jan Kowalski). User picks it.
   - `on_load_draft_click` → loads X.json → `_fill_form_from_draft(data)` → **NEW: `self.unique_identifier = X`** (restored from data) + **NEW: `self._loaded_draft_path = "C:/Sorted tree/Poczekalnia/X.json"`**. Mode → EDIT_DRAFT.
5. User edits "Kowalski" → "Nowakowski". Form is now dirty.
6. User clicks `Zaktualizuj szkic osoby` (Section 3, EDIT_DRAFT-only, enabled).
   - `on_update_draft_click` → `_collect_all_data_to_dict` returns `{..., unique_identifier: X, ...}` (because `self.unique_identifier == X`).
   - `save_person_draft(data with UID=X)` → writes `<poczekalnia>/X.json` (overwrites).
   - **`Poczekalnia/X.json` is overwritten**, NOT created next to a hypothetical `Poczekalnia/Y.json`. Mode → NEW.

**Bug regression test assertion**:

```python
def test_zaktualizuj_szkic_overwrites_same_uuid_no_duplicate(tmp_path, monkeypatch, me_json_factory):
    # Setup: tree service + a draft with UUID X
    root, ts = _make_tree_service(tmp_path, monkeypatch)
    poczekalnia = ts._file_service.get_poczekalnia_path()
    X = "11111111-1111-1111-1111-111111111111"
    draft_data = me_json_factory(uid=X, name="Jan Kowalski", first_name="Jan", last_name="Kowalski")
    ts.save_person_draft(PersonDataWrapper(draft_data))
    assert (poczekalnia / f"{X}.json").exists()
    initial_files = list(poczekalnia.iterdir())
    assert len(initial_files) == 1

    # Simulate load: read the draft and prepare an "edited" version with the SAME UID
    loaded = ts.load_person_draft(str(poczekalnia / f"{X}.json"))
    edited = PersonDataWrapper(loaded)
    edited.set_last_name("Nowakowski")
    edited.set_person_name("Jan Nowakowski")
    # CRITICAL: the loaded UUID must travel through the edit
    assert edited.get_unique_identifier() == X

    # Simulate "Zaktualizuj szkic osoby": save_person_draft with the same UID
    ts.save_person_draft(edited)

    # Assert: still ONE file, still UUID X, contents are the edited version
    final_files = list(poczekalnia.iterdir())
    assert len(final_files) == 1
    assert final_files[0].name == f"{X}.json"
    final_data = ts.load_person_draft(str(final_files[0]))
    assert final_data["last_name"] == "Nowakowski"
```

This is a **service-level** regression test. It locks the data contract. The frame-level wiring (that `self.unique_identifier` is correctly restored on load and that the new menu item invokes the path with this UUID) is covered by separate state-machine tests in §6.

## 6. Test strategy (L0/L1)

All L0 tests are pure-Python or service-level (no wx mainloop). Halt criterion D in the sprint plan: implementor surfaces any wx-only paths instead of skipping coverage silently.

**Group A — Bug regression (1 test, must fail against current `main`):**

- `test_zaktualizuj_szkic_overwrites_same_uuid_no_duplicate` (above, §5).

**Group B — State-machine transitions (5 tests):**

These test a small extracted pure function: `compute_menu_state(mode: MenuMode) -> Dict[str, bool]` that returns the per-action enable matrix. The frame's `_apply_menu_mode` calls this function. By testing the function directly we avoid wx ceremony.

- `test_compute_menu_state_NEW_section1_enabled_others_disabled`
- `test_compute_menu_state_EDIT_TREE_only_section2_save_enabled`
- `test_compute_menu_state_EDIT_DRAFT_only_section3_save_and_promote_enabled`
- `test_compute_menu_state_all_modes_have_load_actions_enabled` (parametrized over 3 modes)
- `test_compute_menu_state_unknown_mode_raises_or_defaults_to_NEW` (defensive)

**Group C — Mode transitions on save (3 tests):**

These test that the frame method that handles "after-save bookkeeping" sets mode → NEW. Since calling `_reset_to_add_mode` requires a live wx frame, factor the mode-flip into a small pure method `_post_save_transition()` that updates `self._menu_mode` and resets internal state — testable without wx by constructing a mock frame.

- `test_post_save_transition_from_NEW_lands_in_NEW`
- `test_post_save_transition_from_EDIT_TREE_lands_in_NEW`
- `test_post_save_transition_from_EDIT_DRAFT_lands_in_NEW`

**Group D — Promote-disposes-draft (2 tests, service-level):**

- `test_promote_draft_to_tree_deletes_draft_file_happy_path`:
  - Setup: draft X in Poczekalnia, person data has parents resolved to existing folders.
  - Action: `ts.save_person_and_add_to_tree(data)` + post-step `draft_path.unlink()` mimicking the frame's promote handler.
  - Assert: `Lista osób/<name>/me.json` exists AND `Poczekalnia/X.json` does NOT exist.
- `test_promote_draft_delete_fails_logs_info_cleanup_continues`:
  - Setup: same as above; monkey-patch `Path.unlink` to raise `PermissionError` for the draft path.
  - Action: invoke the promote sequence wrapped in the same try/except as §3.2.
  - Assert: tree-person folder exists (promote succeeded); today's `<root>/.PyTreeManager/logs/<today>__exceptions.log` contains an `[INFO-CLEANUP]` line referencing the draft path; the exception did NOT propagate out of the handler.

**Group E — Polish-label codepoint check (1 test):**

- `test_menu_labels_have_correct_diacritics`: read `frames/add_person_frame.py` source as text, assert all 9 menu strings from §2.2 are present verbatim. Catches a stray ASCII transliteration. This is a meta-test against the source file — same pattern Sprint 08 used to lock Qt mockup diacritics.

**Out of scope for L0**:

- Live wx menu rendering (manual smoke).
- `wx.EVT_MENU` binding correctness (manual smoke).
- Visual mode-color application (already covered by ADR-005 + manual smoke).

**Estimated test count delta**: +12 tests. Baseline 159 → 171 after Sprint 14.

## 7. Edge cases NOT decided here

These are flagged for `decision-needed.md` and the user's awareness:

- **Loaded draft's file deleted on disk between load and Zaktualizuj click**: the existing `save_person_draft` (`tree_service.py` line 54) calls `write_me_file` which uses `open(path, 'w')` (creates if missing). So Zaktualizuj **silently recreates** the deleted file at the same UUID path. Whether this is correct behavior or should error-out is a UX call. **Flagged in decision-needed.md.**

- **What happens if user runs through EDIT_DRAFT → Zaktualizuj → mode resets to NEW → user immediately clicks Wczytaj again on the same draft?**: works correctly — load reads the freshly-overwritten file and re-enters EDIT_DRAFT. No issue.

- **Two app instances editing the same draft**: out of scope (the app has never been multi-instance safe; not Sprint 14's concern).

## 8. Citations

All code-line references above are against `frames/add_person_frame.py` at commit `4b7bea7` (HEAD of `feature/sprint-13-phase-a` as of 2026-05-11). Re-verify line numbers if the file has been touched between this ADR's date and implementation.

User decision sources: in-chat AskUserQuestion answers 2026-05-11. The three locked decisions are summarized in the dispatch and recorded verbatim in §1.3 of this ADR.

Logger INFO-CLEANUP severity: ADR-007 §4.5 (line shape) + `helpers/logger.py` lines 248-271 (current implementation).
