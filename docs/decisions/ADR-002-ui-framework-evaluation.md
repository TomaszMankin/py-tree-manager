---
id: ADR-002
title: UI framework — keep wxPython for py-tree-manager (with a documented migration path to PySide6 if accessibility needs grow)
kind: tech
status: accepted
date: 2026-05-04
author: architect
supersedes: none
superseded_by: none
---

## Context

Sprint 06 surfaced two requests that wxPython makes painful:

1. **Visual mode distinction** across three modes (ADD-NEW / EDIT-IN-TREE / EDIT-DRAFT) via background color or colored header strip.
2. **Menu font enlargement** for the elderly target user (father).

Background color of a `wx.Frame` is workable in wxPython but not uniformly clean across all child controls. Menu font is the bigger problem: per the research at `1-architecture/discovery/kb-wxpython-menu-font-customization-snapshot.md`, wxPython on Windows can ONLY change menu-item fonts via `wx.MenuItem.SetFont` (Windows-only, owner-drawn, breaks dark mode), and CANNOT change the menu-bar's own font at all (system-owned).

PRD-002 explicitly defers framework re-evaluation: "When framework re-evaluation happens, the criterion is 'does it make father's flow simpler', not 'does it match what the future system might use'." That re-evaluation is the trigger for this ADR.

The decision is whether to:
- **A. Keep wxPython** and accept its menu-customization limits, working within them.
- **B. Switch to PySide6 (Qt)** and gain full styling control at the cost of a 2-4 day migration.
- **C. Hybrid** — a multi-step path that doesn't need to be decided now.

## Decision

**Keep wxPython for the remainder of py-tree-manager's lifetime as a bridge app.** Adopt the limited customization wxPython supports:

