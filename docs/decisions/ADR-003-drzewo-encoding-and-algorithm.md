---
id: ADR-003
title: Drzewo encoding scheme and hourglass selection algorithm
kind: tech
status: accepted
date: 2026-05-08
author: architect
amended: 2026-05-09
sprint: sprint-07
iterates_with_user: true
---

## Changelog

- **2026-05-08** — encoding revised per user feedback (multi-bracket couple-letter
  system); depth cap removed; -ST suffix dropped. See "Amendment 1" below.
- **2026-05-09** — second visible bracket flips sign (display `-gen` instead of
  `gen`); `+` prefix dropped on non-negative values. Maternal-branch bug fix:
  spouse UID is now seeded into the ancestor DFS so spouse's parents become a
  couple at gen=+1 (couple-letter B) — closing an algorithm-vs-intent gap that
  existed in this ADR since Sprint 07 (the worked-example block at Amendment 1
  always showed Jadwiga's parents at gen+1 couple B, but the original
  pseudocode never seeded the spouse into the upward walk). See "Amendment 2"
  below.
- **2026-05-09 (revision, same day)** — earlier draft of Amendment 2 framed the
  bug as `parents_id`-vs-`parents` data drift in brownfield me.json files.
  Refuted by user-verified on-disk evidence: the live test tree at
  `C:\Temp\pytreemanager-smoke` has perfectly symmetric bidirectional links on
  all four me.json files (root, spouse, both maternal grandparents — all UUID
  arrays AND path arrays match). The wxPython app's add/edit save flow IS
  correct. The actual bug was internal to this ADR — the worked example in
  Amendment 1 ("Worked example (root = Zbigniew)" block) explicitly placed
  Jadwiga's parents at `[51][+1][B][F]` and `[51][+1][B][M]`, but the
  pseudocode in Original Decision §2 ("Hourglass selection algorithm") only
  seeded `root_uuid` into the ancestor BFS — spouse's parents were unreachable.
  The `get_effective_parent_ids` reverse-lookup helper was DROPPED.

## Context

Sprint 07 introduces the **Drzewo** feature (PRD-003): a flat directory of
`.lnk` shortcuts under `<root>/Drzewo/`, curated by an "hourglass" selection
relative to a designated root person and named so that Windows Explorer's
default sort orders them by generation.

This ADR pins three technical decisions:
1. **Filename encoding** for the shortcuts.
2. **Selection algorithm** (hourglass traversal).
3. **Edge-case behaviour** (cycles, missing data, multiple spouses, depth caps).

The user pre-accepted the encoding shape ("proposal A") and the
selection rule (hourglass) in the dispatch JOURNAL entry on 2026-05-08; this
ADR ratifies and details them.

## Amendment 2 — 2026-05-09: visible-sign flip + ancestor-traversal hardening

User ran a live demo of Sprint 07's Drzewo with his father on 2026-05-09 and
returned two findings that cross this ADR:

**Finding 1 (encoding flip)** — His father read the bracketed signed numbers
naturally as "ancestors are positive (older = higher number), descendants are
negative (younger = below me)". The Sprint-07 encoding was the opposite —
ancestors `[+1..+N]`, descendants `[-1..-N]`. He wants the **visible** signs
flipped, while the **physical Windows-Explorer order must stay identical**
(descendants on top, root middle, ancestors at bottom). User also requested
**bare numbers** without the `+` prefix on non-negative values: `[0]` not `[+0]`,
`[1]` not `[+1]`.

**Finding 2 (maternal-branch bug)** — After adding his mother's parents to
me.json and refreshing Drzewo, only paternal-side ancestors appeared. Root
cause is **internal to this ADR**: the Amendment 1 "Worked example (root =
Zbigniew)" block (Jadwiga's parents at `[51][+1][B][F]` and `[51][+1][B][M]`)
and the Original Decision §2 "Hourglass selection algorithm" pseudocode
disagree. The example placed spouse's parents in the hourglass at gen+1
couple B; the pseudocode only enqueues `root_uuid`'s parents into the
upward walk. Spouse's parents are therefore unreachable.

The fix is a small algorithm-contract change: at gen=0, after each spouse is
added with `role='spouse'`, also seed the spouse's UUID into the ancestor DFS
queue at gen=+1 starting depth. Specified in detail below.

### Encoding flip — revised second-bracket rule

The internal `gen` field is unchanged. The NN sort key (`NN = gen + 50`) is
unchanged. Only the second visible bracket changes.

**New rule** — second bracket displays `-gen` (the negation of the internal
generation). No sign prefix is added: negative values keep their literal `-`,
non-negative values are bare.

```
internal gen     |  NN  |  second bracket
-----------------+------+----------------
gen = -2         |  48  |  [2]
gen = -1         |  49  |  [1]
gen =  0         |  50  |  [0]
gen = +1         |  51  |  [-1]
gen = +2         |  52  |  [-2]
gen = +12        |  62  |  [-12]
gen = -12        |  38  |  [12]
```

