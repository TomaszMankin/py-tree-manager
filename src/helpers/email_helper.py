"""Email escalation module for py-tree-manager.

Three triggers fire email:
  (a) decorator outer-except (ERROR, source=decorator)
  (b) CRITICAL hooks (OnExceptionInMainLoop + sys.excepthook)
  (c) red-button manual click (REPORT)

log_error() is NOT auto-escalated.

Public surface (via EmailHelper static class):
  EmailHelper.is_email_configured() -> bool
  EmailHelper.enqueue_email_for_severity(severity, headline, body_extra,
                                            handler_name, attachments) -> bool
  EmailHelper.start_retry_timer(host_window) -> wx.Timer
  EmailHelper.stop_retry_timer(timer) -> None

Internal helpers are prefixed with _ but exported for tests.
"""

from __future__ import annotations

import datetime
import email.message
import json
import os
import smtplib
import socket
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

EMAIL_PASSWORD_ENV_VAR = "PYTREEMANAGER_EMAIL_PASSWORD"
EMAIL_RECIPIENT_ENV_VAR = "PYTREEMANAGER_EMAIL_RECIPIENT"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT_SSL = 465
SMTP_TIMEOUT_SECONDS = 10
RETRY_INTERVAL_MINUTES = 30
RETRY_INTERVAL_MS = RETRY_INTERVAL_MINUTES * 60 * 1000   # 1_800_000
GMAIL_ATTACHMENT_LIMIT_BYTES = 25 * 1024 * 1024          # 25 MB
JOURNEY_LOG_TAIL_BYTES = 1 * 1024 * 1024                 # 1 MB tail cap
PENDING_DIR_NAME = "pending"
PENDING_FILENAME_PREFIX = "pending_email_"
PENDING_FILENAME_SUFFIX = ".json"
QUARANTINE_DIR_NAME = "quarantine"
EMAILABLE_SEVERITIES: frozenset = frozenset({"ERROR", "CRITICAL", "REPORT"})


# ---------------------------------------------------------------------------
# Env-var helpers
# ---------------------------------------------------------------------------

def _read_password() -> Optional[str]:
    """Return the Gmail App Password from env, stripped; None if unset/empty."""
    val = os.environ.get(EMAIL_PASSWORD_ENV_VAR, "").strip()
    return val if val else None


def _read_recipient() -> Optional[str]:
    """Return the recipient address from env, stripped; None if unset/empty."""
    val = os.environ.get(EMAIL_RECIPIENT_ENV_VAR, "").strip()
    return val if val else None


def is_email_configured() -> bool:
    """Return True iff both env vars are set (non-empty)."""
    try:
        return _read_password() is not None and _read_recipient() is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Queue directory helpers
# ---------------------------------------------------------------------------

def _queue_dir() -> Path:
    """Return the path to the pending-email queue directory.

    Prefers <root>/logs/pending; falls back to %LOCALAPPDATA%/PyTreeManager/logs/pending.
    Does NOT create the directory — that is the caller's job.
    """
    try:
        # Delegate to helpers.logger for the effective log dir, then append pending/
        from src.helpers.logger import _effective_log_dir  # type: ignore[import]
        return _effective_log_dir() / PENDING_DIR_NAME
    except Exception:
        # Absolute fallback: %LOCALAPPDATA%
        import tempfile
        base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        return Path(base) / "PyTreeManager" / "logs" / PENDING_DIR_NAME


def _quarantine_dir() -> Path:
    """Return the quarantine sub-directory under the queue dir."""
    return _queue_dir() / QUARANTINE_DIR_NAME


# ---------------------------------------------------------------------------
# Log path helpers (delegate to logger)
# ---------------------------------------------------------------------------

def _today_journey_log_path() -> Path:
    """Return today's journey log path via helpers.logger."""
    try:
        from src.helpers.logger import _today_journey_log_path as _ljp  # type: ignore[import]
        return _ljp()
    except Exception:
        import time
        today = time.strftime("%Y-%m-%d")
        return _queue_dir().parent / f"{today}__journey.log"


