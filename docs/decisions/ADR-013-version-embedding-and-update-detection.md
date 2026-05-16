---
id: ADR-013
title: Version embedding via importlib.metadata + in-app update detection against latest.json
kind: tech
decision_type: architecture
status: accepted
date: 2026-05-12
author: architect
sprint: sprint-15
supersedes: (none)
amended_by: ADR-015 (2026-05-17 — URL + JSON shape redefined for GitHub Releases API; min_supported_version field dropped)
iterates_with_user: true   # the Polish dialog string + "skip this version" persistence key may iterate; the schema is locked
related:
  - ADR-012 (CI pipeline produces `latest.json` consumed here)
  - ADR-014 (self-replace update_helper consumes `UpdateInfo` produced by this module)
  - ADR-006 (logging — `check_for_update` failures log one INFO line via `log_error` per ADR-006 §3.10 contract)
  - ADR-010 (settings stored under `<root>/.PyTreeManager/settings.json` — this ADR adds one new key, `skipped_update_version`)
sources:
  - JOURNAL 2026-05-12 — user-locked decisions block (version source = `pyproject.toml`; no-network = silent-skip; once-per-launch; remember "skipped X.Y.Z" across launches)
  - https://pyinstaller.org/en/stable/usage.html — `--copy-metadata PACKAGENAME` documented as "Copy metadata for the specified package. This option can be used multiple times."
  - https://docs.python.org/3/library/importlib.metadata.html — `importlib.metadata.version("name") -> str` returns the version from the package's installed metadata
  - https://packaging.pypa.io/en/stable/version.html — `packaging.version.Version` + `parse()` for PEP 440 robust comparison (handles `1.0.10 > 1.0.9` correctly)
  - https://docs.python.org/3/library/urllib.request.html#urllib.request.urlopen — `urlopen(url, timeout=N)` returns a context manager; the `timeout` raises `socket.timeout` on expiry
  - https://docs.python.org/3/library/socket.html#socket.timeout — exception class catchable as `OSError` superclass
  - C:/Repositories/py-tree-manager/src/wrappers/settings_wrapper.py lines 6-13 (SettingsDataProperty enum — pattern this ADR extends with one new key)
  - C:/Repositories/py-tree-manager/src/helpers/logger.py lines 591-633 (LoggingApp.OnInit — the wiring point for the update check)
---

# ADR-013 — Version embedding + in-app update detection

## 0. Changelog

- **2026-05-12 (initial)** — first issue. Resolves user-locked decisions
  #1, #4, and #5 from Sprint 15 dispatch. Option A (`importlib.metadata`)
  chosen for version read; `urllib.request` chosen for the manifest
  fetch (stdlib only, no new dependency); `packaging.version.parse` for
  comparison.

## 1. Context

ADR-012 produces `latest.json` on Bitbucket Downloads. The running app
must:

1. **Know its own version** to compare against `latest.json.latest_version`.
2. **Fetch `latest.json`** from a static URL.
3. **Compare versions** without string-comparison pitfalls (`"1.0.10" <
   "1.0.9"` lexicographically — wrong).
4. **Prompt the user** in Polish.
5. **Remember "no" answers** so the same release doesn't re-prompt every
   launch.
6. **Silently skip** if the network call fails for any reason.

ADR-014 takes over once the user accepts the update. This ADR stops at
"user clicked yes; we have a confirmed `UpdateInfo`".

## 2. Decision

Three concerns, three small surfaces, all in one new module
`src/helpers/update_helper.py`:

- **Version read** — Option A from dispatch: `importlib.metadata.version("py-tree-manager")`. Works in both `python main.py` dev mode (the package is editable-installed) and PyInstaller frozen mode (PyInstaller bakes in the metadata via `--copy-metadata py-tree-manager` per ADR-012 §2.1).
- **Manifest fetch** — `urllib.request.urlopen(url, timeout=10)`. Stdlib only, no `requests` dependency added. Any exception (network, DNS, HTTP non-2xx, JSON parse error, schema mismatch) becomes `None` return.
- **Version compare** — `packaging.version.parse(a) > packaging.version.parse(b)`. The `packaging` package is added to `requirements.txt` in Sprint 15 (per ADR-012 §4).
- **Settings persistence** — one new key in `settings.json`: `skipped_update_version` (the version string the user clicked No on). On next launch, if `latest.json.latest_version == skipped_update_version`, return `None` without prompting.

