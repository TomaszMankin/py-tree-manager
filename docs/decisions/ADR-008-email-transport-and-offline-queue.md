---
id: ADR-008
title: Email transport — Gmail SMTP_SSL, opportunistic send, file-system offline queue, wx.Timer 30-min retry, log_error does NOT auto-escalate
kind: tech
decision_type: architecture
status: accepted
date: 2026-05-10
author: architect
sprint: sprint-12
supersedes: (none)
iterates_with_user: false
related:
  - PRD-006 (scope contract; amended 2026-05-09 for red-button-not-menu)
  - ADR-006 (logging substrate; email reads logs, never modifies them)
  - ADR-007 (severity model; CRITICAL + ERROR are eligible, INFO and INFO-CLEANUP are not)
  - ADR-009 (companion — red top-of-app button UX + UI integration)
sources:
  - .pipeline/decisions/PRD-006-email-escalation-and-offline-queue.md
  - .pipeline/decisions/ADR-006-logging-architecture-decorator-and-exception-hooks.md
  - .pipeline/decisions/ADR-007-severity-model-and-log-line-format.md
  - .pipeline/JOURNAL.md 2026-05-09 orchestrator entry "Sprint 11+12+13 scope intake"
  - .pipeline/JOURNAL.md 2026-05-09 amendment entry "red button not menu entry"
  - https://docs.python.org/3/library/smtplib.html
  - https://docs.python.org/3/library/email.message.html
  - https://support.google.com/accounts/answer/185833 (Gmail App Passwords reference)
  - https://wiki.wxpython.org/wxTimer
  - https://docs.wxpython.org/wx.Timer.html
---

# ADR-008 — Email transport + offline queue

> Companion to ADR-009 (red button UX). Read together. Email is the
> backend; the red button is one of three triggers (the others being
> CRITICAL exception via hook layer, and ERROR via decorator outer
> except).

## 0. Changelog

- **2026-05-10 (initial)** — first issue.

## 1. Context

PRD-006 locks WHAT triggers an email (CRITICAL auto, ERROR auto, manual
red-button click), what's in the message (subject, body, attachments),
the offline-queue contract, and the periodic-retry vehicle (`wx.Timer`,
30 min). This ADR locks HOW the email subsystem wires into the existing
Sprint 11 logging stack: which `smtplib` class, which Gmail
host:port, which env-var names, the queue-file format, atomic-write
mechanics, where the timer lives, threading discipline, and one
load-bearing escalation-policy decision the PRD left to architect:

