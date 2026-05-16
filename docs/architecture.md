# py-tree-manager — Architecture

A Python/wxPython desktop app for maintaining a family tree as a flat folder structure on Windows. Single-user, Polish UI, Windows-only. The canonical store is the filesystem itself — the app is a maintenance UI around it.

## Module map

```
main.py                          Entry point at repo root. Installs sys.excepthook BEFORE wx import;
                                 constructs LoggingApp. Imports from src.* per pythonpath = . in pytest.ini.

src/
  frames/
    add_person_frame.py          Main wx.Frame. Three modes (NEW / EDIT_TREE / EDIT_DRAFT).
                                 4 relationship pickers (parents, children, spouses, siblings).
                                 3-section context menu + 9 named actions.
    menu_state.py                Pure function compute_menu_state(MenuMode) — wx-free state machine.
    controls/                    Reusable wx controls (multi-person picker, etc.).
    dialogs/                     Polish-language dialog helpers (Yes/No/Cancel localized).

  services/
    tree_service.py              Orchestrates writes: save person, rebuild folder tree (Drzewo),
                                 rebuild lineage (Rody), promote-disposes-draft.
    file_service.py              Bootstrap settings + filesystem scanning. Pointer-driven boot.
    folder_tree_service.py       Hourglass selection + spouse-seeded ancestor DFS;
                                 produces folder tree (Drzewo) shortcut filenames.
    lineage_service.py           Surname extraction from root + spouse parents; alphabetical .lnk
                                 shortcuts produced in <root>/Rody/.

  wrappers/
    person_data_wrapper.py       Typed accessor over me.json. Field-name canonical source.
    settings_wrapper.py          Typed accessor over settings.json. JSON keys may be Polish for back-compat
                                 (FOLDER_TREE_ROOT_UUID = "drzewo_root_uuid").

  helpers/
    logger.py                    @log_user_action decorator + log_error API + dual exception hooks.
                                 init_logging(root) relocates writes to <root>/.PyTreeManager/logs/.
                                 Wires update_helper check in LoggingApp.OnInit after frame.Show() so
                                 the user sees the window first.
    email_helper.py                   SMTP_SSL transport + JSON offline queue + 30-min retry timer.
    shortcut_helper.py           Unicode-clean .lnk creation via IShellLinkW + IPersistFile.
                                 Unicode paths must be set via IPersistFile.Save with a wide-string;
                                 see Microsoft Learn / pywin32 IShellLink docs.
    update_helper.py                   In-app update detection + self-replace helper.
                                 UpdateHelper.check_for_update() fetches latest.json;
                                 UpdateHelper.prompt_user_to_update() shows Polish dialog;
                                 UpdateHelper.download_and_apply_update() streams new .exe + launches
                                 update.bat helper; _compare_versions() wraps packaging.version.parse.
    update_info.py               UpdateInfo frozen dataclass (parsed latest.json payload).

  constants/, data_types/        Small leaf modules (constants, OptionalDate type, etc.).

  tests/                         pytest suite (services/, frames/, helpers/, integration/).
```

Naming convention:

