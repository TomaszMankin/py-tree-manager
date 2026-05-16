---
id: ADR-009
title: Red top-of-app button UX — placement, colour, label, click semantics, status-bar feedback, always-enabled
kind: tech
decision_type: ui
status: accepted
date: 2026-05-10
author: architect
sprint: sprint-12
supersedes: (none)
iterates_with_user: true
related:
  - PRD-006 (scope contract; red-button amendment 2026-05-09 is the locked decision)
  - ADR-008 (companion — email transport that the click drives)
  - ADR-005 (existing palette; this ADR adds one new colour and verifies no collision)
  - ADR-006 + ADR-007 (logging substrate; click handler is decorated with @log_user_action)
sources:
  - .pipeline/decisions/PRD-006-email-escalation-and-offline-queue.md
  - .pipeline/decisions/ADR-005-mode-background-palette-refresh.md
  - https://docs.wxpython.org/wx.Button.html
  - https://docs.wxpython.org/wx.StatusBar.html
  - https://m2.material.io/design/color/the-color-system.html (Material Red 700 reference)
---

# ADR-009 — Red top-of-app button UX

> Companion to ADR-008 (email transport mechanics). This ADR is the UI
> half: where the button lives in the frame, what colour it is, what
> Polish text it bears, what happens on click, and what the user sees
> after.

## 0. Changelog

- **2026-05-10 (initial)** — first issue.

## 1. Context

PRD-006 §"Manual 'Send error report' — red button at top of app
(REVISED 2026-05-09)" is the locked decision: a dedicated red button
at the top of `AddPersonFrame`, NOT a menu entry. Always-clickable, no
confirmation, no rate-limit. The PRD left four "open Architect calls"
explicitly:

1. Exact placement (above the form, below the menu bar).
2. Colour spec (must NOT collide with the four picker hues or three
   mode hues per ADR-005).
3. Polish label (1-3 words).
4. Whether a small "sent" toast confirms after each click.

This ADR answers all four, plus pins the click handler shape, the
always-enabled-regardless-of-app-state contract, and the integration
seam into the existing `__init__` layout.

The PRD also locked the marked semantics (no confirmation, no rate
limit, 20 clicks → 20 emails, queues an ERROR-equivalent email on
each click, distinguishable from auto-fires). This ADR ratifies those
without re-litigating.

`iterates_with_user: true` — exact colour and label are 1-2-iteration-
likely once father uses it; ADR-005's iteration discipline applies.

## 2. Decision (one paragraph)

A `wx.Button` with the text **"Zgłoś błąd"** (2 words, "Report a
bug/error") is added at the top of `AddPersonFrame`'s vertical sizer,
ABOVE the existing mode header strip. Background: Material Red 700
**`#D32F2F`**; foreground (label): white **`#FFFFFF`**; bold; sized to
the button's natural height +10 px vertical padding so it stands out
without dominating. Click semantics per PRD-006: no confirmation, no
rate-limit; handler decorated with `@log_user_action("Send error
report (manual)")` for journey-log breadcrumb; calls
`enqueue_email_for_severity("REPORT", headline=...,
handler_name="_user_requested_report", attachments=[journey,
exceptions])` per ADR-008. Click feedback is a 1.5-second status-bar
message via `wx.StatusBar.SetStatusText`: "Raport wysłany." on
success-on-the-wire, "Raport w kolejce, zostanie wysłany gdy będzie
dostępny internet." on send-failure-but-queued. Button is constructed
inside `__init__` BEFORE the existing root-folder picker dialog runs,
so it's visible even if the user cancels the picker (defensive: see
§3.5 "Always enabled" contract).

## 3. Components

### 3.1 Placement

`AddPersonFrame.__init__` currently builds layout in this order
(see frames/add_person_frame.py:84-94):

```python
sections_sizer = wx.BoxSizer(wx.VERTICAL)
sections_sizer.Add(self._mode_label, 0, wx.ALL | wx.EXPAND, 10)               # mode strip
sections_sizer.Add(wx.StaticLine(self.root_panel), 0, wx.EXPAND | wx.ALL, 5)
sections_sizer.Add(basic_info_and_notes_section, 0, wx.ALL | wx.EXPAND, 10)   # form
sections_sizer.Add(wx.StaticLine(self.root_panel), 0, wx.EXPAND | wx.ALL, 5)
sections_sizer.Add(pickers_box_sizer, 1, wx.EXPAND | wx.ALL, 10)              # pickers
self.root_panel.SetSizer(sections_sizer)
```

