---
id: ADR-020
title: Partial-date prefix markers — "Około" (~) and "Przed" (<) on birth/death dates
kind: tech
decision_type: data-format
status: accepted
date: 2026-05-29
author: architect
sprint: sprint-21
iterates_with_user: true
related:
  - "ADR-003 (Drzewo .lnk filename encoding — NOT date storage; unaffected, see Scope note)"
  - "Issue #25 — Additional date settings"
  - "WPF migration design spec — .NET rewrite will inherit this format"
---

# ADR-020 — Partial-date prefix markers

## Context

Birth and death dates are stored as `YYYY-MM-DD` with `X` for unknown components (e.g., `1942-03-24`, `19XX-XX-XX`). Father requested two additional qualifiers:
- **"Około" (~)** — date is approximate/uncertain
- **"Przed" (<)** — date is an upper boundary ("born before 1900")

Both may apply simultaneously: `~<1900-04-XX` = "around/before April 1900".

The app is a bridge until the .NET rewrite (tree-manager-net); simplicity is favoured over a structured type.

## Scope — which ADRs this touches

This ADR is the sole owner of the birth/death date storage contract. Audited
ADR-001..ADR-019 (PR #27 reviewer request): none documents the person
date-storage format, so none has a contract this feature breaks.
- ADR-003 "encoding" = Drzewo `.lnk` **filename** scheme (generation / couple /
  gender). It never reads or writes `dates_of_birth` / `dates_of_death`. Unaffected.
- `<YYYY-MM-DD>` in ADR-007 / ADR-010 = **log-file** names, not person dates. Unaffected.
- ADR-011 touches `_fill_form_from_draft` (the prefix call sites live here) but its
  contract is draft-UUID restoration + menu state, not date encoding. Unaffected.
The date value remains an opaque string at the `file_service.py` / me.json layer.

## Decision

Prefix markers prepend the existing date string. Format: `[~][<]YYYY-MM-DD` where `~` and/or `<` are optional, in that fixed order.

Examples:
- `1942-03-24` — exact date (backward-compatible; no change)
- `~1942-XX-XX` — around 1942
- `<1900-XX-XX` — before 1900
- `~<1900-04-XX` — around/before April 1900

Storage: the `dates_of_birth` / `dates_of_death` JSON fields hold the prefixed string. `file_service.py` passes the value opaque — no change.

## Constraints

1. **Backward-compatible**: a bare date without prefix loads correctly; both checkboxes unchecked.
2. **Prefix stripping**: `_deconstruct_optional_date` strips `[~<]*` before the body regex (which is start-anchored via `re.match`).
3. **Prefix-only with no body**: storing `~XXXX-XX-XX` is the minimum meaningful prefixed date; returning `None` from `_build_optional_date` when no date fields are set, regardless of checkbox state, is intentional.
4. **Fixed order**: `~` always precedes `<`. Parser accepts any order for robustness, but build always emits `~<`.

## Alternatives rejected

- **Structured JSON** (`{"value": "1942-03-24", "approx": true, "before": true}`): more type-safe, but breaks the simple string convention used across the codebase and adds migration cost for the .NET rewrite. Deferred until the rewrite.
- **Display-only markers** (not stored in JSON): would lose user intent across sessions. Rejected.

## Consequences

- `_deconstruct_optional_date` return arity increases from 5 to 7 (adds `okolo: bool, przed: bool`).
- Both call sites in `_fill_form_from_draft` updated.
- Death-date checkboxes follow the same enable/disable contract as death-date dropdowns.
- **Backward-compat (read-forward)**: existing bare dates load unchanged in this version
  (constraint 1). A prefixed date stays a plain `dates_of_birth` / `dates_of_death` string
  on disk, so no data is lost — but an OLDER app build (before constraint-2 stripping) would
  feed `~1900-XX-XX` into the start-anchored body regex, fail the match, and render a BLANK
  date field. No crash, no file corruption; the stored string survives round-trip and
  re-displays correctly once re-opened in a build with the strip. Acceptable: single-user,
  self-updating app — downgrade is not a supported path.
- **.NET rewrite inherits this format verbatim**: tree-manager-net parses the same
  `[~][<]YYYY-MM-DD` string. No migration step; the prefix is part of the stored value,
  not a sidecar field. This is the simplicity trade made over structured JSON (see
  Alternatives rejected).
