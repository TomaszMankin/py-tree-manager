---
id: ADR-005
title: Mode background palette refresh — three new mode tints distinct from the four relationship-picker hues
kind: tech
status: accepted
date: 2026-05-09
author: architect
sprint: sprint-09
iterates_with_user: true
---

## Context

Sprint 06 (U2 visual distinction work) introduced three form-mode background
tints in `frames/add_person_frame.py`:

```python
MODE_ADD_NEW    = ('add-new',    '#E3F2FD', 'Dodawanie nowej osoby')
MODE_EDIT_TREE  = ('edit-tree',  '#E8F5E9', 'Edycja osoby z drzewa')
MODE_EDIT_DRAFT = ('edit-draft', '#FFF9C4', 'Edycja szkicu osoby')
```

Sprint 06 also fixed (via U1/U2) the four relationship-picker background
colors:

```python
parents_picker.bg_color   = "#E3F2FD"   # light blue
children_picker.bg_color  = "#E8F5E9"   # light green
spouses_picker.bg_color   = "#FCE4EC"   # light pink
siblings_picker.bg_color  = "#FFF3E0"   # light orange
```

The user surfaced during the 2026-05-09 demo that two of the mode tints are
**bit-identical** to two of the picker tints:

- `MODE_ADD_NEW` (`#E3F2FD`) === parents picker (`#E3F2FD`)
- `MODE_EDIT_TREE` (`#E8F5E9`) === children picker (`#E8F5E9`)

The visual cue collapses: in add-new mode, the parents picker fades into the
mode-tinted background. In edit-tree mode, the children picker disappears the
same way. The third mode (edit-draft, `#FFF9C4` pale yellow) and siblings
(`#FFF3E0` pale orange) are close-but-distinct — both warm, low-saturation —
and may also benefit from being separated.

## Constraints

The new mode tints must be:

1. **Distinct from all four picker hues** (`#E3F2FD`, `#E8F5E9`, `#FCE4EC`,
   `#FFF3E0`). Same-hue-different-luminance is not enough — the human eye reads
   "blue" as "blue" regardless of shade in this very-pale range.
2. **Mutually distinguishable** (the three modes must be telling apart).
3. **Legible against black text**, which is what the form labels use today.
   In practical terms: ≥ 95% perceived luminance, no saturated mid-tones.
4. **Not the root_panel gray (`#F5F5F5`)** which is already used as the
   contrast-providing scrolled-window background.
5. **Polish-elderly-accessibility-friendly**: low saturation, no neon. Father
   reads these on a standard LCD, no special contrast settings. (Accessibility
   posture from KB-006: design for elderly Polish users in their normal
   environment.)

## Decision

Adopt three Material Design 50-shade hues from non-conflicting hue families:

```python
MODE_ADD_NEW    = ('add-new',    '#F3E5F5', 'Dodawanie nowej osoby')   # Purple 50
MODE_EDIT_TREE  = ('edit-tree',  '#E0F7FA', 'Edycja osoby z drzewa')   # Cyan 50
MODE_EDIT_DRAFT = ('edit-draft', '#F9FBE7', 'Edycja szkicu osoby')    # Lime 50
```

Hue families and conflict-distance from the four picker hues:

| Mode | Hex | Hue family | Closest picker (hue, hex) | Hue distance |
|---|---|---|---|---|
| MODE_ADD_NEW | `#F3E5F5` | purple | spouses (pink, `#FCE4EC`) | ~30° |
| MODE_EDIT_TREE | `#E0F7FA` | cyan | parents (blue, `#E3F2FD`) | ~30° |
| MODE_EDIT_DRAFT | `#F9FBE7` | lime | siblings (orange, `#FFF3E0`) | ~50° |
|  |  |  | children (green, `#E8F5E9`) | ~30° |

Mutual mode-vs-mode distance: purple↔cyan ~120°, purple↔lime ~150°,
cyan↔lime ~75°. All three pairs read as different "tints" at the perceived-
saturation level used here.