def _today_exceptions_log_path() -> Path:
    """Return today's exceptions log path via helpers.logger."""
    try:
        from src.helpers.logger import _today_exceptions_log_path as _lep  # type: ignore[import]
        return _lep()
    except Exception:
        import time
        today = time.strftime("%Y-%m-%d")
        return _queue_dir().parent / f"{today}__exceptions.log"


def _default_attachments() -> List[Path]:
    """Return list of today's log files that exist on disk."""
    candidates = [_today_journey_log_path(), _today_exceptions_log_path()]
    return [p for p in candidates if p.exists()]


# ---------------------------------------------------------------------------
# Attachment helpers
# ---------------------------------------------------------------------------

def _truncate_attachment_if_oversize(
    path: Path, max_bytes: int
) -> Tuple[bytes, str]:
    """Read the tail of path up to max_bytes; return (bytes_data, filename)."""
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > max_bytes:
                fh.seek(-max_bytes, 2)  # Seek to tail
            data = fh.read()
        return data, path.name
    except Exception:
        return b"", path.name


# ---------------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------------

def _build_email_payload(
    severity: str,
    headline: str,
    body_extra: Optional[str],
    handler_name: Optional[str],
    attachments: Optional[List[Path]],
) -> Dict[str, Any]:
    """Build the JSON-serialisable payload dict.

    Attachment paths are stored as absolute strings (Path not JSON-serialisable).
    """
    import time
    now_str = datetime.datetime.now().astimezone().isoformat()
    wall_clock = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    handler_label = handler_name or "(none)"
    subject = f"[PyTreeManager {severity}] {handler_label} @ {wall_clock}"

    attach_paths: List[Path]
    if attachments is None:
        attach_paths = _default_attachments()
    else:
        attach_paths = list(attachments)

    return {
        "schema_version": 1,
        "created_iso": now_str,
        "severity": severity,
        "subject": subject,
        "headline": headline,
        "body_extra": body_extra,
        "handler_name": handler_label,
        # Store as strings so JSON serialisation never sees Path objects.
        "attachments": [str(p) for p in attach_paths],
    }


# ---------------------------------------------------------------------------
# Serialisation (atomic write-then-rename)
# ---------------------------------------------------------------------------

def _serialize_payload_to_disk(
    payload: Dict[str, Any], queue_dir: Path
) -> Optional[Path]:
    """Write payload to queue_dir/<uuid>.json using tmp-then-rename atomicity.

    Returns the final Path on success, None on any failure.
    Never raises.
    """
    tmp_path: Optional[Path] = None
    try:
        queue_dir.mkdir(parents=True, exist_ok=True)
        final_name = f"{PENDING_FILENAME_PREFIX}{uuid.uuid4()}{PENDING_FILENAME_SUFFIX}"
        tmp_path = queue_dir / (final_name + ".tmp")
        final_path = queue_dir / final_name

        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except (OSError, AttributeError):
                pass

        os.replace(tmp_path, final_path)
        return final_path
    except Exception:
        # Clean up dangling .tmp if possible
        try:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Quarantine
# ---------------------------------------------------------------------------

def _quarantine_payload(payload_path: Path, reason: str) -> None:
    """Move payload_path to the quarantine sub-directory.

    Prevents the retry loop from infinitely re-attempting a corrupt file.
    Never raises.
    """
    try:
        q_dir = payload_path.parent / QUARANTINE_DIR_NAME
        q_dir.mkdir(parents=True, exist_ok=True)
        dest = q_dir / payload_path.name
        # Use os.replace so the move is atomic even if dest already exists
        try:
            os.replace(str(payload_path), str(dest))
        except FileNotFoundError:
            pass  # Already gone; no problem.
    except Exception:
        pass


# ---------------------------------------------------------------------------
# SMTP send
# ---------------------------------------------------------------------------