**Why this works for Windows sort.** StrCmpLogicalW (Explorer's natural sort)
sees `[NN]` first — that's the leading `[48]`, `[49]`, `[50]`, etc. NN is a
zero-padded 2-digit field whose magnitude reflects physical generation order
(newer descendants -> smaller NN -> sorted on top per Sprint 07's locked rule).
The second bracket's display sign is never compared as a number for ordering;
it's a label only. This decouples sort from display entirely.

**Why bare numbers work in the bracket.** The `[0]` and `[1]` cases are visual
choices — `[+0]` was the Sprint-07 form. Father reviewed both side-by-side and
preferred bare numbers because the brackets already provide visual grouping;
`+` is redundant noise.

### Worked examples — all four boundary cases

Root = Zbigniew (gen=0). Sample ancestors and descendants on both lineages.
**These four examples are the boundary cases the implementor must match
exactly:**

```
internal gen=-2: [48][2][AB][F] sister-grandchild Anna's daughter.lnk
internal gen=-1: [49][1][A][M] Tomasz Mankin.lnk
internal gen= 0: [50][0][M] Zbigniew Mankin.lnk
internal gen=+1: [51][-1][A][M] Adam Mankin.lnk
internal gen=+2: [52][-2][A][M] (Adam's father).lnk
```

Note: gen=0 retains 3 brackets (no couple-code at gen 0). gen!=0 retains 4
brackets (NN, signed-display, couple-code, gender). The number of bracket groups
is unchanged from Amendment 1; only the second-bracket content changes.

### Filename-render code diff (for Implementor)

In `services/drzewo_service.py`, function `render_drzewo_filename`
(lines 507-543), the only required change is in the gen-encoding logic:

**Before (Sprint 07 / Amendment 1)**:
```python
if gen == 0:
    gs = "+0"
    return f"[{nn}][{gs}][{gender_token}] {member.full_name}.lnk"
else:
    if gen > 0:
        gs = f"+{gen}"
    else:
        gs = f"{gen}"  # e.g. -1, -2
    code = _couple_code(...)
    return f"[{nn}][{gs}][{code}][{gender_token}] {member.full_name}.lnk"
```

**After (Amendment 2)**:
```python
display = -gen   # flip sign
gs = f"{display}"   # negative values keep '-', non-negatives are bare
if gen == 0:
    return f"[{nn}][{gs}][{gender_token}] {member.full_name}.lnk"
else:
    code = _couple_code(...)
    return f"[{nn}][{gs}][{code}][{gender_token}] {member.full_name}.lnk"
```

`f"{display}"` formats `0` as `"0"` and `-2` as `"-2"` — exactly the bare-number
form. `+` is never emitted. No `abs()` call needed.

### Spouse-seeded ancestor DFS (algorithm contract clarification)

Sprint 07's DFS in `compute_membership` (services/drzewo_service.py lines
236-237 in the shipped code) initializes the ancestor stack with one entry:

```python
dfs_stack: List[Tuple[str, int]] = [(root_uuid, 1)]
ancestor_visited_dfs.add(root_uuid)
```

Spouse(s) are added at gen=0 with `role='spouse'` (lines 195-211) but never
seeded into the upward walk. Therefore spouse's parents at gen=+1 are
unreachable, even though Amendment 1's "Worked example (root = Zbigniew)"
block (in this ADR) already shows them at couple-letter B.

**Contract clarification.** At gen=0, after each spouse is recorded with
`role='spouse'` in `gen0_members`, also enqueue that spouse's UID into the
ancestor DFS seed stack at depth gen=+1. The order of enqueueing is
**spouse(s) first, root last** — because the stack is LIFO and we want
`root_uuid` to pop first so root's parents become couple A (the most-paternal
couple at gen+1, per the existing paternal-first DFS rule). After root's
entire ancestor subtree is exhausted (DFS recurses upward through R's parents,
grandparents, etc.), the spouse pops and their entire ancestor subtree is
walked the same way, producing couple B at gen+1 (spouse's parents) and so on
upward.

Pseudocode (replaces the `dfs_stack` initialization in `compute_membership`):

```
# OLD (Sprint 07 / Amendment 1 ship):
dfs_stack = [(root_uuid, 1)]
ancestor_visited_dfs.add(root_uuid)

# NEW (Amendment 2):
dfs_stack = []
ancestor_visited_dfs.add(root_uuid)

# Push spouses FIRST so root pops first (stack is LIFO).
# Each spouse seeds an independent upward subtree at gen=+1.
for spouse_uid in root_data.get_spouse_ids():
    if spouse_uid and spouse_uid not in ancestor_visited_dfs:
        dfs_stack.append((spouse_uid, 1))
        ancestor_visited_dfs.add(spouse_uid)

# Push root LAST so it pops first; root's parents form couple A at gen+1.
dfs_stack.append((root_uuid, 1))
```

The inner loop (lines 239-306 of the shipped DFS) is unchanged. The
couple-letter assignment logic — paternal-first ordering within each
person's parent list, sequential A/B/C indexing per generation in DFS visit
order — extends naturally:
- gen=+1 couple A = root's parents (root pops first → root's couple registers
  first into `ancestor_couples_by_gen[1]`).
- gen=+1 couple B = spouse's parents (spouse pops after root's whole subtree;
  spouse's couple appends second into `ancestor_couples_by_gen[1]`).
- gen=+2 couples A,B = root's paternal/maternal grandparents (DFS goes deep
  on root's side first).
- gen=+2 couples C,D = spouse's paternal/maternal grandparents (DFS unwinds
  to spouse, then walks her ancestors).
- Higher generations: same pattern; root-side first within each generation,
  spouse-side after.

This is precisely the layout shown by the Amendment 1 "Worked example (root =
Zbigniew)" block in this ADR. The worked example was always the binding intent;
the pseudocode just never matched it.