- **Python identifiers** (classes, methods, vars, file names) are English: `FolderTreeService`, `rebuild_folder_tree()`, `_on_refresh_lineage_click`.
- **User-facing Polish strings** (wx dialogs, menu labels) stay Polish: `"Odśwież drzewo"`, `"Zaktualizuj szkic osoby"`.
- **On-disk folder names** stay Polish (they're what the user navigates to in Explorer): `<root>/Drzewo/`, `<root>/Rody/`, `<root>/Poczekalnia/`, `<root>/Lista osób/`.
- **Back-compat JSON keys** stay Polish in the stored value while the Python enum identifier is English: `FOLDER_TREE_ROOT_UUID = "drzewo_root_uuid"`.

## On-disk layout (user data + app data)

```
<root>/                          User-chosen folder (e.g. C:\<your-tree>\). Path remembered in
                                 %LOCALAPPDATA%\PyTreeManager\last_root.txt (single-line pointer).
  Lista osób/                    Canonical store. One folder per person, each with me.json.
    <Person Name>/
      me.json                    Identity + relationships (path arrays + UUID arrays, bidirectional).
  Drzewo/                        Auto-generated. Hourglass selection from root_person, .lnk shortcuts
                                 sorted by Windows StrCmpLogicalW. Wipe-and-rebuild on demand.
  Rody/                          Auto-generated. ≤4 surname-derived .lnk shortcuts (one per branch).
                                 Wipe-and-rebuild on demand.
  Poczekalnia/                   Draft persons not yet in the tree. <uuid>.json files.
  .PyTreeManager/                App infrastructure.
    settings.json                cached_people, font_size, root_folder_path, drzewo_root_uuid.
    logs/
      YYYY-MM-DD__journey.log    INFO lines: user actions, app starts, log dir relocations.
      YYYY-MM-DD__exceptions.log ERROR / CRITICAL / INFO-CLEANUP lines.
      pending/                   Offline email queue (one .txt per failed send).
```

## Data flow

1. **Launch** → `main.py` installs `sys.excepthook` (wx-free) → constructs `LoggingApp(False)` → `init_logging(None)` writes to `%LOCALAPPDATA%` fallback → `AddPersonFrame(None)` constructs → `FileService.__init__()` reads `last_root.txt`, loads `<root>/.PyTreeManager/settings.json` (or runs one-shot migration from `%TEMP%` legacy location) → `init_logging(real_root)` relocates logs to `<root>/.PyTreeManager/logs/`.
2. **User edits a person** → form fills from `me.json` → user clicks save → `TreeService.save_person_to_tree()` writes `me.json` AND updates bidirectional relationship arrays on every linked person's `me.json`.
3. **User refreshes Drzewo (folder tree)** → `FolderTreeService.compute_membership(root_uuid)` runs hourglass BFS (root's blood-line ancestors via couple A; spouse's blood-line ancestors via couple B; descendants with by-marriage spouses) → wipe `<root>/Drzewo/` → `ShortcutHelper` writes one `.lnk` per member with sortable filename.
4. **User refreshes Rody** → `LineageService.compute_rody(root_uuid)` extracts ≤4 surnames from root's parents + spouse's parents (maiden_name precedence) → wipe `<root>/Rody/` → one `.lnk` per surname.
5. **Exception fires** → `sys.excepthook` (startup) or `LoggingApp.OnExceptionInMainLoop` (event loop) → `_emit_critical` writes one CRITICAL line → `email_helper.enqueue_email_for_severity` queues an email → `wx.Timer` flushes the queue every 30 minutes when online.

## Design highlights

- **Filesystem-is-database**: no DB, no schema migrations. The user can browse `<root>/Lista osób/` in Explorer and the canonical state is right there.
- **Bidirectional relationship sync**: every relationship edge is stored on both endpoints' `me.json` files. Writes propagate to all affected files in one transaction.
- **Polish UI throughout**: every user-facing string and dialog uses Polish with correct diacritics. Codepoints verified by tests (ę U+0119, ń U+0144, ł U+0142, ó U+00F3, ś U+015B, ż U+017C, ą U+0105).
- **Windows-sortable encoding**: Folder tree (Drzewo) filenames use a leading `[NN]` sort key (NN = gen + 50) so Explorer's StrCmpLogicalW orders by generation natively. The displayed second bracket shows the user-visible signed generation; the two are decoupled so generation labels read positive for ancestors and negative for descendants.
- **Crash-resilient logger**: file-lock retry up to 100 suffixes; emergency stderr fallback; logger errors never propagate to the app.
- **Offline-tolerant email**: queue is on the filesystem under `<root>/.PyTreeManager/logs/pending/`; survives crashes and reboots; idempotent retry.

## Glossary

| Term | Meaning |
|---|---|
| **`me.json`** | Per-person identity + relationships JSON file at `<root>/Lista osób/<Person>/me.json`. |
| **Drzewo** | "Tree" (PL) / "Folder tree". The view constructed with links (lnk) and sorted natively by Windows to roughly take shape of hourglass; selection: blood ancestors + descendants of a root person. |
| **Rody** | "Family branches" (PL) / "Lineages". Surname-derived `.lnk` shortcuts pointing at the most senior bearer of each surname. |
| **Poczekalnia** | "Waiting room" (PL). Persons drafted but not yet promoted to the canonical tree. |
| **Root person** | The pivot for Drzewo/Rody. Configured via menu; UUID stored in settings as `drzewo_root_uuid`. |
| **Bridge app** | Project posture: this app is a maintenance UI bridging today's flat-file store to a future server-backed system. Not over-built. |
| **Hourglass selection** | Top half = ancestors (root + spouse, then their parents, etc.); waist = root + spouse(s); bottom half = descendants + by-marriage spouses. |
| **Couple letter** | Per-generation letter token (A, B, …) used in Folder tree (Drzewo) filenames to group spouse pairs together within a generation. Paternal-first DFS assignment. |
| **mode** | Context-menu state machine value: `NEW` (creating a new person), `EDIT_TREE` (editing a tree person), `EDIT_DRAFT` (editing a draft). One mode at a time. |

## Project posture

This is a **bridge tool** — single-user, personal, Polish-language, Windows-only. The target user is an elderly relative who curates the family tree by hand. The codebase prioritises reliability, simple recovery from errors, and Polish-language clarity over feature breadth. Don't over-build.

## Deployment

The app is distributed as a self-contained `.exe` built by PyInstaller (`--onefile
--windowed --copy-metadata py-tree-manager --add-data ".pipelines/update.bat;."`).

- **CI**: `bitbucket-pipelines.yml` at repo root drives a Bitbucket Cloud
  pipeline on a self-hosted Windows runner.  Scripts live under
  `.pipelines/ci/`.  On merge to `main` the pipeline bumps the patch version
  in `pyproject.toml`, commits with `[skip ci]`, tags, builds the `.exe`, and
  publishes a GitHub Release marked as `--latest`.
- **Runtime version**: read via `importlib.metadata.version("py-tree-manager")`.
  Works in both dev (editable install) and frozen mode (PyInstaller
  `--copy-metadata` embeds the metadata).
- **Update detection**: `src/helpers/update_helper.py` fetches
  `https://api.github.com/repos/TomaszMankin/py-tree-manager/releases/latest`
  once per launch, parses `tag_name` (stripping the leading `v`), compares
  with `packaging.version.parse`, prompts in Polish if newer.  Silently skips
  on any network failure (update_helper MUST NEVER crash the app).
- **Self-replace**: `.pipelines/update.bat` (bundled in the .exe via
  `--add-data`) waits for the parent PID to exit, renames `.exe.new` over
  `.exe`, then relaunches.
- **Release flow**: see `docs/RELEASE.md`.

## See also

- `README.md` — install, run, test commands
- `docs/RELEASE.md` — how to cut a release (OAuth setup, first 1.0.0 upload, routine flow)
- `docs/decisions/INDEX.md` — full ADR index
- `docs/decisions/` — full decision log (folder tree (Drzewo) encoding algorithm, CI pipeline, update_helper, etc.)
