---
id: ADR-010
title: Runtime data consolidation under `<root>/.PyTreeManager/` with %LOCALAPPDATA% bootstrap pointer
kind: tech
decision_type: architecture
status: accepted
date: 2026-05-11
author: architect
sprint: sprint-13 (Phase A)
supersedes: (none)
iterates_with_user: false
related:
  - ADR-006 (logging architecture; logger relocation contract referenced at `helpers/logger.py` lines 434-461)
  - ADR-008 (email queue lives under `<root>/logs/pending/` today; relocates with this ADR to `<root>/.PyTreeManager/logs/pending/`)
  - PRD-007 (release engineering; Sprint 13 umbrella PRD — Phase A is this consolidation only; Phase B is PII scrub + deployment)
sources:
  - C:/Repositories/py-tree-manager/services/file_service.py lines 38-50 (settings stored under `%TEMP%/PyTreeManager/`)
  - C:/Repositories/py-tree-manager/services/file_service.py lines 98-125 (`set_root_folder` writes settings.json back to `%TEMP%`; never relocates)
  - C:/Repositories/py-tree-manager/helpers/logger.py lines 62-67 (`_localappdata_log_dir` fallback — uses `%LOCALAPPDATA%` with `tempfile.gettempdir()` defensive fallback)
  - C:/Repositories/py-tree-manager/helpers/logger.py lines 434-461 (`init_logging` docstring + body promising relocation to `<root>/logs/`)
  - C:/Repositories/py-tree-manager/helpers/logger.py line 451 (`new_dir = Path(root_folder) / "logs"` — hardcoded subpath this ADR changes)
  - C:/Repositories/py-tree-manager/helpers/logger.py line 596 (`OnInit` calls `init_logging(root_folder=None)` and never re-calls — Sprint 11 implementor gap surfaced here)
  - `.pipeline/JOURNAL.md` 2026-05-11 — user AskUserQuestion answers (layout = `.PyTreeManager/`; pointer = `%LOCALAPPDATA%\PyTreeManager\last_root.txt`)
  - https://docs.python.org/3/library/os.html#os.replace (atomic-rename guarantee on Windows when target exists)
  - https://docs.python.org/3/library/shutil.html#shutil.move (cross-volume-safe move semantics)
---

# ADR-010 — Runtime data consolidation under `<root>/.PyTreeManager/`

> Phase A of Sprint 13. Phase B (PII scrub, deployment, PyInstaller) is
> a separate dispatch; Phase A is purely a structural refactor that
> moves all runtime state into the user's chosen `<root>` folder and
> leaves a single tiny pointer file in `%LOCALAPPDATA%` to break the
> bootstrap chicken-and-egg. No new product features; no changes to UI,
> services, or any data semantics.

## 0. Changelog

- **2026-05-11 (initial)** — first issue. Two user-locked decisions
  (layout name `.PyTreeManager`; pointer location
  `%LOCALAPPDATA%\PyTreeManager\last_root.txt`) confirmed via in-chat
  AskUserQuestion. Sprint 11 implementor logger-relocation gap
  (`OnInit` never re-calls `init_logging(real_root)` after FileService
  loads) surfaced as a finding and folded into the fix.

## 1. Context

The app today scatters runtime state across three locations:

