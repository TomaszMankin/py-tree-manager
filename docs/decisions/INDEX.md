# Architecture Decision Records — py-tree-manager

> One file per architectural decision, numbered sequentially. New ADRs use the next available `NNN`.

| ID | Title | Status | Date |
|---|---|---|---|
| ADR-001 | Use IShellLink + IPersistFile directly for `.lnk` creation (not WScript.Shell) | accepted | 2026-05-02 |
| ADR-002 | UI framework — keep wxPython with documented migration path to PySide6 | accepted | 2026-05-04 |
| ADR-003 | Drzewo encoding scheme and hourglass selection algorithm (Amendment 2: spouse-seeded ancestor DFS) | accepted | 2026-05-09 |
| ADR-004 | Rody encoding scheme + surname-extraction algorithm + `.lnk` targets | superseded by ADR-016 | 2026-05-09 |
| ADR-005 | Mode background palette refresh — three new mode tints distinct from picker hues | accepted | 2026-05-09 |
| ADR-006 | Logging architecture — decorator-based journey log, dual exception hooks, file-lock self-recovery | accepted | 2026-05-09 |
| ADR-007 | Severity model + log-line format — INFO/ERROR/CRITICAL semantics and grammar | accepted | 2026-05-09 |
| ADR-008 | Email transport — Gmail SMTP_SSL, opportunistic send, file-system offline queue, 30-min retry | accepted | 2026-05-10 |
| ADR-009 | Red top-of-app button UX — placement, colour `#D32F2F`, label "Zgłoś błąd" | accepted | 2026-05-10 |
| ADR-010 | Runtime data consolidation under `<root>/.PyTreeManager/` with `%LOCALAPPDATA%` bootstrap pointer | accepted | 2026-05-11 |
| ADR-011 | Context-menu state machine, three-section menu structure, and draft-update semantics | accepted | 2026-05-11 |
| ADR-012 | CI pipeline architecture — Windows self-hosted Bitbucket runner, version-bump-on-merge, Bitbucket Downloads distribution | superseded by ADR-015 | 2026-05-12 |
| ADR-013 | Version embedding via `importlib.metadata` + in-app update detection against GitHub Releases | accepted (amended by ADR-015) | 2026-05-12 |
| ADR-014 | Self-replace update_helper mechanism — `.bat` helper with retry-on-lock and silent relaunch | accepted | 2026-05-12 |
| ADR-015 | Migrate hosting + CI from Bitbucket Pipelines to GitHub Actions + GitHub Releases | accepted | 2026-05-17 |
| ADR-016 | Lineage folders — surname-grouped subfolders with descendant + ancestor membership (supersedes ADR-004) | superseded by ADR-021 | 2026-05-17 |
| ADR-017 | Picker exclusion lifecycle — `set_selected_people` MUST fire `on_change_callback` on every state mutation (extends ADR-011) | accepted | 2026-05-19 |
| ADR-018 | Inno Setup installer — fixed per-user location, Desktop + Start Menu shortcuts, update-path observability (amends ADR-013/014) | proposed | 2026-05-29 |
| ADR-019 | Folder-selection guards — forbidden root names + person-folder me.json pre-check | proposed | 2026-05-29 |
| ADR-020 | Partial-date prefix markers — "Około" (~) and "Przed" (<) on birth/death dates | accepted | 2026-05-29 |
| ADR-021 | Lineage folders adopt Drzewo generation/couple/gender ordering — one hourglass, two views (supersedes ADR-016) | accepted | 2026-05-30 |

## Conventions

- **Filename**: `ADR-NNN-kebab-slug.md`. `NNN` is sequential and monotonically increasing.
- **Status transitions**: `proposed → accepted → (superseded by ADR-MMM | deprecated)`.
- **Each ADR** has a YAML front-matter block with `id`, `title`, `kind` (`tech`), `status`, `date`, `author`. Amendments add a `Changelog` section at the top of the body and an `amended` date in front-matter.
- **Cite sources inline**: every load-bearing decision cites the URL, doc, or KB note that justifies it.
- **Worked examples** in ADRs use placeholders (`Root`, `Spouse`, `ParentA`, etc.) unless the user has explicitly authored real names in the surrounding context. Real personal data should not appear in committed artifacts.
