---
id: ADR-018
title: Inno Setup installer with fixed per-user location, shortcuts, and update-path observability
kind: tech
status: proposed
date: 2026-05-29
author: architect
amends: ADR-013, ADR-014
---

# ADR-018 — Installer + update observability

## Decision

- Binary installs to `%LOCALAPPDATA%\Programs\PyTreeManager\PyTreeManager.exe` (fixed, per-user, writable).
- Inno Setup script `installer/py-tree-manager.iss` creates Desktop + Start-menu shortcuts.
- App creates `<root>\PyTreeManager.lnk` pointing to canonical exe after user picks tree root.
- On update: app downloads `PyTreeManager-Setup-<v>.exe`, runs `/VERYSILENT /NORESTART`; Inno Setup replaces exe + recreates shortcuts in place.
- Fallback for older releases without installer asset: raw `.exe` + `update.bat` swap (ADR-014 unchanged).
- OnInit update block logs every branch (check-entered, up-to-date, newer-available, accepted, declined, download-failed, launch-failed).
- User declining is NOT persisted — re-prompt on next launch.

## Why

Issue #14: no canonical location, no shortcuts, stale copies after update.
Issue #24: silent no-op (metadata read exception swallowed entire update block).

## Consequences

Release publishes both `py-tree-manager-<v>.exe` (raw, keeps asset-name contract) and `PyTreeManager-Setup-<v>.exe` (installer). First install on father's machine requires one-time manual installer run.
