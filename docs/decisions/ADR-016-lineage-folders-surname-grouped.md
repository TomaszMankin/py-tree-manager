---
id: ADR-016
title: Lineage folders — surname-grouped subfolders with descendant + ancestor membership
kind: tech
status: accepted
date: 2026-05-17
amended: 2026-05-17
author: architect
supersedes: ADR-004
iterates_with_user: true
---

## Changelog

- **2026-05-17 (amendment 1)** — R2 broadened from "root's direct children +
  their spouses" to "root's full descendant subtree" (every generation:
  children, grandchildren, …, plus each descendant's spouse). User clarified
  in #20 comment: root + all descendants reappear in every lineage folder.
  Pseudocode step 1 switches from one-level iteration to recursive walk.
  Risk R-1 closes (no longer user-decidable). Alt §4.3 transitions from
  deferred to accepted.

- **2026-05-17** — initial drafting. Supersedes ADR-004 in full. Origin: issue
  [#20](https://github.com/TomaszMankin/py-tree-manager/issues/20). ADR-004's
  flat `<surname>.lnk` shape never matched the user's mental model — one
  surname is a lineage, and a lineage is a *set of people*, not a single person.
  Replaced.

## Context

ADR-004 produced `<root>/Rody/<surname>.lnk` files, each targeting one
person folder (the "first contributor"). User opened issue #20 reporting
the build is "incorrect": clicking the shortcut jumps to a single parent
instead of opening a folder of people who belong to that lineage. The user
clarified in a follow-up comment:

> This ADR has to be replaced by a newer one. The bug here describes the
> expectations, because current form does not make any sense — how one person
> can state a lineage? Moreover — what if there are more people? All of them
> land in respective `Rody/<parent surname OR maiden name>/<people from that
> lineage>`.

Membership rules (verbatim from issue #20):

- Root + spouse appear in **all** lineage folders.
- Root's **full descendant subtree** (children, grandchildren, …, every generation reachable
  via `children_ids`) plus each descendant's spouse appears in **all** lineage folders.
- The contributing parent + their spouse appear in **their** lineage folder.
- Ancestors of the contributing parent who share the lineage surname appear
  in the folder; walk stops when the surname changes (don't drag mother's
  ancestors into father's lineage).

This ADR pins the new shape, the membership algorithm, the encoding rules,
the test plan, and the alternatives considered. Supersedes ADR-004 in full;
no part of ADR-004 survives.

## 1. Data shape

### 1.1 Folder + .lnk layout

```
<root>/Rody/
  <father-surname>/
    <root-display-name>.lnk             -> Lista osób/<root>
    <root-spouse-display-name>.lnk      -> Lista osób/<root-spouse>     (if exists)
    <child-1-display-name>.lnk          -> Lista osób/<child-1>
    <child-1-spouse-display-name>.lnk   -> Lista osób/<child-1-spouse>  (if exists)
    <father-display-name>.lnk           -> Lista osób/<father>
    <mother-display-name>.lnk           -> Lista osób/<mother>          (spouse of contributing parent)
    <father-father-display-name>.lnk    -> Lista osób/<father-father>   (surname matches)
    <father-father-spouse-display-name>.lnk -> Lista osób/<father-father-spouse>
    ... (further paternal ancestors whose surname still matches)
    build-log.txt

  <mother-maiden>/
    <root-display-name>.lnk
    <root-spouse-display-name>.lnk
    <child-1-display-name>.lnk
    <child-1-spouse-display-name>.lnk
    <mother-display-name>.lnk
    <father-display-name>.lnk            (spouse of contributing parent)
    <mother-mother-display-name>.lnk     (surname matches)
    ... (further maternal ancestors whose surname still matches)
    build-log.txt

  <root-spouse-father-surname>/         (if root has a spouse with parents)
    ...

  <root-spouse-mother-maiden>/
    ...
```

Up to 4 lineage subfolders (root's 2 parents + each spouse's 2 parents,
deduplicated by surname; collisions discussed in §3). At least 0 if root has
no parents and no spouses with parents. The four contributors are the same
set as ADR-004; only the membership-per-surname rule and the disk shape
change.

### 1.2 Worked example

Tree (placeholder names; PII rule — public repo, no real names):

```
<root> (spouse=<root-spouse>, parents=[<father>, <mother>], children=[<child-1>])
<root-spouse> (spouse=[<root>], parents=[<rs-father>, <rs-mother>])
<father> (last_name=<father-surname>, has_maiden=false, parents=[<gf-paternal>, <gm-paternal>])
<mother> (last_name=<father-surname>, maiden_name=<mother-maiden>, has_maiden=true, parents=[<gf-maternal>, <gm-maternal>])
<rs-father> (last_name=<rs-father-surname>, parents=[])
<rs-mother> (last_name=<rs-father-surname>, maiden_name=<rs-mother-maiden>, has_maiden=true, parents=[])
<child-1> (spouse=[<child-1-spouse>])
<child-1-spouse> (last_name=<unrelated>)

<gf-paternal>  (last_name=<father-surname>, parents=[<ggf-paternal>])
<gm-paternal>  (last_name=<father-surname>, maiden_name=<unrelated-maiden>, has_maiden=true)
<ggf-paternal> (last_name=<father-surname>)
<gf-maternal>  (last_name=<unrelated>, maiden=none)
<gm-maternal>  (last_name=<unrelated>, maiden_name=<mother-maiden>, has_maiden=true, parents=[<gggf-maternal>])
<gggf-maternal> (last_name=<unrelated-2>, maiden_name=<mother-maiden>, has_maiden=false)  # surname breaks chain
```

Contributing parents (root's parents + root-spouse's parents):

| Contributor | Lineage surname (extract_lineage_surname) |
|---|---|
| <father> | <father-surname> (has_maiden=false → last_name) |
| <mother> | <mother-maiden> (has_maiden=true → maiden_name) |
| <rs-father> | <rs-father-surname> |
| <rs-mother> | <rs-mother-maiden> |

Four subfolders. No collisions in this example.

Folder `<father-surname>/` membership (traced from algorithm §2.2):

1. Universal members (rules R1+R2 — root + full descendant subtree + descendant spouses):
   `<root>`, `<root-spouse>`, `<child-1>`, `<child-1-spouse>` → 4 shortcuts.
   Example tree has 1 generation of descendants only. If `<child-1>` had children, those
   `<grandchild-N>` + `<grandchild-N-spouse>` would also appear here (and recursively further).
2. Contributing parent (rule R3): `<father>` → 1 shortcut. Spouse of contributing parent (R3): `<mother>` → 1 shortcut.
3. Ancestors walk (rule R4) starts from `<father>`. For each ancestor, include only if `extract_lineage_surname(ancestor) == <father-surname>`.
   - `<gf-paternal>`: lineage surname = <father-surname>. Match. Include. Walk his parents next.
     - Spouse of `<gf-paternal>` = `<gm-paternal>`. Include as spouse-leaf (no walk).
   - `<gm-paternal>`: lineage surname = <unrelated-maiden> (has_maiden=true). No match. Exclude. Do NOT walk her parents. (She is still already included as `<gf-paternal>`'s spouse — leaf-level.)
   - `<ggf-paternal>`: parent of `<gf-paternal>`. Lineage surname = <father-surname>. Match. Include. Walk his parents (none). Done with this branch.

Folder `<father-surname>/` final shortcuts: 4 (universal) + 2 (contributing pair) + 3 (paternal ancestors) = **9 shortcuts**.

Folder `<mother-maiden>/` membership:

1. Universal: `<root>`, `<root-spouse>`, `<child-1>`, `<child-1-spouse>` → 4.
2. Contributing parent: `<mother>` → 1. Spouse: `<father>` → 1.
3. Ancestors walk from `<mother>`:
   - `<gf-maternal>`: lineage surname = <unrelated>. No match. Exclude. No walk.
   - `<gm-maternal>`: lineage surname = <mother-maiden> (has_maiden=true). Match. Include. Spouse-leaf `<gf-maternal>` included. Walk parents.
     - `<gggf-maternal>`: lineage surname = <unrelated-2> (has_maiden=false → last_name; despite maiden_name field being set, has_maiden=false means we use last_name). No match. Exclude. Stop branch.

Folder `<mother-maiden>/` final shortcuts: 4 + 2 + 2 = **8 shortcuts**.

The example traces cleanly through the pseudocode in §2.2. Note the
parity-check trace: rule R4's "include ancestor if surname matches" was
applied to `<gm-paternal>` (excluded — her lineage surname is her maiden name,
which differs from `<father-surname>`) AND her appearance via R4's
spouse-of-included-ancestor sub-rule (included — as `<gf-paternal>`'s
spouse-leaf, no further walk). Both behaviors come from the same pseudocode
block.

### 1.3 .lnk filename inside each subfolder

Each shortcut filename: `<person_display_name>.lnk` where `<person_display_name>`
is the folder name under `Lista osób/` for that person (which equals
`PersonDataWrapper.get_person_name()`).

Rationale: matches how `Lista osób/` already names person folders
(verified in `services/file_service.py` and `wrappers/person_data_wrapper.py`).
The Drzewo encoding scheme (generation prefix, couple code, gender) is NOT
applied — Rody is about identity, not the hourglass position. Plain
person-display-name keeps Rody readable at a glance.

## 2. Membership algorithm

### 2.1 Inputs

```
LineageService.compute_lineages(root_uuid: str) -> Tuple[Dict[str, LineageMembers], List[str]]

LineageMembers (new dataclass, lineage_service.py):
    surname: str           # the lineage surname (folder name)
    contributor_uid: str   # UID of the contributing parent (first wins on collision)
    member_uids: List[str] # ordered: root-side first, then contributor + spouse,
                           # then ancestors in walk order
```

Return shape changes from ADR-004's `Dict[str, str]` to
`Dict[str, LineageMembers]`. The empty-list / no-anomaly log entry pattern
from ADR-004 is preserved.

### 2.2 Pseudocode

```python
def compute_lineages(root_uuid) -> Tuple[Dict[str, LineageMembers], List[str]]:
    log: List[str] = []
    lineages: Dict[str, LineageMembers] = {}  # surname -> LineageMembers

    root = read_person(root_uuid)
    if root is None:
        log.append(f"LINEAGE: root uid={root_uuid} unreadable.")
        return lineages, log

    # --- Step 1: compute universal-member set (root + full descendant subtree) ---
    universal: List[str] = []          # ordered, deduplicated by UID
    universal_seen: Set[str] = set()

    def universal_add(uid):
        if uid and uid not in universal_seen:
            universal.append(uid); universal_seen.add(uid)

    def walk_descendants(person_uid):
        # Cycle-safe via universal_seen: a person already added is not re-walked.
        if person_uid in universal_seen:
            return
        person = read_person(person_uid)
        if person is None:
            log.append(f"LINEAGE: descendant uid={person_uid} not in cache; subtree below skipped.")
            return
        universal_add(person.uid)
        for sp in person.spouse_ids:
            universal_add(sp)        # spouses included as leaves; not walked further
        for ch in person.children_ids:
            walk_descendants(ch)

    walk_descendants(root.uid)        # root + all descendants + each descendant's spouse

    # --- Step 2: enumerate contributing parents (deterministic order) ---
    contributors: List[Tuple[str, str]] = []   # (contributor_uid, role_for_log)
    for i, p_uid in enumerate(root.parent_ids):
        contributors.append((p_uid, f"root.parent[{i}]"))
    for j, sp_uid in enumerate(root.spouse_ids):
        spouse = read_person(sp_uid)
        if spouse is None:
            log.append(f"LINEAGE: spouse[{j}] uid={sp_uid} not readable; their parents skipped.")
            continue
        for i, sp_p_uid in enumerate(spouse.parent_ids):
            contributors.append((sp_p_uid, f"spouse[{j}].parent[{i}]"))

    # --- Step 3: per-contributor, build the lineage member list ---
    for contributor_uid, role in contributors:
        if not contributor_uid:
            continue
        contributor = read_person(contributor_uid)
        if contributor is None:
            log.append(f"LINEAGE: {role} (uid={contributor_uid}) not in cache; skipped.")
            continue

        lineage_surname = extract_lineage_surname(contributor)
        if lineage_surname is None:
            log.append(f"LINEAGE: {role} (uid={contributor_uid}) has no lineage surname; skipped.")
            continue

        # Collision: first contributor wins (matches ADR-004 §3 enumeration order)
        if lineage_surname in lineages:
            log.append(
                f"LINEAGE: surname '{lineage_surname}' already contributed by earlier slot; "
                f"{role} (uid={contributor_uid}) does not create a new folder."
            )
            continue

        members: List[str] = []
        seen: Set[str] = set()

        def add(uid):
            if uid and uid not in seen:
                members.append(uid); seen.add(uid)

        # R1+R2: universal members in fixed order
        for u in universal:
            add(u)

        # R3: contributing parent + their spouse (root's other parent, or
        #      root-spouse's other parent — i.e. the other entry from this
        #      contributor's couple)
        add(contributor_uid)
        for sp_of_contrib in contributor.spouse_ids:
            add(sp_of_contrib)

        # R4: walk ancestors of the contributor, keeping only those whose
        #      lineage surname matches. Each kept ancestor's spouse is added
        #      as a leaf (no further walk through the spouse).
        walk_lineage_ancestors(contributor, lineage_surname, add, log)

        lineages[lineage_surname] = LineageMembers(
            surname=lineage_surname,
            contributor_uid=contributor_uid,
            member_uids=members,
        )

    return lineages, log


def walk_lineage_ancestors(start_person, lineage_surname, add, log):
    """DFS through start_person's parents (and their parents, etc.). At each
    ancestor, include only if their extract_lineage_surname == lineage_surname.
    Each included ancestor's spouse is added as a leaf (NOT walked further).
    Branches whose surname diverges are stopped.
    """
    stack = list(start_person.parent_ids)
    visited: Set[str] = set()
    while stack:
        anc_uid = stack.pop(0)  # BFS-style; order doesn't affect membership
        if not anc_uid or anc_uid in visited:
            continue
        visited.add(anc_uid)
        anc = read_person(anc_uid)
        if anc is None:
            log.append(f"LINEAGE: ancestor uid={anc_uid} not readable; branch stopped.")
            continue
        anc_surname = extract_lineage_surname(anc)
        if anc_surname != lineage_surname:
            continue  # branch terminates here
        add(anc_uid)
        # Spouse-leaf: include but DO NOT walk through them
        for sp_uid in anc.spouse_ids:
            add(sp_uid)
        # Walk this ancestor's parents next
        for pp_uid in anc.parent_ids:
            stack.append(pp_uid)
```

`extract_lineage_surname` is unchanged from ADR-004 §2 — kept verbatim. The
function is still the single source of truth for "what is this person's
lineage surname".

### 2.3 Wipe-and-rebuild ceremony (rebuild_lineage)

`TreeService.rebuild_lineage()` adapts to:

1. Wipe `<root>/Rody/` (existing logic preserves).
2. Call `LineageService.compute_lineages(root_uuid)` → `Dict[surname, LineageMembers]`.
3. For each surname:
   1. Encode surname → folder-safe name (§3).
   2. mkdir `<root>/Rody/<encoded-surname>/`.
   3. For each member_uid in `members.member_uids`:
      - Look up `cached_people[uid][LOCATION]`.
      - If missing, log and skip.
      - Encode the person's `person_name` → filename-safe (§3).
      - Disambiguate filename collisions within the subfolder ( `.lnk`, `(2).lnk`, ... — same pattern Drzewo uses, ADR-003 §2c).
      - `ShortcutHelper.create_shortcut(location, subfolder / encoded_name.lnk)`.
4. Write `build-log.txt` per subfolder (collision and skip lines flow into the
   subfolder's log; cross-cutting log lines flow into a top-level
   `Rody/build-log.txt`).
5. Return `(total_shortcuts_written, log)`.

Both per-subfolder and top-level build-log files are written. Per-subfolder
log carries "person X skipped because location missing" lines that are
specific to that lineage; top-level log carries enumeration-order /
collision lines that span lineages.

## 3. Encoding rules

### 3.1 Surname → folder name

The subfolder name under `<root>/Rody/` is the lineage surname **literally**,
with two minimal transformations:

1. **Strip leading/trailing whitespace.** (defensive)
2. **Replace filesystem-forbidden Windows characters** `\ / : * ? " < > |`
   with `_` (underscore). Polish diacritics are passed through untouched —
   ADR-001 covers Unicode-safe paths via `IShellLinkW`; folder names under
   NTFS are natively UTF-16.

```python
FORBIDDEN = set('\\/:*?"<>|')

def encode_lineage_folder_name(surname: str) -> str:
    s = surname.strip()
    return "".join(("_" if c in FORBIDDEN else c) for c in s)
```

Multi-component surnames ("Kowalski-Nowak") are kept whole — same as ADR-004.

### 3.2 Person → .lnk filename

Inside each lineage subfolder, each `.lnk` is named after the person's
display name (`get_person_name()`). Same transformations:

```python
def encode_person_lnk_name(person_name: str) -> str:
    s = (person_name or "").strip()
    return "".join(("_" if c in FORBIDDEN else c) for c in s) + ".lnk"
```

### 3.3 Filename collisions within a subfolder

Two people with the same `person_name` in the same lineage folder collide.
Resolution: `(2).lnk`, `(3).lnk`, ... appended **before** the `.lnk`
extension. Same pattern Drzewo uses (ADR-003 §2c). Implementor uses a
`seen_filenames: Set[str]` per subfolder.

### 3.4 Missing surname / nieznane handling

If a contributing parent's `extract_lineage_surname` returns `None` (empty,
whitespace-only, or `"(nieznane)"`), they do not create a subfolder — they
are skipped. Log line is emitted (see §2.2). This matches ADR-004 §2
behavior exactly.

### 3.5 Surname collisions across contributors (4 → fewer lineages)

When two contributors yield the same `lineage_surname` (e.g. father and
spouse's father share `Kowalski`), only the **first** contributor (in
enumeration order: root.parents[0], root.parents[1], spouse[0].parents[0],
spouse[0].parents[1], spouse[1]....) creates a subfolder. The second
contributor's membership rules (R3 — them + their spouse) do NOT add
shortcuts to the existing first-contributor subfolder. Log entry records
this.

Rationale: keeps determinism + simple semantics. The user can navigate
from any included person's `Rodzice/` shortcuts to discover the second
contributor manually. A future "merge lineages" feature is a separate ADR
if requested.

## 4. Alternatives considered

### 4.1 ADR-004's flat `<surname>.lnk` shape

**Rejected.** This is what we're replacing. ADR-004 §1 produced a single
`.lnk` per surname targeting one person. User-verified mental model: a
lineage is a *set of people*. Flat shape made #20 inevitable.

### 4.2 Subfolders, but only the contributor + ancestors (no root/children/spouses)

**Rejected.** User explicitly stated root + spouse + children + their
spouses appear in *all* lineage folders. Removing them would empty the
folders of the people the user actively navigates to.

### 4.3 Walk descendants too (full descendant subtree, not just root's
direct children)

**Accepted (amendment 1, 2026-05-17).** User clarified in #20 comment: root +
all descendants (every generation, plus each descendant's spouse) reappear in
every lineage folder. Step 1 of `compute_lineages` recurses via
`walk_descendants(person_uid)`. Cycle-safe (universal_seen guard). Spouses
of descendants are leaves (added, not walked further).

### 4.4 Lineage-walk via blood-link only (skip spouses-of-ancestors)

**Rejected.** User said "The contributing parent + their spouse → appear in
their lineage folder, with spouses if applicable." Same applies one
generation up — including the spouse of each lineage-matching ancestor
gives the user a couple-view, which is how genealogy data is typically
read. Cost: ~2x .lnk files per lineage. Acceptable.

### 4.5 Sort the member list inside each subfolder by birth-date /
generation

**Rejected for v1.** Windows Explorer sorts alphabetically by default;
that's what the user gets. Generation order would require Drzewo-style
encoding (`01_root`, `02_child`, ...) which the user explicitly does not
want in Rody (issue #20 framing). Iterate on real data.

### 4.6 Keep the `LineageService` API returning `Dict[str, str]` and have
`rebuild_lineage` re-compute member sets

**Rejected.** Compute happens once; the service returns the full membership
result. Cleaner test surface — `LineageService.compute_lineages` is fully
testable at L0 without filesystem.

## 5. Risks + halt criteria

### R-1 Descendant depth — resolved 2026-05-17

User clarified in #20: full descendant subtree, not just direct children.
Pseudocode step 1 uses `walk_descendants` recursion. Closed.

### R-2 Walk-up termination on missing data

If an ancestor's me.json is unreadable, the branch terminates at that
ancestor (no children of an unreadable person can be walked — we don't
know their parent IDs). Log entry is emitted. This matches ADR-004's
"missing data is logged, not crashed" posture.

### R-3 Subfolder build-log path stability

`build-log.txt` exists in two places after rebuild: `Rody/build-log.txt`
(cross-cutting) and `Rody/<surname>/build-log.txt` (per-lineage). User
already knows the top-level path from ADR-004; the per-subfolder log is
new. Document in `RELEASE.md` or a `README` line if user wants discovery
visibility.

### R-4 Collision behavior change vs. ADR-004

ADR-004 §3 collision rule: first contributor wins. Carried forward
verbatim (§3.5). No behavior change. Cited explicitly so reviewer can
confirm.

### Halt criteria for sprint-17

- **H-A**: Reproduce issue #20 minimal case (root + father only). After
  rebuild, `<root>/Rody/<father-surname>/` exists, contains `<root>.lnk`
  (only — no children, no spouse) and `<father>.lnk`. NO flat
  `<surname>.lnk` files anywhere under `Rody/`.
- **H-B**: `LineageService.compute_lineages` returns dict-of-`LineageMembers`,
  not dict-of-str. Old shape removed from the codebase — grep for
  `Dict[str, str]` in lineage_service.py returns 0.
- **H-C**: Surname walk-up termination tested: in a 3-generation paternal
  fixture where grandfather's surname matches but great-grandfather's
  doesn't, `<father-surname>/` includes grandfather + grandmother (as his
  spouse) but NOT great-grandfather.
- **H-D**: Universal-members rule verified: `<father-surname>/` and
  `<mother-maiden>/` both contain root + root-spouse + child + child-spouse.
- **H-E**: Baseline 254 tests stay green. New lineage tests slot under
  `tests/L0/services/test_lineage_service.py` and
  `tests/L1/integration/test_lineage_e2e.py` (extending existing files).

## 6. Test plan

### 6.1 L0 unit tests (extend `tests/L0/services/test_lineage_service.py`)

New tests on top of the existing 7:

8. **Universal members in one-parent case** — root has 1 parent (father).
   `<father-surname>/` contains root, spouse-of-root (if exists), child,
   child-spouse, father, mother-of-root (if exists as father's spouse).
9. **Universal members in zero-children case** — root with parents but no
   children. `<father-surname>/` contains root, root-spouse, father,
   mother. No children present.
10. **Ancestor walk happy path** — father has parents matching surname; their
    parent matches too. Three generations included.
11. **Ancestor walk termination on surname mismatch** — grandfather's
    surname differs from lineage surname. Grandfather is NOT in the folder.
    Great-grandparents (regardless of their surname) NOT in folder.
12. **Ancestor spouse-leaf rule** — grandfather's surname matches;
    grandmother's surname differs. Both included (he via walk, she via
    spouse-leaf). Grandmother's own parents NOT walked.
13. **No spouse, no children** — root with parents only. Universal set = {root}.
    Lineage folder contains root + contributing parent + their spouse + ancestors.
14. **Surname collision across contributors** — root.father and
    root-spouse.father share surname. Only one subfolder; first-contributor
    members populate it; second contributor (root-spouse.father) is NOT in
    the folder (he gets no R3 entry).
15. **Empty maiden case for mother** — mother has has_maiden=True but
    maiden_name="(nieznane)". She contributes no subfolder. Log entry
    present.
16. **All 4 contributors distinct** — full 4-lineage case. Each subfolder
    has correct R3 contributor + spouse. Universal members appear in all 4.

### 6.2 L1 integration test (extend `tests/L1/integration/test_lineage_e2e.py`)

One new end-to-end test driving `TreeService.rebuild_lineage()` against a
9-person synthetic tree (root + spouse + child + child-spouse + father +
mother + grandfather-paternal + grandmother-paternal + great-grandfather-paternal).
Asserts on-disk:

- Exactly 2 subfolders exist under `Rody/` (father-surname + mother-maiden).
- `Rody/<father-surname>/` contains 8 `.lnk` files (root, spouse, child,
  child-spouse, father, mother, grandfather, grandmother).
- `Rody/<father-surname>/great-grandfather.lnk` does NOT exist (chain broke
  at great-grandfather since his surname differs).
- `Rody/<father-surname>/build-log.txt` exists.
- `ShortcutHelper.create_shortcut` is mocked (mirrors existing pattern); no
  COM in L1.

### 6.3 Regression / preservation

All 7 existing `test_lineage_service.py` tests stay green after the API
change OR are rewritten to assert the new return shape — implementor's
call. The function signature change from `Dict[str, str]` to
`Dict[str, LineageMembers]` is a guaranteed compile-time break of all
existing assertions; full rewrite of the test file is expected and is
documented in the sprint plan.

## Sources

- Issue [#20](https://github.com/TomaszMankin/py-tree-manager/issues/20)
  body + clarifying comment (2026-05-17 20:46Z).
- ADR-004 — superseded by this ADR. Algorithm enumeration order +
  `extract_lineage_surname` semantics preserved verbatim.
- ADR-003 §2c — `(2).lnk`/`(3).lnk` disambiguation pattern.
- ADR-001 — `IShellLinkW + IPersistFile.Save` Polish-character contract.
- `src/wrappers/person_data_wrapper.py:126-186` — `get_has_maiden_name`,
  `get_maiden_name`, `get_last_name`, `get_parent_ids`, `get_spouse_ids`,
  `get_children_ids` accessors (all grep-verified before drafting).
- `src/services/lineage_service.py:53-114` — current `compute_lineages`
  shape being rewritten.
- `src/services/tree_service.py:494-556` — current `rebuild_lineage`
  wipe-and-rebuild flow being adapted.
- `src/tests/L0/services/test_lineage_service.py:1-80` — existing test
  helpers `_write_person` / `_add_to_cache` reused unchanged.

## Revisit when

- User reports that grandchildren-and-below should appear in lineage folders
  (R-1). One-line amendment to step 1 of `compute_lineages` + new test.
- User asks for sort order other than alphabetic-by-filename in subfolders
  (e.g. generation order). Implies Drzewo-style encoding inside Rody;
  rewrite both this ADR + parts of ADR-003.
- User asks lineage walk to follow `other_last_names` / `other_maiden_names`
  alternates (the `;`-suffixed alternates we currently ignore). Implies
  `extract_lineage_surname` returns a *set*, not a single surname; cascades
  through the algorithm.
- Surname collision across contributors becomes a real annoyance (R-4).
  Likely fix: produce one subfolder with both contributors' members merged,
  not "first wins" exclusion.