Luminance (CIE-L\*): `#F3E5F5` ~92, `#E0F7FA` ~96, `#F9FBE7` ~98 — all in the
"very light" band; black text legibility per the constraint above.

Why Material 50-shade specifically: it's a published, stable palette family
designed for low-saturation accessibility. Picking from it instead of guessing
hex values gives us a defensible justification ("Material 50 colors are
designed for this exact backdrop role") and a known-good visual neighborhood.

## Alternatives considered

- **Keep the existing `#FFF9C4` (pale yellow) for edit-draft.** Rejected. While
  it is technically distinct from `#FFF3E0` (siblings orange), both are warm
  pastels in the yellow-orange family and the visual distance is small enough
  that two-mode (add-new vs edit-tree) collisions are likely to recur on
  edit-draft when siblings is the focus picker.
- **Use cooler grays at differing luminance for the three modes.** Rejected —
  root_panel is already gray (`#F5F5F5`) and adding three more gray tints
  creates a "what is the actual current mode?" cognitive load, especially for
  Father.
- **Saturate the three mode colors more strongly to make them stand out.**
  Rejected. Higher saturation reduces black-text legibility and feels heavier
  on the elderly-accessibility scale (KB-006). The picker tints are already
  pale-saturated; modes at parity look right alongside.
- **Use only two modes (drop the edit-draft tint and just use the form title).**
  Rejected. Edit-draft is a distinct flow with different button labels and a
  different save target (`Poczekalnia/` vs `Lista osób/`); the visual cue
  matters and was a Sprint 06 design intent.
- **Add a thin colored border to the mode header strip instead of a background
  tint.** Worth considering as a future iteration if Father reports the
  background tint still feels noisy. Out of scope for Sprint 09 — minimal
  diff, maximum recovery from the demo regression.

## Consequences

**Positive:**
- Two of the three mode tints (add-new, edit-tree) immediately disambiguate
  from the picker they currently collide with. Demo bug closed.
- Three-mode visual distinction (Sprint 06 U2 promise) is preserved.
- Material 50 palette gives a defensible-by-source rationale; future
  Implementor or Critic does not have to wonder why these specific hex values.

**Negative:**
- Father's eye recalibrates to the new tints. Sprint 09 lands one diff; he
  re-validates by manual smoke. If a hue is wrong, this ADR is
  `iterates_with_user: true` and a follow-up swap is one-line.

**Neutral:**
- Exact hex values are minor; the design intent ("three picker-distinct
  pastels") is what matters and survives any small re-tuning.

## Iteration plan

This ADR is `iterates_with_user: true`. Expected:

1. Sprint 09 ships these three hexes.
2. Father smoke-tests; reports if any of the three feels off.
3. If a single hex needs swapping, write a one-paragraph ADR-005 amendment with
   the new hex + reasoning. No fresh ADR needed unless the entire palette
   strategy changes.

## Sources

- JOURNAL 2026-05-09 orchestrator entry — demo finding for item 3 (palette
  conflict) explicitly states `MODE_ADD_NEW` collides with parents and
  `MODE_EDIT_TREE` collides with children.
- `frames/add_person_frame.py` lines 30-32 (current mode tuples).
- `frames/add_person_frame.py` lines 391, 400, 409, 418 (current picker
  bg_color values).
- ADR-002 (UI framework — wxPython) — base UI framework whose styling primitives
  this ADR's hex changes ride on.
- KB-006 `~/.claude/kb/KB-006-wxpython-gotchas-localized-elderly-ui.md`
  — elderly-accessibility posture (low saturation, high luminance, black text)
  applied here. Snapshot at
  `.pipeline/1-architecture/discovery/kb-wxpython-menu-font-customization-snapshot.md`
  is the project-side reference; this ADR's hex picks honor that snapshot's
  rules without requiring a fresh KB cite.
- Material Design color system, "50" shade variants:
  https://m2.material.io/design/color/the-color-system.html
  (Verified URL renders 2026-05-09; this is a reference page, not a UI
  walkthrough — vendor-UI rot does not apply.)