**Why this is a contract clarification rather than a feature addition.** The
intent has been documented since Amendment 1 (2026-05-08, in the "Worked
example (root = Zbigniew)" block: `[51][+1][B][F] (Jadwiga's mother)` and
`[51][+1][B][M] (Jadwiga's father)`).
The Sprint 07 implementation never delivered that intent. Amendment 2
brings the algorithm into compliance with the example. Couple-letter
semantics, paternal-first ordering, and the gender-fallback rule from Original
Decision section 2 are all unchanged. No new edge cases.

### Worked-example trace — 6-person tree (parity check)

Per the architect agent's "example ↔ pseudocode parity check" rule (added to
agent definition after Sprint 09's diagnosis revision), this amendment is
verified end-to-end by tracing a minimal 6-person reproducer through the
revised pseudocode. **This trace is the parity check; do not skip it on
re-read.**

Tree:
- R (root, male)
- S (root's spouse, female)
- RF (root's father, male) — RF.parents_id = [], children_id = [R]
- RM (root's mother, female) — RM.parents_id = [], children_id = [R]
- SF (spouse's father, male) — SF.parents_id = [], children_id = [S]
- SM (spouse's mother, female) — SM.parents_id = [], children_id = [S]

Cached_people contains all 6. R.parents_id = [RF.uid, RM.uid]; R.spouse_id =
[S.uid]. S.parents_id = [SF.uid, SM.uid]; S.spouse_id = [R.uid].

Trace through revised `compute_membership(R.uid)`:

1. Gen 0: R added with `role='self'`; S added with `role='spouse'`.
   `gen0_members = {R: ..., S: ...}`. Two entries.
2. Stack initialization (NEW logic):
   - `dfs_stack = []`; `ancestor_visited_dfs = {R.uid}`.
   - Push S: `dfs_stack = [(S, 1)]`; `ancestor_visited_dfs = {R, S}`.
   - Push R: `dfs_stack = [(S, 1), (R, 1)]`.
3. Pop R (LIFO). R's parents = [RF, RM]. RF male → father edge; RM female →
   mother edge. parents_sorted (by edge): [(RF, F), (RM, M)] — paternal first.
   Register couple at gen=1: `ancestor_couples_by_gen[1] = [(RF, RM)]`.
   Push parents in reversed order: push RM first (gen=2), then RF (gen=2).
   `dfs_stack = [(S, 1), (RM, 2), (RF, 2)]`.
4. Pop RF. RF.parents_id = []; `parent_ids` empty → continue. No couple
   added at gen=2 from RF.
5. Pop RM. RM.parents_id = []; same → continue.
6. Pop S. S's parents = [SF, SM]. Same paternal-first sort.
   Register couple at gen=1: `ancestor_couples_by_gen[1] = [(RF, RM), (SF, SM)]`.
   Push parents: push SM (gen=2), then SF (gen=2).
   `dfs_stack = [(SM, 2), (SF, 2)]`.
7. Pop SF, SM. Both have empty parents → continue.
8. Stack empty. DFS done.

Now build DrzewoMember objects for ancestors (lines 308+ of the shipped
code, unchanged):
- gen=1, couples = [(RF, RM), (SF, SM)]; total=2.
- couple_idx=0 (couple A): RF and RM both added with `couple_index=0,
  total_couples_in_generation=2`.
- couple_idx=1 (couple B): SF and SM both added with `couple_index=1,
  total_couples_in_generation=2`.

Final membership has 6 entries: R (gen=0, role=self), S (gen=0, role=spouse),
RF + RM (gen=1, couple A), SF + SM (gen=1, couple B). Filename render under
the Amendment 2 sign-flip rule:

```
[50][0][M] R.lnk
[50][0][F] S.lnk
[51][-1][A][M] RF.lnk
[51][-1][A][F] RM.lnk
[51][-1][B][M] SF.lnk
[51][-1][B][F] SM.lnk
```

All 6 appear. Couple A is root's parents; couple B is spouse's parents.
This matches Amendment 1's "Worked example (root = Zbigniew)" block (in
this ADR) exactly — specifically the rows `[51][+1][A][M] Adam Mankin`,
`[51][+1][A][F] (Adam's wife)`, `[51][+1][B][F] (Jadwiga's mother)`,
`[51][+1][B][M] (Jadwiga's father)`, modulo the encoding-flip from Amendment
2 (signs flip in the second bracket; A/B couple letters and pairing are
identical). **Parity confirmed.**

### Regression test (must land in sprint-09)

L0 test in `tests/services/test_drzewo_service.py` titled
`test_spouse_parents_appear_at_gen_plus_1_couple_b`:

- Build the 6-person fixture above (R + S + RF + RM + SF + SM).
- Call `compute_membership(R.uid)`.
- Assert all 6 UIDs appear in returned members.
- Assert R has `(generation=0, role='self')`.
- Assert S has `(generation=0, role='spouse')`.
- Assert RF, RM both have `(generation=1, couple_index=0,
  total_couples_in_generation=2, role='ancestor')`.
- Assert SF, SM both have `(generation=1, couple_index=1,
  total_couples_in_generation=2, role='ancestor')`.
- Assert `build_log` does NOT contain any unexpected ERROR entries (CYCLE
  log allowed only if test data accidentally creates one — it doesn't).

This test would have caught the bug pre-ship. The previous Sprint 07 test
suite did not cover this case because no test fixture included a spouse with
ancestors of her own.

### What is NOT changed

- `parents_id` semantics (UUID list of biological parents): unchanged.
- `parents` (path list of biological parents): unchanged; not consulted by
  the DFS. The user-verified on-disk evidence at `C:\Temp\pytreemanager-smoke`
  shows the wxPython app's add/edit save flow keeps `parents_id` and
  `parents` symmetric. There is no drift to defend against on this codepath.
- Cycle-detection log line (existing line 304-306): unchanged.
- Per-couple silent-skip when a UID has been visited (existing line 300-302):
  unchanged.
- `get_effective_parent_ids` helper (proposed in an earlier draft of this
  amendment): **dropped**. Not needed; not implemented.
- Cross-sprint dependency in ADR-004 §7 referencing
  `get_effective_parent_ids`: **stale** as of this revision; ADR-004 §7 is
  amended to drop the dependency (Rody walks `parents_id` directly because
  the wxPython app's save flow IS symmetric).

### Optional log line (Implementor judgment call)

If a spouse's me.json has `parents_id == []` (lineage truly unknown — common
case for in-laws where the user hasn't entered grandparent data yet), the
DFS terminates that branch silently per the existing rule (line 247-248:
`if not parent_ids: continue`). One INFO-level log line at this point would
make the build-log self-explanatory ("spouse <uid> has no parents in
me.json — branch terminates"). Implementor's call whether to add it; the
existing CYCLE log + per-couple silent skip is sufficient for now and the
user has not asked for the new log line. If added, the message format
should match the existing build-log vocabulary (e.g., "ANCESTRY_LEAF: uid
<X> (gen <N>) has no parents in me.json"), but this is a stretch goal,
not a bug fix.

---

## Amendment 1 — 2026-05-08: multi-bracket couple-letter encoding

After the Sprint 07 implementor run, the user iterated on the encoding spec three
times.  The original F/M-lineage-stacking approach (below in "Original Decision")
is **superseded** by the couple-letter system described here.  The original text is
preserved for historical context.

### Revised encoding format

```
[NN][±G][couple-code][gender] FullName.lnk      (gen != 0)
[NN][+0][gender] FullName.lnk                    (gen == 0, no couple-code)
```

- `[NN]` = `generation + 50`, zero-padded to 2 digits.  Primary sort key.
  Same as before.
- `[±G]` = literal sign + magnitude of generation (`+0`, `-1`, `+12`, etc.).
  Informational only; not used for sort.
- `[couple-code]` = couple identifier within the generation.  Omitted at gen 0
  (only one couple).  Letter assignment:
    - Ancestors (gen >= +1): paternal-first DFS traversal.  Letter A = most-paternal
      lineage; B = next branch; etc.  At gen +1: A = paternal grandparents,
      B = maternal grandparents.  At gen +2: A = paternal-grandfather's parents,
      B = paternal-grandmother's parents, C = maternal-grandfather's parents,
      D = maternal-grandmother's parents.
    - Descendants (gen <= -1): birth-order DFS through me.json children arrays.
      Each child + their by-marriage spouse share one couple-letter.
  Width is pre-detected per-generation based on actual couple count:
    - <= 26 couples: width 1 (A..Z)
    - 27-676 couples: width 2 (AA..ZZ)
    - 677-17,576 couples: width 3 (AAA..ZZZ)
    - General: `width = ceil(log_26(N))` with explicit boundary checks at 26 and
      676 to avoid floating-point rounding.  All couples in one generation share
      the same width — guarantees clean Windows lexical sort within a generation.
- `[gender]` = `F` or `M`.  F sorts before M lexically — female-on-left within
  couple in Windows Explorer.

**Rationale for replacing F/M stacking:**
The F/M stacking encoded the traversal path in the filename
(`[51+01FF]M` = gen+2, paternal grandfather's father).  This was unreadable
past depth 3 and produced filenames like `[63+13FFFMFFMMFFFM]M` for a 12-generation
lineage.  The couple-letter system encodes the same implicit lineage via the
deterministic letter-assignment rule (paternal-first DFS) without embedding the
path in the filename.  Sort order and spouse-adjacency are preserved.

**Per-generation width pre-detection rationale:**
All couples in a generation share the same code width, so filenames sort cleanly
within a generation under Windows StrCmpLogicalW.

### -ST suffix dropped

By-marriage spouses get the same encoding as blood relatives.  The shared
couple-letter provides the pairing context.  The `-ST` suffix was redundant and
added clutter.

### Depth cap removed

No cap on ancestor traversal depth.  Tomasz's father has documented ancestors
back to the 1700s (~12 generations).  A cap was defensive over-engineering.
Branch tokens (old F/M stacking) are gone; couple letters grow in width only
when a generation truly has >26 couples, which is unrealistic on any human tree.

### Worked example (root = Zbigniew)

```
[46][-4][AA][F] sister-grandchild Anna's daughter.lnk    <- >26 couples at gen -4
[46][-4][AA][M] sister-grandchild Anna's son.lnk
[46][-4][AB][F] sister-grandchild Maria's daughter.lnk
[48][-2][A][F] (sister's grandchild).lnk
[48][-2][A][M] (sister's other grandchild).lnk
[49][-1][A][F] (Tomasz's wife — by marriage).lnk
[49][-1][A][M] Tomasz Mankin.lnk
[49][-1][B][F] Katarzyna Mankin.lnk
[49][-1][B][M] (Katarzyna's husband — by marriage).lnk
[50][+0][F] Jadwiga Mankin.lnk
[50][+0][M] Zbigniew Mankin.lnk
[51][+1][A][F] (Adam's wife).lnk
[51][+1][A][M] Adam Mankin.lnk
[51][+1][B][F] (Jadwiga's mother).lnk
[51][+1][B][M] (Jadwiga's father).lnk
[52][+2][A][F] (Adam's mother).lnk
[52][+2][A][M] (Adam's father).lnk
[52][+2][B][F] (Adam's wife's mother).lnk
[52][+2][B][M] (Adam's wife's father).lnk
[52][+2][C][F] (Jadwiga's father's mother).lnk
[52][+2][C][M] (Jadwiga's father's father).lnk
[52][+2][D][F] (Jadwiga's mother's mother).lnk
[52][+2][D][M] (Jadwiga's mother's father).lnk
```

---

## Original Decision (superseded by Amendment above)

### 1. Filename encoding — proposal A (original)

Format: `[NNGS<branch?>][gender] FullName.lnk`

Where:

- `NN` = `generation + 50`, zero-padded to **2 digits**. Drives the primary
  Windows-Explorer sort order. `+0` -> `50`, `-1` -> `49`, `+1` -> `51`,
  `+10` -> `60`, `-10` -> `40`, etc.
- `GS` = literal sign character + absolute value of the generation, **with a
  leading zero only for ancestors** to lock human-readable lexical width
  alongside the recursive branch token. For descendants we keep the bare sign:
    - `+0`, `-1`, `-2`, ... for descendants (no zero pad — never recurses).
    - `+01`, `+02`, `+03`, ... for ancestors (always at least 2 chars; lines
      up cleanly with multi-letter `branch` tokens that follow).
- `branch` = lineage trace (ancestors only). Letters from {`F`, `M`} indicating
  father's line (`F`) or mother's line (`M`), read **outermost-to-innermost**:
  `+1F` = father, `+1M` = mother, `+2FF` = father's father, `+2FM` =
  father's mother, `+2MM` = mother's mother, etc. Recurses through depth.
- `gender` = `M` (male), `F` (female), `ST` ("strona z marriażu" — by-marriage
  spouse). `ST` is used at gen <= 0 only; the underlying person's biological
  gender is still recorded in their own `me.json` and reachable via the
  shortcut target.
- `FullName` = `PersonDataWrapper.get_full_name()` output. Polish characters
  are safe per ADR-001 (IShellLinkW). The shortcut filename inherits the
  Windows path-character constraints: no `<>:"/\|?*`. Our prefix uses only
  `[]+-` plus letters and digits, all legal.

**Worked example** (root = Zbigniew Mankin):

| Filename | Reading |
|---|---|
| `[48-2M] Wnuk.lnk` | gen -2, male, "Wnuk" (root's grandson via daughter Katarzyna) |
| `[49-1F] Katarzyna Szafran zd. Mankin.lnk` | gen -1, female, root's daughter |
| `[49-1F-ST] Szafran.lnk` | gen -1, by-marriage spouse of Katarzyna |
| `[49-1M] Tomasz Mankin.lnk` | gen -1, male, root's son |
| `[50+0F] Jadwiga Mankin.lnk` | gen 0, female, root's spouse |
| `[50+0M] Zbigniew Mankin.lnk` | gen 0, the root person |
| `[51+01FF] (paternal grandfather).lnk` | gen +1, father's branch... wait — see depth note |
| `[51+01F-M] Matka Zbigniewa.lnk` | gen +1, father-line female (paternal grandmother) |

(Two clarifications follow.)

#### 1a. Branch token at gen +1

At gen +1 the `branch` token is exactly one letter (`F` or `M`) — naming the
single parent on whose lineage we are walking. Re-read: `[51+01F]` means
"depth 1 ancestor reached by following the father from root". Not yet
specifying the gender of the ancestor. We append the ancestor's own gender
last: `[51+01FM]` = depth 1 ancestor reached via father, who is male = "root's
father". `[51+01FF]` = depth 1 ancestor reached via father, who is female =
"root's father's wife" — but that wife IS root's mother only if she is the
biological mother of the corresponding child. Use the more readable form
below for unambiguous human reading.

**Adopted form (final)**: `[NN+0KGGGG...]<gender>` where the `branch` token
records the **path of edges traversed** from the root to this ancestor, NOT
the gender of intermediate ancestors. The trailing `gender` letter records
the gender of the **named** person.

So at gen +1: branch is one letter (the edge from root: `F` or `M`); gender
is one letter (`M`/`F`).

- `[51+01F]M` = "via father edge", male = root's father.
- `[51+01F]F` = "via father edge", female = root's father's wife (i.e., mother
  if biological).
- `[51+01M]M` = "via mother edge", male = root's mother's husband.
- `[51+01M]F` = "via mother edge", female = root's mother.

This is verbose but unambiguous. The bracket closes at the end of the
ancestor-path token; gender follows outside the brackets, then space + name.

Final filename pattern: `[NNGS<branch>?]<gender> FullName.lnk`.

#### 1b. Recursion depth — no cap

**No cap on branch-token recursion.** Family trees can extend back many
generations (Tomasz's father has found ancestors back to the 1700s, ~12
generations). Branch tokens grow as long as the lineage demands. Maximum
filename length stays well within Windows' 255-character limit even at extreme
depths (e.g., `[63+13FFFMFFMMFFFM]M Some Long Polish Name zd. Other Name.lnk`
is ~80 chars).

At gen +N the branch token has length N. A 12-generation lineage produces a
12-letter branch token — still machine-readable and sorts correctly. The
`NN` two-digit sort key handles depths up to gen +205 before overflow (not a
realistic concern on any human tree).

#### 1c. Generation magnitude > 9

Never expected on a real human tree (gen +/- 10 means 1024+ ancestors per
generation; nobody has the data). But defensively: `NN+10` is still 2 digits
for the sort key (`60` = gen +10 since `60 = 10 + 50`); the `GS` token grows
to 3 chars; sort still works because StrCmpLogicalW (Windows Explorer's
default natural sort, see Sources) numerically sorts the leading `60`/`61`/...
correctly. The only oddity is that `[60+010]` and `[60+10]` would tie on the
sort key but differ on `GS` width — so we standardize on **always at least 2
GS digits at gen >= 1** (already the rule; gen +10 -> `+10`, gen +1 -> `+01`).
Descendants stay un-padded since they never recurse.

#### 1d. Filename character constraints

Windows-illegal in filenames: `< > : " / \ | ? *`. Our prefix uses `[`, `]`,
`+`, `-`, letters, digits — all legal. `FullName` may already contain Polish
characters (verified Polish-safe per ADR-001 / IShellLinkW). The space between
the bracket+gender prefix and `FullName` is a literal ASCII space; legal.

Shortcut path total length stays well under MAX_PATH for any reasonable tree
(prefix is ~10-15 chars; person's full name is typically 20-40 chars; whole
filename < 80 chars; full path = `<root>\Drzewo\<filename>.lnk` well under
260).

### 2. Hourglass selection algorithm

**Inputs**: `root_uuid` (from settings); `cached_people` dict from
FileService (uuid -> {location, person_name}). `me.json` files reachable
through `cached_people[uid].location`.

**Output**: dict `{uuid: (generation: int, branch: str|None, role: str)}` for
every person to include, where `role` in `{'self', 'spouse', 'ancestor',
'descendant', 'descendant_spouse'}`.

**Algorithm** (pseudocode):

```
def compute_drzewo_membership(root_uuid):
    members = {}        # uid -> (generation, branch, role, gender)
    visited = set()     # cycle guard

    # Gen 0: root + spouses
    add(members, root_uuid, gen=0, branch=None, role='self')
    for spouse_uid in spouses_of(root_uuid):
        add(members, spouse_uid, gen=0, branch=None, role='spouse')

    # Ancestors: BFS upward, tracking branch
    queue = [(root_uuid, gen=1, branch_prefix='')]
    while queue:
        person_uid, gen, branch = queue.pop(0)
        if person_uid in visited: continue  # cycle guard
        visited.add(person_uid)
        for parent_uid, edge in parents_with_edge(person_uid):
            # edge in {'F', 'M'} based on parent's gender; if gender unknown,
            # fall back to ordering: first-listed parent in me.json -> 'F',
            # second -> 'M'. Document this fallback in the filename comment.
            new_branch = (branch + edge) if gen <= 3 else None
            add(members, parent_uid, gen=gen, branch=new_branch,
                role='ancestor')
            queue.append((parent_uid, gen + 1, branch + edge))
        # NOTE: we do NOT enqueue siblings of ancestors and we do NOT enqueue
        # ancestor-spouses other than direct-line parents.

    # Descendants: BFS downward, including by-marriage spouses
    queue = [(root_uuid, gen=-1)]
    descendant_visited = set([root_uuid])  # separate from ancestor visited
    for child_uid in children_of(root_uuid):
        if child_uid in descendant_visited: continue
        descendant_visited.add(child_uid)
        add(members, child_uid, gen=-1, branch=None, role='descendant')
        for spouse_uid in spouses_of(child_uid):
            if spouse_uid == root_uuid: continue  # don't re-tag root's spouse
            if spouse_uid in members: continue   # already tagged at gen 0
            add(members, spouse_uid, gen=-1, branch=None,
                role='descendant_spouse')
        queue.append((child_uid, gen=-2))

    while queue:
        ancestor_uid, gen = queue.pop(0)
        for child_uid in children_of(ancestor_uid):
            if child_uid in descendant_visited: continue
            descendant_visited.add(child_uid)
            add(members, child_uid, gen=gen, branch=None, role='descendant')
            for spouse_uid in spouses_of(child_uid):
                if spouse_uid in members: continue
                add(members, spouse_uid, gen=gen, branch=None,
                    role='descendant_spouse')
            queue.append((child_uid, gen - 1))

    return members
```

Then for each `(uid, gen, branch, role)` in `members`, render the filename
per section 1, point a `.lnk` at `cached_people[uid].location`, and write it
to `<root>/Drzewo/`.

#### 2a. Cycle / inconsistent data handling

The two `visited` sets (one for ancestor BFS, one for descendant BFS) prevent
infinite loops on cyclic me.json data. If a cycle is detected (we encounter a
visited UUID), we **skip the second visit silently** but log a warning to a
new `Drzewo/build-log.txt` file with the UUID and the conflicting parent /
child path. The build proceeds with the first-encountered classification.

Rationale: a cycle in genealogy data is always a data error (you can't be
your own ancestor). The product target is father; do not crash on him.
Surface the issue but ship a usable Drzewo. Build-log inspection is a
reviewer / developer task.

#### 2b. Person appears in both ancestor and descendant trees

In a real genealogical dataset this should not happen (you cannot be both
your own ancestor and your own descendant). If it does (data error), the
**ancestor classification wins** (encountered first in the algorithm above
because the ancestor BFS runs before the descendant BFS). Logged to
build-log.txt.

#### 2c. Multiple spouses (current + ex)

`me.json` lists `spouse` / `spouse_id` as flat arrays — no current/ex
distinction, no marriage-order metadata. All listed spouses get `[50+0F-ST]`
or equivalent.

If root has multiple spouses, all of them appear at gen 0 with role
`'spouse'`. If multiple have the same gender (or both default to `F` in
filename), they will collide on filename if their full names are identical
(very unlikely but possible). On collision, append ` (2)`, ` (3)`, etc. to
the filename — same disambiguation pattern that
`FileService._get_unique_folder_name` already uses for person folders.

If a descendant's spouse happens to coincide with the root person's own
spouse (incest scenario, or data error), the gen-0 classification wins (set
membership check `if spouse_uid in members: continue`).

#### 2d. Adoption / step-relationships

`me.json` and `PersonDataWrapper` carry no adoption/step fields (verified by
inspection 2026-05-08). The model is biological-only. Drzewo treats
`parents` / `children` as authoritative without distinguishing biological vs
adoptive — same posture the rest of the app already takes.

If adoption modeling is added in a future sprint, Drzewo's traversal is the
place to honor it (e.g., "adoptive parents do not propagate ancestor lineage
upward"). Not in scope for Sprint 07.

#### 2e. Missing me.json / unreachable cached_person

If a referenced UUID is not in `cached_people` or its me.json cannot be read,
**skip that branch** with a build-log entry. Drzewo is not the place to fix
canonical-data corruption — that's a `Lista osób` repair job.

#### 2f. Performance

Walk size: bounded by hourglass selection. On a 354-person canonical tree,
the typical hourglass for one root is 30-80 people. BFS is O(V + E) where V
and E are restricted to the hourglass. Each person's me.json is read once.
Order-of-magnitude: < 1 second on the user's machine.

The full rebuild flow is also O(N) shortcut-creates after a `Drzewo/` wipe,
where N is the hourglass count. With Polish-safe `IShellLinkW` (~10-50ms per
shortcut create per ADR-001 evidence), total wall-clock for rebuild is well
under 5 seconds for any realistic hourglass.

### 3. Hourglass-rendering edge cases on the filename side

#### 3a. Spouse of root with unknown gender

Render with `F` if `me.json.sex` is the Polish female value, `M` if male,
fall back to `M` only if explicitly set; otherwise default to `F` (matches
the user's example). Trailing `-ST` only when role is `descendant_spouse` or
when role is `spouse` AND we want to differentiate the marriage edge in the
display. Per the user's worked example, gen 0 spouse renders without `-ST`
because the gender letter alone is enough; gen <= -1 spouse renders with
`-ST`.

Adopted rule:
- `role == 'self'`: no `-ST`. `[50+0M] FullName`.
- `role == 'spouse'` (gen 0): no `-ST`. `[50+0F] FullName`.
- `role == 'ancestor'`: no `-ST` (ancestors are always direct-line and
  biological). `[51+01FM] FullName`.
- `role == 'descendant'`: no `-ST`. `[49-1M] FullName`.
- `role == 'descendant_spouse'`: WITH `-ST`. `[49-1F-ST] FullName`.

This matches the user-supplied worked example exactly.

#### 3b. Branch letter when gender of intermediate ancestor is unknown

`me.json.parents` is a list of folder paths; `me.json.parents_id` is the
parallel list of UUIDs. There is **no order convention** documented for
mother-vs-father in either list (verified by reading PersonDataWrapper). The
person's own me.json may have `sex` populated, allowing the algorithm to
classify each parent's edge as `F` or `M`.

Fallback when both parents' `sex` is empty: deterministically map list
position 0 -> `F` (father), position 1 -> `M` (mother). This is a guess and
will be correct ~50% of the time. Log to build-log.txt when applied so the
user can verify and fix the underlying me.json. Document this in the code
comment so future-me does not assume it is reliable.

If only one parent is recorded, the edge is whatever the parent's gender
says, or `F` as the silent fallback (single missing parent is the common
case in genealogy datasets).

## Alternatives considered

- **Encoding option B — pure-numeric leading sort key** (e.g., `0050+0M-...`,
  `0049-1F-...`). Rejected. Wider sort key, no real legibility benefit. The
  `NN` two-digit form is already enough for sort-by-generation because
  StrCmpLogicalW handles the numeric portion correctly across the realistic
  range.
- **Encoding option C — generation as a folder, not a prefix** (e.g.,
  `Drzewo/+0/Zbigniew Mankin.lnk`, `Drzewo/-1/Tomasz Mankin.lnk`). Rejected per
  PRD-003 ("flat directory only"). Would also break the sort-by-gen-then-by-
  branch UX — within a generation folder, branch info would be lost in the
  filename.
- **Algorithm option B — include siblings of ancestors** ("uncles"). Rejected
  per the user's locked hourglass rule. Easy to revert in a future ADR
  superseding this one if requested.
- **Algorithm option C — lazy / incremental rebuild** (track edits, rebuild
  only affected branches). Rejected for Sprint 07. The wipe-and-rebuild on
  manual refresh is simpler, predictable, and fast enough at this scale.
  Revisit if Drzewo grows to hundreds of entries and rebuild starts to feel
  slow.
- **Cap branch token at depth 3** (original design). Removed 2026-05-08 per
  user feedback: Tomasz's father has ancestors back to the 1700s (~12
  generations). A cap was defensive over-engineering; couple letters replace the
  entire F/M stacking mechanism.
- **F/M-lineage-stacking** (original proposal A). Superseded 2026-05-08 per
  amendment.  Unreadable at depth >3; couple-letter system gives cleaner sort +
  spouse-adjacency without encoding the traversal path in the filename.

## Consequences

**Positive:**
- Filenames sort by generation in plain Windows Explorer with zero per-folder
  configuration (StrCmpLogicalW does the rest natively, see Sources).
- The encoding is fully reversible: given a Drzewo filename and the linked
  person's me.json, we can reconstruct the (generation, branch, role) tuple.
  Useful for future Drzewo audit / verification tooling.
- Wipe-and-rebuild is the simplest possible model. No drift, no stale state,
  no race conditions.

**Negative:**
- Branch token is a **traversal-edge** trace, not a **gender-of-ancestor**
  trace. The two are different at gen +N when an intermediate ancestor's
  gender is unknown and we fell back to list-position. The build-log entries
  flag this; the user can correct underlying me.json data and refresh.
- Wipe-and-rebuild means the user can lose nothing real but can briefly see
  "Drzewo is empty" mid-rebuild if they happen to navigate to it during the
  operation. Rebuild completes in < 5s in normal cases; not a real concern.
- The encoding is opinionated and Polish-language. Cannot be repurposed for a
  non-Polish family-tree app without changes. Acceptable per PRD-002 (no
  cross-language goal).

**Neutral:**
- New file `<root>/Drzewo/build-log.txt` on every rebuild (overwritten, not
  appended). Plain text, UTF-8, lists data anomalies encountered during the
  build. User-visible but not in-the-way.
- Two BFS visited sets (one for ancestors, one for descendants) keep the
  cycle guard simple and avoid the wrong-direction reuse problem.

## Revisit when

- Father reports specific Drzewo entries that are wrong because of the gender
  fallback at gen +1 (the F/M edge guess for an ancestor with unset
  `sex`). Likely fix: prompt user to populate sex in me.json; the underlying
  algorithm is correct.
- User requests a different couple-letter assignment rule (e.g., alphabetical by
  name rather than DFS order). Trivial change in `compute_membership`.
- A second designated root person is requested, requiring filename
  disambiguation across multiple Drzewo folders (PRD-003 revisit).
- An adoption / step-relationship modeling change lands in `me.json`. The
  ancestor traversal will need to honor it; this ADR's hourglass rule still
  applies but the edge classification changes.

## Sources

- JOURNAL 2026-05-08 orchestrator entry (Sprint 07 dispatch — encoding
  proposal A locked, hourglass selection rule locked).
- `wrappers/person_data_wrapper.py` (verified relationship arrays + lack of
  adoption / step fields).
- `services/file_service.py` `set_root_folder` (confirmed `Drzewo/` is created
  empty today; PRD-003 requires it stay so until first root selection).
- `services/file_service.py` `_get_unique_folder_name` (the disambiguation
  pattern reused for filename collisions).
- `helpers/shortcut_helper.py` (the Polish-character-safe IShellLinkW call
  shipped in Sprint 04 per ADR-001).
- ADR-001 — IShellLinkW + IPersistFile.Save Polish-character contract that
  Drzewo's `.lnk` creation rides on.
- ADR-002 — UI framework decision (still wxPython; Drzewo regen does not
  change the framework calculus because it is service-layer + a single new
  picker dialog).
- Microsoft Learn: StrCmpLogicalW reference — natural sort behaviour Windows
  Explorer uses by default, the sort-key contract Drzewo's filenames are
  designed against:
  https://learn.microsoft.com/en-us/windows/win32/api/shlwapi/nf-shlwapi-strcmplogicalw
- Meridian Discovery, "Why Windows Sorts Numeric File Names Differently"
  (independent confirmation of the natural-sort default and the registry key
  that disables it on Windows XP+):
  https://www.meridiandiscovery.com/how-to/why-windows-sorts-numeric-file-names-differently/

### Amendment 2 (2026-05-09) sources

- JOURNAL 2026-05-09 orchestrator entry — demo feedback intake (encoding flip,
  maternal-branch bug report), sprint-09 dispatch.
- JOURNAL 2026-05-09 orchestrator entry titled "architect diagnosis revision —
  verified evidence" — user-verified on-disk state of test tree at
  `C:\Temp\pytreemanager-smoke`. Bidirectional links table proving all four
  me.json files (Jadwiga, Anna Staluszka, Roman Staluszka, Zbigniew) have
  perfectly symmetric `parents_id` ↔ `parents` arrays. The wxPython save flow
  IS correct; no drift exists on this dataset. Refutes the earlier draft of
  this amendment that framed the bug as `parents_id`-vs-`parents` data drift.
- This ADR Amendment 1, "Worked example (root = Zbigniew)" block — the
  binding intent that spouse's parents belong at gen+1 couple B; documented
  since 2026-05-08. The Sprint 07 implementation never delivered it.
- This ADR Original Decision §2 ("Hourglass selection algorithm") pseudocode
  block — the algorithm that only seeds `root_uuid` into the ancestor BFS.
  This is the artifact that contradicts the worked example.
- `services/drzewo_service.py` lines 195-211 (gen=0 spouse-add block — the
  insertion point for the new spouse-seed code).
- `services/drzewo_service.py` lines 236-237 (current stack initialization —
  the lines that change in Amendment 2).
- `services/drzewo_service.py` lines 239-306 (inner DFS loop — unchanged by
  Amendment 2, kept for reference).
- `wrappers/person_data_wrapper.py` `get_spouse_ids()` — the read API the
  new spouse-seed loop calls.
- KB-005 `~/.claude/kb/KB-005-windows-sortable-folder-encoding.md` — the
  StrCmpLogicalW reference, unchanged in scope; the Amendment 2 visible-sign
  flip does not require re-validation because the NN sort key is unchanged
  and the spouse-seed change does not touch filename encoding.