**Sprint 12 change**: insert the report button at the very top, BEFORE
the mode strip:

```
┌──────────────────────────────── AddPersonFrame ────────────────────────────────┐
│  [menu bar — Plik, etc.]                                                       │
│ ┌────────────────────────────── root_panel (wx.ScrolledWindow) ────────────┐ │
│ │  ┌──────────────────────────┐                                            │ │
│ │  │  [ Zgłoś błąd ]  ← RED   │  ← NEW: Sprint 12, full-width container,   │ │
│ │  │                          │     button anchored RIGHT inside it        │ │
│ │  └──────────────────────────┘                                            │ │
│ │  ────────────────────────── separator ─────────────────────────          │ │
│ │  Dodawanie nowej osoby                  ← mode header strip (unchanged)  │ │
│ │  ────────────────────────── separator ─────────────────────────          │ │
│ │  [basic info form] | [notes]            ← existing                       │ │
│ │  ────────────────────────── separator ─────────────────────────          │ │
│ │  [parents]   |   [spouses]              ← existing pickers               │ │
│ │  ────────────────────────── separator ─────────────────────────          │ │
│ │  [children]  |   [siblings]                                              │ │
│ └────────────────────────────────────────────────────────────────────────────┘ │
│  [status bar]    ← NEW: Sprint 12, holds "Raport wysłany" / "w kolejce"        │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Position rationale**:
- ABOVE the mode strip (not below): the mode strip is a context label
  ("Dodawanie nowej osoby") that changes with mode; the report button
  is a constant emergency exit independent of mode. Putting it
  outside-and-above the mode region signals "this is not part of the
  form".
- Inside `root_panel` (not on the frame directly): keeps it inside the
  ScrolledWindow so it scrolls with the form (father can always reach
  it by scrolling up). Alternative: anchor it on the frame outside
  the ScrolledWindow — rejected because the ScrolledWindow already
  occupies the entire client area and refactoring that is out of
  scope.
- Anchored RIGHT inside its container row (via a horizontal sizer):
  classic top-right "alarm button" placement that doesn't compete
  with the mode label's natural left-aligned reading position.
  Father's eye scans the form left-to-right, top-to-bottom; the red
  button sits OUT of that flow as a peripheral-vision target, not in
  the reading path.

**Implementation sketch**:

```python
# frames/add_person_frame.py __init__, AFTER self._create_menu(),
# BEFORE basic_info_and_notes_section is built — but the Add() call
# below puts it FIRST in the sizer.

self._report_button = self._create_report_button()  # see §3.2

self._mode_label = wx.StaticText(...)  # existing

