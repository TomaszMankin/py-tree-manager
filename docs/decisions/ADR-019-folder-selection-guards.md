---
id: ADR-019
title: Folder-selection guards — person-folder me.json pre-check
kind: tech
status: proposed
date: 2026-05-29
author: architect
---

# ADR-019 — Folder-selection guards

## Problem

User could select any folder in the tree browser — including subfolders that contain no `me.json` — and the app would crash with a raw `FileNotFoundError`, displaying a confusing technical error message instead of a clear explanation.

## Decision

Before calling `_load_person_for_edit`, check that the selected folder contains `me.json`. If absent: show Polish warning dialog and return early. Keep the existing `except FileNotFoundError` as a race-condition safety net.

## Consequences

`on_open_person_click` gains a `Path(folder) / "me.json"` existence check before the try/except load block.