1. Use background color on the root `wx.ScrolledWindow` (already supported and already used at line 62 of `add_person_frame.py`) for the three-mode visual distinction (U2 in Sprint 06 scope).
2. For menu font enlargement (R1 → U-implementation): defer to Sprint 06b or later. First, ship the bug fixes (B1/B2/B3) and the mode-color UI rework (U1/U2/U3) on wxPython. **Father uses the form, not the menu, in 95% of his sessions.** The menu only fires for "open person" / "load draft" / "save". If those button-like actions get problematic, replace the menu with a `wx.ToolBar` of large `wx.Button`s — an option this ADR endorses as a pre-approved fallback that does not require a new ADR.
3. **Document the PySide6 migration path explicitly** (this ADR's "Consequences" + the KB snapshot). If father reports menu trouble OR if a future sprint needs styling that wxPython cannot deliver, the migration is a 2-4 day project against an unchanged service layer — well within a single sprint.

Accepted by user 2026-05-08. Keep wxPython for this iteration; migration tripwires defined above remain active for future sprints.

## Alternatives considered

### Alternative A — Keep wxPython (RECOMMENDED, this decision)

**Rationale:**
- Sprint 05 just shipped successfully on wxPython. 37 tests green. The full 1.0 feature surface (Phases 1, 2, 3, 4.1, 4.2) is now wxPython-resident.
- PRD-002 boundary: this app is a bridge with a months-to-years lifetime. Migrating to a new framework for a multi-month bridge tool is **the textbook scope-creep pattern PRD-002 was written to prevent**.
- The actual UX problems (B1, B2, B3, U1, U2, U3) are mostly NOT framework-bound. B1 is a stub handler. B2 is a missing UI flow. B3 is a missing menu wiring. U1 is menu reorganization (wxPython native). U2 is a background color change (wxPython native). U3 is form clearing (wxPython native).
- Menu font (R1 driver) is the ONE wxPython-painful item, and even there: (a) the OS-level "make text bigger" route exists and is Microsoft-recommended; (b) father has not yet reported menu use as a problem; (c) the toolbar fallback exists.
- Migration cost is non-trivial (2-4 days of mechanical work + retesting) and the only thing that justifies it would be repeated styling pain.

**Trade-off accepted**: the three-mode visual distinction will be slightly less polished than it would be in Qt (e.g., colored header strip might not paint as cleanly across all child controls), but the user will have something working.

### Alternative B — Switch to PySide6 (Qt) NOW, Sprint 07

**Rationale (the case FOR this option):**
- Qt's QSS makes background color, header strips, menu fonts, and dark mode trivial — all the customization desires from Sprint 06 collapse to one-liners.
- `QApplication::setFont` propagates to `QMenu` (with caveats — see KB snapshot — but works in practice for the customization scope father needs).
- `qt-material` library provides density scaling specifically for accessibility, including elderly-friendly large-font modes out of the box.
- The service-layer / UI separation is already clean, so migration touches only `frames/` + `main.py`. 37 tests are unaffected.
- PySide6 is LGPL — no license problem for this project.

**Why rejected (the case AGAINST):**
- PRD-002: 2-4 days on framework migration for a bridge app whose REPLACEMENT (the larger server-backed system) is already on the user's roadmap is poor ROI. That 2-4 days could ship 2 more useful sprints.
- "Time-to-Sprint-06-shipping" matters now (B1/B2/B3 are user-visible bugs). Migration adds a sprint between user and bug fixes.
- The Sprint 06 problems do NOT, in the architect's read, require Qt to solve. Background color + larger menu fonts via `wx.MenuItem.SetFont` (Windows-only, but py-tree-manager IS Windows-only per PRD-002) cover the practical needs.
- Risk of late-stage migration bugs in production single-user data flow. The Polish-character `.lnk` path took 4 sprints to surface; Qt-side parallels could exist.
- "Just because we can switch frameworks for free doesn't mean we should." The bridge-app principle says we don't.

This option becomes attractive ONLY IF: father reports menu use is a problem AND the toolbar fallback (Alternative A escape hatch) is ALSO unsatisfactory. Until then, keeping wxPython is correct.

### Alternative C — Hybrid (rewrite `frames/` in Qt, keep services)

This is what Alternative B actually IS in practice. There is no "true hybrid" where wxPython and Qt cohabit in the same Python process — they would each want to own the event loop. So Alternative C reduces to "do Alternative B at some future date." The ADR endorses this implicitly: if Alternative A's escape hatches are exhausted, jump straight to Alternative B; the path is clean.

### Alternative D — Switch to Tkinter (built-in, no install)

**Rejected.** Tkinter is even more limited than wxPython for styling on Windows (themed `ttk` widgets help but are not Qt-class), and the ttk theming story for elderly accessibility is weaker than either wxPython's `MenuItem.SetFont` or Qt's QSS. Migration cost similar to Qt's; payoff strictly worse. Not a serious contender.

## Consequences

### Positive
- Sprint 06 can ship its bug fixes and UX rework against the existing codebase. No framework migration in the critical path.
- 37 existing tests stay relevant. Manual testing surface stays known.
- Father gets the bug fixes faster.
- PRD-002's "no framework migration this iteration" stance is upheld with a documented evaluation, not a hand-wave.

### Negative
- Three-mode visual distinction will use the wxPython-supported subset (background color of `root_panel`, possibly a colored `wx.StaticText` header strip). Slightly less elegant than Qt's QSS.
- Menu fonts cannot be enlarged beyond what `wx.MenuItem.SetFont` supports (per-item, owner-drawn, dark-mode incompatible). If father wants larger menus, the path is "OS-level text scaling" first, "toolbar replacement" second.
- Future styling requests will hit the same wxPython wall. Each one re-litigates this ADR, eventually triggering Alternative B.

### Migration tripwire (when to revisit)

**Re-open this ADR (and likely flip to Alternative B) when ANY of these occur:**
1. Father explicitly reports menu use as a problem AND a toolbar replacement does not satisfy.
2. A second styling request lands that wxPython cannot deliver cleanly (third would be a pattern, not an exception).
3. The future server-backed family-tree system starts and decides on Qt for its desktop client — at which point migration here aligns py-tree-manager's lessons with the future system's choice.
4. Dark mode becomes a requirement (wxPython + `MenuItem.SetFont` is incompatible with dark mode by design).

When triggered: the migration is pre-scoped at 2-4 days per the KB snapshot. No further ADR needed for the migration itself; this ADR's Alternative B IS the migration plan.

## Sources

- `1-architecture/discovery/kb-wxpython-menu-font-customization-snapshot.md` (full research notes + sources)
- `1-architecture/discovery/kb-qt-vs-wxpython-for-customizable-desktop-ui-snapshot.md` (framework comparison + migration cost analysis)
- `decisions/PRD-002-bridge-app-scope-boundary.md` — bridge-app principle; specifically the boundary that says framework re-evaluation must serve father's flow, not future-system alignment.
- wxPython Phoenix `wx.MenuItem` reference: https://wxpython.org/Phoenix/docs/html/wx.MenuItem.html
- discuss.wxpython.org "Menu item font size": https://discuss.wxpython.org/t/menu-item-font-size/34209
- doc.qt.io PySide6 widget styling: https://doc.qt.io/qtforpython-6/tutorials/basictutorial/widgetstyling.html
- pythonguis.com 2026 framework comparison: https://www.pythonguis.com/faq/which-python-gui-library/
- qt-material density-scaling library (accessibility precedent): https://github.com/UN-GCPDS/qt-material