def _attempt_send(payload: Dict[str, Any]) -> bool:
    """Build MIME message + connect + login + send via SMTP_SSL. Return True on success.

    Self-recovery: NEVER raises.  Returns False on any failure.
    Calls log_error best-effort to record the failure with a REDACTED error
    class only (never str(e) — protects against credential leak in exception text).
    Does NOT call enqueue_email_for_severity (no recursion).
    """
    try:
        if not is_email_configured():
            return False

        recipient = _read_recipient()
        password = _read_password()

        msg = email.message.EmailMessage()
        msg["From"] = recipient
        msg["To"] = recipient
        msg["Subject"] = payload.get("subject", "[PyTreeManager]")

        body_lines = [
            payload.get("headline", ""),
            "",
            f"Severity: {payload.get('severity', '?')}",
            f"Handler: {payload.get('handler_name', '(none)')}",
            f"Created: {payload.get('created_iso', '?')}",
        ]
        if payload.get("body_extra"):
            body_lines.append("")
            body_lines.append(payload["body_extra"])
        msg.set_content("\n".join(body_lines))

        total_attached = 0
        for path_str in payload.get("attachments", []) or []:
            p = Path(path_str)
            if not p.exists():
                continue
            data, fname = _truncate_attachment_if_oversize(p, JOURNEY_LOG_TAIL_BYTES)
            if data:
                msg.add_attachment(
                    data,
                    maintype="text",
                    subtype="plain",
                    filename=fname,
                )
                total_attached += 1
                if total_attached >= 4:   # Safety cap; we ship at most 2
                    break

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT_SSL, timeout=SMTP_TIMEOUT_SECONDS) as srv:
            srv.login(recipient, password)
            srv.send_message(msg)
        return True

    except Exception as e:
        # Redacted: only class name, never str(e) (could embed credentials).
        try:
            _safe_log_error(f"SMTP send failed: {type(e).__name__}")
        except Exception:
            pass
        return False


# ---------------------------------------------------------------------------
# log_error proxy — module-level so tests can monkeypatch email_helper_module.log_error
# to intercept send-failure records and verify no-recursion property.
# Python resolves function names at call time, so definition order here is fine.
# ---------------------------------------------------------------------------

def log_error(exc: BaseException, context: Optional[str] = None) -> None:
    """Thin proxy to helpers.logger.log_error.

    Defined at module level so tests can monkeypatch email_helper_module.log_error
    to assert it is called (send-failure record) while verifying that
    enqueue_email_for_severity is NOT called from _attempt_send (no recursion).
    """
    try:
        from src.helpers.logger import log_error as _real_log_error  # type: ignore[import]
        _real_log_error(exc, context=context)
    except Exception:
        pass


def _safe_log_error(msg: str) -> None:
    """Call log_error (proxy) best-effort on SMTP send failure. Never raises.

    Uses only the error class name, never str(e), so SMTP credentials cannot
    leak into the exception log (secret discipline: log class name, never str(e)).
    """
    try:
        log_error(RuntimeError(msg), context="email_helper._attempt_send")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Queue walker
# ---------------------------------------------------------------------------

def _walk_queue_and_retry(queue_dir: Path) -> None:
    """Read every pending_email_*.json in queue_dir and attempt to send each.

    On send success: delete the file.
    On send failure: leave the file (retry next tick).
    On JSON parse failure: move to quarantine/.
    On any other exception per file: skip silently.
    Never raises.
    """
    try:
        pattern = f"{PENDING_FILENAME_PREFIX}*{PENDING_FILENAME_SUFFIX}"
        for p in list(queue_dir.glob(pattern)):
            try:
                try:
                    payload = json.loads(p.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, ValueError):
                    _quarantine_payload(p, reason="json_parse_error")
                    continue

                sent = _attempt_send(payload)
                if sent:
                    try:
                        p.unlink(missing_ok=True)
                    except Exception:
                        pass
            except Exception:
                # Per-file errors must not abort the whole walk.
                pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# wx.Timer retry class
#
# _EmailRetryTimer is a callable (a factory function) that builds and returns
# a wx.Timer subclass instance.  wx is imported lazily when the factory is
# called so the module itself stays wx-free at import time.
#
# Tests monkeypatch email_helper_module._EmailRetryTimer with a MagicMock, which
# is why this is a module-level name rather than a hidden inner function.
# ---------------------------------------------------------------------------