> **Does `log_error()` (Sprint 11's manual API) ALSO fire an email, or
> is email escalation triggered ONLY from the decorator outer-except,
> the `sys.excepthook` / `OnExceptionInMainLoop` hooks, and the manual
> red-button click?**

PRD-006's "Trigger model" section says "ERROR events → automatic email"
without specifying which producer of ERROR is meant. ADR-007 §3 names
two ERROR producers (decorator path with `[source=decorator]`, manual
path with `[source=manual]`). This ADR ratifies the answer for both.

## 2. Decision (one paragraph)

A new module `helpers/email_helper.py` exposes three public entry points:
`enqueue_email_for_severity(severity, headline, body_extra, attachments,
context)`, `attempt_send_pending(queue_path)`, and `start_retry_timer()`.
Email transport uses **`smtplib.SMTP_SSL("smtp.gmail.com", 465,
timeout=10)`** with App-Password auth read from env var
`PYTREEMANAGER_EMAIL_PASSWORD`; the recipient + sender address comes
from env var `PYTREEMANAGER_EMAIL_RECIPIENT` (single string, used for
both `From` and `To` because Gmail SMTP requires `From == authenticated
user`). When either env var is unset, the entire email subsystem is
disabled silently (one INFO line at startup; queue still writes
payloads but no send is attempted). Offline queue lives at
`<root>/logs/pending/pending_email_<uuid>.json` (JSON serialization,
write-then-rename atomicity, `uuid.uuid4()` filename uniqueness). A
single app-level `wx.Timer` lives on the `LoggingApp` instance, started
in `OnInit`, fires every 30 minutes; its `Notify` callback is wrapped
in `wx.CallAfter` only insofar as SMTP send runs on a `threading.Thread`
to avoid blocking the wx main loop for >100 ms (PRD-006 §"Success
criteria" item 7). **Escalation policy** (load-bearing call):
**`log_error()` does NOT auto-enqueue email** (Option b from dispatch).
The catch-site sweep already populated 10 inner-except sites with
`log_error` calls in Sprint 11; auto-emailing each one would produce
chatty, low-signal email storms. The decorator outer-except DOES
auto-enqueue (every uncaught-by-handler exception is escalation-worthy
by definition). The hook layer (`sys.excepthook` /
`OnExceptionInMainLoop`) DOES auto-enqueue (CRITICAL = process is
terminating, Tomasz needs to know). The red button DOES enqueue per
ADR-009. `log_error` stays a pure-write API (its name says "log", not
"escalate") — preserving the Sprint 11 contract that
`log_error` MUST NOT raise and MUST NOT do anything beyond append a
line to the exception log.

## 3. Components

### 3.1 New module — `helpers/email_helper.py`

Public surface:

```python
# Constants — exported for tests
EMAIL_PASSWORD_ENV_VAR  = "PYTREEMANAGER_EMAIL_PASSWORD"
EMAIL_RECIPIENT_ENV_VAR = "PYTREEMANAGER_EMAIL_RECIPIENT"
SMTP_HOST               = "smtp.gmail.com"
SMTP_PORT_SSL           = 465
SMTP_TIMEOUT_SECONDS    = 10
RETRY_INTERVAL_MINUTES  = 30
RETRY_INTERVAL_MS       = RETRY_INTERVAL_MINUTES * 60 * 1000  # 1_800_000
GMAIL_ATTACHMENT_LIMIT_BYTES = 25 * 1024 * 1024   # 25 MB Gmail cap
JOURNEY_LOG_TAIL_BYTES  = 1 * 1024 * 1024         # 1 MB tail per PRD-006 over-limit case
PENDING_DIR_NAME        = "pending"
PENDING_FILENAME_PREFIX = "pending_email_"
PENDING_FILENAME_SUFFIX = ".json"
QUARANTINE_DIR_NAME     = "quarantine"

# Severity values eligible for email (per ADR-007 §3)
EMAILABLE_SEVERITIES: frozenset = frozenset({"ERROR", "CRITICAL", "REPORT"})
# REPORT = synthetic severity tag for the red-button manual click. Treated
# as ERROR for queueing/retry purposes per PRD-006 "Manual button" section,
# but the subject prefix differs ("[REPORT]" not "[ERROR]") so Tomasz can
# filter at a glance.

# Public functions called by the rest of the app
def is_email_configured() -> bool:
    """Return True iff both env vars are set (non-empty)."""

def enqueue_email_for_severity(
    severity: str,                          # "ERROR" | "CRITICAL" | "REPORT"
    headline: str,                          # one-line summary for body+subject
    body_extra: Optional[str] = None,       # multi-line additional context (e.g. traceback)
    handler_name: Optional[str] = None,     # for subject: "[PYT <SEV>] <handler>"
    attachments: Optional[List[Path]] = None,  # default: today's journey + exceptions
) -> bool:
    """Build email payload, persist to queue, attempt opportunistic send.

    Returns:
      True  — email was sent successfully on the wire (queue file
              written then deleted as part of the send-success path).
      False — anything else: send-failed-but-queued (offline), channel
              disabled (env vars unset), queue-write failed (disk full),
              or any internal exception swallowed by the self-recovery
              wrap. The caller (e.g., the red button click handler in
              ADR-009 §3.4) reads this bool to choose between
              "Raport wysłany." and "Raport w kolejce..." UI feedback.

    Self-recovery: never raises. On any internal failure, falls through
    silently and returns False. Logs (ERROR best-effort) the queue-write
    failure, BUT does NOT re-enqueue (that would loop). See §3.6.
    """

def start_retry_timer(host_window: "wx.Window") -> "wx.Timer":
    """Start the 30-minute retry timer parented to host_window.

    host_window MUST be the long-lived LoggingApp or top-level frame —
    NOT a transient dialog. Returns the wx.Timer reference for testability;
    caller stores it to prevent GC. See PRD-006 §"Periodic retry"
    (timer must survive frame transitions).
    """

def stop_retry_timer(timer: "wx.Timer") -> None:
    """Stop the retry timer. Called from app shutdown."""

# Internal — exposed for tests
def _build_email_payload(severity, headline, body_extra, handler_name,
                         attachments) -> Dict[str, Any]: ...
def _serialize_payload_to_disk(payload, queue_dir) -> Optional[Path]: ...
def _attempt_send(payload: Dict[str, Any]) -> bool: ...
def _walk_queue_and_retry(queue_dir: Path) -> None: ...
def _quarantine_payload(payload_path: Path, reason: str) -> None: ...
def _read_password() -> Optional[str]: ...
def _read_recipient() -> Optional[str]: ...
def _today_journey_log_path() -> Path: ...   # delegates to helpers.logger
def _today_exceptions_log_path() -> Path: ... # delegates to helpers.logger
def _truncate_attachment_if_oversize(path: Path, max_bytes: int) -> Tuple[bytes, str]: ...
```

The module imports `helpers.logger` for path helpers + `log_error`
(used to record the rare "queue-write itself failed" case) but does
NOT modify the logger. The dependency direction is one-way:
`email_helper → logger`, never `logger → email_helper`. This prevents the
recursive-write hazard PRD-006 §"Disk full" calls out.

### 3.2 Why SMTP_SSL on port 465 (not STARTTLS on 587)

Two viable options for Gmail:

**Option A — `smtplib.SMTP_SSL("smtp.gmail.com", 465)`.** SSL from the
first byte; no plaintext handshake; one-line connect + login. Picked.

**Option B — `smtplib.SMTP("smtp.gmail.com", 587)` + `starttls()`.** Connects
plaintext, upgrades to TLS via STARTTLS. Two-line dance. Vulnerable to
**STRIPTLS** intermediaries (a hostile/buggy network that strips the
upgrade, leaving the auth in cleartext). Not realistic for father's
home network but a real concern for general use.

Decision: **Option A**. Implicit-SSL is simpler, no upgrade dance, no
STRIPTLS surface. Both ports are documented-and-supported by Gmail
(https://support.google.com/mail/answer/7126229 lists both as outgoing
mail server options); 465 is "SSL/TLS", 587 is "STARTTLS". For a
single-user single-recipient app on a residential network, either
works; 465 wins on simplicity.

### 3.3 Env-var names + secret discipline

Two env vars:

| Var | Purpose | Required? | Failure mode |
|---|---|---|---|
| `PYTREEMANAGER_EMAIL_PASSWORD` | Gmail App Password (16-char string) | yes | Channel disabled silently; queue still writes; one INFO startup line |
| `PYTREEMANAGER_EMAIL_RECIPIENT` | Tomasz's Gmail address (used as both `From` and `To`) | yes | Same: channel disabled, queue writes |

**Naming rationale**: matches user's existing convention from
`reference_kodland_api.md` (env-var-prefixed-with-app-name). The
`PYTREEMANAGER_` prefix is verbose but namespaces clearly on a multi-app
machine. PRD-006 left exact names to architect; these match the
project's existing single-secret-store posture.

**Values NEVER appear in any artifact**:
- Not in logs (the logger formatter does not enumerate `os.environ`).
- Not in emails (`From: <recipient_address>` is the only echo, and
  the password is never echoed).
- Not in error messages on send-failure (smtplib's exception messages
  are fielded via `f"send failed: {type(e).__name__}"` not `str(e)` —
  see §3.6 for the redaction).
- Not in `.env`-ish committed files (no `.env` is created by this
  sprint; values come from the user's environment).

**Reading the env vars** is centralized in `_read_password()` and
`_read_recipient()`. They return `Optional[str]` and strip whitespace.
Empty string is treated as unset.

### 3.4 Queue file format + atomicity

**Format: JSON.** Picked over plain-text-with-headers for two reasons:
(a) JSON gives a clean roundtrip for the attachment paths and any
non-ASCII body content without escaping concerns; (b) corrupted-payload
detection is automatic (`json.JSONDecodeError` triggers the quarantine
path per PRD-006 §"Pending payload corrupted").

Schema (one queue file = one queued email):

```json
{
  "schema_version": 1,
  "created_iso": "2026-05-10T14:32:11+02:00",
  "severity": "CRITICAL",
  "subject": "[PyTreeManager CRITICAL] on_save_click @ 2026-05-10 14:32",
  "headline": "KeyError: 'uid-cafef00d' in on_save_click",
  "body_extra": "  Traceback (most recent call last):\n  ...",
  "handler_name": "on_save_click",
  "attachments": [
    "C:/Sorted tree/logs/2026-05-10__journey.log",
    "C:/Sorted tree/logs/2026-05-10__exceptions.log"
  ]
}
```

`attachments` paths are stored as ABSOLUTE STRINGS; the retry timer
re-reads them at send time (so a log file rotated since enqueue still
gets sent if it still exists — and is silently skipped if it doesn't,
with a one-line `_emit_info_raw` "attachment missing" entry).

**Atomicity = write-then-rename**:

```python
def _serialize_payload_to_disk(payload, queue_dir):
    queue_dir.mkdir(parents=True, exist_ok=True)
    final_name = f"{PENDING_FILENAME_PREFIX}{uuid.uuid4()}{PENDING_FILENAME_SUFFIX}"
    tmp_path = queue_dir / (final_name + ".tmp")
    final_path = queue_dir / final_name
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.flush()
        try:
            os.fsync(fh.fileno())   # best-effort durability; ignore if not supported
        except (OSError, AttributeError):
            pass
    os.replace(tmp_path, final_path)   # atomic on Windows + POSIX
    return final_path
```

`os.replace` is atomic on Windows (single MoveFileEx call with
MOVEFILE_REPLACE_EXISTING) and on POSIX (rename(2)). A reader (the
retry timer) that arrives mid-write either sees no file at all (hasn't
been renamed yet) or sees the complete file (rename happened) — never
a half-written file. UUID filename prevents two concurrent writers
(unlikely in single-process app, possible if user runs two instances)
from clobbering.

### 3.5 wx.Timer integration + threading

**Where the timer lives**: instance attribute on the `LoggingApp`
subclass (the one defined in `helpers/logger.py` via the deferred-import
factory). Created in `OnInit`, stopped in `OnExit`. Parenting it to
`LoggingApp` (not to `AddPersonFrame`) means timer survives if the
frame is destroyed and re-created (currently not a code path, but
defensive).

```python
# In helpers/logger.py LoggingApp subclass — extension only, not modification
class LoggingApp(wx.App):
    def OnInit(self) -> bool:
        init_logging(root_folder=None)
        cleanup_old_logs()
        from frames.add_person_frame import AddPersonFrame
        from helpers.email_helper import start_retry_timer
        frame = AddPersonFrame(None)
        frame.Show()
        self._email_retry_timer = start_retry_timer(self)   # NEW (Sprint 12)
        return True

    def OnExit(self) -> int:                                # NEW (Sprint 12)
        from helpers.email_helper import stop_retry_timer
        timer = getattr(self, "_email_retry_timer", None)
        if timer is not None:
            stop_retry_timer(timer)
        return 0

    def OnExceptionInMainLoop(self) -> bool:
        # ... unchanged from Sprint 11 ...
```

**The timer object itself**:

```python
# helpers/email_helper.py
class _EmailRetryTimer(wx.Timer):
    def __init__(self, host_window):
        super().__init__(host_window)
    def Notify(self):
        # Called on the wx main thread every RETRY_INTERVAL_MS.
        try:
            queue_dir = _queue_dir()
            if not queue_dir.exists():
                return
            pending = list(queue_dir.glob(f"{PENDING_FILENAME_PREFIX}*{PENDING_FILENAME_SUFFIX}"))
            if not pending:
                return     # PRD-006 "Decision: retry runs only when queue is non-empty"
            # Offload the actual send to a worker thread so the wx main
            # loop is never blocked on SMTP. See §3.5 threading section.
            t = threading.Thread(
                target=_walk_queue_and_retry,
                args=(queue_dir,),
                name="email_helper-retry",
                daemon=True,
            )
            t.start()
        except Exception:
            # Timer callback NEVER crashes the app.
            pass

def start_retry_timer(host_window):
    timer = _EmailRetryTimer(host_window)
    timer.Start(RETRY_INTERVAL_MS, oneShot=False)
    return timer

def stop_retry_timer(timer):
    try:
        timer.Stop()
    except Exception:
        pass
```

**Threading rationale**: PRD-006 success criterion 7 ("never blocks the
wx main loop for >100 ms"). `smtplib.SMTP_SSL.connect+login+sendmail`
takes hundreds of milliseconds to seconds even on a fast network; the
retry walks N pending files. Synchronous-on-tick would freeze the UI
visibly each retry, especially when offline (each connect attempt
times out at 10 s). Solution: dispatch a `threading.Thread` from the
timer's `Notify` callback. The thread does smtplib calls + file
deletes; no UI updates — so no `wx.CallAfter` needed for thread→main
marshalling.

**Daemon thread** = not joined on app exit. Acceptable: the worst-case
truncation is a single in-flight SMTP transaction; retried next app
launch (file still on disk). No data corruption surface.

**Concurrency on the queue dir**: two writers to disk are fine (UUID
filenames). Two readers (re-entrant timer + manual click coincidence)
are fine — `_walk_queue_and_retry` uses `Path.unlink(missing_ok=True)`
on success; a file already deleted by another thread is ignored. Two
deletes of the same file is impossible because a file is consumed
once: send-success → unlink — and parsing-failure → quarantine via
`os.replace`. The first thread to act on a given file wins; second
thread gets either unlink-of-missing-file (silently OK) or
replace-of-missing-source (raises FileNotFoundError, caught).

### 3.6 Crash flow + SMTP timeout

For CRITICAL (uncaught exception → process terminating):

1. Decorator's outer except logs ERROR. Re-raises.
2. wxPython catches → `OnExceptionInMainLoop` runs on main thread.
3. `_emit_critical(...)` writes the CRITICAL line to today's
   exceptions.log. This is the Sprint 11 path — **unchanged**.
4. **NEW (Sprint 12)**: same hook, after `_emit_critical`, calls
   `enqueue_email_for_severity("CRITICAL", headline=..., body_extra=tb,
   handler_name=...)`. This:
   - Builds payload dict.
   - Calls `_serialize_payload_to_disk(payload, queue_dir)` — atomic
     write. File now exists on disk.
   - Calls `_attempt_send(payload)` **synchronously** with the 10-s
     `SMTP_TIMEOUT_SECONDS` timeout. If success, deletes the queue
     file. If failure, leaves the queue file (retry will pick it up).
   - **Why synchronous in the CRITICAL path** (vs threaded for retry):
     the process is terminating. A daemon thread spawned in
     `OnExceptionInMainLoop` may be killed mid-SMTP-handshake when
     the process exits ~milliseconds later. Synchronous send gives
     the email a fighting chance; the 10-s SMTP timeout caps the
     "user waiting on dying app" duration at 10 s worst case.
   - **What user sees during these 10 s**: the wx event loop has
     already returned `False` from `OnExceptionInMainLoop` and is
     unwinding. The UI is no longer responsive (it's dying). The 10-s
     synchronous send is "the app appears frozen for 10 s before
     closing" — acceptable, because the alternative is "the email
     never sends because the daemon thread was killed".
5. Hook returns `False` → wx event loop exits → process unwinds.

For ERROR (decorator outer except → caught & re-raised):

1. Decorator's outer except logs ERROR (Sprint 11 path).
2. **NEW (Sprint 12)**: same outer except, after `_emit_error`, calls
   `enqueue_email_for_severity("ERROR", headline=..., body_extra=tb,
   handler_name=func.__name__)`. Synchronous serialize + attempt send.
   If send succeeds, queue file is deleted (no leftover). If fails,
   queue file remains for retry.
3. Decorator re-raises. **NOTE**: control flow then goes back to
   wxPython, which calls `OnExceptionInMainLoop`. That hook also
   enqueues — for the SAME exception. Result: TWO emails per uncaught
   exception (one ERROR-tagged from decorator, one CRITICAL-tagged
   from hook). **This is acceptable**: ADR-007 §3 already documents
   that one uncaught exception produces two log lines (ERROR +
   CRITICAL); two corresponding emails are the email-side parallel.
   Tomasz triages on subject prefix and groups by handler name.
   PRD-006 §"App killed mid-send" explicitly accepts duplicate-email
   tolerance.

For ERROR (manual `log_error` from inner except → recovers):

1. Inner except calls `log_error(e, context=...)` — writes ERROR
   `[source=manual]` line to exceptions.log. Sprint 11 path.
2. **`log_error` does NOT enqueue email** (this ADR's load-bearing
   call — see §4.1). The handler's recovery path runs (dialog,
   return). Quiet on email channel.

For manual red button (PRD-006 §"Manual ... red button"):

1. Click → `enqueue_email_for_severity("REPORT", headline="User
   manually requested a report.", handler_name="_user_requested_report")`.
2. Same sync-send-with-timeout path. On send fail, in-app feedback
   per ADR-009 (toast or status bar).

**SMTP timeout = 10 s**: long enough to handle real-network slowness,
short enough that a hung connection during a CRITICAL crash doesn't
hang the dying app for minutes. Configurable constant
`SMTP_TIMEOUT_SECONDS`; trivially tunable post-shipping.

### 3.7 `_attempt_send` — the actual SMTP call

```python
def _attempt_send(payload: Dict[str, Any]) -> bool:
    """Build MIME message + connect + login + send. Return True on success.

    Self-recovery: NEVER raises. Returns False on any failure. Calls
    log_error best-effort to record the failure (with redacted SMTP
    error message — credentials must not leak into the exception log).
    """
    try:
        if not is_email_configured():
            return False  # Channel disabled; queue file remains.

        recipient = _read_recipient()
        password = _read_password()
        # SECRET DISCIPLINE: do not echo recipient or password into log lines.
        # The recipient address is settings-level (PRD-006 says it's not a
        # secret), but echoing it into logs creates a PII-leak surface for
        # the screenshot-heavy ticket workflow Tomasz uses; suppress.

        msg = email.message.EmailMessage()
        msg["From"] = recipient
        msg["To"] = recipient
        msg["Subject"] = payload["subject"]

        body_lines = [
            payload["headline"],
            "",
            f"Severity: {payload['severity']}",
            f"Handler: {payload.get('handler_name', '(none)')}",
            f"Created: {payload['created_iso']}",
        ]
        if payload.get("body_extra"):
            body_lines.append("")
            body_lines.append(payload["body_extra"])
        msg.set_content("\n".join(body_lines))

        # Attach today's logs (or whatever the payload references).
        total_attached = 0
        for path_str in payload.get("attachments", []) or []:
            p = Path(path_str)
            if not p.exists():
                continue
            data, fname = _truncate_attachment_if_oversize(p, JOURNEY_LOG_TAIL_BYTES)
            msg.add_attachment(
                data,
                maintype="text",
                subtype="plain",
                filename=fname,
            )
            total_attached += 1
            if total_attached >= 4:   # safety cap; we ship at most 2
                break

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT_SSL,
                              timeout=SMTP_TIMEOUT_SECONDS) as srv:
            srv.login(recipient, password)
            srv.send_message(msg)
        return True

    except Exception as e:
        # Redacted error class only — never str(e) (could echo password
        # if smtplib's exception text accidentally embeds it; defense
        # in depth).
        try:
            log_error(
                RuntimeError(f"SMTP send failed: {type(e).__name__}"),
                context="email_helper._attempt_send",
            )
        except Exception:
            pass   # log_error is best-effort itself.
        return False
```

`_truncate_attachment_if_oversize` reads the tail of journey.log if the
file size exceeds `JOURNEY_LOG_TAIL_BYTES`; otherwise reads whole.
Filename in attachment = source filename (so Tomasz sees
`2026-05-10__journey.log` in the attachment list).

PRD-006 §"Disk full" recursion-risk addressed: `_attempt_send` calls
`log_error` on send failure. If `log_error` itself raises, the bare
`except Exception: pass` swallows. There is **no path** by which
`_attempt_send`'s failure handler enqueues an email — the function does
not call `enqueue_email_for_severity`. The recursion door is closed by
construction.

### 3.8 Self-recovery — top-level wrap

Every public function in `helpers/email_helper.py` is wrapped:

```python
def enqueue_email_for_severity(severity, headline, body_extra=None,
                               handler_name=None, attachments=None) -> None:
    try:
        # ... real work ...
    except Exception:
        return   # NEVER crash the app. PRD-006 implicit; ADR-006 explicit.
```

No exception escapes the email_helper module. If the disk is full and the
queue file can't be written, return silently — the log line is still
on disk (Sprint 11 wrote it before email tried), Tomasz can manually
email if he can reach the machine. PRD-006 calls this out as the
documented degraded mode.

### 3.9 Subject + body templates

**Subject** (single-line, sortable in Gmail):

```
SUBJECT = "[PyTreeManager " SEVERITY "] " HANDLER " @ " WALL_CLOCK
SEVERITY = "ERROR" | "CRITICAL" | "REPORT"
HANDLER  = handler_name (decorator) | "OnExceptionInMainLoop" (hook) |
           "_user_requested_report" (red button) |
           "(none)" (any other case)
WALL_CLOCK = "%Y-%m-%d %H:%M"   # minute-precision; second-precision is noise
```

Concrete examples:

```
[PyTreeManager ERROR] on_save_click @ 2026-05-10 14:32
[PyTreeManager CRITICAL] OnExceptionInMainLoop @ 2026-05-10 14:32
[PyTreeManager REPORT] _user_requested_report @ 2026-05-10 14:33
```

**Body** (plain text, no HTML — PRD-006 lockdown):

```
KeyError: 'uid-cafef00d' in on_save_click

Severity: ERROR
Handler: on_save_click
Created: 2026-05-10T14:32:11+02:00

  Traceback (most recent call last):
    File "frames/add_person_frame.py", line 883, in on_save_click
      self._tree_service.save_person_and_add_to_tree(person_data)
    ...
  KeyError: 'uid-cafef00d'
```

For manual REPORT-tagged emails the body's first line restates the
fact-of-being-manual:

```
User manually requested a report. Currently loaded person: Anna Staluszka.

Severity: REPORT
Handler: _user_requested_report
Created: 2026-05-10T14:33:02+02:00
```

Person context for the manual case is read from
`helpers.logger._last_known_person_label` at click time (same module
state the journey log uses).

## 4. Key design decisions

### 4.1 `log_error()` does NOT auto-enqueue email (Option b)

This is the **load-bearing call** the dispatch flagged. Three options
were on the table:

- **(a)** Yes — every `log_error()` call queues an email.
- **(b)** No — only decorator outer-except + sys.excepthook +
  OnExceptionInMainLoop + manual button trigger email. `log_error()`
  writes log only.
- **(c)** Configurable per call — `log_error(exc, context, escalate=True)`.

**Picked (b).** Reasoning:

1. **Volume control / signal-to-noise**. The catch-site sweep already
   populated 10 inner-except sites with `log_error` calls (Sprint 11
   plan Item 8). These sites are *recovery-from-known-failure-modes*:
   draft-corruption, root-not-set, rebuild-failed, save-failed-with-
   user-dialog. Each is a "user clicked X, X is unavailable, app
   recovered cleanly". Auto-emailing all of them would produce a
   per-click email storm if the user retries (e.g., father clicks
   "Refresh Drzewo" three times because the message wasn't visible —
   three emails for three correctly-handled errors). PRD-006
   §"Trigger model" already accepts no-rate-limit; `log_error`
   auto-escalation would compound the spam risk.

2. **Severity semantics**. ADR-007 distinguishes `[source=decorator]`
   (escapee, app-may-die) from `[source=manual]` (caught, app-lives).
   The decorator-source IS the "we lost control" signal — the email
   trigger. The manual-source IS the "we kept control" signal — the
   log-only signal. Auto-emailing manual-source dilutes the meaning.

3. **Sprint 11 contract preservation**. Sprint 11 ADR-006 §3.10 docs
   `log_error` as "MUST NOT raise; use inside an inner except that
   catches and recovers". Adding email-enqueue to this contract
   widens the surface. `enqueue_email_for_severity` is explicitly a
   different function; callers that DO want to escalate can call both.

4. **PRD-006 ambiguity tilt**. PRD-006 §"Trigger model" says "ERROR
   events → automatic email" without naming source. The PRD's worked
   example for the trigger ("Caught exceptions where the app notified
   the user and continued running") sounds like the manual-source
   case AT FIRST READ. But the next sentence — "The user keeps using
   the app; the email goes out opportunistically in the background" —
   describes the decorator-outer-except path more accurately
   (decorator catches → re-raises → main loop continues if hook
   chooses, OR app terminates if hook returns False). The
   manual-source case IS "user keeps using the app", but its
   email-storm potential makes it the wrong default. **If I'm wrong
   here, this is the spot to revisit** — it's
   `iterates_with_user: true`-eligible.

5. **Option (c) (per-call flag) is rejected** as introducing churn:
   every existing catch site would need a `escalate=True/False`
   decision, adding cognitive load to the inner-except authors.
   Better to have ONE policy that holds, with a separate call to
   `enqueue_email_for_severity` if a specific catch site genuinely
   needs both.

**What this means for the catch-site sweep that Sprint 11 already
shipped**: NO CHANGE. The 10 existing `log_error(e, context=...)` calls
in `add_person_frame.py` continue to do exactly what they do today —
write one ERROR line `[source=manual]` to today's exceptions.log. They
do NOT email. If a future sprint decides one of those sites SHOULD
email, it gains a second line: `enqueue_email_for_severity("ERROR",
...)`. Explicit, opt-in, per site.

**What this means for the decorator's outer except** (the path that
ALREADY emails per this ADR): Sprint 12 Item 4 wires
`enqueue_email_for_severity("ERROR", ...)` into the decorator's outer
except, AFTER `_emit_error` (logging stays first; email is the
escalation downstream of logging).

**What this means for `OnExceptionInMainLoop` and `sys.excepthook`**:
both wire `enqueue_email_for_severity("CRITICAL", ...)` AFTER
`_emit_critical`. Same shape.

### 4.2 SSL on 465 vs STARTTLS on 587

Picked SSL (§3.2 above). Decision-revisitable if Gmail deprecates 465
(no signal that this is happening); the swap to STARTTLS is ~5 LOC.

### 4.3 JSON queue file (vs plain-text headers)

Picked JSON (§3.4 above). Decision-revisitable if the queue file
schema needs to evolve in a way JSON makes painful — but at v1 the
schema is dead simple and JSON gives free corruption detection.

### 4.4 Threaded send for retry, synchronous send for crash path

Picked split (§3.5 + §3.6). The retry timer is the high-volume path
(walks queue every 30 min, sometimes N>1) and MUST NOT block UI; the
crash path is one-shot and MUST give the email a chance before the
process dies. Different constraints, different mechanisms.

### 4.5 Single env-var for both `From` and `To`

PRD-006 §"Email payload" says "From: same Gmail address (Gmail SMTP
requires `From == authenticated user`)" and "To: Tomasz's Gmail
address". For Tomasz-emails-himself (single-user-bridge-app
constraint), these are the same address. Picked: one env var
`PYTREEMANAGER_EMAIL_RECIPIENT` doubles as both. Decision-revisitable
if Tomasz wants to send from a separate Gmail account; trivial to
split into `PYTREEMANAGER_EMAIL_SENDER` + `PYTREEMANAGER_EMAIL_RECIPIENT`.

## 5. Worked examples (full traces)

### 5.1 CRITICAL crash, online — the canonical path

Setup: father clicks "Zapisz" → `on_save_click` → uncaught `KeyError`.
Network is up. App terminates after the email goes out.

Trace:

1. Decorator INFO line written to journey.log: `[2026-05-10 14:32:11]
   [INFO] [Person: New] User clicked 'Save person (new)'`.
2. Handler raises `KeyError`.
3. Decorator outer except catches. `_emit_error(...)` writes ERROR
   line `[source=decorator] handler=on_save_click KeyError: ...`
   plus payload + traceback to today's exceptions.log.
4. **Sprint 12 NEW**: decorator outer except calls
   `enqueue_email_for_severity("ERROR", headline="KeyError: ...",
   body_extra=tb, handler_name="on_save_click",
   attachments=[journey, exceptions])`.
5. `enqueue_email_for_severity`:
   - Builds payload dict.
   - `_serialize_payload_to_disk` writes `pending_email_<uuid>.json`
     to `<root>/logs/pending/`.
   - `_attempt_send(payload)`: SMTP_SSL connect succeeds; login
     succeeds; send_message succeeds. Returns True.
   - Email file deleted from `pending/` (pending dir now empty).
6. Decorator re-raises KeyError.
7. wxPython catches → `OnExceptionInMainLoop`.
8. `_emit_critical(...)` writes CRITICAL line to exceptions.log.
9. **Sprint 12 NEW**: hook calls `enqueue_email_for_severity("CRITICAL",
   ...)`. Same path: serialize, attempt, succeed, delete. Tomasz now
   has two emails: `[ERROR] on_save_click @ 14:32` and
   `[CRITICAL] OnExceptionInMainLoop @ 14:32`. Both attach the same
   two log files; the CRITICAL one is the proof-of-termination, the
   ERROR one is the diagnostic-with-payload.
10. Hook returns False. App terminates.

Net evidence Tomasz receives: 2 emails in inbox within ~seconds.
Logs are also on disk in `<root>/logs/`; pending dir is empty. The
journey.log + exceptions.log show the same evidence the email body
already contains (subject filtering for `[CRITICAL]` finds the
termination event).

### 5.2 CRITICAL crash, offline — queue + retry

Setup: same as 5.1, but father's wifi just dropped. Network is down.

Trace:

1-3 same as 5.1 (decorator INFO, ERROR; logs written normally — local
disk doesn't need network).
4. Decorator calls `enqueue_email_for_severity("ERROR", ...)`.
5. Serialize: `pending_email_<uuid_A>.json` written. Pending dir
   contains 1 file.
6. `_attempt_send`: `smtplib.SMTP_SSL(host, port, timeout=10)` raises
   `socket.gaierror` (DNS failure offline) or `socket.timeout` after
   10 s, or `ConnectionRefusedError` if a captive-portal returns ICMP
   reject. Caught by `_attempt_send`'s outer except. Returns False.
7. Pending file remains on disk (queue file was never deleted because
   send didn't succeed).
8. **Best-effort send-failure log**: `_attempt_send` calls
   `log_error(RuntimeError("SMTP send failed: gaierror"),
   context="email_helper._attempt_send")`. ERROR line `[source=manual]`
   appended to exceptions.log. (No recursion — `log_error` per §4.1
   does NOT enqueue email.)
9. **User notification on send failure**: email_helper signals the failure
   via a small return-value side channel — see ADR-009 §"Click
   feedback" for how the red-button UI reads it; for the
   decorator/hook paths, the failure signal is silent (the user
   already saw the dialog from the inner except, or the app already
   crashed). PRD-006 §"User notification on send-failure" calls for
   a toast for the manual case; auto-fire ERROR/CRITICAL paths
   don't toast (would be noise on top of the existing dialog/crash).
10. Decorator re-raises. Hook fires. Logs CRITICAL.
11. **Sprint 12 NEW**: hook calls `enqueue_email_for_severity
    ("CRITICAL", ...)`. Serialize: `pending_email_<uuid_B>.json`
    written (pending dir now contains 2 files). `_attempt_send`
    fails again (still offline). Both files remain.
12. Hook returns False. App terminates with 2 pending files on disk.

15 minutes pass. Father reopens the app (or app stays closed; the
machine reboots; whatever).

13. App starts. `OnInit` runs: `init_logging`, `cleanup_old_logs`,
    AddPersonFrame, **`start_retry_timer(self)`**. Timer registered
    on the LoggingApp; first tick will be 30 minutes from now.

Approximately 30 minutes later (or however long until the first tick
post-reconnect):

14. Father's wifi is back. Timer fires (`Notify`).
15. `Notify` callback: queue dir exists, has 2 pending files →
    spawn worker thread `email_helper-retry`.
16. Worker thread runs `_walk_queue_and_retry(queue_dir)`. For each
    pending file:
    - Open + `json.load`. If parse fails → quarantine
      (`pending/quarantine/`).
    - Call `_attempt_send(payload)`. Network is up; succeeds.
    - `Path.unlink(missing_ok=True)` on the queue file. Pending dir
      is now empty.
17. Tomasz receives both emails ~30 minutes after the original crash.
    Both contain the journey + exceptions logs from the day-of-crash
    (paths in payload still resolve; logs still exist because they're
    only 14-day-cleaned).

### 5.3 Red-button click, online (preview — full ADR-009)

Setup: father clicks the red button at the top of the app.

1. Click handler (decorated `@log_user_action("Send error report
   (manual)")`). Decorator INFO line written: `[INFO] [Person:
   Anna Staluszka] User clicked 'Send error report (manual)'`.
2. Handler body calls `enqueue_email_for_severity("REPORT",
   headline="User manually requested a report. Currently loaded
   person: Anna Staluszka.", handler_name="_user_requested_report",
   attachments=[journey, exceptions])`.
3. Serialize → write `pending_email_<uuid>.json`. Attempt send.
4. Send succeeds → file deleted.
5. Handler shows status-bar message "Raport wysłany." (per
   ADR-009 §"Click feedback"). 1.5-second auto-dismiss.

Father sees the status message; clicks elsewhere. Tomasz gets
`[PyTreeManager REPORT] _user_requested_report @ ...` in his inbox.

### 5.4 Red-button click, offline (the user's stated scenario)

Setup: same click, network down.

1-3 same as 5.3, except `_attempt_send` returns False.
4. Queue file remains on disk.
5. Handler shows status-bar message "Raport w kolejce, zostanie
   wysłany gdy będzie dostępny internet." (per ADR-009).
6. ~30 min later (or whenever wifi returns + next tick), retry
   succeeds, file deleted.

### 5.5 Disk full during enqueue (defensive trace)

Setup: ERROR fires, but `<root>/logs/pending/` is on a full volume.

1. Decorator ERROR line attempt — logger's lock-retry-cap-99 chain
   may itself fail; that's already handled by Sprint 11 silent-fall-
   through.
2. `enqueue_email_for_severity("ERROR", ...)` called.
3. `_serialize_payload_to_disk` raises `OSError: No space left on
   device` during the `tmp_path.open("w")` line. Caught by
   `enqueue_email_for_severity`'s top-level try/except. Returns None
   silently.
4. **No re-queue, no recursion**. The function does not call
   `_attempt_send` because serialize failed. Email is lost; logs
   may also be partial (depending on lock-retry result). User can
   manually email logs once disk is freed.
5. App continues normally (decorator re-raise still happens; the
   email failure didn't introduce a new exception).

This is the "documented degraded mode" PRD-006 §"Disk full"
references.

## 6. Dependency directionality + Sprint 11 contract preservation

```
                  ┌─────────────────────┐
                  │  helpers/logger.py  │  (Sprint 11 — UNCHANGED contract)
                  │  log_user_action,   │
                  │  log_error,         │
                  │  _emit_*,           │
                  │  init_logging,      │
                  │  cleanup_old_logs   │
                  └──────────▲──────────┘
                             │
                  reads logger paths;
                  calls log_error best-effort
                  on send failure (no recursion)
                             │
                  ┌──────────┴──────────┐
                  │ helpers/email_helper.py  │  (Sprint 12 NEW)
                  │  enqueue_email_*,   │
                  │  start_retry_timer, │
                  │  _attempt_send,     │
                  │  _walk_queue_*,     │
                  │  _serialize_*       │
                  └──────────▲──────────┘
                             │
                  ┌──────────┴────────────────┐
                  │                            │
        decorator outer except         OnExceptionInMainLoop
        (in helpers/logger.py —        (in helpers/logger.py —
        Sprint 12 Item 4 EXTENSION)    Sprint 12 Item 4 EXTENSION)
                                       sys.excepthook hook (same)
                                       red button click handler (ADR-009)
```

**Logger module is NOT modified at the public-surface level**. Sprint
12 adds two NEW import-time hooks inside the existing decorator and
hook code paths — but the additions are behind `try: from
helpers.email_helper import enqueue_email_for_severity / except
ImportError: pass` so the logger remains importable independently of
the email_helper (Halt-E parity).

**Catch sites that already call `log_error`**: untouched. They
continue to log only; they do NOT email per §4.1.

## 7. Alternatives considered

### 7.1 Use `aiosmtplib` (async SMTP)

Rejected. Adds a dependency; introduces an event loop the wxPython app
doesn't otherwise need; the threading approach (§3.5) is simpler and
sufficient for the volume profile (1-10 emails/day at most).

### 7.2 Bake retry into the decorator itself (no separate timer)

Rejected. Would mean every UI click that fires after a previously-
queued failure attempts to drain the queue — couples retry to user
activity, which is exactly the offline-tolerance PRD-006 says to
avoid (father may not click anything for hours during a long
background-stretch).

### 7.3 Use Windows Task Scheduler instead of wx.Timer

Rejected. Would require an out-of-process worker, install-time setup,
elevated privileges to register a task. wx.Timer in-process is simpler
and matches PRD-006's locked decision.

### 7.4 Always poll (regardless of queue empty)

Rejected per PRD-006 §"Periodic retry" decision. Already locked.

### 7.5 Encrypt queue files at rest

Rejected. Trust boundary is "the user's own machine"; PRD-006 already
locks logs as plain text; queue files contain log-derived data plus
attachment paths, no incremental sensitivity. Adding encryption adds
key management with no security benefit at this trust boundary.

### 7.6 OAuth refresh-token instead of App Password

Rejected for v1. App Password is the path of least resistance Tomasz
already runs in his existing patterns. OAuth refresh is the upgrade
path for "App Password is going away" (Google has signaled this for
some workspace flows) — but for personal Gmail, App Password is still
the documented option as of 2026. Decision-revisitable if Google
deprecates personal-Gmail App Passwords.

### 7.7 Auto-enqueue on every `log_error` (Option a)

Rejected per §4.1.

### 7.8 Per-call `escalate=True` flag on `log_error` (Option c)

Rejected per §4.1.

## 8. Pre-Implementor self-check (architect, 2026-05-10)

Per Sprint 09 + Sprint 11 retro lessons — example ↔ pseudocode parity
checks:

**Worked example 5.1 (CRITICAL online)**:
- §3.7 `_attempt_send` pseudocode shows SMTP_SSL connect + login +
  send_message + return True. Trace step 5 produces `True`. ✓
- §3.6 says "decorator outer except calls enqueue after _emit_error".
  Trace step 4 puts enqueue AFTER step 3's `_emit_error`. ✓
- §3.6 also says "OnExceptionInMainLoop calls enqueue after
  _emit_critical". Trace step 9 puts enqueue AFTER step 8's
  `_emit_critical`. ✓
- §3.6 documents "two emails per uncaught exception". Trace step 10
  produces 2 emails. ✓

**Worked example 5.2 (CRITICAL offline + retry)**:
- §3.5 timer pseudocode walks queue when non-empty, spawns daemon
  thread `_walk_queue_and_retry`. Trace step 16 follows that. ✓
- §3.4 atomicity: write-then-rename; reader sees nothing-or-complete.
  Trace step 5 (write) and step 16 (read) align. ✓
- §3.7 `_attempt_send` redaction: catches send failure, calls
  `log_error(RuntimeError("SMTP send failed: gaierror"), ...)`.
  Trace step 8 names that exact pattern. ✓
- §4.1 says `log_error` does NOT enqueue email. Trace step 8 shows
  log_error called from inside `_attempt_send`; trace does NOT then
  show another enqueue. ✓ (No recursion.)

**Worked example 5.3-5.4 (red button)**:
- ADR-009 §"Click handler" must produce a handler that calls
  `enqueue_email_for_severity("REPORT", ...)`. Trace step 2 of 5.3
  matches. ✓ (Cross-ADR check; the actual handler code lives in
  ADR-009.)

**Worked example 5.5 (disk full)**:
- §3.8 self-recovery contract: `enqueue_email_for_severity` wrapped
  in top-level try/except; never raises. Trace step 3 swallows the
  OSError. ✓
- §4.1 + §3.7 no-recursion property: serialize failure does NOT
  re-enqueue. Trace step 4 confirms no second enqueue attempt. ✓

**Cross-check — env var names appear consistently**:
- §3.1 constants block: `EMAIL_PASSWORD_ENV_VAR =
  "PYTREEMANAGER_EMAIL_PASSWORD"`, `EMAIL_RECIPIENT_ENV_VAR =
  "PYTREEMANAGER_EMAIL_RECIPIENT"`. ✓
- §3.3 table: same two names. ✓
- §3.7 `_attempt_send` reads via `_read_recipient` / `_read_password`
  helpers (which read those constants). ✓ no string-literal drift.

**Cross-check — `attachments` field round-trips**:
- §3.4 schema: `"attachments": [absolute path strings]`.
- §3.7 `_attempt_send`: `for path_str in payload.get("attachments",
  []) or []: p = Path(path_str)`.
- §5.1 trace step 4: builder passes `attachments=[journey,
  exceptions]` (Path objects).
- **MISMATCH FLAG**: payload passes Path objects in via the public
  `enqueue_email_for_severity` API but `_serialize_payload_to_disk`
  has to JSON-serialize them. Path objects aren't JSON-serializable
  by default. Resolution: builder converts to `str(p)` before
  serialize; `_attempt_send` converts back via `Path(path_str)`.
  **Documented here so Implementor doesn't trip**: in
  `_build_email_payload`, do `[str(p) for p in (attachments or [])]`.
  ✓ Captured.

**Cross-check — wx.Timer parent ownership**:
- §3.5 `start_retry_timer(host_window)` parents the timer to
  host_window.
- LoggingApp.OnInit calls `start_retry_timer(self)` — `self` is the
  LoggingApp instance. wx.Timer accepts `wx.EvtHandler` as parent
  (which `wx.App` is). ✓
- PRD-006 §"Periodic retry" warning: "If the implementation
  accidentally parents it to the add-person frame and the frame
  closes, the queue stops draining". §3.5 explicitly forbids that;
  verified parent = LoggingApp. ✓

**Failure mode end-to-end trace** (dispatch self-read item #2):

Picked: "User clicks red button → no internet → queue file written →
timer fires 30 min later when network is back → email sends → queue
file deleted."

1. Click → handler → `enqueue_email_for_severity("REPORT", ...)`.
2. Build payload with `severity="REPORT"`, `headline="User manually
   requested..."`, `handler_name="_user_requested_report"`,
   `attachments=[absolute paths to today's two log files]`.
3. `_serialize_payload_to_disk` writes `pending_email_<uuid>.json.tmp`,
   `os.replace` to `pending_email_<uuid>.json`. File on disk.
4. `_attempt_send`: `smtplib.SMTP_SSL("smtp.gmail.com", 465,
   timeout=10)` raises `socket.gaierror` after DNS fails (offline
   machines fail fast on DNS — no 10-s wait). Returns False.
5. ADR-009 click handler reads the False return, shows status-bar
   message "Raport w kolejce, zostanie wysłany gdy będzie dostępny
   internet."
6. Time passes. App stays open; LoggingApp's `_email_retry_timer`
   keeps firing every 30 minutes. Each tick: queue dir exists, has
   1 pending file → spawn daemon thread.
7. Each pre-online tick: `_attempt_send` returns False (still
   offline); file remains. No spam to user (UI is silent on retry
   failures).
8. Father's network returns. The next 30-min tick (worst case 30
   minutes after wifi returned, best case immediately): worker
   thread `_walk_queue_and_retry` sees the pending file, opens it,
   `json.load` parses cleanly. Calls `_attempt_send`. SSL connect
   succeeds. Login succeeds (env vars are set, App Password is
   valid). `send_message` succeeds.
9. Worker thread: `Path.unlink(missing_ok=True)` on the queue file.
   File removed. Pending dir is empty.
10. Tomasz's inbox now has `[PyTreeManager REPORT]
    _user_requested_report @ <original click time>`. The email body
    references the click's original timestamp (created_iso in the
    payload), not the retry time — Tomasz sees when the user
    clicked, not when the network came back.

**Halt criterion match**: Sprint 12 plan's halt criterion (a) "actual
SMTP send doesn't hang on bad credentials" — the 10-s timeout on
SMTP_SSL covers this (login failure is a fast SMTPAuthenticationError,
not a hang; bad-host hang is capped at 10 s). Halt criterion (b)
"queue file roundtrip works" — §3.4 atomicity + §3.7 read align.
Halt criterion (d) "timer keeps firing across days-long uptime" — wx
documentation confirms `wx.Timer` continues firing while the parent
event handler (LoggingApp) is alive; we don't stop it except in
OnExit. Verifiable via day-long manual smoke; not in unit-test scope.

## 9. Consequences

**Positive:**
- Push-notification of any ERROR or CRITICAL event reaches Tomasz
  within seconds (online) or within 30-minute retry windows (offline-
  recovered).
- Logger module stays clean: no email knowledge leaked into Sprint 11
  contracts. Sprint 12's email module imports from the logger, not
  vice versa.
- `log_error` API stays a pure-write contract per §4.1; user can
  rely on calls to it being silent on email channel.
- Queue-file format is JSON; corruption-detection is automatic;
  schema-versioned for future evolution.
- Timer parented to LoggingApp survives any frame transition.

**Negative:**
- Two emails per uncaught exception (ERROR + CRITICAL for the same
  event). PRD-006 accepts duplicate-tolerance; Tomasz triages by
  subject prefix.
- Synchronous SMTP send during CRITICAL crash adds up to 10 s of
  "frozen UI before close" worst case. Acceptable; alternative is
  losing the email entirely.
- Daemon thread for retry is not joined on app exit. Worst case is a
  truncated SMTP transaction — retried next launch. No corruption.
- New dependency on `smtplib` (stdlib) and `email.message` (stdlib).
  Zero external pip dependency added.

**Neutral:**
- Sprint 11's catch-site sweep stays exactly as-shipped per §4.1;
  no rewriting needed.
- Quarantine dir at `<root>/logs/pending/quarantine/` is gitignored
  by the existing `logs/` rule — no `.gitignore` change needed.

## 10. Out of scope

- Email rate-limiting (PRD-006 v1 explicitly accepts no limit).
- Encrypted email body or attachment.
- Multi-recipient send.
- HTML body.
- Read receipts / delivery confirmations.
- OAuth / refresh-token flow (App Password only).
- Outlook / non-Gmail providers.
- Email-channel health dashboard.
- Sweeping or modifying any existing Sprint 11 catch site (§4.1
  load-bearing decision: NO CHANGES to Sprint 11 catch sites).

## 11. Sources

- `PRD-006-email-escalation-and-offline-queue.md` — scope contract;
  red-button amendment 2026-05-09.
- `ADR-006-logging-architecture-decorator-and-exception-hooks.md` —
  Sprint 11 substrate; §3.10 `log_error` API contract preserved.
- `ADR-007-severity-model-and-log-line-format.md` — severity
  enumeration; §4.1 references the [source=decorator|manual] split.
- JOURNAL 2026-05-09 orchestrator entry "Sprint 11+12+13 scope intake"
  — Gmail SMTP App Password, opportunistic delivery, offline queue,
  wx.Timer 30-min retry, offline-tolerance constraint.
- JOURNAL 2026-05-09 orchestrator amendment "red button not menu
  entry".
- https://docs.python.org/3/library/smtplib.html — SMTP_SSL,
  send_message, timeout parameter, exception classes.
- https://docs.python.org/3/library/email.message.html —
  EmailMessage, set_content, add_attachment.
- https://support.google.com/accounts/answer/185833 — Gmail App
  Password reference (verified URL renders 2026-05-10; reference
  page, not a UI walkthrough — vendor-UI rot risk minimal).
- https://support.google.com/mail/answer/7126229 — Gmail SMTP server
  settings (port 465 SSL, port 587 STARTTLS).
- https://wiki.wxpython.org/wxTimer — wx.Timer API + Notify callback
  semantics.
- https://docs.wxpython.org/wx.Timer.html — wx.Timer Start/Stop +
  parent-handler ownership.
- `helpers/logger.py` lines 540-594 — `_build_logging_app_class` +
  module `__getattr__` deferred-import pattern; this ADR's
  `OnInit`/`OnExit` extension piggybacks that pattern.
- `frames/add_person_frame.py` lines 880, 895, 939, 957, 1181, 1203,
  1263, 1434, 1472, 1500 — the 10 existing `log_error` catch sites
  that §4.1's no-auto-escalate decision preserves.
