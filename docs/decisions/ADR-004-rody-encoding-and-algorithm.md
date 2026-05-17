---
id: ADR-004
title: Rody encoding scheme + surname-extraction algorithm + .lnk targets
kind: tech
status: superseded-by ADR-016
date: 2026-05-09
amended: 2026-05-17
author: architect
sprint: sprint-10
---

## Changelog

- **2026-05-17** — superseded by **ADR-016**. Issue
  [#20](https://github.com/TomaszMankin/py-tree-manager/issues/20) showed
  the flat `<surname>.lnk` shape does not match the user's mental model
  (a lineage is a set of people, not a single contributor). The new
  `<root>/Rody/<surname>/<person>.lnk` subfolder layout + R1-R4 membership
  rules live in ADR-016. The `extract_lineage_surname` function + the
  four-contributors enumeration order + the first-contributor collision
  rule survive verbatim (cited as sources in ADR-016 §2.1, §3.5).
  Everything else in this ADR is replaced.
- **2026-05-09** — initial drafting (Sprint 10 design dispatch).
- **2026-05-09 (revision, same day)** — §7 dependency on Sprint 09's
  `get_effective_parent_ids` helper **dropped**. The helper was tied to a
  data-drift hypothesis (parents_id-vs-parents asymmetry in brownfield
  me.json files) that user-verified on-disk evidence refuted. The wxPython
  app's add/edit save flow IS symmetric (verified at
  `C:\Temp\pytreemanager-smoke`). Rody's surname extraction now walks
  `parents_id` directly via `get_parent_ids()`. See ADR-003 Amendment 2
  changelog for the same revision; see JOURNAL 2026-05-09 orchestrator entry
  "architect diagnosis revision — verified evidence" for the source.

## Context

PRD-004 defines Rody as a flat directory of `.lnk` shortcuts under
`<root>/Rody/`, one per **distinct family-branch surname** ("ród"), derived
from the root person's parents + root's spouse(s)'s parents. This ADR pins
three technical decisions:

1. **Filename encoding** for the shortcuts.
2. **Surname-extraction algorithm** (handle maiden names, multi-component,
   missing data, collisions, diacritics).
3. **Where the shortcut points** (target person folder).

Plus the implementation-shape decision: new `services/rody_service.py` vs
extending `services/drzewo_service.py`.

## Decision

### 1. Filename encoding

Format: `<surname>.lnk`

Bare. No NN sort key. No couple code. No gender. No bracket prefixes.

Examples (root = Tomasz; his parents are Adam Mankin and Anna Mankin née
Pastryk; his spouse is Maria; her parents are Piotr Kowalski and Ewa Kowalska
née Nowak):

```
Rody/Kowalski.lnk
Rody/Mankin.lnk
Rody/Nowak.lnk
Rody/Pastryk.lnk
```

Sorted alphabetically by Windows Explorer's default natural sort
(StrCmpLogicalW). Plain Unicode lexical works for typical Polish surnames.

**No NN sort key needed**: there is no generation hierarchy to encode. Surname
alone is the primary sort key.

**No multi-bracket scheme needed**: the four pieces of metadata in Drzewo
(generation, sign-display, couple-code, gender) all serve hourglass-display
needs. Rody has no such needs — one surname = one entry, no relationships
between entries.

### 2. Surname-extraction algorithm

```
def extract_rod_surname(person_data: PersonDataWrapper) -> Optional[str]:
    """Return the rod (family-branch) surname for a person, or None if unknown."""
    if person_data.get_has_maiden_name():
        candidate = (person_data.get_maiden_name() or "").strip()
    else:
        candidate = (person_data.get_last_name() or "").strip()

    if not candidate:
        return None
    if candidate == "(nieznane)":
        return None
    return candidate
```

Strip leading/trailing whitespace defensively. The `(nieznane)` sentinel is
PersonDataWrapper.UNKNOWN — the form's "missing data" placeholder. We treat it
as "no surname".

`other_last_names` and `other_maiden_names` (the `;`-suffixed alternates) are
**ignored**. Per PRD-004 they are alternate display forms of the same identity.

Multi-component surnames ("Kowalski-Nowak", "Wojciech-Sienkiewicz") are kept
**whole** as a single ród. We do not split on `-`.

Polish diacritics (ą, ć, ę, ł, ń, ó, ś, ź, ż) are preserved. ADR-001
(IShellLinkW + IPersistFile.Save) guarantees Polish-character-safe `.lnk`
filenames.

### 3. Surname collection — the "four contributors" rule