def _build_email_retry_timer_class():
    """Build and return the wx.Timer subclass. Called lazily when wx is available."""
    import wx  # noqa: PLC0415

    class _RealEmailRetryTimer(wx.Timer):
        """wx.Timer that fires _walk_queue_and_retry every 30 minutes."""

        def Notify(self) -> None:  # noqa: N802
            """Called on the wx main thread every RETRY_INTERVAL_MS."""
            try:
                queue_dir = _queue_dir()
                if not queue_dir.exists():
                    return
                pending = list(
                    queue_dir.glob(
                        f"{PENDING_FILENAME_PREFIX}*{PENDING_FILENAME_SUFFIX}"
                    )
                )
                if not pending:
                    return  # Nothing to retry; skip spawning a thread.
                t = threading.Thread(
                    target=_walk_queue_and_retry,
                    args=(queue_dir,),
                    name="email_helper-retry",
                    daemon=True,
                )
                t.start()
            except Exception:
                pass

    return _RealEmailRetryTimer


def _EmailRetryTimer(host_window: Any) -> Any:
    """Factory: build and return a wx.Timer retry instance parented to host_window.

    This is a module-level callable so tests can monkeypatch it with a MagicMock.
    wx is imported lazily inside _build_email_retry_timer_class().
    Never raises.
    """
    cls = _build_email_retry_timer_class()
    return cls(host_window)


# ---------------------------------------------------------------------------
# Public timer API
# ---------------------------------------------------------------------------

def start_retry_timer(host_window: Any) -> Any:
    """Start the 30-minute retry timer parented to host_window.

    Returns the timer object (caller must keep a reference to prevent GC).
    Never raises.
    """
    try:
        timer = _EmailRetryTimer(host_window)
        timer.Start(RETRY_INTERVAL_MS, oneShot=False)
        return timer
    except Exception:
        return None


def stop_retry_timer(timer: Any) -> None:
    """Stop the retry timer. Called from app shutdown. Never raises."""
    try:
        timer.Stop()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def enqueue_email_for_severity(
    severity: str,
    headline: str,
    body_extra: Optional[str] = None,
    handler_name: Optional[str] = None,
    attachments: Optional[List[Path]] = None,
) -> bool:
    """Build email payload, persist to queue, attempt opportunistic send.

    Returns:
      True  — email was sent successfully on the wire.
      False — anything else: queued (offline), channel disabled, write failed,
              or any internal error swallowed by self-recovery.

    Never raises (self-recovery: top-level try/except).
    """
    try:
        payload = _build_email_payload(
            severity=severity,
            headline=headline,
            body_extra=body_extra,
            handler_name=handler_name,
            attachments=attachments,
        )

        queue_dir = _queue_dir()
        queue_path = _serialize_payload_to_disk(payload, queue_dir)
        if queue_path is None:
            # Write failed (disk full, permissions, etc.) — return False silently.
            return False

        sent = _attempt_send(payload)
        if sent:
            try:
                queue_path.unlink(missing_ok=True)
            except Exception:
                pass
            return True
        else:
            # Queue file remains on disk for retry.
            return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# EmailHelper static-method namespace
# ---------------------------------------------------------------------------

class EmailHelper:
    """Email transport, offline queue, and retry timer.

    Static-method namespace grouping — same pattern as UpdateHelper.
    """

    @staticmethod
    def is_email_configured() -> bool:
        """Return True iff both email env vars are set (non-empty)."""
        return is_email_configured()

    @staticmethod
    def enqueue_email_for_severity(
        severity: str,
        headline: str,
        body_extra: Optional[str] = None,
        handler_name: Optional[str] = None,
        attachments=None,
    ) -> bool:
        """Build email payload, persist to queue, attempt opportunistic send."""
        return enqueue_email_for_severity(
            severity=severity,
            headline=headline,
            body_extra=body_extra,
            handler_name=handler_name,
            attachments=attachments,
        )

    @staticmethod
    def start_retry_timer(host_window: Any) -> Any:
        """Start the 30-minute retry timer parented to host_window."""
        return start_retry_timer(host_window)

    @staticmethod
    def stop_retry_timer(timer: Any) -> None:
        """Stop the retry timer. Never raises."""
        stop_retry_timer(timer)
