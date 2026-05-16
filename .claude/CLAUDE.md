# PyTreeManager — Claude project config

## Layout

This project follows the stranger-readable surface standard:
- ADRs at `docs/decisions/ADR-NNN-*.md`. Index at `docs/decisions/INDEX.md`.
- Architecture overview at `docs/architecture.md` (single page; module map + data flow + glossary).
- Per-project Claude config at `.claude/CLAUDE.md` (this file).
- Agent operational scaffolding under `.pipeline/` is **gitignored entirely**. JOURNAL, STATE, sprint backlog, PM intake docs (PRDs), critiques, feedback, archaeology — all local-only.

## Session-start ritual

Before any substantive response in this project, read in order:
1. `.pipeline/STATE.md` — current phase + last agent action + carry-forward items.
2. The last ~5 entries of `.pipeline/JOURNAL.md` (narrative thread across sessions).
3. The user-memory pointer `~/.claude/projects/C--Users-Duch003/memory/project_py_tree_manager_status.md` — durable status; refreshed at every sprint close.
4. `docs/decisions/INDEX.md` for any in-scope ADRs.
5. Run `git log --oneline -10` from the project directory if my own conversation summary disagrees with the filesystem. **The filesystem is authoritative**; my summary may be stale.

If you find yourself about to assert "the last shipped sprint is N", verify against `git log --grep "Merged feature/sprint-"` first.

## Quick context

- **Tech stack**: Python 3 + wxPython 4.x + pywin32; Windows-only desktop app
- **Entry point**: `main.py` (installs `sys.excepthook` before `wx` import to keep the module wx-free at import time)
- **Local venv**: not committed; recreate via `python -m venv env && env\Scripts\activate && pip install -r requirements.txt -r requirements-dev.txt`
- **Run the app**: `env\Scripts\python.exe main.py`
- **Run tests**: `python -m pytest`

## Domain quick-reference

- Each person = one folder under `<root>/Lista osób/` containing `me.json`. Relationships stored as path arrays + UUID arrays, kept bidirectionally synchronized.
- Primary ID: `unique_identifier` (UUID; legacy typo `unique_indentifier` was fixed in early sprints).
- All UI text is **Polish**. Target user is an elderly relative; keep messages simple, no technical jargon. Polish diacritic codepoints used in the UI: ę (U+0119), ń (U+0144), ł (U+0142), ó (U+00F3), ś (U+015B), ż (U+017C), ą (U+0105). Tests enforce these.
- Forbidden folder names to skip during scanning: "Pozostałe nieuporządkowane", "Rutowscy - dane ogólne", "Do ustalenia", "Wspólne".
- Runtime data lives under `<root>/.PyTreeManager/` (settings + logs), bootstrapped via a one-line pointer at `%LOCALAPPDATA%\PyTreeManager\last_root.txt`.

## Commit convention

Conventional Commits style for new commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`). Scope optional but useful where natural (e.g., `feat(services): ...`).

## Project posture

Bridge app for a single elderly user. Polish-language. Windows-only. Don't over-build; reliability + clarity over feature breadth. The longer-term vision is a fuller family-tree application (separate project, server-backed); PyTreeManager keeps the source-of-truth tree clean while that bigger system is being designed.

For the full architectural picture see `docs/architecture.md`.