```
def collect_rod_surnames(root_uuid, fs) -> Dict[str, str]:
    """Return {surname -> person_uid} for the root and root's spouses' parents.

    Order of enumeration is deterministic — same order every rebuild:
        1. root.parents[0]   (typically father)
        2. root.parents[1]   (typically mother)
        3. for each spouse in root.spouses (in me.json list order):
              4. spouse.parents[0]
              5. spouse.parents[1]

    On collision (same surname from two contributors), the FIRST encountered
    contributor wins — their UUID is kept; subsequent contributors with the
    same surname are dropped (their UID is not stored against the surname).
    """
    surnames: Dict[str, str] = {}  # surname -> person_uid
    log: List[str] = []

    def consider(person_uid: str, role_for_log: str) -> None:
        person_data = read_person(person_uid)
        if person_data is None:
            log.append(f"RODY: {role_for_log} (uid={person_uid}) not in cache; skipped.")
            return
        s = extract_rod_surname(person_data)
        if s is None:
            log.append(f"RODY: {role_for_log} (uid={person_uid}) has no rod surname; skipped.")
            return
        if s in surnames:
            log.append(f"RODY: surname '{s}' already contributed by earlier "
                       f"slot; {role_for_log} (uid={person_uid}) does not add a shortcut.")
            return
        surnames[s] = person_uid

    root = read_person(root_uuid)
    if root is None:
        log.append(f"RODY: root uid={root_uuid} unreadable.")
        return surnames, log

    for i, parent_uid in enumerate(root.get_parent_ids()):
        consider(parent_uid, f"root.parent[{i}]")

    for j, spouse_uid in enumerate(root.get_spouse_ids()):
        spouse = read_person(spouse_uid)
        if spouse is None:
            continue
        for i, sp_parent_uid in enumerate(spouse.get_parent_ids()):
            consider(sp_parent_uid, f"spouse[{j}].parent[{i}]")

    return surnames, log
```

