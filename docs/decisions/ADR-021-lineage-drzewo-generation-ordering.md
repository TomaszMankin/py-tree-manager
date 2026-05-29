---
id: ADR-021
title: Lineage folders adopt Drzewo generation/couple/gender ordering (supersedes ADR-016)
kind: tech
status: accepted
date: 2026-05-30
author: architect
supersedes: ADR-016
---

## Context

Lineage `.lnk` files (`Rody/<surname>/<person>.lnk`) are flat — plain
`get_person_name()` filenames, no generation order. Drzewo encodes every
person with a global `[generation][couple][letter][gender]` prefix
(`render_folder_tree_filename`, `folder_tree_service.py:521-568`). Father
(issue #17) wants lineage folders to look like Drzewo, and the same person to
carry the SAME generation token in Drzewo and in his lineage folder (AC#3:
grandfather = gen X in Drzewo MUST be gen X in his lineage folder).

ADR-016 ran lineage as its own membership engine with no generation concept.
Two independent generation sources = drift risk — the exact bug class ADR-003
Amendment 2 spent a sprint killing.

## Decision

**One hourglass, two views.** `FolderTreeService.compute_membership`
(`folder_tree_service.py`) is the single generation authority. Drzewo already
computes the hourglass ONCE, emitting `List[FolderTreeMember]` with global
generation / couple / gender.

`LineageService` is demoted from membership-engine to an
**assignment-over-Drzewo-members** layer: takes the already-computed
`List[FolderTreeMember]`, groups by surname (`extract_lineage_surname`,
unchanged), and names each `.lnk` via `render_folder_tree_filename` (the same
Drzewo encoder, reused verbatim). Surname subfolder structure from ADR-016
§1.3 (`Rody/<surname>/`) is preserved.

## Constraints

1. **Couple letters are Drzewo-GLOBAL.** Do NOT re-pack per surname folder. A
   person at couple B in Drzewo stays couple B in his surname folder, even if
   that folder shows no couple A. Couple letter is identity, not a
   within-folder index.
2. **All spouses shown** (D-1=A). Ex-spouse distinction is out of scope — the
   data model has no current/ex field; that is a separate future M-class
   sprint. Do NOT design ex-spouse logic into sprint-22.
3. **Full descendant subtree retained** (D-2=B, matches ADR-016 Amendment 1).
   Generation numbering is correct either way; only the surname filter moves.

## Consequences

- `.lnk` names change: `Tomasz Mankin.lnk` → `[49][1][A][M] Tomasz Mankin.lnk`.
- Wipe-and-rebuild already rewrites every shortcut, so the rename is low-impact.
- Father browses via Explorer; surname grouping unchanged, so navigation
  shape is intact.
- ADR-016 superseded in full.

## Alternatives rejected

- **Build a parallel hourglass inside `LineageService`.** Rejected — re-opens
  the generation-drift bug class killed in ADR-003 Amendment 2. Two generation
  sources cannot be guaranteed consistent under refactor. Reusing the single
  Drzewo authority is the only way AC#3 (identical token) holds by construction.

## Sources

- Issue [#17](https://github.com/TomaszMankin/py-tree-manager/issues/17).
- ADR-003 Amendment 2 — spouse-seeded ancestor DFS + generation-drift history.
- ADR-016 — superseded by this ADR; surname grouping + `extract_lineage_surname` preserved.
- `src/services/folder_tree_service.py:521-568` — `render_folder_tree_filename` (reused verbatim).
- `src/services/folder_tree_service.py` — `FolderTreeService.compute_membership` (generation authority).
- `src/services/lineage_service.py` — `compute_lineages` being refactored.
- `src/services/tree_service.py:494-579` — `rebuild_lineage` being rewired.