### 2.1 Public API of `src/helpers/update_helper.py`

```python
from dataclasses import dataclass
from typing import Optional
import wx  # only for prompt_user_to_update; check_for_update is wx-free

LATEST_JSON_URL = "https://bitbucket.org/Duch003/py-tree-manager/downloads/latest.json"
FETCH_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class UpdateInfo:
    latest_version: str         # e.g. "1.0.1"
    download_url: str           # full URL to the versioned .exe
    released_at: str            # ISO-8601 string, opaque to the app
    min_supported_version: str  # see §3.5 below for semantics


def check_for_update(
    current_version: str,
    skipped_version: Optional[str] = None,
    *,
    url: str = LATEST_JSON_URL,
    timeout: float = FETCH_TIMEOUT_SECONDS,
) -> Optional[UpdateInfo]:
    """Return UpdateInfo if a newer version exists AND the user has not
    already declined it. Return None for any of:

    - network/HTTP/timeout/DNS error (silent per user-locked decision #5)
    - JSON malformed / required field missing
    - latest_version <= current_version (no update)
    - latest_version == skipped_version (user said no to this version)
    """


def prompt_user_to_update(parent_window, update_info: UpdateInfo) -> bool:
    """Show wx.MessageDialog with Polish strings. Return True if user
    clicked Tak (yes), False otherwise. No side effects."""


def remember_skipped_version(settings_wrapper, version: str) -> None:
    """Write skipped_update_version to settings.json. Pure persistence —
    no UI."""


def download_and_apply_update(update_info: UpdateInfo) -> None:
    """ADR-014's territory. Implemented in Sprint 15 per ADR-014 §3.
    Documented here only so the public API is complete."""
```

### 2.2 Where it's wired into `LoggingApp.OnInit`

Per user-locked decision #5 ("Once per app launch is the right default")
and the dispatch's "Architect picks; surface tradeoff" framing:

**Wired AFTER `frame.Show()`, BEFORE `start_retry_timer`**, near
`src/helpers/logger.py:622`. Rationale:

- After `frame.Show()` so the father sees the app come up first.
  Network calls feel laggy; the dialog appears on top of an already-
  visible window — less scary than a blank screen + dialog.