This honors the PRD-004 rule:
- Up to two surnames from root's parents.
- Up to two-per-spouse from each spouse's parents.
- Collisions favor the **first contributor** in the enumeration order (root's
  parents first, spouses' parents next).
- Missing data is logged, not crashed.

**Note (Amendment 2026-05-09)**: an earlier draft of this ADR cross-referenced
a `get_effective_parent_ids` reverse-lookup helper from ADR-003 Amendment 2.
That helper is **dropped** in the same-day revision of ADR-003 Amendment 2 —
user-verified on-disk evidence (`C:\Temp\pytreemanager-smoke`) showed the
wxPython app's save flow keeps `parents_id` and `parents` symmetric, so no
drift-recovery is needed on this codepath. Rody calls
`person.get_parent_ids()` directly. If a real drift case is reported later
(likely against the brownfield 707-file `C:/Sorted tree/` dataset), Rody
should pick up whatever helper is added at that point — but this is not a
Sprint 10 concern.

### 4. Where each shortcut points

Each shortcut named `<surname>.lnk` targets the folder of the **first
contributor** with that surname (the UID stored in `surnames[s]` from the
algorithm above).

That folder path is `cached_people[uid][LOCATION]` — a normal `Lista osób/<X>/`
folder. The shortcut is created via the existing `ShortcutHelper.create_shortcut`
(ADR-001's Polish-safe IShellLinkW path).

**Alternative considered and rejected**: target the most-senior known ancestor
with surname S (walk up from the contributor through parents until either S
no longer matches or no further parents). Rejected per PRD-004 — the
"first contributor" rule is intentionally simple and the user can navigate
upward from the contributor's folder using existing `Rodzice/` shortcuts.
Walking up costs more I/O, more code, more edge cases (when does S "still
match"? what if a daughter married away from S but her father carried S?),
for marginal value.

### 5. Filename collisions on disk

When two surnames are extracted and they happen to be **identical** (after
strip), the algorithm above keeps only the first contributor — there is
exactly one `<surname>.lnk` per distinct surname. So the `(2)` /` (3)`
disambiguation pattern Drzewo uses (ADR-003 section 2c) is **not needed** in
Rody. There is no filename collision because there is no second entry.

If two surnames are **almost-identical** but differ in diacritics or case
("Kowalski" vs "kowalski"), they are treated as distinct surnames (Unicode
exact match). This matches the user's data — surname normalization is a
canonical-data concern, not a Rody-render concern.

If two surnames appear identical in the filename but differ in invisible
characters (e.g., zero-width joiner), Python's `==` will see them as
different and emit two `.lnk` files. In practice this does not happen in
real genealogical data; if a user reports it, fix is one strip+normalize
call in `extract_rod_surname`.

### 6. Refresh model + menu wiring

Mirror the Drzewo pattern from PRD-003 / Sprint 07:

**TreeService changes**:
- New method `TreeService.rebuild_rody() -> Tuple[int, List[str]]` (count of
  shortcuts written + log entries; mirrors `rebuild_drzewo`).
- The existing `set_drzewo_root_person()` rename to nothing (keep the name —
  Rody shares the root with Drzewo per PRD-004). The caller-side flow:
  `_on_pick_drzewo_root_click` calls `set_drzewo_root_person`,
  then calls **both** `rebuild_drzewo()` and `rebuild_rody()` in sequence.

**Frame changes** (`frames/add_person_frame.py`):
- New menu item "Odśwież rody" — Polish exact text, no diacritic ASCII fallback.
  Wired to a new handler `_on_refresh_rody_click` that mirrors
  `_on_refresh_drzewo_click` — guard against no-root-set, call
  `tree_service.rebuild_rody()`, show a Polish success/failure dialog.
- The existing root-picker handler `_on_pick_drzewo_root_click` extends to
  also call `rebuild_rody()` after `rebuild_drzewo()`. Both dialogs collapse
  into one composite success message ("Drzewo zbudowane: N skrótów. Rody
  zbudowane: M skrótów.") OR two sequential dialogs — implementor picks the
  cleaner UX; the spec is that BOTH rebuild on root change.

**FileService changes**:
- `set_root_folder()` adds `<root>/Rody/` to the folders it creates
  (alongside `Lista osób/`, `Drzewo/`, `Poczekalnia/`).

### 7. Implementation shape — new file vs. extend drzewo_service.py

**Decision: new file** `services/rody_service.py`.

Rationale:
- Different selection rule (surname-derived, not hourglass).
- Different encoding (no brackets, no NN, no couple code, no gender).
- Different sort axis (alphabetic on surname, not numeric on generation).
- The two services share **only** the wipe-and-rebuild ceremony and the
  `ShortcutHelper.create_shortcut` call — both already exist in `TreeService`
  and don't need internal abstraction.

What the new file contains:
- `class RodyService:` with `compute_rody(root_uuid) -> Tuple[Dict[str, str], List[str]]`
  returning `({surname -> person_uid}, log_entries)`.
- Module-level helper `extract_rod_surname(person_data) -> Optional[str]`.
- No filename-render function (the filename is just `f"{surname}.lnk"` —
  inlined at the rebuild site; not worth a function).

**What does NOT go in rody_service.py**:
- A drift-recovery / reverse-lookup helper for `parents_id` ↔ `parents`
  reconciliation. Earlier draft of this ADR specified one (the
  `get_effective_parent_ids` helper from ADR-003 Amendment 2's earlier
  draft); both are dropped per the 2026-05-09 same-day revision. The
  wxPython save flow is symmetric on the live test data. Rody calls
  `person.get_parent_ids()` directly. **Sprint 10 has no cross-sprint
  helper dependency.**

### 8. Test coverage

L0 tests in `tests/services/test_rody_service.py`:

1. **Empty root** — root has no parents and no spouses → empty `{}` returned;
   Rody folder exists but empty after rebuild.
2. **Single-spouse, four-grandparents** — typical case → 4 surnames returned;
   shortcut filenames match expected (alphabetical).
3. **Mother carries maiden name** — has_maiden_name=True → maiden_name is
   used, not last_name. Cite the wrapper's UNKNOWN sentinel handling.
4. **Father has no recorded last_name** → he contributes nothing; log entry
   present; build succeeds.
5. **Surname collision** — root's father AND root's spouse's father share
   the same last_name → exactly ONE shortcut, pointing to root's father (first
   in enumeration); log entry "already contributed by earlier slot".
6. **Multiple spouses** — root has two spouses each with two parents → up to
   6 surname slots; collisions handled per the same first-contributor rule.
7. **Diacritics preserved** — surname "Łukasiewicz" round-trips to filename
   `Łukasiewicz.lnk` (verifies ADR-001 IShellLinkW Polish-safety still
   applies; mock the helper as in existing Drzewo tests).
8. **(Dropped — was a drift-case test tied to the dropped helper)**. The
   user-verified test tree at `C:\Temp\pytreemanager-smoke` confirms the
   wxPython save flow is symmetric; no drift defense needed. Test #8
   originally exercised the `get_effective_parent_ids` reverse-lookup path
   that no longer exists. Slot left empty rather than renumbered to keep
   the count at "8 L0 tests" matching the Sprint 10 plan's effort estimate.
   If a real drift case is reported later, a regression test is added at
   that time.

L1 integration test (one only, mirrors Sprint 07's `tests/integration/`
posture):
9. **End-to-end build against synthetic 7-person tree** — drives
   `TreeService.rebuild_rody()` against a synthetic tree; asserts files
   exist on disk with correct names; mock `ShortcutHelper.create_shortcut`.

## Alternatives considered

- **Encoding option B — include the contributor's relation prefix**
  (`father.lnk`, `mother.lnk`, `spouse-father.lnk`, ...). Rejected. The user's
  intent for "ród" is the surname identity, not the relation. Forcing prefixes
  shifts the semantic axis.
- **Encoding option C — include couple-letter as Drzewo does** to handle
  collision. Rejected per PRD-004 — collisions resolve to first-contributor;
  no second `.lnk` needs to exist.
- **Algorithm option B — walk up to most-senior ancestor with surname S**.
  Rejected per PRD-004 (out of scope). One walk per surname costs N
  me.json reads (where N is lineage depth); marginal user value.
- **Algorithm option C — auto-discover surnames from the entire tree**, not
  just immediate parents-of-root and parents-of-spouse. Rejected per PRD-004
  (out of scope; user explicitly framed it as the four-contributors rule).
- **Implementation option B — extend drzewo_service.py with Rody methods**.
  Rejected per "Implementation shape" above; different selection rule and
  encoding don't share enough internals.

## Consequences

**Positive:**
- Filename is human-readable at a glance ("which families am I dealing
  with?").
- Sort by surname matches user's mental model.
- Polish-character-safe via the existing IShellLinkW path.
- The wipe-and-rebuild model carries forward zero new state risk.
- The first-contributor-on-collision rule is deterministic — same rebuild
  every time given the same data.

**Negative:**
- A surname collision (two people with the same family name from different
  lineages) results in only ONE shortcut. The user sees fewer entries than the
  count of unique surname-bearing relatives. Build-log entry surfaces this.
- Surnames are not normalized — diacritic typos in source data produce
  duplicate "Łukasiewicz" / "Lukasiewicz" entries. This is a canonical-data
  problem, not a Rody problem.
- No clue is preserved as to "which contributor" the shortcut points to.
  The user has to open the shortcut to see. Acceptable — Rody is a directory
  of family-name landings, not a relationship navigator.

**Neutral:**
- The new `<root>/Rody/` folder appears alongside `<root>/Drzewo/` etc., visible
  in any normal Windows Explorer view of the root folder. No ambiguity about
  what it is — its name says it.
- Build-log lives at `<root>/Rody/build-log.txt` (mirrors Drzewo).

## Revisit when

- User reports specific Rody entries that are wrong because of the
  first-contributor-collision rule (e.g., he wants the maternal-grandmother's
  surname collision to point at *her* not at the paternal-uncle who happens
  to share the surname). Likely fix: add a "preferred-target" rule to the
  algorithm, not a contract change.
- User wants Rody to walk up to the most-senior known ancestor (per the
  rejected alternative). Trivial change in `compute_rody`.
- Multiple roots become a thing (currently single-root, shared with Drzewo).
  Then `Rody/` would need to be per-root same as Drzewo would, and PRD-003 +
  PRD-004 both revisit together.
- A user-facing "merge similar surnames" feature is requested. That's a
  canonical-data feature, not a Rody-rendering one — likely a new ADR.

## Sources

- PRD-004 — product scope; this ADR is the technical companion.
- ADR-003 Amendment 2 (revised 2026-05-09 same day) — the spouse-seeded
  ancestor DFS contract clarification. **Rody does not reuse any helper
  from ADR-003 Amendment 2** because the reverse-lookup helper that the
  earlier draft specified is dropped. The Polish-safe `.lnk` filename
  contract Rody inherits is unchanged.
- JOURNAL 2026-05-09 orchestrator entry "architect diagnosis revision —
  verified evidence" — the source for dropping the helper dependency.
- ADR-001 — IShellLinkW + IPersistFile.Save Polish-character contract.
- `wrappers/person_data_wrapper.py` lines 96-130 — `last_name`,
  `maiden_name`, `has_maiden_name` field semantics; the source of the
  surname-extraction rule.
- `wrappers/person_data_wrapper.py` line 230-235 — `get_full_name()` shows
  the existing app already treats `has_maiden_name + maiden_name` as the
  identity-defining surname display.
- `services/file_service.py` `set_root_folder()` — the existing site that
  creates `<root>/Drzewo/` and `<root>/Lista osób/` and `<root>/Poczekalnia/`;
  Rody adds `<root>/Rody/` to that list.
- `services/tree_service.py` `rebuild_drzewo()` — the existing
  wipe-and-rebuild pattern Rody copies. The Rody equivalent
  `rebuild_rody()` follows the same shape line-for-line.
- `frames/add_person_frame.py` lines 1390-1444 (Sprint 07 root-picker +
  refresh handlers) — the pattern Rody's menu wiring mirrors.
- KB-005 `~/.claude/kb/KB-005-windows-sortable-folder-encoding.md` — the
  StrCmpLogicalW reference; not directly cited because Rody's filename has
  no numeric sort key (it's pure alphabetic, where StrCmpLogicalW reduces to
  Unicode lexical for non-numeric strings).
- ADR-002 (wxPython baseline) — UI framework Rody menu items live in.
