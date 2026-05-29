"""Diagnostic logging foundation for py-tree-manager.

Two plain-text per-day log files:
  <logdir>/<YYYY-MM-DD>__journey.log    -- INFO lines; one per user action.
  <logdir>/<YYYY-MM-DD>__exceptions.log -- ERROR, CRITICAL, INFO-CLEANUP lines.

Design choices made in this file:
  - wx import isolation: install_python_excepthook() has NO wx import.
    LoggingApp (which subclasses wx.App) is defined further down and IS
    imported at the point wx is available. This keeps the module importable
    before wx is installed (verified by test_a_imports.py).
  - Module-level _last_known_person_label tracks person context across the
    full module; set_current_person_label() updates both the frame sentinel
    and this module-level state.
  - All emit functions wrap their body in bare try/except Exception so a
    logger bug never crashes the app.
"""

from __future__ import annotations

import functools
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TextIO

# ---------------------------------------------------------------------------
# Public constants (exported for tests)
# ---------------------------------------------------------------------------

LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_DATE_FORMAT = "%Y-%m-%d"
LOG_RETENTION_DAYS = 14
LOG_LOCK_RETRY_CAP = 99
PERSON_PLACEHOLDER = "-"

# Save-handler whitelist: handlers in this set get their form payload dumped
# when the decorator catches an unhandled exception.
SAVE_HANDLER_WHITELIST: frozenset = frozenset({
    "on_save_click",
    "on_save_edit_click",
    "on_save_draft_click",
    "on_update_draft_click",   # Zaktualizuj szkic osoby
    "on_promote_draft_click",  # Dodaj szkic osoby do drzewa
})

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_root_log_dir: Optional[Path] = None       # set by init_logging when root known
_active_log_dir: Optional[Path] = None     # actual write target; falls back to %LOCALAPPDATA%
_last_known_person_label: str = PERSON_PLACEHOLDER
_logging_initialized: bool = False


# ---------------------------------------------------------------------------
# Internal path helpers
# ---------------------------------------------------------------------------

def _localappdata_log_dir() -> Path:
    """Return %LOCALAPPDATA%/PyTreeManager/logs, or a tempdir fallback."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "PyTreeManager" / "logs"
    return Path(tempfile.gettempdir()) / "PyTreeManager" / "logs"


def _effective_log_dir() -> Path:
    """Return the currently active log directory (never None)."""
    return _active_log_dir if _active_log_dir is not None else _localappdata_log_dir()


def _today_journey_log_path() -> Path:
    today = time.strftime(LOG_FILE_DATE_FORMAT)
    return _effective_log_dir() / f"{today}__journey.log"


def _today_exceptions_log_path() -> Path:
    today = time.strftime(LOG_FILE_DATE_FORMAT)
    return _effective_log_dir() / f"{today}__exceptions.log"


def _read_global_person_label() -> str:
    """Return the current person label (module-level state), defaulting to placeholder."""
    return _last_known_person_label or PERSON_PLACEHOLDER


# ---------------------------------------------------------------------------
# File-lock self-recovery
# ---------------------------------------------------------------------------

def _open_for_append_with_lock_retry(target_path: Path) -> Optional[TextIO]:
    """Open target_path for UTF-8 append; retry with __N suffixes on lock contention.

    Returns the file handle, or None if all 100 attempts fail.
    Caller falls back to stderr — never crashes the app.
    """
    base = target_path.parent / target_path.stem   # e.g. .../2026-05-09__journey
    suffix = target_path.suffix                    # '.log'

    candidates = [target_path]
    candidates.extend(
        Path(f"{base}__{i}{suffix}") for i in range(1, LOG_LOCK_RETRY_CAP + 1)
    )

    for candidate in candidates:
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            return candidate.open("a", encoding="utf-8", newline="")
        except (PermissionError, OSError):
            continue
        except Exception:
            # Truly unexpected; bail to stderr fallback instead of propagating.
            break

    try:
        sys.stderr.write(
            f"[logger] could not open {target_path} or any __1..__99 suffix; "
            f"this log line is dropped\n"
        )
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Internal emit helpers (wrapped in top-level try/except each)
# ---------------------------------------------------------------------------

def _emit_info(person_label: str, action_verb: str) -> None:
    """Write one INFO line to today's journey log."""
    try:
        ts = time.strftime(LOG_DATE_FORMAT)
        line = f"[{ts}] [INFO] [Person: {person_label}] User clicked '{action_verb}'\n"
        target = _today_journey_log_path()
        fh = _open_for_append_with_lock_retry(target)
        if fh is None:
            return
        try:
            fh.write(line)
        finally:
            fh.close()
    except Exception:
        pass  # Logger NEVER crashes the app.


