"""L0 unit tests for helpers/logger.py.

All tests point the logger at a tmp_path log dir via the logger_env fixture,
which calls init_logging() and resets module-level state on teardown.
No test reads or writes the real %LOCALAPPDATA% log dir.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

import pytest

import src.helpers.logger as logger_module
from src.helpers.logger import (
    LOG_DATE_FORMAT,
    LOG_FILE_DATE_FORMAT,
    LOG_LOCK_RETRY_CAP,
    LOG_RETENTION_DAYS,
    PERSON_PLACEHOLDER,
    SAVE_HANDLER_WHITELIST,
    log_cleanup_failure,
    _emit_critical,
    _emit_error,
    _emit_info,
    _open_for_append_with_lock_retry,
    _today_exceptions_log_path,
    _today_journey_log_path,
    cleanup_old_logs,
    clear_current_person_label,
    init_logging,
    install_python_excepthook,
    log_error,
    log_user_action,
    set_current_person_label,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def logger_env(tmp_path, monkeypatch):
    """Reset all module-level logger state before each test and point to tmp_path."""
    # Reset module state before test
    monkeypatch.setattr(logger_module, "_root_log_dir", None)
    monkeypatch.setattr(logger_module, "_active_log_dir", None)
    monkeypatch.setattr(logger_module, "_last_known_person_label", PERSON_PLACEHOLDER)
    monkeypatch.setattr(logger_module, "_logging_initialized", False)

    # Point to tmp_path so no real LOCALAPPDATA writes happen
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(logger_module, "_active_log_dir", log_dir)
    monkeypatch.setattr(logger_module, "_logging_initialized", True)

    yield log_dir

    # Teardown: reset state again
    monkeypatch.setattr(logger_module, "_root_log_dir", None)
    monkeypatch.setattr(logger_module, "_active_log_dir", None)
    monkeypatch.setattr(logger_module, "_last_known_person_label", PERSON_PLACEHOLDER)
    monkeypatch.setattr(logger_module, "_logging_initialized", False)


def _read_journey(log_dir: Path) -> str:
    today = time.strftime(LOG_FILE_DATE_FORMAT)
    p = log_dir / f"{today}__journey.log"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _read_exceptions(log_dir: Path) -> str:
    today = time.strftime(LOG_FILE_DATE_FORMAT)
    p = log_dir / f"{today}__exceptions.log"
    return p.read_text(encoding="utf-8") if p.exists() else ""


# ---------------------------------------------------------------------------
# TestLogLineFormat
# ---------------------------------------------------------------------------

class TestLogLineFormat:
    def test_info_line_format_with_person_loaded(self, logger_env):
        log_dir = logger_env
        _emit_info("Anna", "Save person")
        content = _read_journey(log_dir)
        pattern = r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \[INFO\] \[Person: Anna\] User clicked 'Save person'\n$"
        assert re.match(pattern, content), f"Did not match pattern. Got: {repr(content)}"

    def test_info_line_format_with_person_placeholder(self, logger_env):
        log_dir = logger_env
        _emit_info("-", "Close window")
        content = _read_journey(log_dir)
        assert "[Person: -]" in content
        assert "User clicked 'Close window'" in content

    def test_error_line_format_includes_handler_and_traceback(self, logger_env):
        log_dir = logger_env
        try:
            raise KeyError("xyz")
        except KeyError:
            exctype, value, tb = sys.exc_info()
        _emit_error(person_label="-", handler_name="on_save_click",
                    exctype=exctype, value=value, tb=tb)
        content = _read_exceptions(log_dir)
        assert "[ERROR]" in content
        assert "[source=decorator]" in content
        assert "handler=on_save_click" in content
        assert "KeyError" in content
        assert "xyz" in content
        assert "Traceback" in content
        # Payload line absent when no extra_data
        assert "payload:" not in content

    def test_error_line_includes_payload_when_provided(self, logger_env):
        log_dir = logger_env
        try:
            raise ValueError("bad")
        except ValueError:
            exctype, value, tb = sys.exc_info()
        _emit_error(person_label="New", handler_name="on_save_click",
                    exctype=exctype, value=value, tb=tb,
                    extra_data={"first_name": "Adam"})
        content = _read_exceptions(log_dir)
        assert "payload:" in content
        assert "'first_name': 'Adam'" in content

    def test_critical_line_format_with_source(self, logger_env):
        log_dir = logger_env
        try:
            raise RuntimeError("kaboom")
        except RuntimeError:
            exctype, value, tb = sys.exc_info()
        _emit_critical("-", exctype, value, tb, source="sys.excepthook")
        content = _read_exceptions(log_dir)
        assert "[CRITICAL]" in content
        assert "source=sys.excepthook" in content
        assert "RuntimeError" in content
        assert "kaboom" in content


# ---------------------------------------------------------------------------
# TestDecorator
# ---------------------------------------------------------------------------

class TestDecorator:
    def _make_frame(self, label: Optional[str] = "TestPerson",
                    include_collect: bool = False) -> MagicMock:
        frame = MagicMock()
        if label is not None:
            frame._current_person_label = label
        else:
            # Simulate frame with no label attribute
            del frame._current_person_label
        if include_collect:
            frame._collect_all_data_to_dict.return_value = {"first_name": "Adam"}
        return frame

    def test_decorator_emits_info_on_entry(self, logger_env):
        log_dir = logger_env

        @log_user_action("test verb")
        def handler(self, event):
            pass

        frame = self._make_frame("TestPerson")
        handler(frame, None)

        content = _read_journey(log_dir)
        assert "[INFO]" in content
        assert "[Person: TestPerson]" in content
        assert "User clicked 'test verb'" in content

    def test_decorator_emits_error_and_reraises_on_exception(self, logger_env):
        log_dir = logger_env

        @log_user_action("risky verb")
        def handler(self, event):
            raise RuntimeError("boom")

        frame = self._make_frame("TestPerson")
        with pytest.raises(RuntimeError, match="boom"):
            handler(frame, None)

        content = _read_exceptions(log_dir)
        assert "[ERROR]" in content
        assert "RuntimeError" in content
        assert "boom" in content

    def test_decorator_preserves_return_value(self, logger_env):
        @log_user_action("return test")
        def handler(self, event):
            return 42

        frame = self._make_frame()
        result = handler(frame, None)
        assert result == 42

    def test_decorator_uses_placeholder_when_no_person_label_attribute(self, logger_env):
        log_dir = logger_env

        @log_user_action("no label verb")
        def handler(self, event):
            pass

        frame = MagicMock(spec=[])  # No attributes at all
        handler(frame, None)

        content = _read_journey(log_dir)
        assert "[Person: -]" in content

    def test_decorator_uses_save_handler_payload_for_whitelisted_handlers(self, logger_env):
        log_dir = logger_env

        @log_user_action("Save person (new)")
        def on_save_click(self, event):
            raise KeyError("uid-abc")

        frame = self._make_frame("New", include_collect=True)
        with pytest.raises(KeyError):
            on_save_click(frame, None)

        content = _read_exceptions(log_dir)
        assert "payload:" in content
        assert "'first_name': 'Adam'" in content

    def test_decorator_name_preserved_by_functools_wraps(self, logger_env):
        @log_user_action("whatever")
        def my_special_handler(self, event):
            pass

        assert my_special_handler.__name__ == "my_special_handler"


# ---------------------------------------------------------------------------
# TestFileLockRetry
# ---------------------------------------------------------------------------

class TestFileLockRetry:
    def test_open_for_append_returns_handle_when_unlocked(self, tmp_path):
        target = tmp_path / "test__journey.log"
        fh = _open_for_append_with_lock_retry(target)
        assert fh is not None
        fh.close()
        assert target.exists()

    def test_open_for_append_falls_through_to_suffix_when_canonical_locked(self, tmp_path):
        """Simulate canonical path locked by monkeypatching Path.open."""
        target = tmp_path / "test__journey.log"
        call_count = [0]
        real_open = Path.open

        def patched_open(self, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call (canonical path): simulate permission denied
                raise PermissionError("locked")
            return real_open(self, *args, **kwargs)

        with patch.object(Path, "open", patched_open):
            fh = _open_for_append_with_lock_retry(target)

        assert fh is not None
        fh.close()
        # Suffix file should have been used
        suffix_path = tmp_path / "test__journey__1.log"
        assert suffix_path.exists()

    def test_open_for_append_caps_at_99_suffixes_then_returns_none(self, tmp_path, capsys):
        """All attempts raise PermissionError; function returns None."""
        target = tmp_path / "test__journey.log"

        def always_locked(self, *args, **kwargs):
            raise PermissionError("locked")

        with patch.object(Path, "open", always_locked):
            result = _open_for_append_with_lock_retry(target)

        assert result is None
        # Stderr warning emitted
        captured = capsys.readouterr()
        assert "[logger]" in captured.err


# ---------------------------------------------------------------------------
# TestCleanup (amended 2026-05-09)
# ---------------------------------------------------------------------------

class TestCleanup:
    def _set_mtime(self, path: Path, age_seconds: float) -> None:
        mtime = time.time() - age_seconds
        import os
        os.utime(str(path), (mtime, mtime))

    def test_cleanup_deletes_files_older_than_14_days(self, logger_env, tmp_path):
        log_dir = logger_env
        old1 = log_dir / "2026-04-01__journey.log"
        old2 = log_dir / "2026-04-02__exceptions.log"
        fresh = log_dir / "2026-05-09__journey.log"
        old1.write_text("old1")
        old2.write_text("old2")
        fresh.write_text("fresh")

        self._set_mtime(old1, 15 * 86400)
        self._set_mtime(old2, 15 * 86400)
        self._set_mtime(fresh, 60)  # 1 minute old

        cleanup_old_logs(retention_days=14)

        assert not old1.exists(), "old1 should have been deleted"
        assert not old2.exists(), "old2 should have been deleted"
        assert fresh.exists(), "fresh file must survive"

    def test_cleanup_does_not_delete_13_day_old_files(self, logger_env, tmp_path):
        log_dir = logger_env
        borderline = log_dir / "2026-04-26__journey.log"
        borderline.write_text("borderline")
        self._set_mtime(borderline, 13 * 86400)

        cleanup_old_logs(retention_days=14)

        assert borderline.exists(), "13-day-old file must survive"

    def test_cleanup_emits_info_cleanup_line_on_permission_error(
        self, logger_env, monkeypatch
    ):
        log_dir = logger_env
        stale = log_dir / "2026-04-01__journey.log"
        stale.write_text("stale")
        self._set_mtime(stale, 15 * 86400)

        def raise_on_unlink(self):
            raise PermissionError("locked")

        monkeypatch.setattr(Path, "unlink", raise_on_unlink)

        cleanup_old_logs(retention_days=14)

        # No exception should have escaped
        exc_content = _read_exceptions(log_dir)
        assert "[INFO-CLEANUP]" in exc_content
        pattern = r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \[INFO-CLEANUP\] \[Person: -\] Cleanup: failed to delete .+: PermissionError: locked"
        assert re.search(pattern, exc_content), (
            f"INFO-CLEANUP line not found. Got: {repr(exc_content)}"
        )

    def test_cleanup_does_not_recurse_when_emit_cleanup_failure_itself_fails(
        self, logger_env, monkeypatch
    ):
        log_dir = logger_env
        stale = log_dir / "2026-04-01__journey.log"
        stale.write_text("stale")
        self._set_mtime(stale, 15 * 86400)

        def raise_on_unlink(self):
            raise PermissionError("locked")

        def raise_on_open(self, *args, **kwargs):
            raise OSError("cannot open")

        monkeypatch.setattr(Path, "unlink", raise_on_unlink)
        monkeypatch.setattr(Path, "open", raise_on_open)

        # Must complete without recursion or exception
        import threading
        result = []
        def run():
            try:
                cleanup_old_logs(retention_days=14)
                result.append("ok")
            except Exception as e:
                result.append(f"error: {e}")

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=2.0)
        assert not t.is_alive(), "cleanup should complete in well under 2 seconds"
        assert result == ["ok"]

    def test_cleanup_silent_when_log_dir_missing(self, monkeypatch):
        monkeypatch.setattr(logger_module, "_active_log_dir", Path("/nonexistent/path/logs"))
        monkeypatch.setattr(logger_module, "_root_log_dir", None)

        # Must not raise
        cleanup_old_logs(retention_days=14)


# ---------------------------------------------------------------------------
# TestLogError (new, 2026-05-09 amendment)
# ---------------------------------------------------------------------------

class TestLogError:
    def test_log_error_writes_one_error_line_with_source_manual(
        self, logger_env, monkeypatch
    ):
        log_dir = logger_env
        monkeypatch.setattr(logger_module, "_last_known_person_label", "Anna")
        try:
            raise RuntimeError("boom")
        except RuntimeError as e:
            exc = e
        log_error(exc, context="Refresh folder tree: rebuild_folder_tree failed")
        content = _read_exceptions(log_dir)
        pattern = (
            r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \[ERROR\] \[Person: Anna\] "
            r"\[source=manual\] \[context=Refresh folder tree: rebuild_folder_tree failed\] "
            r"RuntimeError: boom"
        )
        assert re.search(pattern, content), f"Pattern not found. Got: {repr(content)}"
        # Traceback should be indented 2 spaces
        assert "  Traceback" in content or "  RuntimeError" in content or "  File" in content

    def test_log_error_omits_context_field_when_context_is_none(
        self, logger_env, monkeypatch
    ):
        log_dir = logger_env
        monkeypatch.setattr(logger_module, "_last_known_person_label", "-")
        try:
            raise RuntimeError("boom")
        except RuntimeError as e:
            exc = e
        log_error(exc, context=None)
        content = _read_exceptions(log_dir)
        assert "[source=manual]" in content
        assert "RuntimeError: boom" in content
        assert "[context=" not in content

    def test_log_error_uses_person_placeholder_when_label_unset(
        self, logger_env, monkeypatch
    ):
        log_dir = logger_env
        monkeypatch.setattr(logger_module, "_last_known_person_label", PERSON_PLACEHOLDER)
        try:
            raise ValueError("oops")
        except ValueError as e:
            exc = e
        log_error(exc)
        content = _read_exceptions(log_dir)
        assert "[Person: -]" in content

    def test_log_error_does_not_raise_on_internal_failure(self, logger_env, monkeypatch):
        def raise_on_open(self, *args, **kwargs):
            raise OSError("cannot open log")

        monkeypatch.setattr(Path, "open", raise_on_open)
        try:
            raise RuntimeError("boom")
        except RuntimeError as e:
            exc = e
        # Must not raise
        log_error(exc, context="whatever")

    def test_log_error_does_not_raise_on_traceback_format_failure(
        self, logger_env, monkeypatch
    ):
        import traceback as tb_module

        def raise_in_format(exc):
            raise RuntimeError("inner traceback error")

        monkeypatch.setattr(tb_module, "format_exception", raise_in_format)
        try:
            raise RuntimeError("original")
        except RuntimeError as e:
            exc = e
        # Must not raise
        log_error(exc)

    def test_log_error_writes_to_exceptions_log_not_journey_log(
        self, logger_env, monkeypatch
    ):
        log_dir = logger_env
        monkeypatch.setattr(logger_module, "_last_known_person_label", "-")
        try:
            raise RuntimeError("boom")
        except RuntimeError as e:
            exc = e
        log_error(exc, context="test")
        exceptions_content = _read_exceptions(log_dir)
        journey_content = _read_journey(log_dir)
        assert "boom" in exceptions_content
        assert "boom" not in journey_content

    def test_log_error_does_not_re_raise(self, logger_env, monkeypatch):
        monkeypatch.setattr(logger_module, "_last_known_person_label", "-")
        try:
            raise RuntimeError("boom")
        except RuntimeError as e:
            exc = e
        # Must return normally, not raise
        result = log_error(exc)
        assert result is None


# ---------------------------------------------------------------------------
# TestInitLoggingIdempotency
# ---------------------------------------------------------------------------

class TestInitLoggingIdempotency:
    def test_init_logging_with_none_uses_localappdata(self, monkeypatch, tmp_path):
        # Reset to uninitialized state
        monkeypatch.setattr(logger_module, "_active_log_dir", None)
        monkeypatch.setattr(logger_module, "_logging_initialized", False)
        monkeypatch.setattr(logger_module, "_root_log_dir", None)

        # Redirect LOCALAPPDATA so we don't touch real %LOCALAPPDATA%
        fake_local = tmp_path / "fake_localappdata"
        fake_local.mkdir()
        monkeypatch.setenv("LOCALAPPDATA", str(fake_local))

        init_logging(None)

        assert logger_module._active_log_dir is not None
        assert "PyTreeManager" in str(logger_module._active_log_dir)
        assert "logs" in str(logger_module._active_log_dir)

    def test_init_logging_with_root_uses_root(self, monkeypatch, tmp_path):
        """init_logging(root) must point to <root>/.PyTreeManager/logs."""
        monkeypatch.setattr(logger_module, "_active_log_dir", None)
        monkeypatch.setattr(logger_module, "_logging_initialized", False)
        monkeypatch.setattr(logger_module, "_root_log_dir", None)

        init_logging(tmp_path)

        # Log path is .PyTreeManager/logs
        assert logger_module._active_log_dir == tmp_path / ".PyTreeManager" / "logs"

    def test_init_logging_emits_app_started_line_first_call(self, monkeypatch, tmp_path):
        monkeypatch.setattr(logger_module, "_active_log_dir", None)
        monkeypatch.setattr(logger_module, "_logging_initialized", False)
        monkeypatch.setattr(logger_module, "_root_log_dir", None)

        init_logging(tmp_path)

        today = time.strftime(LOG_FILE_DATE_FORMAT)
        journey = (tmp_path / ".PyTreeManager" / "logs" / f"{today}__journey.log")
        content = journey.read_text(encoding="utf-8") if journey.exists() else ""
        assert "App started" in content

    def test_init_logging_emits_relocated_line_on_root_change(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(logger_module, "_active_log_dir", None)
        monkeypatch.setattr(logger_module, "_logging_initialized", False)
        monkeypatch.setattr(logger_module, "_root_log_dir", None)

        fake_local = tmp_path / "fake_localappdata"
        fake_local.mkdir()
        monkeypatch.setenv("LOCALAPPDATA", str(fake_local))

        init_logging(None)   # first call: uses %LOCALAPPDATA%

        root2 = tmp_path / "root2"
        root2.mkdir()
        init_logging(root2)  # second call: relocates

        today = time.strftime(LOG_FILE_DATE_FORMAT)
        relocated_log = root2 / ".PyTreeManager" / "logs" / f"{today}__journey.log"
        content = relocated_log.read_text(encoding="utf-8") if relocated_log.exists() else ""
        assert "Log dir relocated" in content


# ---------------------------------------------------------------------------
# TestPersonLabelHelper
# ---------------------------------------------------------------------------

class TestPersonLabelHelper:
    def test_set_current_person_label_updates_frame_and_module_state(
        self, monkeypatch
    ):
        monkeypatch.setattr(logger_module, "_last_known_person_label", PERSON_PLACEHOLDER)
        frame = MagicMock()
        set_current_person_label(frame, "Anna")
        assert frame._current_person_label == "Anna"
        assert logger_module._last_known_person_label == "Anna"

    def test_clear_current_person_label_resets_to_placeholder(self, monkeypatch):
        monkeypatch.setattr(logger_module, "_last_known_person_label", "Anna")
        frame = MagicMock()
        frame._current_person_label = "Anna"
        clear_current_person_label(frame)
        assert frame._current_person_label == PERSON_PLACEHOLDER
        assert logger_module._last_known_person_label == PERSON_PLACEHOLDER


# ---------------------------------------------------------------------------
# TestPythonExceptHook
# ---------------------------------------------------------------------------

class TestPythonExceptHook:
    def test_install_python_excepthook_sets_sys_excepthook(self):
        original = sys.excepthook
        try:
            install_python_excepthook()
            assert sys.excepthook is not sys.__excepthook__
        finally:
            sys.excepthook = original

    def test_excepthook_writes_critical_line_with_source_field(
        self, logger_env, monkeypatch
    ):
        log_dir = logger_env
        original = sys.excepthook
        try:
            install_python_excepthook()
            # Manually invoke the hook (simulates an uncaught exception)
            try:
                raise KeyError("x")
            except KeyError:
                exctype, value, tb = sys.exc_info()

            # Patch sys.__excepthook__ to avoid printing to stderr in tests
            monkeypatch.setattr(sys, "__excepthook__", lambda et, ev, etb: None)
            sys.excepthook(exctype, value, tb)
        finally:
            sys.excepthook = original

        content = _read_exceptions(log_dir)
        assert "[CRITICAL]" in content
        assert "source=sys.excepthook" in content

    def test_excepthook_chains_to_default(self, logger_env, monkeypatch):
        counter = [0]
        original_hook = sys.__excepthook__

        def counting_default(et, ev, etb):
            counter[0] += 1

        monkeypatch.setattr(sys, "__excepthook__", counting_default)
        original = sys.excepthook
        try:
            install_python_excepthook()
            try:
                raise RuntimeError("chain test")
            except RuntimeError:
                exctype, value, tb = sys.exc_info()
            sys.excepthook(exctype, value, tb)
        finally:
            sys.excepthook = original
            sys.__excepthook__ = original_hook

        assert counter[0] == 1, "Default hook should have been called once"


# ---------------------------------------------------------------------------
# L1/L2/L3: .PyTreeManager/logs subpath
# ---------------------------------------------------------------------------

class TestInitLoggingPyTreeManagerSubpath:
    """Pins the contract: root-folder log path uses .PyTreeManager/logs."""

    def _reset_logger(self, monkeypatch):
        monkeypatch.setattr(logger_module, "_root_log_dir", None)
        monkeypatch.setattr(logger_module, "_active_log_dir", None)
        monkeypatch.setattr(logger_module, "_logging_initialized", False)

    def test_L1_init_logging_with_root_uses_pytreemanager_subpath(
        self, monkeypatch, tmp_path
    ):
        """L1: init_logging(root) sets _active_log_dir to root/.PyTreeManager/logs."""
        self._reset_logger(monkeypatch)
        init_logging(tmp_path)
        assert logger_module._active_log_dir == tmp_path / ".PyTreeManager" / "logs"

    def test_L2_init_logging_idempotent_on_same_root(self, monkeypatch, tmp_path):
        """L2: Calling init_logging(root) twice does not emit a second relocation line."""
        self._reset_logger(monkeypatch)
        init_logging(tmp_path)  # first call: emits "App started"

        today = time.strftime(LOG_FILE_DATE_FORMAT)
        log_dir = tmp_path / ".PyTreeManager" / "logs"
        journey = log_dir / f"{today}__journey.log"
        content_after_first = journey.read_text(encoding="utf-8") if journey.exists() else ""

        init_logging(tmp_path)  # second call: same dir -> no-op

        content_after_second = journey.read_text(encoding="utf-8") if journey.exists() else ""

        # No new "Log dir relocated" line should appear on the second call.
        assert content_after_second == content_after_first, (
            "Second init_logging call with same root should be a no-op; "
            f"extra content: {repr(content_after_second[len(content_after_first):])}"
        )

    def test_L3_init_logging_relocates_after_none_then_real_root(
        self, monkeypatch, tmp_path
    ):
        """L3: After init_logging(None) then init_logging(root), second INFO line
        lands in root/.PyTreeManager/logs, not in %LOCALAPPDATA% path.
        """
        self._reset_logger(monkeypatch)

        fake_local = tmp_path / "fake_localappdata"
        fake_local.mkdir()
        monkeypatch.setenv("LOCALAPPDATA", str(fake_local))

        init_logging(None)   # First call: active_log_dir = %LOCALAPPDATA%/.../logs

        from src.helpers.logger import _emit_info
        _emit_info("-", "Before relocation")

        root = tmp_path / "myroot"
        root.mkdir()
        init_logging(root)   # Second call: relocates to root/.PyTreeManager/logs

        _emit_info("-", "After relocation")

        today = time.strftime(LOG_FILE_DATE_FORMAT)
        # The "After relocation" line should be in root/.PyTreeManager/logs/
        relocated_log = root / ".PyTreeManager" / "logs" / f"{today}__journey.log"
        assert relocated_log.exists(), (
            f"No journey log created at relocated path {relocated_log}"
        )
        content = relocated_log.read_text(encoding="utf-8")
        assert "After relocation" in content, (
            f"'After relocation' line not found in relocated log. Content: {repr(content)}"
        )