| What | Where today | Source |
|---|---|---|
| `settings.json` (root folder path, cached_people, drzewo_root_uuid, font_size, flags) | `%TEMP%\PyTreeManager\settings.json` | `services/file_service.py:38-50, 98-125, 267-268` |
| Plain-text logs (`<YYYY-MM-DD>__journey.log`, `<YYYY-MM-DD>__exceptions.log`) | `%LOCALAPPDATA%\PyTreeManager\logs\*.log` (because `init_logging(None)` is the only call ever made) | `helpers/logger.py:62-67, 596` |
| Pending-email queue | `<root>/logs/pending/pending_email_<uuid>.json` (only path that's actually under `<root>` — accidentally correct because the queue path is built from the logger's `_active_log_dir`, which IS supposed to relocate but doesn't) | ADR-008 §3.1; `helpers/email_helper.py` |
| Drafts | `<root>/Poczekalnia/<uuid>.json` (already under root — Sprint 07 F2 fix) | `services/file_service.py:240-258` |
| `Lista osób/`, `Drzewo/`, `Rody/` | `<root>/...` (already under root — created in `set_root_folder`) | `services/file_service.py:120-123` |

There are two problems with this split state:

**Problem A — settings outside the tree.** `%TEMP%` is volatile;
Windows Disk Cleanup, Storage Sense, or a corporate-policy reset can
empty it. The user's live `settings.json` contains 10 cached_people
and the Drzewo root UUID; losing it triggers the first-run
`select_folder` dialog and a full re-scan. Worse, when the user moves
the tree (e.g. external drive → local SSD), the settings cache stays
behind in `%TEMP%` and references the old absolute paths inside
`cached_people` — silent data drift.

**Problem B — logger never re-points after root is known.** ADR-006
§3.2 explicitly promises:

> `init_logging(root_folder)` is idempotent. First call with `None`
> opens `%LOCALAPPDATA%/PyTreeManager/logs/`. Subsequent call with the
> real `<root>` re-points `_active_log_dir` to `<root>/logs/`.

`helpers/logger.py:434-461` implements both branches correctly. But
`LoggingApp.OnInit()` at line 596 calls `init_logging(root_folder=None)`
**ONCE** and never re-calls it after `FileService` loads
`root_folder_path` from `settings.json`. Result: every log line in the
app's lifetime is written to `%LOCALAPPDATA%\PyTreeManager\logs\`,
not to the user's tree. This is a Sprint 11 implementor gap that the
reviewer didn't catch because Halt-E (wx-isolation) and Halt-G
(additions-only) didn't include a runtime-path-assertion check. I'm
not opening a separate ADR for this; the fix is structurally part of
the consolidation work and lives in the same plan.

**The user's request** (in-chat, 2026-05-11): unify everything under
`<root>` so the runtime state travels with the tree. AskUserQuestion
locked the two design points:

- **Folder name**: `.PyTreeManager/` (dot-prefix; user picked this
  preview from three options — alternatives were `_PyTreeManager/` and
  `PyTreeManager/`).
- **Bootstrap pointer**: a single line of text at
  `%LOCALAPPDATA%\PyTreeManager\last_root.txt` containing the absolute
  path of the chosen root. This is the ONLY thing that lives outside
  `<root>` after consolidation; it survives `%TEMP%` cleaning and is
  per-user.

## 2. Decision (one paragraph)

All runtime state moves under `<root>/.PyTreeManager/` —
**`<root>/.PyTreeManager/settings.json`** (replaces
`%TEMP%\PyTreeManager\settings.json`) and
**`<root>/.PyTreeManager/logs/`** (replaces both the
`%LOCALAPPDATA%\PyTreeManager\logs\` fallback and the never-actually-
reached `<root>/logs/` location). A single
**`%LOCALAPPDATA%\PyTreeManager\last_root.txt`** pointer file (UTF-8,
one line, the absolute root path) breaks the bootstrap chicken-and-egg:
without it, `FileService.__init__()` can't know where to read
`settings.json` from. On first launch after this change, a one-shot
idempotent migration moves any existing `%TEMP%\PyTreeManager\
settings.json` into the new layout and writes the pointer. The
logger's `init_logging(<root>)` is called a second time after
`FileService` finishes loading, finally honoring ADR-006's relocation
promise. **Subsequent app launches see only the new layout.** The old
`%LOCALAPPDATA%\PyTreeManager\logs\` directory is left where it is
(historical; gets swept naturally by the existing 14-day
`cleanup_old_logs` sweep which already walks
`_localappdata_log_dir()` per `helpers/logger.py:502`).

## 3. Components

### 3.1 New runtime layout

```
<root>/                                 (user-chosen, persisted in pointer)
├── .PyTreeManager/                     (NEW — Phase A)
│   ├── settings.json                   (was %TEMP%\PyTreeManager\settings.json)
│   └── logs/
│       ├── 2026-05-11__journey.log
│       ├── 2026-05-11__exceptions.log
│       └── pending/
│           └── pending_email_<uuid>.json
├── Lista osób/                         (unchanged — created in set_root_folder)
├── Drzewo/                             (unchanged)
├── Rody/                               (unchanged)
└── Poczekalnia/                        (unchanged)

%LOCALAPPDATA%\PyTreeManager\
├── last_root.txt                       (NEW pointer — see §3.2)
└── logs\                               (LEGACY — left alone; aged out by cleanup_old_logs)
```

The `.PyTreeManager/` folder is dot-prefixed on purpose: it
de-emphasizes the folder in Windows Explorer (the user's tree is the
visual content, the infrastructure folder is plumbing).

### 3.2 Bootstrap pointer file

**Path**: `%LOCALAPPDATA%\PyTreeManager\last_root.txt`.

**Contents**: one UTF-8 line, the absolute path of the chosen root.

```
C:\<user-tree-root>
```

**Write semantics**: written every time `set_root_folder(path)` is
called successfully (after the existing
`(root_path / "Lista osób").mkdir(...)` block in
`services/file_service.py:120-123` succeeds). Trailing newline is
acceptable but not required; read path strips whitespace.

**Read semantics**: read-once at `FileService.__init__()`. If the
file does not exist OR cannot be read OR contains a path that no
longer exists on disk, treat as "no pointer" and fall through to
either migration (§3.4) or the first-run `select_folder` dialog.

**Why `%LOCALAPPDATA%` (not `%APPDATA%`, not `%TEMP%`)**:
- `%TEMP%` — volatile (the original problem; ruled out by definition).
- `%APPDATA%` (roaming) — overkill; this is a single-machine
  preference, not a profile-roamable setting. The user is two
  machines: dev and father's. They don't share a domain profile.
- `%LOCALAPPDATA%` — per-user, per-machine, survives reboots and
  `%TEMP%` cleaning. Already established for the logger's fallback
  path in `helpers/logger.py:62-67`, so the env-var unset edge case
  has prior art.

**Degraded mode** (env var unset): fall back to
`tempfile.gettempdir() / "PyTreeManager" / "last_root.txt"` AND emit
a CRITICAL log line about the degraded mode. This mirrors the
existing `_localappdata_log_dir()` defensive fallback at
`helpers/logger.py:64-67` — same pattern, same justification (a
machine with `%LOCALAPPDATA%` somehow unset is broken enough that
crash-clean-then-tell-the-user beats silent-data-loss).

### 3.3 Bootstrap sequence (load-bearing — Implementor must follow this exact order)

The bootstrap chicken-and-egg: to know WHERE to read settings, we
need the pointer; but the logger needs to be alive BEFORE the
pointer/settings layer in case anything in that layer throws. Solved
by initialising the logger TWICE — once defensively against
`%LOCALAPPDATA%`, then once authoritatively against the real root.

```
main.py
  └─> app = LoggingApp()           # subclasses wx.App
       └─> LoggingApp.OnInit()     # helpers/logger.py:595-611
            ├─ 1. init_logging(root_folder=None)
            │     → _active_log_dir = %LOCALAPPDATA%\PyTreeManager\logs
            │     (Catch-net: any exception in step 2-3 will log here.)
            │
            ├─ 2. cleanup_old_logs()
            │     (existing; sweeps both _active_log_dir AND
            │     _localappdata_log_dir — unchanged.)
            │
            ├─ 3. from frames.add_person_frame import AddPersonFrame
            │     frame = AddPersonFrame(None)
            │     └─ AddPersonFrame.__init__()
            │          └─> self._file_service = FileService()
            │               └─ FileService.__init__()
            │                    ├─ a. pointer = read_bootstrap_pointer()
            │                    ├─ b. if pointer exists AND <root>/.PyTreeManager/settings.json exists:
            │                    │       load settings from <root>/.PyTreeManager/settings.json
            │                    ├─ c. elif legacy %TEMP%/PyTreeManager/settings.json exists:
            │                    │       run one-shot migration (see §3.4)
            │                    │       then load from new location
            │                    └─ d. else:
            │                          fresh-install path — create default settings
            │                          in-memory; defer disk write until set_root_folder()
            │
            ├─ 4. if FileService loaded a root_folder_path successfully:
            │       init_logging(Path(root_folder_path))
            │       → _active_log_dir relocates to <root>/.PyTreeManager/logs
            │       → emits one INFO line: "Log dir relocated to <new>"
            │       (This is the call Sprint 11 promised but never wired.)
            │
            ├─ 5. frame.Show()
            │
            └─ 6. start_retry_timer(self)
                  (existing Sprint 12 email_helper wiring — unchanged.)
```

**Step 4 is the new wiring.** Without it, the logger continues to
write to `%LOCALAPPDATA%` and the consolidation only goes halfway.

**Subsequent `set_root_folder(new_path)` calls** (user changes root
via dialog):

```
FileService.set_root_folder(new_path)
  ├─ 1. existing checks + mkdir of Lista osób / Drzewo / Poczekalnia / Rody
  ├─ 2. NEW: (new_path / ".PyTreeManager").mkdir(exist_ok=True)
  ├─ 3. NEW: (new_path / ".PyTreeManager" / "logs").mkdir(exist_ok=True)
  ├─ 4. dump settings.json to <new_path>/.PyTreeManager/settings.json
  │       (replaces the existing %TEMP% write at file_service.py:125)
  ├─ 5. NEW: write_bootstrap_pointer(new_path)
  └─ 6. NEW: from helpers.logger import init_logging
             init_logging(Path(new_path))
             (relocates logger to <new_path>/.PyTreeManager/logs)
```

### 3.4 One-shot migration (idempotent)

Decision table — given the state on disk at app start, what does
`FileService.__init__()` do?

| Pointer exists | Legacy `%TEMP%/PyTreeManager/settings.json` exists | Action |
|:---:|:---:|---|
| yes | (don't care) | Pointer is authoritative. Load `<root>/.PyTreeManager/settings.json`. If that file is missing — treat as fresh-install on the recorded root (don't migrate; the pointer says we already migrated). |
| no | yes | **Migrate**: read legacy settings, extract `root_folder_path`, ensure `<root>/.PyTreeManager/` exists, `shutil.move(legacy, <root>/.PyTreeManager/settings.json)`, write pointer with `<root>`, delete legacy `%TEMP%/PyTreeManager/` folder if empty. |
| no | no | **Fresh install**. Create default in-memory settings; fall through to the existing first-run flow (`select_folder` dialog). When the user picks a root, `set_root_folder()` writes both the settings to the new location AND the pointer (per §3.3 subsequent-call flow). |
| yes, but pointer's path does not exist on disk | (don't care) | **Stale pointer**. Log one INFO line if the logger is up (it is, step 1 of bootstrap); treat as fresh install. The orphaned `<old-root>/.PyTreeManager/` is left in place (per §3.5). |

**Migration is idempotent**: running it on a machine that's already
migrated (pointer present) skips immediately. Running it twice on a
machine with no legacy settings is a no-op (the `elif` in §3.3 step
3c only fires when legacy exists).

**Migration uses `shutil.move`** (not `os.replace`) because the
legacy `%TEMP%` and the user's `<root>` may live on different
volumes (e.g., `C:\` and `D:\`). `os.replace` is documented as
working "on the same filesystem" only; `shutil.move` handles
cross-volume with a copy+delete fallback.

**Failure modes during migration**:
- Read legacy settings fails (corruption) → don't move anything;
  log ERROR via `log_error()`; fall through to fresh-install flow.
  The user will re-pick the root and a fresh settings file is
  created; the broken legacy stays in place for forensic recovery.
- `<root>/.PyTreeManager/` mkdir fails (permissions on the tree
  drive) → don't move; log ERROR; fall through to fresh-install.
- `shutil.move` itself fails → log ERROR; if the destination file
  exists (partial copy), don't try to recover automatically — the
  next launch will see legacy still in place and re-attempt. (See
  Halt-A in the implementation plan.)

### 3.5 Backward compatibility / cleanup policy

When the user resets to a different root (changes from
`C:\Tree-old` to `D:\Tree-new`):

- A new `D:\Tree-new\.PyTreeManager/` is created (per §3.3 set-root
  flow).
- The pointer is rewritten to point at `D:\Tree-new`.
- **`C:\Tree-old\.PyTreeManager/` is LEFT IN PLACE.** Orphaned but
  harmless. The user owns their tree drives; we don't garbage-
  collect their disks. If they want to free the space, they delete
  the `.PyTreeManager/` folder themselves.
- The old `%LOCALAPPDATA%\PyTreeManager\logs\*.log` files (legacy
  Sprint 11 location) are also left in place. They get swept by the
  existing 14-day `cleanup_old_logs` sweep — `helpers/logger.py:502`
  walks `_active_log_dir`, `_root_log_dir`, AND
  `_localappdata_log_dir()`. After the relocation in §3.3 step 4,
  `_active_log_dir` is the new location; `_localappdata_log_dir()`
  still returns the legacy location; so the sweep still catches
  them. **No code change needed for legacy log cleanup.**

What is NOT swept automatically:
- A `<old-root>/.PyTreeManager/logs/` from a previous root choice
  (if the user changed roots after this ADR ships). These will
  accumulate one folder per root the user ever picked. Document
  this explicitly; don't try to clean up. Sprint 13+ candidate if
  it becomes a real problem.
- A `<previous-root>/logs/` folder (Sprint 11-era location, never
  actually written to because of the OnInit bug — but defensively,
  if a future bug pointed `_active_log_dir` there, it would not be
  swept). Not a real risk; the line 451 change closes this off.

## 4. Code diff specifics

### 4.1 `helpers/logger.py` line 451

```diff
 def init_logging(root_folder: Optional[Path]) -> None:
     ...
     try:
         new_dir: Path
         if root_folder is None:
             new_dir = _localappdata_log_dir()
         else:
-            new_dir = Path(root_folder) / "logs"
+            new_dir = Path(root_folder) / ".PyTreeManager" / "logs"
```

That is the only change to `init_logging`. The docstring at lines
434-443 also references "`<root>/logs/`" — update to
"`<root>/.PyTreeManager/logs/`" in the same edit.

### 4.2 `services/file_service.py` `__init__`

The current body (lines 29-61) builds `temp_folder_for_manager_path`
unconditionally and writes settings there. Replace with the
pointer-driven bootstrap. Suggested shape (architect-level; final
LOC is Implementor's):

```python
def __init__(self) -> None:
    self.saved_drafts_locations = []

    # 1. Try the pointer.
    pointer_path = _bootstrap_pointer_path()  # %LOCALAPPDATA%\PyTreeManager\last_root.txt
    candidate_root: Optional[Path] = _read_bootstrap_pointer(pointer_path)

    # 2. If no pointer, check for legacy %TEMP% settings to migrate.
    if candidate_root is None:
        legacy_settings = Path(tempfile.gettempdir()) / "PyTreeManager" / "settings.json"
        if legacy_settings.exists():
            candidate_root = _migrate_from_legacy_temp(legacy_settings, pointer_path)
            # _migrate returns the root path on success, None on failure.

    # 3. Load settings from the new location, or fall through to fresh-install.
    if candidate_root is not None:
        new_settings_path = candidate_root / ".PyTreeManager" / "settings.json"
        if new_settings_path.exists():
            with open(new_settings_path, 'r', encoding='utf-8-sig') as f:
                self.settings = SettingsWrapper(json.load(f))
            self._settings_file_path = new_settings_path
        else:
            # Pointer pointed somewhere with no settings — treat as fresh-install.
            self.settings = SettingsWrapper(self._get_default_settings_json())
            self._settings_file_path = None  # set by set_root_folder
    else:
        # Fresh install — defer disk write until set_root_folder().
        self.settings = SettingsWrapper(self._get_default_settings_json())
        self._settings_file_path = None

    self._forbidden_locations: List[str] = [...]  # unchanged
```

`set_root_folder(path)` becomes:

```python
def set_root_folder(self, path: str) -> None:
    root_path = Path(path)
    if not root_path.exists():
        raise FileNotFoundError(...)  # unchanged

    self._set_root_folder(root_path)
    self._set_root_selected_flag(False)

    (root_path / "Lista osób").mkdir(exist_ok=True)
    (root_path / "Drzewo").mkdir(exist_ok=True)
    (root_path / "Poczekalnia").mkdir(exist_ok=True)
    (root_path / "Rody").mkdir(exist_ok=True)
    # NEW:
    (root_path / ".PyTreeManager").mkdir(exist_ok=True)
    (root_path / ".PyTreeManager" / "logs").mkdir(exist_ok=True)

    self._settings_file_path = root_path / ".PyTreeManager" / "settings.json"
    self._dump_json_data(self._settings_file_path, self.settings.to_dict())

    _write_bootstrap_pointer(_bootstrap_pointer_path(), root_path)

    # Relocate the logger to the new location.
    try:
        from helpers.logger import init_logging  # noqa: PLC0415 — deferred
        init_logging(root_path)
    except Exception:
        pass  # logger init must NEVER crash the app
```

Other `_dump_json_data(self.temp_folder_for_manager_path / 'settings.json', ...)`
call sites (lines 228, 267-268) need to change to use
`self._settings_file_path` instead. The `temp_folder_for_manager_path`
attribute can be removed entirely; the Implementor should grep for
all references first.

### 4.3 `helpers/logger.py` `LoggingApp.OnInit` — new step

```diff
 def OnInit(self) -> bool:
     init_logging(root_folder=None)
     cleanup_old_logs()
     from frames.add_person_frame import AddPersonFrame
     frame = AddPersonFrame(None)
+    # NEW Sprint 13 Phase A — relocate logger to <root>/.PyTreeManager/logs
+    # after FileService has loaded the root from the pointer/settings.
+    try:
+        fs = getattr(frame, "_file_service", None)
+        if fs is not None and fs.is_root_location_set():
+            root_str = fs._get_root_folder()
+            if root_str:
+                init_logging(Path(root_str))
+    except Exception:
+        pass  # logger init must NEVER crash the app
     frame.Show()
     ...
```

`init_logging` is idempotent (it checks `new_dir == _active_log_dir`
at line 453), so a no-op re-call is safe.

### 4.4 New helpers (suggested placement: top of `services/file_service.py`)

```python
def _bootstrap_pointer_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "PyTreeManager" / "last_root.txt"
    # Degraded mode: %LOCALAPPDATA% unset. Mirror _localappdata_log_dir's fallback.
    # The CRITICAL log will be emitted by the caller when the env var is missing.
    return Path(tempfile.gettempdir()) / "PyTreeManager" / "last_root.txt"


def _read_bootstrap_pointer(pointer_path: Path) -> Optional[Path]:
    """Return the root path from the pointer, or None if absent/invalid/stale."""
    if not pointer_path.exists():
        return None
    try:
        content = pointer_path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not content:
        return None
    candidate = Path(content)
    if not candidate.exists():
        # Stale pointer (root moved/deleted). Treat as no pointer.
        return None
    return candidate


def _write_bootstrap_pointer(pointer_path: Path, root_path: Path) -> None:
    """Write the absolute root path to the pointer file. Idempotent overwrite."""
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(str(root_path), encoding="utf-8")


def _migrate_from_legacy_temp(
    legacy_settings_path: Path,
    pointer_path: Path,
) -> Optional[Path]:
    """One-shot migration of %TEMP%/PyTreeManager/settings.json into <root>/.PyTreeManager/.

    Returns the root path on success, None on failure (caller falls through to fresh-install).
    """
    try:
        with open(legacy_settings_path, 'r', encoding='utf-8-sig') as f:
            legacy = json.load(f)
        root_str = legacy.get(SettingsDataProperty.ROOT_FOLDER_PATH.value, "")
        if not root_str:
            return None
        root_path = Path(root_str)
        if not root_path.exists():
            return None

        new_dir = root_path / ".PyTreeManager"
        new_dir.mkdir(parents=True, exist_ok=True)
        new_settings_path = new_dir / "settings.json"

        # shutil.move handles cross-volume; os.replace would not.
        import shutil
        shutil.move(str(legacy_settings_path), str(new_settings_path))

        _write_bootstrap_pointer(pointer_path, root_path)

        # Best-effort: remove the now-empty %TEMP%/PyTreeManager/ folder.
        legacy_dir = legacy_settings_path.parent
        try:
            # Only rmdir if empty; don't recurse-delete in case the user has
            # legacy drafts there from before Sprint 07.
            if not any(legacy_dir.iterdir()):
                legacy_dir.rmdir()
        except OSError:
            pass

        return root_path
    except Exception:
        # Don't surface to user; the next launch will retry, and the legacy
        # settings remain in place for forensic recovery.
        return None
```

## 5. Worked example — bootstrap on a live machine

Trace from the user's actual machine state on 2026-05-11, assuming
the user's `C:\<user-tree-root>` is the live root and the legacy
`%TEMP%\PyTreeManager\settings.json` contains 10 cached_people +
`drzewo_root_uuid = 4a91101e-...`. The user has NOT yet run the new
code.

**Pre-state**:
```
%TEMP%\PyTreeManager\settings.json    (legacy, with cached_people)
%LOCALAPPDATA%\PyTreeManager\logs\    (old logs from prior runs)
%LOCALAPPDATA%\PyTreeManager\last_root.txt   (does NOT exist)
C:\<user-tree-root>\Lista osób\...         (existing)
C:\<user-tree-root>\Drzewo\...             (existing)
C:\<user-tree-root>\.PyTreeManager\        (does NOT exist)
```

**First launch with new code**:

1. `main.py` → `LoggingApp.OnInit()`.
2. `init_logging(None)` → `_active_log_dir = %LOCALAPPDATA%\PyTreeManager\logs`.
3. `cleanup_old_logs()` — sweeps `_active_log_dir` and
   `_localappdata_log_dir()` (same dir; deduped per
   `helpers/logger.py:500-505`).
4. `AddPersonFrame(None)` → `FileService()`.
5. `FileService.__init__()`:
   - `pointer = _read_bootstrap_pointer(%LOCALAPPDATA%\PyTreeManager\last_root.txt)`
     → returns `None` (file doesn't exist).
   - Check `legacy = %TEMP%\PyTreeManager\settings.json` → **exists**.
   - Call `_migrate_from_legacy_temp(legacy, pointer_path)`:
     - Read legacy → `root_folder_path = "C:\\Sorted tree"` + cached_people.
     - `Path("C:\\Sorted tree").exists()` → True.
     - `mkdir C:\<user-tree-root>\.PyTreeManager` (new).
     - `shutil.move(legacy, C:\<user-tree-root>\.PyTreeManager\settings.json)`.
       → Settings now at new location WITH all 10 cached_people preserved.
     - `_write_bootstrap_pointer(pointer_path, Path("C:\\Sorted tree"))`.
       → `%LOCALAPPDATA%\PyTreeManager\last_root.txt` now contains
       `C:\<user-tree-root>`.
     - `%TEMP%\PyTreeManager\` is now empty → `rmdir`.
   - Returns `Path("C:\\Sorted tree")`.
   - `new_settings_path = C:\<user-tree-root>\.PyTreeManager\settings.json`
     → exists (just moved there).
   - Load settings → SettingsWrapper holds 10 cached_people +
     drzewo_root_uuid.
6. Back in `OnInit`, after `AddPersonFrame(None)` returns:
   - `fs.is_root_location_set()` → True.
   - `fs._get_root_folder()` → `"C:\\Sorted tree"`.
   - `init_logging(Path("C:\\Sorted tree"))`.
     - `new_dir = Path("C:\\Sorted tree") / ".PyTreeManager" / "logs"`
       per the line 451 diff.
     - `new_dir != _active_log_dir` (which is `%LOCALAPPDATA%\...`) →
       relocate.
     - mkdir `C:\<user-tree-root>\.PyTreeManager\logs` (new).
     - Emit `[2026-05-11 HH:MM:SS] [INFO] [Person: -] Log dir
       relocated to C:\<user-tree-root>\.PyTreeManager\logs` to the new
       journey log.
7. `frame.Show()`. UI appears with the cached_people list populated
   exactly as before the upgrade.

**Post-state**:
```
%TEMP%\PyTreeManager\               (DELETED — empty after move)
%LOCALAPPDATA%\PyTreeManager\last_root.txt   → "C:\<user-tree-root>"
%LOCALAPPDATA%\PyTreeManager\logs\           (LEFT — old logs, swept by 14d cleanup)
C:\<user-tree-root>\.PyTreeManager\settings.json  (10 cached_people preserved)
C:\<user-tree-root>\.PyTreeManager\logs\2026-05-11__journey.log
                                              (NEW — contains the "relocated" line)
```

**Second launch** (the very next time, no further user action):
1. `init_logging(None)` → `_active_log_dir = %LOCALAPPDATA%\...`.
2. `cleanup_old_logs()` — sweeps as before.
3. `FileService.__init__()`:
   - Pointer **exists**, content `"C:\<user-tree-root>"`.
   - `<root>/.PyTreeManager/settings.json` **exists**.
   - Load directly. No migration. Idempotent.
4. `init_logging(Path("C:\\Sorted tree"))` → relocates again.
   Journey log appends a "Log dir relocated" line.
5. Everything else as before.

**Parity check between this example and the §3.3 pseudocode**:
trace 3 lines.
- Example step 5 "pointer = None, legacy exists" → §3.4 row 2
  (action: Migrate). MATCHES.
- Example step 6 calls `init_logging(Path("C:\\Sorted tree"))` →
  §3.3 step 4 ("if FileService loaded a root_folder_path
  successfully, init_logging(Path(root_folder_path))"). MATCHES.
- Example step 7 cached_people populated → §3.4 migration table
  ("read legacy settings, ... move ... into it"). The cached_people
  travel inside the moved JSON file. MATCHES.

## 6. Alternatives considered

### 6.1 `PyTreeManager/` (no dot prefix)

- **Pro**: more discoverable to a Windows user who is browsing the
  tree manually; "what is this folder?" answers itself.
- **Con**: user explicitly rejected in chat — wants the
  infrastructure folder visually de-emphasized; the tree is the
  content.
- **Decided**: rejected per user lock.

### 6.2 `_PyTreeManager/` (underscore prefix)

- **Pro**: same de-emphasis intent as dot-prefix; works on platforms
  where the dot-prefix Explorer-hide convention isn't honored.
- **Con**: dot-prefix is the cross-platform convention (`.git/`,
  `.vscode/`, `.idea/`, `.pipeline/` literally in this very repo);
  user picked it from the preview.
- **Decided**: rejected per user lock.

### 6.3 Pointer at `%APPDATA%` (roaming) instead of `%LOCALAPPDATA%`

- **Pro**: if Tomasz ever sets up a domain-roaming profile shared
  with father, the pointer roams.
- **Con**: not the deployment model. Two machines, no domain
  profile, no cross-machine root path (Tomasz's dev tree at
  `C:\Repositories\...`, father's tree at his own `C:\...`).
  Roaming the pointer would do active harm.
- **Decided**: rejected.

### 6.4 No pointer — auto-detect by walking common locations

- **Pro**: zero external state.
- **Con**: brittle. "Walk common locations" is `Desktop`, `Documents`,
  `C:\`, every external drive... and even then we might match a
  folder that has a `me.json` somewhere by coincidence. Worse, a
  user with two trees (one historical, one current) gets ambiguity.
- **Decided**: rejected. The pointer is one line of text; the cost
  of a tiny external file is far less than the cost of the wrong
  inference.

### 6.5 Pointer inside `<root>/.PyTreeManager/` only — no `%LOCALAPPDATA%` file

- **Pro**: zero external state (variant of 6.4).
- **Con**: chicken-and-egg. You can't know which `<root>` to look in
  without the pointer.
- **Decided**: rejected.

### 6.6 Migrate `%LOCALAPPDATA%\PyTreeManager\logs\` too (not just settings)

- **Pro**: clean break — no orphan logs.
- **Con**: those logs are historical; the user may want to grep
  them for past errors. The 14-day `cleanup_old_logs` sweep
  already handles their natural expiry. Moving them adds risk
  (cross-volume, file-locks-on-active-handles) for no real gain.
- **Decided**: rejected. Leave old logs in place.

## 7. Tests

### 7.1 Existing tests that need fixture updates

- **`tests/conftest.py` `tmp_root` fixture** — must be updated so
  that after `set_root_folder()`, the test asserts settings live
  at `<root>/.PyTreeManager/settings.json` (not `%TEMP%`). The
  existing `monkeypatch.setattr(_tempfile, "gettempdir", ...)`
  redirect can stay (still used for the pointer's degraded-mode
  fallback path; harmless if the new code reads `%LOCALAPPDATA%`
  via `os.environ`). Add a `monkeypatch.setenv("LOCALAPPDATA",
  str(tmp_path / "appdata"))` so the pointer file goes into a
  per-test scratch space and never touches the real user's
  `%LOCALAPPDATA%`.

- **`tests/services/test_file_service.py` `_make_fs` /
  `_make_rooted_fs` helpers** — analogous monkeypatch of
  `LOCALAPPDATA`. The existing `_tempfile.gettempdir` monkeypatch
  is no longer load-bearing for the settings location but is still
  needed for the degraded-fallback test (§7.2 below).

- Any test that asserts `temp_folder_for_manager_path` directly
  needs to retarget. (Grep: there is one
  `self.temp_folder_for_manager_path` reference inside
  `FileService.scan_root_location` at line 228 and two in
  `set_drzewo_root_uuid` / lines around 267-268; tests don't
  appear to assert this attribute directly, so the surface
  change is internal — confirm with grep before edit.)

### 7.2 New tests (in `tests/services/test_data_consolidation_migration.py`)

| # | Test name | Asserts |
|---|---|---|
| T1 | `test_migration_runs_when_pointer_absent_and_legacy_settings_present` | Pre: write a legacy `%TEMP%/PyTreeManager/settings.json` with `root_folder_path = tmp_root`. Post `FileService()`: `<tmp_root>/.PyTreeManager/settings.json` exists; pointer file contains `tmp_root`; legacy `%TEMP%` dir is gone or empty; settings dict survived. |
| T2 | `test_migration_preserves_cached_people` | Same setup as T1 but legacy settings have 10 entries in `cached_people`. Post: new settings have all 10 entries with identical UUIDs and locations. |
| T3 | `test_migration_idempotent_on_second_call` | Run T1, then run `FileService()` again. Assert no exception; same final state; the legacy `%TEMP%` is NOT recreated. |
| T4 | `test_pointer_authoritative_when_present` | Pre: write pointer + new-layout settings; ALSO write legacy `%TEMP%` settings with a DIFFERENT `root_folder_path`. Post: settings loaded reflect the pointer's location, not the legacy. Legacy is left alone (not auto-cleaned in this case — only the no-pointer migration cleans). |
| T5 | `test_stale_pointer_falls_through_to_fresh_install` | Pre: write pointer pointing at `C:\does\not\exist\anywhere\xyz`. Post: `is_root_location_set()` returns False; no crash. |
| T6 | `test_fresh_install_no_pointer_no_legacy` | Pre: nothing. Post: `is_root_location_set()` returns False; no settings file created on disk yet (deferred to `set_root_folder()`). |
| T7 | `test_set_root_folder_writes_pointer_and_relocates_settings` | Post `set_root_folder(tmp_root)`: pointer file contains `tmp_root`; `<tmp_root>/.PyTreeManager/settings.json` exists; `<tmp_root>/.PyTreeManager/logs/` dir exists. |
| T8 | `test_set_root_folder_called_twice_rewrites_pointer` | Call `set_root_folder(rootA)`, then `set_root_folder(rootB)`. Assert pointer now contains `rootB`; `rootA/.PyTreeManager/` still exists (orphan policy §3.5); `rootB/.PyTreeManager/settings.json` exists. |
| T9 | `test_migration_failure_falls_through_cleanly` | Pre: legacy settings JSON is corrupt (bad JSON). Post: no crash; no migration; legacy stays in place; `is_root_location_set()` returns False. (Test the failure-mode contract in §3.4.) |
| T10 | `test_localappdata_unset_falls_back_to_tempdir` | Monkeypatch `os.environ` to delete `LOCALAPPDATA`. Post `FileService()`: pointer reads/writes go to `tempfile.gettempdir() / "PyTreeManager" / "last_root.txt"`. (Degraded-mode contract §3.2.) |

### 7.3 New tests in `tests/helpers/test_logger.py`

| # | Test name | Asserts |
|---|---|---|
| L1 | `test_init_logging_with_root_uses_pytreemanager_subpath` | Call `init_logging(Path(tmp_path))`. Assert `_active_log_dir == tmp_path / ".PyTreeManager" / "logs"`. (Pins the line 451 change.) |
| L2 | `test_init_logging_idempotent_on_same_root` | Call `init_logging(Path(tmp_path))` twice. Assert no new "Log dir relocated" line on the second call. (Existing behavior; pins it for the new subpath.) |
| L3 | `test_init_logging_relocates_after_none_then_real_root` | Call `init_logging(None)`; emit one INFO line; call `init_logging(Path(tmp_path))`; emit another INFO line. Assert first line is in `%LOCALAPPDATA%\...` (or wherever fallback resolves), second is in `tmp_path/.PyTreeManager/logs/`. |

### 7.4 Tests deliberately NOT in scope

- L1 integration test (full `wx.App.MainLoop()` driven) — same
  reason as Sprint 11/12 (no headless wx fixture). Live-data smoke
  in the implementation plan covers this.
- Test against the user's real `%LOCALAPPDATA%` (without
  monkeypatch). The implementor's live-data smoke is the only
  place we touch the real env var.

## 8. Risks (Implementor's halt criteria reference)

Halt criteria are in the implementation plan (`sprint-13/architect-
implementation-plan.md`). Summarized here for ADR completeness:

- **R1 — migration loses cached_people**. Halt-A. User's live
  settings have 10 entries; losing them re-triggers a full re-scan
  and possibly a re-pick of the Drzewo root.
- **R2 — logger relocation breaks the 136-test baseline**. Halt-B.
  Some tests may have implicit assumptions about `<root>/logs/`
  via the `tmp_root` fixture.
- **R3 — `%LOCALAPPDATA%` env var unset on father's machine**.
  Halt-C. Defensive fallback per §3.2 + L10 test.
- **R4 — bootstrap order issue (FileService throws before
  `init_logging(real_root)` can fire)**. Halt-D. The
  `%LOCALAPPDATA%` fallback log still receives the failure; the
  app crashes cleanly per ADR-006 prime directive.

## 9. Decision-tree summary

```
At app start:
├─ %LOCALAPPDATA%\PyTreeManager\last_root.txt exists?
│  ├─ yes → read root from pointer
│  │       ├─ root dir exists?
│  │       │  ├─ yes → load <root>/.PyTreeManager/settings.json
│  │       │  │       ├─ exists? → use it (NORMAL PATH)
│  │       │  │       └─ no → fresh in-memory settings (rare; pointer-without-settings edge case)
│  │       │  └─ no → STALE POINTER; treat as fresh install
│  └─ no → check %TEMP%\PyTreeManager\settings.json
│         ├─ exists → MIGRATE (one-shot)
│         └─ no → FRESH INSTALL (select_folder dialog)
```

## 10. Sources

- `services/file_service.py:38-50` (current `%TEMP%` bootstrap)
- `services/file_service.py:98-125` (current `set_root_folder`)
- `services/file_service.py:228, 267-268` (other settings-write
  call sites that need to retarget)
- `helpers/logger.py:62-67` (`_localappdata_log_dir` fallback pattern)
- `helpers/logger.py:434-461` (`init_logging` body + docstring)
- `helpers/logger.py:451` (the hardcoded `"logs"` subpath being changed)
- `helpers/logger.py:498-525` (`cleanup_old_logs` — confirms legacy
  `%LOCALAPPDATA%` logs get swept naturally; no code change needed)
- `helpers/logger.py:596` (`OnInit` — the missing second
  `init_logging` call)
- ADR-006 §3.2 (logger-relocation contract)
- ADR-008 §3.1 (pending-queue path; relocates implicitly via
  `_active_log_dir`)
- PRD-007 (Sprint 13 umbrella — Phase A carved out today,
  2026-05-11)
- `.pipeline/JOURNAL.md` 2026-05-11 (architect dispatch entry —
  user-locked decisions captured below in JOURNAL append)
- https://docs.python.org/3/library/shutil.html#shutil.move
  (cross-volume move semantics)
- https://docs.python.org/3/library/os.html (LOCALAPPDATA env var
  convention)

## 11. Self-critique

See `critiques/C-039-architect-sprint-13-phase-a.md`.