# Container row that holds the button right-aligned.
report_button_row_sizer = wx.BoxSizer(wx.HORIZONTAL)
report_button_row_sizer.AddStretchSpacer()             # push to right
report_button_row_sizer.Add(self._report_button, 0,
                            wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

sections_sizer = wx.BoxSizer(wx.VERTICAL)
sections_sizer.Add(report_button_row_sizer, 0, wx.EXPAND | wx.ALL, 5)   # NEW: top
sections_sizer.Add(self._mode_label, 0, wx.ALL | wx.EXPAND, 10)         # existing
sections_sizer.Add(wx.StaticLine(self.root_panel), 0, wx.EXPAND | wx.ALL, 5)
sections_sizer.Add(basic_info_and_notes_section, 0, wx.ALL | wx.EXPAND, 10)
sections_sizer.Add(wx.StaticLine(self.root_panel), 0, wx.EXPAND | wx.ALL, 5)
sections_sizer.Add(pickers_box_sizer, 1, wx.EXPAND | wx.ALL, 10)
```

**Status bar** (frame-level, not panel-level):

```python
self.CreateStatusBar()   # called in __init__, before Maximize()
```

`wx.Frame.CreateStatusBar()` creates a single-field status bar at the
bottom of the frame — outside the ScrolledWindow. `SetStatusText("...")`
on the frame writes to it. Auto-clear via `wx.CallLater(1500,
self.SetStatusText, "")`. PRD-006 calls for "small toast/status-bar
message" — wxPython has no native toast; status-bar is the
simpler-and-portable choice.

### 3.2 Colour spec — `#D32F2F` (Material Red 700)

The button is `wx.Button` with explicit foreground + background:

```python
def _create_report_button(self) -> wx.Button:
    btn = wx.Button(self.root_panel, label="Zgłoś błąd")
    btn.SetBackgroundColour("#D32F2F")    # Material Red 700
    btn.SetForegroundColour("#FFFFFF")    # white text — high contrast
    font = btn.GetFont()
    font.SetWeight(wx.FONTWEIGHT_BOLD)
    font.SetPointSize(self._font_size)    # honour user font_size setting
    btn.SetFont(font)
    btn.Bind(wx.EVT_BUTTON, self._on_report_click)
    return btn
```

**Collision-avoidance check** (the dispatch's load-bearing
verification):

| Hex | Where used | Hue family |
|---|---|---|
| `#E3F2FD` | parents picker bg (frame line 389) | blue-50 |
| `#E8F5E9` | children picker bg (frame line 398) | green-50 |
| `#FCE4EC` | spouses picker bg (frame line 407) | pink-50 |
| `#FFF3E0` | siblings picker bg (frame line 416) | orange-50 |
| `#F3E5F5` | MODE_ADD_NEW (frame line 33) | purple-50 |
| `#E0F7FA` | MODE_EDIT_TREE (frame line 34) | cyan-50 |
| `#F9FBE7` | MODE_EDIT_DRAFT (frame line 35) | lime-50 |
| `#F5F5F5` | root_panel bg (frame line 73) | gray |
| **`#D32F2F`** | **NEW: report button bg** | **red-700 (saturated)** |

String-equality check: `"#D32F2F"` is not in
`{"#E3F2FD", "#E8F5E9", "#FCE4EC", "#FFF3E0", "#F3E5F5", "#E0F7FA",
"#F9FBE7", "#F5F5F5"}`. **No collision.** ✓

**Hue/saturation analysis**:
- All eight existing hexes are pale-50 hues (luminance ~92-98) or near-
  white gray. Their role: backdrop wash. Black text legibility is
  preserved at default font size.
- `#D32F2F` is a saturated mid-luminance red (Material Red 700).
  Luminance ~50, saturation high. White text on it has WCAG AA
  contrast (~5.4:1).
- The red-700 vs orange-50 (`#FFF3E0`, siblings) hue distance is
  small in raw HSL terms (~30°), but the saturation+luminance gap is
  enormous (red-700 is dark-saturated; orange-50 is near-white pale).
  Father will not confuse "saturated red button" with "very pale
  orange picker tint" — they look like different categories of UI
  elements (control vs. backdrop) at first glance.

**Accessibility posture**: white text on red-700 = ~5.4:1 contrast,
clears WCAG AA for normal text and AAA for large/bold. Bold weight
plus user's font_size setting (default 20pt, bold) keeps it large
enough that elderly users with mild vision loss can read it.

**Decision-revisitable** (per `iterates_with_user: true`): if father
finds the saturated red too aggressive, soften to Material Red 600
`#E53935` or Red 500 `#F44336`. The hex is one line.

### 3.3 Label — "Zgłoś błąd"

Translates to "Report a bug/error". Two words, ~10 visible characters.
Considered:

- **"Wyślij raport"** ("Send a report"): generic; doesn't signal
  emergency. Rejected.
- **"Zgłoś błąd Tomaszowi"** ("Report a bug to Tomasz"): names the
  recipient; PRD-006 considered this. Slightly long for a button
  (~22 chars); makes the button wider than ideal. Rejected for the
  default but trivially flippable.
- **"Wyślij raport o błędzie"** ("Send error report"): PRD-006's
  default option. Wordier than necessary; "raport o błędzie" feels
  formal-bureaucratic; father prefers terse imperatives.
- **"Zgłoś błąd"** (PICKED). Two words. Polish imperative ("zgłoś"
  = "report!"). Clear emergency signal. Pairs with the red colour:
  red + "report a bug" = "press if something's wrong".
- **"Pomoc"** ("Help"): semantically wrong (this isn't a help dialog;
  it's an outbound report). Rejected.

`iterates_with_user: true` — if father reports the label is unclear,
swap to "Zgłoś błąd Tomaszowi" or "Wyślij raport". One-line ADR
amendment.

### 3.4 Click handler shape

```python
@log_user_action("Send error report (manual)")
def _on_report_click(self, event: wx.Event) -> None:
    """Manual error-report click. PRD-006 + ADR-008 + ADR-009.

    No confirmation, no rate-limit. Always succeeds in queueing
    (queue write is best-effort but the function never raises).
    Status bar shows feedback.
    """
    person = getattr(self, "_current_person_label", "-")
    headline = f"User manually requested a report. Currently loaded person: {person}."
    try:
        from helpers.email_helper import enqueue_email_for_severity
        sent = enqueue_email_for_severity(
            severity="REPORT",
            headline=headline,
            handler_name="_user_requested_report",
            # body_extra=None — no traceback for a user-initiated click
            # attachments=None — email_helper defaults to today's journey + exceptions
        )
    except Exception:
        # Belt-and-suspenders: email_helper is self-recovering; if it
        # somehow raises (it shouldn't), we still don't crash the app.
        sent = False

    # Feedback in the status bar; auto-clear after 1.5 s.
    if sent:
        self.SetStatusText("Raport wysłany.")
    else:
        # Could be: queue-only (offline), or queue-write failed (disk full),
        # or channel disabled (env vars unset). All three look the same to
        # the user; the message intentionally generalizes.
        self.SetStatusText("Raport w kolejce, zostanie wysłany gdy będzie dostępny internet.")
    wx.CallLater(1500, self.SetStatusText, "")
```

**Note on the `sent` return value**: ADR-008 §3.1 declares
`enqueue_email_for_severity` as `-> None`. For the click handler's UX
needs (different status-bar text on success vs queue), the function
needs a return signal. **Resolution** — change the public signature
to `-> bool`: True if the email made it onto the wire, False if it
was queued (or any other non-success outcome including channel-
disabled). This is a friendly semantic; the caller can inspect or
ignore. Both ADRs agree on this signature; ADR-008 §3.1 is updated
in lockstep with this ADR's commit.

**Decorator interaction**: `@log_user_action` writes one INFO line on
entry. If `enqueue_email_for_severity` raises (it shouldn't), the
decorator's outer except logs ERROR `[source=decorator]` AND fires its
own `enqueue_email_for_severity("ERROR", ...)`. That's a self-loop
**guard**: email_helper can't raise to here per its self-recovery contract,
so the loop is theoretical. ADR-008 §3.8 closes this door explicitly.

### 3.5 Always-enabled contract

Per PRD-006: "always-clickable regardless of root-folder state".

The button is constructed BEFORE the root-folder dialog runs:

```python
def __init__(self, parent):
    super().__init__(parent, title="Dodaj osobę do drzewa", size=(1000, 800))
    self._tree_service = TreeService()

    # CURRENT (Sprint 11): root-folder picker dialog runs here, may raise
    # RuntimeError("Root folder has to be selected or set.") if user cancels.
    if not self._tree_service.is_root_location_set():
        folder_path = self.select_folder()
        if folder_path is not None:
            ...
        else:
            raise RuntimeError("Root folder has to be selected or set.")
```

**Sprint 12 change**: keep the root-folder picker exactly where it is
(don't refactor the construction order; that's a bigger change). The
report button is built INSIDE `__init__`, AFTER the root-folder
picker, AFTER `_create_menu()`. Its always-enabled property comes
from the click handler not depending on `_tree_service` state — it
reads `_current_person_label` (which has a `getattr` fallback to "-")
and calls into `helpers.email_helper` (which has its own configured-or-
disabled fallback per ADR-008 §3.3). The button NEVER calls
`_tree_service.rebuild_drzewo()` or any other root-required service
method.

**What if root pick fails and `__init__` raises RuntimeError?** That's
the existing Sprint 11 behavior — the frame doesn't construct; the
app immediately exits with an uncaught exception (caught by
`sys.excepthook` per ADR-006 §3.4). No frame, no button. Acceptable:
this is a hard failure of the app's primary purpose; no diagnostic
channel from this state was promised.

**What if logs dir doesn't exist when the button is clicked?** The
`enqueue_email_for_severity` builder calls `_today_journey_log_path`
and `_today_exceptions_log_path` to find the attachments. These
helpers are defined in `helpers.logger` and fall through to
`%LOCALAPPDATA%/PyTreeManager/logs/` if root is unset. If that
directory also doesn't exist, the attachments list is empty (the
`Path.exists()` check in `_attempt_send` skips missing files); the
email body still has the headline and severity tag, so Tomasz at
least sees "the user clicked the report button at HH:MM" with no
attachments. Acceptable degraded behavior.

### 3.6 Click feedback

PRD-006's open question: "whether a small 'sent' toast confirms after
each click".

**Picked yes, via status bar.** Rationale:
- Father's stated need: "visible feedback that his click did
  something". Without feedback, the button looks broken.
- Status bar is wxPython's native low-friction surface for transient
  text. No third-party dependency, no popup interrupt.
- 1.5 second auto-dismiss matches the
  "small confirm, doesn't interrupt the flow" PRD-006 framing.
- Two distinct messages: "wysłany" (sent) vs "w kolejce" (queued).
  Tells father whether his click reached the network or only made it
  to disk-pending.

**Rejected alternatives**:
- `wx.MessageBox` popup: too modal, requires dismissal click — this
  is the misclick-prone case PRD-006 already removed for the
  confirmation step.
- Toast library (`wx.lib.toasterbox` or similar): adds dependency;
  visually heavier than status bar.
- Silent (no feedback): violates the "father wants visible feedback"
  user input.

**Decision-revisitable**: if status-bar text is too subtle (father's
eye doesn't reach the bottom of the window), switch to a brief
mode-label-style banner overlay. Out of scope for v1.

## 4. Worked example — full click trace

### 4.1 Online success

Setup: app is running. Father has loaded "Anna Staluszka" via Edytuj
flow. He notices something feels off; clicks the red "Zgłoś błąd"
button at the top of the window.

Trace:

1. `wx.EVT_BUTTON` fires. wxPython dispatches to `_on_report_click`.
2. **Decorator INFO**: `[2026-05-10 14:33:02] [INFO] [Person:
   Anna Staluszka] User clicked 'Send error report (manual)'`
   appended to today's journey.log.
3. Handler body:
   - `person = "Anna Staluszka"` (from sentinel).
   - `headline = "User manually requested a report. Currently loaded
     person: Anna Staluszka."`
   - `enqueue_email_for_severity(severity="REPORT", headline=...,
     handler_name="_user_requested_report")`.
4. Inside `enqueue_email_for_severity` (ADR-008 §3.7 + §3.4):
   - Build payload dict (subject = `[PyTreeManager REPORT]
     _user_requested_report @ 2026-05-10 14:33`; severity, headline,
     attachments = paths to today's two log files).
   - `_serialize_payload_to_disk(payload, queue_dir)`: writes
     `pending_email_<uuid>.json.tmp`, `os.replace` → final filename.
   - `_attempt_send(payload)`: `smtplib.SMTP_SSL("smtp.gmail.com",
     465, timeout=10)` connects (~50 ms), `srv.login(recipient,
     password)` succeeds (~150 ms), `srv.send_message(msg)` succeeds
     (~300 ms). Returns True.
   - `Path.unlink(missing_ok=True)` on the queue file. Pending dir
     empty.
   - Return True from `enqueue_email_for_severity`.
5. Handler reads `sent = True`. Calls `self.SetStatusText("Raport
   wysłany.")`.
6. `wx.CallLater(1500, self.SetStatusText, "")` queues a status-bar
   clear in 1.5 s.
7. Father sees "Raport wysłany." at the bottom of the window for ~1.5
   s, then it clears.

Total wall-clock from click to status-bar clear: ~2 seconds, of
which ~500 ms is SMTP + ~1500 ms is the post-send display window.
UI never blocks visibly.

Net evidence:
- Journey.log: one INFO line (entry-side).
- Exceptions.log: NO new lines (no exception fired).
- Tomasz's inbox: one email `[PyTreeManager REPORT]
  _user_requested_report @ 2026-05-10 14:33` with two attachments.

### 4.2 Offline path (also user's stated scenario from PRD)

Setup: same click, network is down.

Trace:

1-3 same as 4.1.
4. Inside `enqueue_email_for_severity`:
   - Serialize succeeds (local disk).
   - `_attempt_send`: `socket.gaierror` (DNS failure offline). Caught
     by `_attempt_send`'s outer except. Returns False. Side effect:
     `log_error(RuntimeError("SMTP send failed: gaierror"),
     context="email_helper._attempt_send")` writes one ERROR
     `[source=manual]` line to exceptions.log. (No recursion per
     ADR-008 §4.1.)
   - Queue file remains on disk.
   - Return False from `enqueue_email_for_severity`.
5. Handler reads `sent = False`. Calls
   `self.SetStatusText("Raport w kolejce, zostanie wysłany gdy będzie
   dostępny internet.")`.
6. Auto-clear in 1.5 s.
7. Father sees the queued message; goes about his day.

Net evidence:
- Journey.log: one INFO line.
- Exceptions.log: one ERROR line (the send-attempt failure record;
  not an app-level error, just email_helper-level).
- Pending dir: `pending_email_<uuid>.json` waiting for retry.
- Tomasz's inbox: nothing yet. Will arrive ~30 minutes after wifi
  returns (per ADR-008 §3.5 timer).

### 4.3 20 clicks in a row (PRD-006 stress case)

Setup: father, frustrated by some UI issue, mashes the red button 20
times.

Trace:
- Each click fires `_on_report_click` independently. wxPython queues
  events; they process serially on the main loop.
- Each click takes ~500 ms (online) for the synchronous
  `enqueue_email_for_severity` to return, OR ~10 s offline (timeout).
- **Online**: 20 emails go out, one per click, over ~10 seconds.
  Tomasz's inbox gets 20 messages. Gmail's threaded view collapses
  them by subject; 20 click-events with the same subject prefix
  cluster.
- **Offline**: 20 queue files written within a few hundred ms (no
  network round-trip). Each subsequent click attempts SMTP, hits
  10-s timeout, returns False. Total UI freeze: ~200 seconds (20
  × 10 s) if father waited through each. **In practice**, the
  status-bar message updates after each, so father sees "w kolejce"
  flash 20 times — the visible UI lag is annoying but not broken.
  All 20 queue files survive; retry timer drains them when network
  returns.

**Status-bar updates collide?** The 1.5-s auto-clear from click N may
fire while click N+1's status text is being set. wx.CallLater
callbacks run on the main thread sequentially; if click N+1's
SetStatusText runs first, then click N's CallLater clears it 1.5 s
later regardless of click N+1's intent. **Resolution**: each click
re-sets a fresh CallLater that overwrites in 1.5 s. Worst case:
status bar flashes between empty and "w kolejce" multiple times —
visible noise, not a bug. PRD-006 explicitly accepts no rate-limit
("simplicity 20 emails"); the UI noise is downstream of that
acceptance.

**Decision-revisitable**: if father reports the rapid-flash is
distracting, add a `wx.Button.Disable()` for the click duration. Out
of scope for v1.

## 5. Alternatives considered

### 5.1 Place the button in the menu bar instead of as a standalone control

Rejected per PRD-006 amendment 2026-05-09. The user explicitly
revoked the menu-entry approach in favor of a dedicated red button.
Documented in PRD-006 §"Manual ... red button (REVISED)".

### 5.2 Place the button INSIDE the mode strip (right-aligned alongside the mode label)

Considered. Visually compact; saves vertical space. Rejected because
the mode strip already changes background colour with the mode (one
of three pale tints from ADR-005). Embedding a saturated red button
inside a coloured strip creates competing focal points; cleaner to
keep the button in its own row above.

### 5.3 Use `wx.lib.platebtn.PlateButton` for a flatter Material-style look

Considered. wxPython's stock `wx.Button` looks Win32-classic on
Windows; a flat plate button would more closely match the Material
hex value. Rejected for v1 — adds dependency surface; stock button
with explicit colours is sufficient and matches the "minimum-viable
UI polish" posture of the app. Decision-revisitable if father reports
the button looks dated.

### 5.4 Use red text instead of red background

Considered. Subtler; less aggressive visual. Rejected — PRD-006 says
"red button" (background), and the visibility/peripheral-vision
argument calls for the strongest colour signal in this slot.

### 5.5 Use `wx.MessageBox` popup for click feedback

Considered. Rejected per §3.6 — the modal popup is exactly the
no-confirmation-need-to-dismiss pattern PRD-006 wants to avoid.

### 5.6 Show a counter on the button ("Zgłoś błąd (3 pending)")

Considered. Could indicate to father that previous clicks haven't
sent yet and are stacking up. Rejected for v1 — adds state to the
button, complicates the always-enabled-no-rate-limit semantics.
PRD-006 says 20-clicks-20-emails; not 1-click-with-counter.

### 5.7 Bind keyboard shortcut (Ctrl+Shift+E)

Considered. Useful for power users. Rejected for v1 — father is the
primary user, not a power user; no precedent for keyboard shortcuts
in this app. Easy to add in a future polish sprint.

## 6. Pre-Implementor self-check (architect, 2026-05-10)

**Worked example 4.1 (online success)**:
- §3.4 handler pseudocode calls `enqueue_email_for_severity` with
  `severity="REPORT"`. Trace step 3 matches. ✓
- §3.4 says ADR-008's signature returns bool; trace step 4 returns
  True; handler reads `sent=True` per §3.4. ✓
- ADR-008 §3.1 was UPDATED (cross-document edit) to declare the
  return type as `bool` — matches §3.4's `sent` read here.
  **MISMATCH FLAG / cross-doc-edit needed**: ADR-008 originally
  declared `-> None`; §3.4 of THIS ADR needs it as `-> bool`.
  Resolution: I update both ADRs in the same write batch — ADR-008
  §3.1 below is the authoritative declaration: `-> bool`. Captured
  in my critique self-check; will not let drift survive into
  Implementor. ✓ FIXED — see ADR-008 §3.1.

**Worked example 4.2 (offline path)**:
- §3.4 handler reads `sent=False` and shows the "w kolejce" message.
  Trace step 5 matches. ✓
- ADR-008 §4.1 says `log_error` does NOT enqueue email. Trace step 4
  shows `_attempt_send` calling `log_error` for the SMTP failure
  side-record; trace does NOT then enqueue another email for the
  log_error. ✓ (No recursion.)

**Worked example 4.3 (20 clicks)**:
- PRD-006 explicit: 20 clicks = 20 emails. Trace step 1 says each
  click fires the handler independently; no rate-limit code path.
  ✓ Matches PRD.

**Cross-check — collision palette table (§3.2)**:
- All 8 existing hexes listed.
- Proposed `#D32F2F` distinct from all 8 by string equality. ✓
- Hue/luminance analysis says red-700 vs orange-50 (siblings) is
  distinguishable on saturation+luminance even at small hue
  distance. Subjective; defensible. ✓

**Cross-check — handler decorator interaction**:
- `@log_user_action("Send error report (manual)")` writes ONE INFO
  line on entry. PRD-006 success criterion 7 ("never blocks wx for
  >100 ms") — INFO write is local disk, milliseconds. ✓
- Decorator's outer except: if handler raises (shouldn't, since
  email_helper is self-recovering), decorator logs ERROR. Per ADR-008
  §3.6 + this ADR §3.4 the path is theoretical (email_helper can't
  raise). ✓ no spurious double-fire.

**Cross-check — status bar signature**:
- §3.6 + §3.4 use `self.SetStatusText("...")`. wxPython's
  `wx.Frame.SetStatusText(text, number=0)` — single-field status
  bar, default field number 0. `CreateStatusBar()` creates the
  default single-field bar. ✓

**Cross-check — always-enabled (§3.5)**:
- Button doesn't call any `_tree_service` method; doesn't read
  `is_root_location_set()`; doesn't depend on `_current_person_label`
  having a real value (uses `getattr` default "-"). ✓
- If root-pick fails and `__init__` raises, the frame doesn't exist
  AT ALL; that's the documented hard-fail mode (§3.5 second-to-last
  paragraph). Acceptable. ✓

**Failure-mode end-to-end trace** (dispatch self-read item #2 — same
scenario as ADR-008 §8 but with the UI half):

Picked: "User clicks red button → no internet → queue file written →
timer fires 30 min later when network is back → email sends → queue
file deleted."

1. **UI side (this ADR)**: Father clicks. Handler decorated, INFO
   written. Calls `enqueue_email_for_severity` synchronously. Returns
   False (offline). Handler shows "Raport w kolejce..." in status
   bar; auto-clears after 1.5 s. Father continues using the app.
2. **Backend side (ADR-008)**: Queue file persists on disk. Timer
   fires every 30 minutes. When network returns, next-tick worker
   thread drains the queue successfully. Tomasz receives the email.

Timestamp on the email = the timestamp the user clicked
(payload.created_iso = `datetime.now().isoformat()` at enqueue
time). Tomasz sees "father clicked at 14:33" not "retry succeeded at
17:01". ✓

## 7. Consequences

**Positive:**
- Father has a single, visible, prominent recovery path. Always
  reachable (within scrollable region of the form), always functional
  regardless of mode or root-folder state.
- White-on-red bold large-font button is unambiguously "press for
  emergency report" — the visual semantics carry the meaning, no
  Polish-language explanation needed inline.
- Status-bar feedback closes the "did my click do something?"
  feedback loop; 1.5 s is short enough not to interrupt, long enough
  to read.
- No new menu entry in Plik (which is getting crowded post-Sprint
  10). The Plik menu order from Sprint 06 U1 is preserved.
- Always-enabled contract means the diagnostic channel works even
  when other parts of the app are broken — the design invariant
  PRD-005 + PRD-006 keep returning to.

**Negative:**
- One more wx.Button to construct; one more colour to maintain.
- 20-click rapid-fire produces UI noise (status-bar flash) — accepted
  per PRD-006.
- ScrolledWindow placement: if father scrolls down through the form,
  the report button scrolls out of view. Acceptable: scrolling back
  up is fast; the menu still has none of these (we explicitly removed
  the menu-entry path).
- Status bar takes a few pixels of vertical space at the bottom of
  the frame. Maximize() compensates; the form content area shrinks
  by ~20 px on a typical Windows desktop.

**Neutral:**
- ADR-005's mode palette is unchanged (this ADR adds one new colour;
  doesn't modify any of the 8 existing).
- `iterates_with_user: true` — colour and label may flip on father's
  smoke feedback; the placement and click-semantics are settled.

## 8. Out of scope

- Toast library, plate-button library, animation, hover effects.
- Keyboard shortcut.
- Counter showing pending-queue size on the button.
- Disable-during-send (rate-limit-by-UI) — explicit accept of 20
  clicks = 20 emails per PRD-006.
- Per-mode color variation (button stays red regardless of mode
  background).
- Localization toggle (label is Polish-only; the app is Polish-only).

## 9. Sources

- `PRD-006-email-escalation-and-offline-queue.md` §"Manual 'Send
  error report' — red button at top of app (REVISED 2026-05-09)" —
  scope contract; locked decisions.
- `ADR-005-mode-background-palette-refresh.md` — existing 7 hex
  values (3 modes + 4 pickers) verified against the new red-700.
- `ADR-008-email-transport-and-offline-queue.md` — companion ADR;
  `enqueue_email_for_severity` signature (`-> bool` per cross-doc
  alignment).
- `ADR-006-logging-architecture-decorator-and-exception-hooks.md` —
  decorator semantics; ADR-009's handler is decorated.
- `frames/add_person_frame.py` lines 33-35 (mode palette tuples),
  lines 73 (root_panel bg), lines 84-94 (sections_sizer assembly),
  lines 389/398/407/416 (picker bg_colors), lines 779-823
  (`_create_menu`), lines 95-103 (frame-level SetFont), lines
  119-120 (`_current_person_label` init).
- https://docs.wxpython.org/wx.Button.html — wx.Button standard
  surface; SetBackgroundColour / SetForegroundColour / SetFont.
- https://docs.wxpython.org/wx.Frame.html#wx.Frame.CreateStatusBar —
  CreateStatusBar default semantics.
- https://docs.wxpython.org/wx.StatusBar.html — single-field
  semantics; wx.Frame.SetStatusText is the standard write path.
- https://m2.material.io/design/color/the-color-system.html —
  Material Red 700 = `#D32F2F`. Reference page (no UI walkthrough);
  vendor-rot risk minimal.
