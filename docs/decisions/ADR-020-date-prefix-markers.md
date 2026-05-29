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

Birth and death dates are stored as `YYYY-MM-DD` with `X` for unknown components. Two additional qualifiers are needed to express date uncertainty:
- **"Około" (~)** — date is approximate
- **"Przed" (<)** — date is an upper boundary ("born before 1900")

## Decision

Prefix markers prepend the existing date string. Format: `[~][<]YYYY-MM-DD`, markers optional, fixed order.

Examples:
- `1942-03-24` — exact date
- `~1942-XX-XX` — around 1942
- `<1900-XX-XX` — before 1900
- `~<1900-04-XX` — around/before April 1900

Storage: the `dates_of_birth` / `dates_of_death` JSON fields hold the prefixed string as-is.

## Constraints

1. Backward-compatible: bare dates load correctly with both prefix markers unchecked.
2. Fixed order: `~` always precedes `<`.
3. Prefix with no date body: treated as no date (None).

## Alternatives rejected

None.

## Consequences

- Existing bare dates remain valid and unchanged.
- An older app build without prefix support would render a blank date field on prefixed dates (no crash, no file corruption). Downgrade is not a supported path.
- The .NET rewrite inherits this format verbatim.
