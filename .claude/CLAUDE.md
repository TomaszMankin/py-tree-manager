# PyTreeManager — Claude project config

## Layout

This project follows the stranger-readable surface standard:
- ADRs at `docs/decisions/ADR-NNN-*.md`. Index at `docs/decisions/INDEX.md`.
- Architecture overview at `docs/architecture.md` (single page; module map + data flow + glossary).
- Per-project Claude config at `.claude/CLAUDE.md` (this file).
- Agent operational scaffolding under `.pipeline/` is **gitignored entirely**. JOURNAL, STATE, sprint backlog, PM intake docs (PRDs), critiques, feedback, archaeology — all local-only.

## Session-start ritual

Before any substantive response in this project, read in order:
1. `.claude/.pipeline/STATE.md` — current phase + last agent action + carry-forward items.
2. The last ~5 entries of `.claude/.pipeline/JOURNAL.md` (narrative thread across sessions).
3. The user-memory pointer `~/.claude/projects/C--Users-Duch003/memory/project_py_tree_manager_status.md` — durable status; refreshed at every sprint close.
4. `docs/decisions/INDEX.md` for any in-scope ADRs.
5. Run `git log --oneline -10` from the project directory if my own conversation summary disagrees with the filesystem. **The filesystem is authoritative**; my summary may be stale.

If you find yourself about to assert "the last shipped sprint is N", verify against `git log --grep "Merged feature/sprint-"` first.

## Pipeline agent convention

When `/deliver-project` (or any pipeline agent) runs against a dashboard issue, discoveries / refinements / decision-needed flags go as **comments on the source GitHub issue** via `gh issue comment <N> --body "..."`. Sprint plans, critiques, retros still go to `.claude/.pipeline/2-sprints/sprint-NN/` (gitignored, local) as before — only the user-facing thread goes to the issue.

## Quick context

- **Tech stack**: Python 3.11+ + wxPython 4.x + pywin32; Windows-only desktop app
- **Entry point**: `main.py` (installs `sys.excepthook` before `wx` import to keep the module wx-free at import time)
- **Local venv**: not committed; recreate via `python -m venv env && env\Scripts\activate && pip install -e ".[dev]"`
- **Run the app**: `env\Scripts\python.exe main.py`
- **Run tests**: `python -m pytest`

## CI / self-hosted runner

GitHub Actions on a self-hosted Windows runner registered at the repo level. Workflows live at `.github/workflows/`. Helper scripts at `.pipelines/ci/`.

### Inspect runs
- `gh run list --limit 5` — recent runs
- `gh run view <id>` — summary; `--log-failed` for the failed-step log only
- `gh run watch <id>` — stream live until done

### Runner service (Windows)
- Discover: `Get-CimInstance Win32_Service -Filter "Name LIKE 'actions.runner%'" | Format-List Name,StartName,State`
- Restart after any PATH / Python change: `Restart-Service '<exact Name from above>'`
- The runner inherits System PATH at service-start; user-scoped installs are invisible to it. Python must be installed system-wide (`C:\Program Files\Python3xx\`) and on System PATH, OR the service must be reconfigured to log on as a user with the install.

### Known runner-environment quirks
- Default service account `NT AUTHORITY\NETWORK SERVICE` cannot read other users' AppData.
- `tmp_path` under `C:\Windows\ServiceProfiles\NetworkService\...` — paths returned by `IShellLinkW.Save()` are canonicalised through the shell registry and may differ in case (`Windows` vs `WINDOWS`). Compare paths via `pathlib.Path()` equality, not strings.
- pwsh 7 is the default shell for `run:` steps when installed system-wide; PS 5.1 traps don't apply here (unlike the prior Bitbucket pipeline).

### When CI fails but local tests pass
1. Service-account path-case (above).
2. Encoding (system Python may differ from local; check cp1252 vs utf-8).
3. Missing dev dependency in `pyproject.toml`'s `[project.optional-dependencies.dev]`.
4. PEP 440 violation in derived version strings (PR builds use `<base>.dev<N>+<sha>`, never hyphens).

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