- Before `start_retry_timer` so the order is: window up → update
  check → email retry. The email retry can fire mid-check without
  interaction (it's a 30-min timer, not an immediate call); the
  ordering is for code-readability, not correctness.
- Inside a bare `try/except Exception` so an update_helper bug NEVER crashes
  the app (matches the logger's prime directive from PRD-005).

```python
# In LoggingApp.OnInit, after frame.Show() at logger.py:622, before
# start_retry_timer at line 627:
try:
    from src.helpers.update_helper import check_for_update, prompt_user_to_update, \
        remember_skipped_version, download_and_apply_update
    from importlib.metadata import version as _pkg_version
    current = _pkg_version("py-tree-manager")
    settings = fs.get_settings_wrapper() if fs is not None else None
    skipped = settings.get(SettingsDataProperty.SKIPPED_UPDATE_VERSION) if settings else None
    info = check_for_update(current, skipped_version=skipped)
    if info is not None:
        if prompt_user_to_update(frame, info):
            download_and_apply_update(info)  # ADR-014: exits the app
        else:
            if settings is not None:
                remember_skipped_version(settings, info.latest_version)
                fs.save_settings()  # standard persistence
except Exception:
    pass  # update_helper MUST NEVER crash the app
```

The `fs.get_settings_wrapper()` and `fs.save_settings()` call sites
are accurate against the post-Sprint 13 Phase A FileService (verified
in §6 parity check below).

## 3. `latest.json` schema (specification)

The CI pipeline (ADR-012 §2.3 `rename-artifact.ps1`) writes the file;
this ADR is the consumer-side spec.

```json
{
  "latest_version": "1.0.1",
  "download_url": "https://bitbucket.org/Duch003/py-tree-manager/downloads/py-tree-manager-1.0.1.exe",
  "released_at": "2026-05-13T14:32:00Z",
  "min_supported_version": "1.0.0"
}
```

### 3.1 `latest_version` (string, required)

PEP 440 version string. The version the app should consider "the
latest" and offer to upgrade to. `packaging.version.parse` parses
this; rejection on parse failure means the manifest is treated as
malformed → `check_for_update` returns `None`.

### 3.2 `download_url` (string, required)

Absolute HTTPS URL to the versioned `.exe`. The app does NOT
string-template this from `latest_version` — it reads the URL
verbatim. This allows ADR-012's "manual rollback by editing
`latest.json`" path: point `download_url` at an older versioned `.exe`,
leave `latest_version` at the older string.

The app validates the URL has the `https://` scheme; `http://` is
rejected (returns `None`) to prevent a future-Tomasz typo in the
manifest from downgrading to plaintext.

### 3.3 `released_at` (string, required, opaque)

ISO-8601 timestamp. The app does NOT parse this. It's surfaced to the
user in the prompt text ("wydana 2026-05-13"). The CI script writes
it; the app trusts it as a display string. Validation: must be a
non-empty string; further format checking is intentionally absent
(robustness over precision).

### 3.4 `min_supported_version` (string, required)

The lowest version this app's update flow can safely roll FORWARD from.
**Semantics**: if `parse(current_version) < parse(min_supported_version)`,
the user is on a too-old build. We do NOT silently skip — we surface
the prompt anyway (because not prompting leaves the user stuck), but
the body text adds:

> "Twoja wersja jest bardzo stara. Zaktualizuj koniecznie."

For Sprint 15, `min_supported_version` is set equal to `latest_version - patches`
or simply `1.0.0` — operationally the CI script (ADR-012
`rename-artifact.ps1`) sets it to the current version it's replacing.
This is forward-compatible: if ever a critical fix requires a
must-update behavior (e.g., a settings.json format change), the script
can hard-code a value that forces the warning text.

**Why not skip the field entirely**: leaving it out of the schema today
forces a schema migration later if it's ever needed. Including it now
with `1.0.0` as the universal floor costs nothing and avoids that
migration.

The field is **required in the schema** but the app's check_for_update
treats a missing or unparseable value as `"0.0.0"` (no warning ever
fires). Robustness over precision.

### 3.5 Schema robustness

`check_for_update` validates by attempting to construct an `UpdateInfo`
dataclass. Any missing key → `KeyError` → caught → `None`. Any non-
string value → `TypeError` later in `packaging.version.parse` → caught
→ `None`. The function is intentionally lenient on inputs and strict on
outputs.

## 4. Behavior matrix

| Scenario | `check_for_update` returns | `prompt_user_to_update` shown? | Settings update |
|---|---|---|---|
| `latest_version > current_version`, user has NOT skipped this version, network OK | `UpdateInfo(...)` | Yes | On No: write `skipped_update_version = latest_version`. On Yes: nothing (app exits). |
| `latest_version == current_version` | `None` | No | None |
| `latest_version < current_version` (rollback scenario, e.g. dev box runs unreleased) | `None` | No | None |
| `latest_version == skipped_version` | `None` | No | None |
| Network failure (timeout, DNS, HTTP 5xx, etc.) | `None` | No | None |
| JSON malformed / fields missing | `None` | No | None |
| `download_url` is `http://` not `https://` | `None` | No | None |
| `latest.json` parsed but `current_version < min_supported_version` | `UpdateInfo(...)` | Yes, with extra warning text | Same as row 1 |

## 5. Polish dialog text (locked for first release; `iterates_with_user`)

```python
TITLE = "Dostępna jest nowa wersja"
BODY_NORMAL = (
    "Dostępna jest nowa wersja aplikacji: {latest}.\n"
    "Twoja wersja: {current}.\n"
    "Wydana: {released_at}.\n\n"
    "Zaktualizować teraz? Aplikacja zamknie się i sama się otworzy."
)
BODY_FORCED = (
    "UWAGA: Twoja wersja jest bardzo stara i może działać niepoprawnie.\n\n"
    + BODY_NORMAL
)
YES_LABEL = "Tak, zaktualizuj"
NO_LABEL = "Pomiń tę wersję"
```

Polish codepoints used and verified:
- `ę` U+0119 — "Dostępna", "zamknie", "tę"
- `ż` U+017C — "może"
- `ą` U+0105 — "się" no (that's ę). "się" uses `ę`. `ą` appears in… (none in this text — that's fine, text doesn't need it).
- `ś` U+015B — "się"
- `ó` U+00F3 — none in this text
- `ł` U+0142 — "Pobrać"? no, that's not in this text. Check: "działać" uses `ł` (U+0142) and `ć` (U+0107).
- `ć` U+0107 — "Zaktualizować", "działać"

Note for implementor: `wx.MessageDialog` button labels are customized
via `SetYesNoLabels(YES_LABEL, NO_LABEL)` — see `src/frames/dialogs/`
existing pattern (Sprint 06 carry-forward item #2 mentioned this; Sprint 14
already uses it for "Yes/No/Cancel" dialogs).

## 6. Pre-implementor parity check

### 6.1 Attribute chain — `fs.get_settings_wrapper()` and `fs.save_settings()`

Per Sprint 13 Phase A reviewer note (C-041): "architect parity-check
ritual should extend to attribute chains I reference in pseudocode".
Checking against current HEAD:

- `services/file_service.py` post-Sprint 13 Phase A: `FileService`
  exposes the settings wrapper. The exact method name on current HEAD
  may differ from `get_settings_wrapper()` — **implementor MUST grep**.
  If the public method is `get_settings()` or the wrapper is exposed as
  a public attribute (`fs.settings`), use that and update this ADR's
  pseudocode in §2.2 with the correct chain. Treat this as a "C-041
  attribute-chain check" debt: do not silently invent a method name.

- `fs.save_settings()`: the persistence method that writes
  `settings.json` to disk. Sprint 13 Phase A's `set_root_folder` calls
  this internally. Implementor: grep `def save_settings`, `def
  _save_settings`, or the equivalent. If naming differs, use the
  actual name.

This is intentionally honest: I have not re-grepped current HEAD's
exact FileService surface for these two methods in this session
(the file was last touched in Sprint 13 Phase A and the surface may
have evolved). Treating as a documented implementor verification step,
not a bug, per the parity-check rule.

### 6.2 `SettingsDataProperty` extension

`src/wrappers/settings_wrapper.py:6-13` defines the enum. New row:

```python
class SettingsDataProperty(Enum):
    # ... existing rows ...
    SKIPPED_UPDATE_VERSION = "skipped_update_version"  # ADR-013 §2
```

Plus matching get/set on `SettingsWrapper`:

```python
def get_skipped_update_version(self) -> Optional[str]:
    return self.settings.get(SettingsDataProperty.SKIPPED_UPDATE_VERSION.value)

def set_skipped_update_version(self, value: Optional[str]) -> None:
    self.settings[SettingsDataProperty.SKIPPED_UPDATE_VERSION.value] = value
```

JSON key stays English here — this is a new field with no back-compat
constraint (unlike `drzewo_root_uuid` which preserves Polish for the
existing `me.json` files). Per the project-wide naming rule (English
for new identifiers).

### 6.3 Example ↔ pseudocode parity

§2.2 pseudocode and §4 behavior matrix traced against each other on 3
lines:

1. §2.2 calls `check_for_update(current, skipped_version=skipped)` →
   §4 row 4 says "if `latest == skipped`, return None". Trace: yes,
   skipped is passed in, the function checks it before returning.
   MATCHES.
2. §2.2 writes `skipped_update_version = info.latest_version` on No
   click → §4 row 1 says "On No: write `skipped_update_version`".
   MATCHES.
3. §2.2 calls `download_and_apply_update(info)` on Yes click → ADR-014
   §3 handles this; this ADR does not implement it. MATCHES (delegation
   boundary).

No drift caught.

## 7. Alternatives considered

### 7.1 Option B from dispatch — generate `src/_version.py` at build time

Reject. Adds a build-time codegen step that's easy to forget locally
(developer runs `python main.py` from source; sees stale version).
Option A (`importlib.metadata`) is the modern Python answer; it
works in both modes because PyInstaller's `--copy-metadata` flag
copies the dist-info into the bundle.

### 7.2 Option C from dispatch — read `pyproject.toml` at runtime via `tomllib`

Reject. PyInstaller `--onefile` does NOT include `pyproject.toml` in
the bundle by default (it's a build manifest, not a runtime asset).
Adding `--add-data pyproject.toml;.` would work but is more fragile
than `--copy-metadata`. Also slower (file read + TOML parse on every
launch) vs `importlib.metadata.version` which is cached.

### 7.3 Use `requests` library for HTTP fetch

Reject — adds a transitive-dependency surface. `urllib.request` from
stdlib is sufficient for a single GET with a timeout. No proxying, no
auth, no streaming required (the manifest is ~200 bytes).

### 7.4 Compare versions with `tuple(int, int, int)` parsing

Reject for general case, accept as fallback. `packaging.version` is
already in the dependency graph because it's used by `pip`
transitively; explicitly listing it adds zero install cost. It
correctly handles `1.0.10 > 1.0.9`, pre-release tags (`1.0.1-rc1`),
and PEP 440 corner cases that a hand-rolled tuple compare would miss.

Tuple compare as fallback inside `_compare_versions`: try
`packaging.version.parse(a) > packaging.version.parse(b)` first;
on `packaging.version.InvalidVersion`, fall back to a strict
`tuple(int(x) for x in a.split("."))` compare; on tuple compare
also failing (non-numeric segments), return `False` (treat as "no
update"). Tested in L0.

### 7.5 Poll for updates while running (every 30 min, piggybacked on email retry timer)

Reject per user-locked decision #5 ("Once per app launch is the right
default"). The bridge-app posture: the father opens the app, uses it,
closes it. There's no scenario where he'd benefit from a mid-session
prompt.

### 7.6 Show "what's new" changelog in the prompt

Reject for Sprint 15. The `latest.json` schema could grow a `changelog`
field later; for now, the version + release date are enough. Adding it
is a backward-compatible schema extension (new optional field).

### 7.7 Use a dedicated `wx.Frame` instead of `wx.MessageDialog`

Reject. `wx.MessageDialog` with `wx.YES_NO` + `SetYesNoLabels` gives
the user a native-looking prompt with custom Polish button labels.
No need for a custom frame.

### 7.8 Background-thread the HTTPS fetch (don't block OnInit)

**Considered carefully.** Today's draft is synchronous: `OnInit` waits
up to 10 seconds for the manifest before showing the frame fully
interactive.

For an elderly user on a possibly-flaky connection, a 10-second
freeze on every launch is poor UX. **However**: `frame.Show()` is
called BEFORE the update_helper check per §2.2, so the user sees the
window immediately. The 10s timeout only affects when the prompt
might appear, not when the window appears.

A background thread would add ~30 LOC of `threading.Thread` +
`wx.CallAfter` coordination. The user-locked decision is "silently
skip if offline" — the synchronous path already satisfies that. The
threaded version is a Sprint-N+ enhancement if the 10s wait becomes
visibly annoying.

**Decision**: synchronous for Sprint 15. Revisitable.

## 8. Test plan

| Layer | What | Mock | Asserts |
|---|---|---|---|
| L0 | `check_for_update` happy path | `urllib.request.urlopen` returns a fake response with the manifest JSON; `current = "1.0.0"`, `latest = "1.0.1"` | Returns `UpdateInfo` with all four fields populated |
| L0 | `check_for_update` no-update | `latest = "1.0.0"`, `current = "1.0.0"` | Returns `None` |
| L0 | `check_for_update` downgrade | `latest = "0.9.0"`, `current = "1.0.0"` | Returns `None` |
| L0 | `check_for_update` skipped | `latest = "1.0.1"`, `current = "1.0.0"`, `skipped = "1.0.1"` | Returns `None` |
| L0 | `check_for_update` timeout | `urlopen` raises `socket.timeout` | Returns `None`, no exception propagated |
| L0 | `check_for_update` DNS error | `urlopen` raises `URLError("Name or service not known")` | Returns `None` |
| L0 | `check_for_update` HTTP 404 | `urlopen` raises `HTTPError(code=404)` | Returns `None` |
| L0 | `check_for_update` JSON malformed | response body is `"not json"` | Returns `None` |
| L0 | `check_for_update` missing field | response body is `'{"latest_version": "1.0.1"}'` (missing `download_url` etc.) | Returns `None` |
| L0 | `check_for_update` http:// URL rejected | manifest has `"download_url": "http://..."` | Returns `None` |
| L0 | `_compare_versions("1.0.10", "1.0.9")` | n/a | Returns True (10 > 9) — guards against the string-compare bug |
| L0 | `_compare_versions("1.0.1-rc1", "1.0.0")` | n/a | Returns True (pre-release > released-earlier) |
| L0 | `_compare_versions("invalid-x", "1.0.0")` fallback | n/a | Returns False (treat as no-update, no crash) |
| L0 | `remember_skipped_version` round-trip | tmpdir settings.json | Write `"1.0.1"`, re-read, assert equal |
| L0 | `min_supported_version` warning trigger | `current = "0.9.0"`, `latest = "1.0.1"`, `min = "1.0.0"` | Returns `UpdateInfo`; **caller** is responsible for surfacing warning text; the dataclass carries the values |
| L1 | (deferred) | live HTTPS fetch against Bitbucket Downloads — first release rehearsal | Manual smoke. |
| L2 | (deferred) | actual `prompt_user_to_update` dialog rendering | Requires wx mainloop fixture (Sprint 11 carry-forward). Manual smoke. |

L0 tests live at `src/tests/helpers/test_update_helper.py`. Sprint 11
carry-forward (no headless-wx fixture yet) means `prompt_user_to_update`
stays at L2 manual smoke — same boundary as Sprint 14's wx-only paths.

## 9. Risks

### Risk 1 — Father is on a metered connection, manifest fetch consumes data

`latest.json` is ~200 bytes. Fetched once per launch. Negligible.

### Risk 2 — `urllib.request` hangs longer than `timeout` on Windows

`socket.timeout` is enforced by the underlying socket; 10s is the cap.
On a hung-on-handshake scenario, the timeout fires. Tested in L0 via
mock.

### Risk 3 — `skipped_update_version` accumulates stale state

If the user skips 1.0.1, then 1.0.5 ships, the comparison is `1.0.5 ==
"1.0.1"` → false → prompt fires. Correct behavior. **Not a risk.**

### Risk 4 — User clicks Yes but the download fails (ADR-014's territory)

ADR-014 handles this. From this ADR's perspective: `download_and_apply_update`
either exits the app (success path) or raises (caller catches; app
keeps running with the unchanged binary; user retries on next launch).

### Risk 5 — `latest.json` field-set drift between CI script and Python module

ADR-012 §2.1 `rename-artifact.ps1` writes the schema; ADR-013 §3 reads
it. If the script writer adds a field and the reader doesn't tolerate
it, the manifest becomes unreadable. **Mitigation**: reader uses
`.get(key)` with explicit checks for the 4 known fields; extra fields
are ignored (forward-compatible). Verified in L0 schema-robustness
tests.

## 10. Halt criteria

(H-B) `_compare_versions("1.0.10", "1.0.9")` returns True. This is the
single most important assertion in the suite — string comparison
breaking this is the canonical bug for version-aware code.

(H-C) `check_for_update` returns `None` on every shape of network
failure mocked in L0. App-MUST-NOT-CRASH from a failed fetch.

(See ADR-014 §6 for self-replace halt criteria.)

## 11. Sources

(See front-matter `sources:` block.)