def _emit_info_raw(person_label: str, payload: str) -> None:
    """Write one INFO line with a custom payload (used by init_logging for 'App started')."""
    try:
        ts = time.strftime(LOG_DATE_FORMAT)
        line = f"[{ts}] [INFO] [Person: {person_label}] {payload}\n"
        target = _today_journey_log_path()
        fh = _open_for_append_with_lock_retry(target)
        if fh is None:
            return
        try:
            fh.write(line)
        finally:
            fh.close()
    except Exception:
        pass


def _format_traceback(exctype, value, tb) -> str:
    """Format a traceback, indented 2 spaces per line."""
    try:
        lines = traceback.format_exception(exctype, value, tb)
        raw = "".join(lines)
        indented = "\n".join("  " + line for line in raw.splitlines())
        return indented + "\n"
    except Exception:
        return "  (traceback unavailable)\n"


def _emit_error(
    person_label: str,
    handler_name: str,
    exctype,
    value,
    tb,
    extra_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Write one ERROR block (decorator path, source=decorator) to today's exceptions log.

    Format:
      [ts] [ERROR] [Person: X] [source=decorator] handler=<name> ExcClass: msg
        payload: {...}    (only for whitelisted save handlers)
        Traceback ...
    """
    try:
        ts = time.strftime(LOG_DATE_FORMAT)
        exc_class = exctype.__name__ if exctype else "UnknownError"
        one_line_msg = str(value).replace("\n", "\\n").replace("\r", "\\r") if value else ""
        header = (
            f"[{ts}] [ERROR] [Person: {person_label}] [source=decorator] "
            f"handler={handler_name} {exc_class}: {one_line_msg}\n"
        )
        payload_line = ""
        if extra_data is not None:
            payload_line = f"  payload: {repr(extra_data)}\n"
        tb_block = _format_traceback(exctype, value, tb)
        body = header + payload_line + tb_block

        target = _today_exceptions_log_path()
        fh = _open_for_append_with_lock_retry(target)
        if fh is None:
            return
        try:
            fh.write(body)
        finally:
            fh.close()
    except Exception:
        pass


def _emit_critical(person_label: str, exctype, value, tb, source: str) -> None:
    """Write one CRITICAL block to today's exceptions log.

    Format:
      [ts] [CRITICAL] [Person: X] source=<source> ExcClass: msg
        Traceback ...
    """
    try:
        ts = time.strftime(LOG_DATE_FORMAT)
        exc_class = exctype.__name__ if exctype else "UnknownError"
        one_line_msg = str(value).replace("\n", "\\n").replace("\r", "\\r") if value else ""
        header = (
            f"[{ts}] [CRITICAL] [Person: {person_label}] "
            f"source={source} {exc_class}: {one_line_msg}\n"
        )
        tb_block = _format_traceback(exctype, value, tb)
        body = header + tb_block

        target = _today_exceptions_log_path()
        fh = _open_for_append_with_lock_retry(target)
        if fh is None:
            return
        try:
            fh.write(body)
        finally:
            fh.close()
    except Exception:
        pass


def log_cleanup_failure(target: Path, exc: BaseException) -> None:
    """Write one INFO-CLEANUP line to today's exception log for a cleanup-delete failure.

    Called by on_promote_draft_click (and any future caller) when a file
    deletion fails during cleanup.

    Format:
      [ts] [INFO-CLEANUP] [Person: -] Cleanup: failed to delete <path>: ExcClass: msg

    Args:
        target: The path of the file that failed to be deleted.
        exc:    The exception that was raised.
    """
    try:
        ts = time.strftime(LOG_DATE_FORMAT)
        person = _last_known_person_label or PERSON_PLACEHOLDER
        reason = f"{type(exc).__name__}: {exc}"
        line = (
            f"[{ts}] [INFO-CLEANUP] [Person: {person}] "
            f"Cleanup: failed to delete {target}: {reason}\n"
        )
        log_path = _today_exceptions_log_path()
        fh = _open_for_append_with_lock_retry(log_path)
        if fh is None:
            return
        try:
            fh.write(line)
        finally:
            fh.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Decorator helper: collect save payload for whitelisted handlers
# ---------------------------------------------------------------------------

def _collect_save_payload_if_save_handler(
    frame: Any, handler_name: str
) -> Optional[Dict[str, Any]]:
    """Return the form dict for save handlers; None otherwise.

    Only handlers whose __name__ is in SAVE_HANDLER_WHITELIST get their
    form payload dumped in the ERROR line.
    """
    if handler_name not in SAVE_HANDLER_WHITELIST:
        return None
    collect = getattr(frame, "_collect_all_data_to_dict", None)
    if callable(collect):
        try:
            return collect()
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Public decorator
# ---------------------------------------------------------------------------

def log_user_action(action_verb: str) -> Callable:
    """Decorator factory for UI handler methods.

    On entry: emits one INFO line to today's journey log.
    On exception: emits one ERROR line (source=decorator) to today's
      exceptions log, then re-raises so wxPython sees the exception.
    On normal return: returns the wrapped function's return value.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            person_label = getattr(self, "_current_person_label", PERSON_PLACEHOLDER)

            try:
                _emit_info(person_label, action_verb)
            except Exception:
                pass  # Logger NEVER crashes the app.

            try:
                return func(self, *args, **kwargs)
            except Exception:
                exctype, value, tb = sys.exc_info()
                try:
                    extra = _collect_save_payload_if_save_handler(self, func.__name__)
                    _emit_error(
                        person_label=person_label,
                        handler_name=func.__name__,
                        exctype=exctype,
                        value=value,
                        tb=tb,
                        extra_data=extra,
                    )
                except Exception:
                    pass

                # Enqueue ERROR email after _emit_error.  The decorator
                # outer-except is the auto-email trigger; log_error() call
                # sites are not auto-escalated (no recursion).
                try:
                    from src.helpers.email_helper import enqueue_email_for_severity  # noqa: PLC0415
                    exc_class = exctype.__name__ if exctype else "UnknownError"
                    one_line_msg = str(value).replace("\n", "\\n") if value else ""
                    tb_block = _format_traceback(exctype, value, tb)
                    enqueue_email_for_severity(
                        severity="ERROR",
                        headline=f"{exc_class}: {one_line_msg} in {func.__name__}",
                        body_extra=tb_block,
                        handler_name=func.__name__,
                    )
                except Exception:
                    pass

                raise
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Manual ERROR API
# ---------------------------------------------------------------------------

def log_error(exc: BaseException, context: Optional[str] = None) -> None:
    """Write ONE ERROR line (source=manual) to today's exceptions log.

    Use inside an inner `except` block that catches and recovers from an
    exception. The function MUST NOT raise (self-recovery contract).

    Args:
        exc: the caught exception instance (the `e` in `except ... as e`).
        context: optional free-form caller description of what was happening.
            When None, the [context=...] field is omitted entirely.

    Line shape:
      [ts] [ERROR] [Person: X] [source=manual] [context=<ctx>] ExcClass: msg
        Traceback ...
    When context is None:
      [ts] [ERROR] [Person: X] [source=manual] ExcClass: msg
        Traceback ...
    """
    try:
        person_label = _read_global_person_label()
        exc_class = type(exc).__name__
        one_line_msg = str(exc).replace("\n", "\\n").replace("\r", "\\r")
        ts = time.strftime(LOG_DATE_FORMAT)

        ctx_field = f"[context={context}] " if context is not None else ""
        header = (
            f"[{ts}] [ERROR] [Person: {person_label}] [source=manual] "
            f"{ctx_field}{exc_class}: {one_line_msg}\n"
        )

        try:
            tb_lines = traceback.format_exception(exc)
        except TypeError:
            tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tb_block = "".join(tb_lines)
        tb_block_indented = "\n".join("  " + line for line in tb_block.splitlines()) + "\n"

        body = header + tb_block_indented

        target = _today_exceptions_log_path()
        fh = _open_for_append_with_lock_retry(target)
        if fh is None:
            return
        try:
            fh.write(body)
        finally:
            fh.close()
    except Exception:
        # Logger NEVER crashes the app.
        return


# ---------------------------------------------------------------------------
# Person-context helpers
# ---------------------------------------------------------------------------

def set_current_person_label(frame: Any, label: str) -> None:
    """Update both the frame sentinel and module-level person label (Option A)."""
    global _last_known_person_label
    frame._current_person_label = label
    _last_known_person_label = label


def clear_current_person_label(frame: Any) -> None:
    """Reset the person label to the placeholder on both frame and module level."""
    set_current_person_label(frame, PERSON_PLACEHOLDER)


# ---------------------------------------------------------------------------
# Bootstrap: init_logging
# ---------------------------------------------------------------------------

def init_logging(root_folder: Optional[Path]) -> None:
    """Initialize (or re-initialize) the active log directory.

    Idempotent: subsequent calls with the same root are no-ops.
    First call with None uses %LOCALAPPDATA%/PyTreeManager/logs.
    Subsequent call with a real path re-points to <root>/.PyTreeManager/logs/.

    Emits one INFO line on first call ("App started") and one INFO line
    on root-folder transitions ("Log dir relocated").
    """
    global _root_log_dir, _active_log_dir, _logging_initialized

    try:
        new_dir: Path
        if root_folder is None:
            new_dir = _localappdata_log_dir()
        else:
            new_dir = Path(root_folder) / ".PyTreeManager" / "logs"

        if _logging_initialized and new_dir == _active_log_dir:
            return  # No-op: same dir.

        first_call = not _logging_initialized
        _active_log_dir = new_dir
        _logging_initialized = True

        if root_folder is not None:
            _root_log_dir = new_dir

        try:
            new_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        if first_call:
            # Determine version (best-effort)
            version = "unknown"
            try:
                import importlib.metadata
                version = importlib.metadata.version("py-tree-manager")
            except Exception:
                pass
            _emit_info_raw(PERSON_PLACEHOLDER, f"App started, version {version}, log_dir {new_dir}")
        else:
            _emit_info_raw(PERSON_PLACEHOLDER, f"Log dir relocated to {new_dir}")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Cleanup: 14-day sweep
# ---------------------------------------------------------------------------

def cleanup_old_logs(retention_days: int = LOG_RETENTION_DAYS) -> None:
    """Delete *.log files older than retention_days by mtime.

    Sweeps both the active log dir and the %LOCALAPPDATA% fallback dir
    (covering the case where the root was relocated mid-session, leaving
    old logs in the previous location).

    On delete failure: emit one INFO-CLEANUP line to today's exception log.
    Never crashes the app.
    """
    try:
        cutoff = time.time() - (retention_days * 86400)
        # Collect unique dirs to sweep.
        seen: set = set()
        candidate_dirs = []
        for d in (_active_log_dir, _root_log_dir, _localappdata_log_dir()):
            if d is not None and d not in seen:
                seen.add(d)
                candidate_dirs.append(d)

        for log_dir in candidate_dirs:
            if not log_dir.exists():
                continue
            try:
                for log_file in log_dir.glob("*.log"):
                    try:
                        if log_file.stat().st_mtime < cutoff:
                            log_file.unlink()
                    except (PermissionError, FileNotFoundError, OSError) as e:
                        try:
                            log_cleanup_failure(log_file, e)
                        except Exception:
                            pass  # Logger NEVER crashes the app.
                        continue
            except Exception:
                # Directory iteration failure: cannot log to a dir we cannot iterate.
                continue
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Exception hooks
# ---------------------------------------------------------------------------

def install_python_excepthook() -> None:
    """Install sys.excepthook before wx is imported.

    This function has NO wx import. It writes a CRITICAL line and chains
    to the default hook (preserving stderr output).
    """
    def _hook(exctype, value, tb):
        try:
            person_label = _read_global_person_label()
            _emit_critical(person_label, exctype, value, tb, source="sys.excepthook")
        except Exception:
            pass

        # Enqueue CRITICAL email after _emit_critical.  Synchronous because
        # the process is unwinding and a daemon thread would be killed mid-send.
        try:
            from src.helpers.email_helper import enqueue_email_for_severity  # noqa: PLC0415
            exc_class = exctype.__name__ if exctype else "UnknownError"
            one_line_msg = str(value).replace("\n", "\\n") if value else ""
            tb_block = _format_traceback(exctype, value, tb)
            enqueue_email_for_severity(
                severity="CRITICAL",
                headline=f"{exc_class}: {one_line_msg}",
                body_extra=tb_block,
                handler_name="sys.excepthook",
            )
        except Exception:
            pass

        sys.__excepthook__(exctype, value, tb)

    sys.excepthook = _hook


# ---------------------------------------------------------------------------
# LoggingApp (wx.App subclass) — wx import is DEFERRED until class is used
#
# wx isolation: install_python_excepthook() must be importable without wx.
# This module does NOT import wx at module-level. The LoggingApp class is
# built lazily on first access via a module __getattr__ hook, which means
# `from helpers.logger import install_python_excepthook` never pulls in wx.
# ---------------------------------------------------------------------------

def _build_logging_app_class():
    """Build and return the LoggingApp class (imports wx at call time)."""
    import wx  # noqa: PLC0415 — deferred import; wx must not be imported at module level

    class LoggingApp(wx.App):
        """wx.App subclass that integrates the dual exception-hook logging.

        OnInit:
          - Calls init_logging(None) to open %LOCALAPPDATA% log dir.
          - Calls cleanup_old_logs() for 14-day sweep.
          - Constructs and shows AddPersonFrame.

        OnExceptionInMainLoop:
          - Emits one CRITICAL line to today's exceptions log.
          - Returns False (terminate the event loop).
        """

        def OnInit(self) -> bool:  # type: ignore[override]
            init_logging(root_folder=None)
            cleanup_old_logs()

            # Copy update.bat from PyInstaller bundle into exe_dir on first
            # frozen launch. No-op in dev mode.
            try:
                from src.helpers.update_helper import UpdateHelper  # noqa: PLC0415
                UpdateHelper.ensure_update_helper_present()
            except Exception as e:
                log_error(e, context="OnInit: ensure_update_helper_present failed")

            from src.frames.add_person_frame import AddPersonFrame
            frame = AddPersonFrame(None)

            # Relocate logger to <root>/.PyTreeManager/logs once FileService
            # knows the user's root.  Construct a fresh FileService rather than
            # scraping one off the frame; it is idempotent and reads the same
            # pointer file.
            try:
                from src.services.file_service import FileService  # noqa: PLC0415
                fs = FileService()
                if fs.is_root_location_set():
                    root_str = fs._get_root_folder()
                    if root_str:
                        init_logging(Path(root_str))
            except Exception as e:
                log_error(e, context="OnInit: log relocation failed")

            frame.Show()

            # Check for update after frame.Show() so the user sees the window
            # first; the update dialog appears on top.
            try:
                from src.helpers.update_helper import UpdateHelper  # noqa: PLC0415
                from src.services.file_service import FileService  # noqa: PLC0415
                from importlib.metadata import version as _pkg_version  # noqa: PLC0415
                fs2 = FileService()
                current = _pkg_version("py-tree-manager")
                skipped = None
                if fs2.is_root_location_set():
                    skipped = fs2.settings.get_skipped_update_version()
                try:
                    _emit_info_raw(
                        _read_global_person_label(),
                        f"Update check: entered current={current} skipped={skipped} url=<api>",
                    )
                except Exception:
                    pass
                info = UpdateHelper.check_for_update(current, skipped_version=skipped)
                if info is not None:
                    try:
                        _emit_info_raw(
                            _read_global_person_label(),
                            f"Update check: newer version {info.latest_version} available; prompting user",
                        )
                    except Exception:
                        pass
                    if UpdateHelper.prompt_user_to_update(frame, info):
                        try:
                            _emit_info_raw(
                                _read_global_person_label(),
                                f"Update: user accepted {info.latest_version}; entering download_and_apply",
                            )
                        except Exception:
                            pass
                        UpdateHelper.download_and_apply_update(info)
                    else:
                        try:
                            _emit_info_raw(
                                _read_global_person_label(),
                                f"Update: user declined {info.latest_version}; remembered as skipped",
                            )
                        except Exception:
                            pass
                        if fs2.is_root_location_set():
                            UpdateHelper.remember_skipped_version(fs2.settings, info.latest_version)
                            fs2.save_settings()
            except Exception as e:
                log_error(e, context="OnInit: update_helper check failed")

            # Start the 30-minute email-retry timer parented to LoggingApp
            # so it survives frame transitions.
            try:
                from src.helpers.email_helper import EmailHelper  # noqa: PLC0415
                self._email_retry_timer = EmailHelper.start_retry_timer(self)
            except Exception as e:
                log_error(e, context="OnInit: email retry timer start failed")
                self._email_retry_timer = None

            return True

        def OnExit(self) -> int:  # type: ignore[override]
            # Stop the retry timer on clean shutdown.
            try:
                from src.helpers.email_helper import EmailHelper  # noqa: PLC0415
                timer = getattr(self, "_email_retry_timer", None)
                if timer is not None:
                    EmailHelper.stop_retry_timer(timer)
            except Exception:
                pass
            return 0

        def OnExceptionInMainLoop(self) -> bool:  # type: ignore[override]
            exctype, value, tb = sys.exc_info()
            try:
                person_label = _read_global_person_label()
                _emit_critical(
                    person_label, exctype, value, tb,
                    source="wx.App.OnExceptionInMainLoop"
                )
            except Exception:
                pass

            # Enqueue CRITICAL email after _emit_critical.  Synchronous because
            # the process is terminating and a daemon thread would be killed
            # mid-SMTP-handshake.
            try:
                from src.helpers.email_helper import enqueue_email_for_severity  # noqa: PLC0415
                exc_class = exctype.__name__ if exctype else "UnknownError"
                one_line_msg = str(value).replace("\n", "\\n") if value else ""
                tb_block = _format_traceback(exctype, value, tb)
                enqueue_email_for_severity(
                    severity="CRITICAL",
                    headline=f"{exc_class}: {one_line_msg}",
                    body_extra=tb_block,
                    handler_name="OnExceptionInMainLoop",
                )
            except Exception:
                pass

            return False  # Exit the event loop and terminate.

    return LoggingApp


# Module-level __getattr__ provides lazy access to LoggingApp.
# When a caller writes `from helpers.logger import LoggingApp`, Python calls
# this __getattr__ for 'LoggingApp', which builds the class (importing wx
# at that point). install_python_excepthook is defined above and is never
# reached by this path, so it remains wx-free.
_LoggingApp_cache: Optional[type] = None


def __getattr__(name: str):
    if name == "LoggingApp":
        global _LoggingApp_cache
        if _LoggingApp_cache is None:
            _LoggingApp_cache = _build_logging_app_class()
        return _LoggingApp_cache
    raise AttributeError(f"module 'helpers.logger' has no attribute {name!r}")
