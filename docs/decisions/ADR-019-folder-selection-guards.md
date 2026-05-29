---
id: ADR-019
title: Folder-selection guards — person-folder me.json pre-check
kind: tech
status: proposed
date: 2026-05-29
author: architect
---

# ADR-019 — Folder-selection guards

## Decision

Before calling `_load_person_for_edit`, check that the selected folder contains `me.json`. If absent: show Polish warning dialog and return early. Keep the existing `except FileNotFoundError` as a race-condition safety net.

## Why

Issue #24: `_load_person_for_edit` raised `FileNotFoundError` when the user selected a folder without `me.json` (e.g. a person's subfolder rather than their root folder). The exception was caught and showed a generic error; pre-check gives a clearer message and avoids the exception path entirely.

## Consequences

`on_open_person_click` gains a `Path(folder) / "me.json"` existence check before the try/except load block.
