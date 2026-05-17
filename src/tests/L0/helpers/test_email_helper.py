"""L0 unit tests for helpers/email_helper.py.

All tests mock smtplib.SMTP_SSL — no real email is ever sent.
Tests cover: env-var config, payload serialisation, send attempts,
queue lifecycle, the public enqueue function, timer construction/teardown,
and the no-recursion guard.
"""

from __future__ import annotations

import json
import os
import smtplib
import socket
import threading
import uuid
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Module-level SMTP mock — must be in place BEFORE helpers.email_helper is imported
# for the first time, otherwise a real SMTP_SSL could be attempted.
# We patch at the smtplib level so every test sees the mock by default.
# Individual tests that need specific SMTP behaviour can further configure
# the mock inside the test body.
# ---------------------------------------------------------------------------

# We rely on monkeypatch inside each test to avoid global state leakage.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_payload(**overrides) -> Dict[str, Any]:
    """Return a minimal valid email payload dict."""
    base: Dict[str, Any] = {
        "schema_version": 1,
        "created_iso": "2026-05-10T14:32:11+02:00",
        "severity": "ERROR",
        "subject": "[PyTreeManager ERROR] on_save_click @ 2026-05-10 14:32",
        "headline": "TestError: something broke",
        "body_extra": None,
        "handler_name": "on_save_click",
        "attachments": [],
    }
    base.update(overrides)
    return base


# ===========================================================================
# TestEnvVarConfig
# ===========================================================================

class TestEnvVarConfig:
    """Tests for is_email_configured() — env-var presence/absence."""

    def test_is_email_configured_returns_false_when_neither_env_var_set(
        self, monkeypatch
    ):
        monkeypatch.delenv("PYTREEMANAGER_EMAIL_PASSWORD", raising=False)
        monkeypatch.delenv("PYTREEMANAGER_EMAIL_RECIPIENT", raising=False)

        from src.helpers.email_helper import is_email_configured
        assert is_email_configured() is False

    def test_is_email_configured_returns_false_when_password_unset_only(
        self, monkeypatch
    ):
        monkeypatch.delenv("PYTREEMANAGER_EMAIL_PASSWORD", raising=False)
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_RECIPIENT", "test@example.com")

        from src.helpers.email_helper import is_email_configured
        assert is_email_configured() is False

    def test_is_email_configured_returns_true_when_both_env_vars_set(
        self, monkeypatch
    ):
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_PASSWORD", "app_pass_16")
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_RECIPIENT", "test@example.com")

        from src.helpers.email_helper import is_email_configured
        assert is_email_configured() is True


# ===========================================================================
# TestPayloadSerialize
# ===========================================================================

class TestPayloadSerialize:
    """Tests for _serialize_payload_to_disk — atomicity, content, naming."""

    def test_payload_round_trip_via_json(self, tmp_path, monkeypatch):
        """Build payload, serialize to tmp_path, read back, assert fields preserved."""
        from src.helpers.email_helper import _serialize_payload_to_disk

        payload = _make_payload(
            headline="RoundTrip: zażółć gęślą jaźń",
            body_extra="  Traceback line\n",
        )
        out_path = _serialize_payload_to_disk(payload, tmp_path)

        assert out_path is not None
        assert out_path.exists()
        loaded = json.loads(out_path.read_text(encoding="utf-8"))

        assert loaded["severity"] == payload["severity"]
        assert loaded["headline"] == payload["headline"]
        assert loaded["body_extra"] == payload["body_extra"]
        assert loaded["schema_version"] == 1
        assert loaded["created_iso"] == payload["created_iso"]

    def test_atomic_write_uses_tmp_then_replace(self, tmp_path, monkeypatch):
        """os.replace must be called exactly once with .tmp source and final destination."""
        from src.helpers import email_helper as email_helper_module

        replace_calls = []
        real_replace = os.replace

        def capturing_replace(src, dst):
            replace_calls.append((str(src), str(dst)))
            return real_replace(src, dst)

        monkeypatch.setattr(email_helper_module.os, "replace", capturing_replace)

        from src.helpers.email_helper import _serialize_payload_to_disk
        _serialize_payload_to_disk(_make_payload(), tmp_path)

        assert len(replace_calls) == 1
        src, dst = replace_calls[0]
        assert src.endswith(".tmp")
        # Destination must NOT end in .tmp
        assert not dst.endswith(".tmp")
        assert dst.endswith(".json")

    def test_filename_uses_uuid_prefix_and_json_suffix(self, tmp_path):
        """Produced file must match pending_email_*.json pattern."""
        from src.helpers.email_helper import (
            PENDING_FILENAME_PREFIX,
            PENDING_FILENAME_SUFFIX,
            _serialize_payload_to_disk,
        )

        out_path = _serialize_payload_to_disk(_make_payload(), tmp_path)
        assert out_path is not None
        assert out_path.name.startswith(PENDING_FILENAME_PREFIX)
        assert out_path.name.endswith(PENDING_FILENAME_SUFFIX)

    def test_attachment_paths_stored_as_strings_not_path_objects(self, tmp_path):
        """JSON cannot serialize Path objects; builder converts to str."""
        from src.helpers.email_helper import _serialize_payload_to_disk

        attach_path = tmp_path / "some_log.log"
        attach_path.write_text("log content", encoding="utf-8")
        payload = _make_payload(attachments=[str(attach_path)])

        out_path = _serialize_payload_to_disk(payload, tmp_path)
        assert out_path is not None
        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        for item in loaded["attachments"]:
            assert isinstance(item, str), "Attachment path must be a str in JSON"

    def test_disk_full_during_serialize_returns_none_silently(
        self, tmp_path, monkeypatch
    ):
        """OSError during write must be swallowed; returns None."""
        from src.helpers.email_helper import _serialize_payload_to_disk
        import builtins

        real_open = builtins.open

        def exploding_open(file, *args, **kwargs):
            if str(file).endswith(".tmp"):
                raise OSError("No space left on device")
            return real_open(file, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", exploding_open)

        result = _serialize_payload_to_disk(_make_payload(), tmp_path)
        assert result is None


# ===========================================================================
# TestAttemptSend
# ===========================================================================

class TestAttemptSend:
    """Tests for _attempt_send — SMTP calls, return values, failure modes."""

    def test_attempt_send_returns_false_when_channel_disabled(
        self, monkeypatch
    ):
        """Both env vars unset → _attempt_send returns False; SMTP_SSL not called."""
        monkeypatch.delenv("PYTREEMANAGER_EMAIL_PASSWORD", raising=False)
        monkeypatch.delenv("PYTREEMANAGER_EMAIL_RECIPIENT", raising=False)

        smtp_mock = MagicMock()
        monkeypatch.setattr(smtplib, "SMTP_SSL", smtp_mock)

        from src.helpers.email_helper import _attempt_send
        result = _attempt_send(_make_payload())

        assert result is False
        smtp_mock.assert_not_called()

    def test_attempt_send_calls_smtp_ssl_with_correct_host_port_timeout(
        self, monkeypatch
    ):
        """SMTP_SSL must be called with smtp.gmail.com, 465, timeout=10."""
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_PASSWORD", "test_pass")
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_RECIPIENT", "test@example.com")

        smtp_instance = MagicMock()
        smtp_instance.__enter__ = MagicMock(return_value=smtp_instance)
        smtp_instance.__exit__ = MagicMock(return_value=False)
        smtp_class = MagicMock(return_value=smtp_instance)
        monkeypatch.setattr(smtplib, "SMTP_SSL", smtp_class)

        from src.helpers.email_helper import (
            SMTP_HOST,
            SMTP_PORT_SSL,
            SMTP_TIMEOUT_SECONDS,
            _attempt_send,
        )
        _attempt_send(_make_payload())

        smtp_class.assert_called_once_with(
            SMTP_HOST, SMTP_PORT_SSL, timeout=SMTP_TIMEOUT_SECONDS
        )

    def test_attempt_send_returns_true_on_success(self, monkeypatch):
        """Mock SMTP succeeds; _attempt_send returns True."""
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_PASSWORD", "test_pass")
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_RECIPIENT", "test@example.com")

        smtp_instance = MagicMock()
        smtp_instance.__enter__ = MagicMock(return_value=smtp_instance)
        smtp_instance.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr(smtplib, "SMTP_SSL", MagicMock(return_value=smtp_instance))

        from src.helpers.email_helper import _attempt_send
        result = _attempt_send(_make_payload())

        assert result is True

    def test_attempt_send_returns_false_on_smtp_auth_failure(self, monkeypatch):
        """SMTPAuthenticationError → _attempt_send returns False."""
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_PASSWORD", "wrong_pass")
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_RECIPIENT", "test@example.com")

        smtp_instance = MagicMock()
        smtp_instance.__enter__ = MagicMock(return_value=smtp_instance)
        smtp_instance.__exit__ = MagicMock(return_value=False)
        smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(
            535, b"Bad credentials"
        )
        monkeypatch.setattr(smtplib, "SMTP_SSL", MagicMock(return_value=smtp_instance))

        from src.helpers.email_helper import _attempt_send
        result = _attempt_send(_make_payload())

        assert result is False

    def test_attempt_send_returns_false_on_connection_timeout(self, monkeypatch):
        """socket.timeout → _attempt_send returns False; no recursive enqueue."""
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_PASSWORD", "test_pass")
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_RECIPIENT", "test@example.com")

        monkeypatch.setattr(
            smtplib, "SMTP_SSL", MagicMock(side_effect=socket.timeout("timed out"))
        )

        from src.helpers import email_helper as email_helper_module
        enqueue_calls: list = []
        real_enqueue = email_helper_module.enqueue_email_for_severity

        def counting_enqueue(*args, **kwargs):
            enqueue_calls.append((args, kwargs))
            return real_enqueue(*args, **kwargs)

        # Patch enqueue to watch call count
        monkeypatch.setattr(email_helper_module, "enqueue_email_for_severity", counting_enqueue)

        from src.helpers.email_helper import _attempt_send
        result = _attempt_send(_make_payload())

        assert result is False
        # _attempt_send must NOT call enqueue_email_for_severity (no recursion)
        assert len(enqueue_calls) == 0


# ===========================================================================
# TestQueueLifecycle
# ===========================================================================

class TestQueueLifecycle:
    """Tests for _walk_queue_and_retry — drain, retain, quarantine, skip, permission."""

    def _write_payload_file(self, queue_dir: Path, payload: Dict[str, Any]) -> Path:
        """Helper: write a valid JSON payload file directly (bypassing uuid naming)."""
        fname = f"pending_email_{uuid.uuid4()}.json"
        p = queue_dir / fname
        p.write_text(json.dumps(payload), encoding="utf-8")
        return p

    def test_walk_queue_drains_pending_files_on_send_success(
        self, tmp_path, monkeypatch
    ):
        """When _attempt_send returns True, all 3 queue files are removed."""
        from src.helpers import email_helper as email_helper_module
        from src.helpers.email_helper import _walk_queue_and_retry

        queue_dir = tmp_path / "pending"
        queue_dir.mkdir()
        for _ in range(3):
            self._write_payload_file(queue_dir, _make_payload())

        monkeypatch.setattr(email_helper_module, "_attempt_send", MagicMock(return_value=True))

        _walk_queue_and_retry(queue_dir)

        remaining = list(queue_dir.glob("pending_email_*.json"))
        assert remaining == [], f"Expected no files remaining, found {remaining}"

    def test_walk_queue_leaves_pending_files_on_send_failure(
        self, tmp_path, monkeypatch
    ):
        """When _attempt_send returns False, all 3 queue files survive."""
        from src.helpers import email_helper as email_helper_module
        from src.helpers.email_helper import _walk_queue_and_retry

        queue_dir = tmp_path / "pending"
        queue_dir.mkdir()
        for _ in range(3):
            self._write_payload_file(queue_dir, _make_payload())

        monkeypatch.setattr(email_helper_module, "_attempt_send", MagicMock(return_value=False))

        _walk_queue_and_retry(queue_dir)

        remaining = list(queue_dir.glob("pending_email_*.json"))
        assert len(remaining) == 3

    def test_walk_queue_quarantines_corrupt_payload(self, tmp_path, monkeypatch):
        """Invalid JSON file moves to quarantine/; doesn't block other files."""
        from src.helpers import email_helper as email_helper_module
        from src.helpers.email_helper import QUARANTINE_DIR_NAME, _walk_queue_and_retry

        queue_dir = tmp_path / "pending"
        queue_dir.mkdir()
        bad_file = queue_dir / "pending_email_corrupt.json"
        bad_file.write_text("{ NOT VALID JSON", encoding="utf-8")

        monkeypatch.setattr(email_helper_module, "_attempt_send", MagicMock(return_value=True))

        _walk_queue_and_retry(queue_dir)

        quarantine_dir = queue_dir / QUARANTINE_DIR_NAME
        assert quarantine_dir.exists(), "Quarantine dir must be created"
        quarantined = list(quarantine_dir.iterdir())
        assert len(quarantined) >= 1, "Corrupt file must be moved to quarantine"
        # The bad file must no longer be in the queue dir directly
        assert not bad_file.exists(), "Corrupt file must be removed from queue root"

    def test_walk_queue_skips_when_no_pending_files(self, tmp_path, monkeypatch):
        """Empty queue dir → _attempt_send never called."""
        from src.helpers import email_helper as email_helper_module
        from src.helpers.email_helper import _walk_queue_and_retry

        queue_dir = tmp_path / "pending"
        queue_dir.mkdir()

        send_mock = MagicMock()
        monkeypatch.setattr(email_helper_module, "_attempt_send", send_mock)

        _walk_queue_and_retry(queue_dir)

        send_mock.assert_not_called()

    def test_walk_queue_handles_permission_error_silently(self, tmp_path, monkeypatch):
        """PermissionError during file delete must not raise."""
        from src.helpers import email_helper as email_helper_module
        from src.helpers.email_helper import _walk_queue_and_retry

        queue_dir = tmp_path / "pending"
        queue_dir.mkdir()
        self._write_payload_file(queue_dir, _make_payload())

        monkeypatch.setattr(email_helper_module, "_attempt_send", MagicMock(return_value=True))

        # Make Path.unlink raise PermissionError
        original_unlink = Path.unlink

        def exploding_unlink(self_path, *args, **kwargs):
            if "pending_email_" in str(self_path):
                raise PermissionError("Access denied")
            return original_unlink(self_path, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", exploding_unlink)

        # Must not raise
        _walk_queue_and_retry(queue_dir)


# ===========================================================================
# TestEnqueueEmailForSeverity
# ===========================================================================

class TestEnqueueEmailForSeverity:
    """Tests for the public enqueue_email_for_severity() function."""

    def test_enqueue_returns_true_on_send_success(self, tmp_path, monkeypatch):
        """Mock send returns True → function returns True; no leftover file."""
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_PASSWORD", "test_pass")
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_RECIPIENT", "test@example.com")

        # Point queue dir to tmp_path
        from src.helpers import email_helper as email_helper_module
        pending_dir = tmp_path / "pending"
        monkeypatch.setattr(email_helper_module, "_queue_dir", lambda: pending_dir)

        # Mock successful SMTP
        smtp_instance = MagicMock()
        smtp_instance.__enter__ = MagicMock(return_value=smtp_instance)
        smtp_instance.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr(smtplib, "SMTP_SSL", MagicMock(return_value=smtp_instance))

        from src.helpers.email_helper import enqueue_email_for_severity
        result = enqueue_email_for_severity(
            severity="ERROR",
            headline="Test headline",
            handler_name="test_handler",
        )

        assert result is True
        # Queue dir should have no pending file after successful send
        if pending_dir.exists():
            remaining = list(pending_dir.glob("pending_email_*.json"))
            assert remaining == [], "File should be deleted after successful send"

    def test_enqueue_returns_false_on_send_failure(self, tmp_path, monkeypatch):
        """Mock send returns False → function returns False; payload file survives."""
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_PASSWORD", "test_pass")
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_RECIPIENT", "test@example.com")

        from src.helpers import email_helper as email_helper_module
        pending_dir = tmp_path / "pending"
        monkeypatch.setattr(email_helper_module, "_queue_dir", lambda: pending_dir)
        monkeypatch.setattr(email_helper_module, "_attempt_send", MagicMock(return_value=False))

        from src.helpers.email_helper import enqueue_email_for_severity
        result = enqueue_email_for_severity(
            severity="ERROR",
            headline="Test headline",
            handler_name="test_handler",
        )

        assert result is False
        # File should remain on disk
        assert pending_dir.exists()
        remaining = list(pending_dir.glob("pending_email_*.json"))
        assert len(remaining) == 1

    def test_enqueue_returns_false_when_channel_disabled(self, tmp_path, monkeypatch):
        """Env vars unset → returns False; payload still written (queue-while-disabled)."""
        monkeypatch.delenv("PYTREEMANAGER_EMAIL_PASSWORD", raising=False)
        monkeypatch.delenv("PYTREEMANAGER_EMAIL_RECIPIENT", raising=False)

        from src.helpers import email_helper as email_helper_module
        pending_dir = tmp_path / "pending"
        monkeypatch.setattr(email_helper_module, "_queue_dir", lambda: pending_dir)

        smtp_mock = MagicMock()
        monkeypatch.setattr(smtplib, "SMTP_SSL", smtp_mock)

        from src.helpers.email_helper import enqueue_email_for_severity
        result = enqueue_email_for_severity(
            severity="REPORT",
            headline="Manual report",
            handler_name="_user_requested_report",
        )

        assert result is False
        smtp_mock.assert_not_called()

    def test_enqueue_does_not_raise_on_internal_failure(self, tmp_path, monkeypatch):
        """If _serialize_payload_to_disk raises OSError, function returns False without raising."""
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_PASSWORD", "test_pass")
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_RECIPIENT", "test@example.com")

        from src.helpers import email_helper as email_helper_module
        pending_dir = tmp_path / "pending"
        monkeypatch.setattr(email_helper_module, "_queue_dir", lambda: pending_dir)
        monkeypatch.setattr(
            email_helper_module,
            "_serialize_payload_to_disk",
            MagicMock(side_effect=OSError("disk full")),
        )

        from src.helpers.email_helper import enqueue_email_for_severity
        # Must not raise
        result = enqueue_email_for_severity(
            severity="ERROR",
            headline="Serialization failure test",
            handler_name="test_handler",
        )
        assert result is False


# ===========================================================================
# TestRetryTimer
# ===========================================================================

class TestRetryTimer:
    """Tests for start_retry_timer / stop_retry_timer construction and teardown."""

    def test_start_retry_timer_creates_wx_timer_with_correct_interval(
        self, monkeypatch
    ):
        """start_retry_timer must call timer.Start with RETRY_INTERVAL_MS, oneShot=False."""
        # We cannot use a real wx.App in L0 tests, so mock wx.Timer at the
        # helpers.email_helper level.
        import src.helpers.email_helper as email_helper_module
        from src.helpers.email_helper import RETRY_INTERVAL_MS

        timer_instance = MagicMock()
        timer_class = MagicMock(return_value=timer_instance)

        # Patch _EmailRetryTimer inside email_helper so we don't need wx
        monkeypatch.setattr(email_helper_module, "_EmailRetryTimer", timer_class)

        host_window = MagicMock()
        from src.helpers.email_helper import start_retry_timer
        returned = start_retry_timer(host_window)

        timer_class.assert_called_once_with(host_window)
        timer_instance.Start.assert_called_once_with(RETRY_INTERVAL_MS, oneShot=False)
        assert returned is timer_instance

    def test_stop_retry_timer_calls_stop_on_timer(self, monkeypatch):
        """stop_retry_timer must call Stop() on the passed timer."""
        timer_mock = MagicMock()

        from src.helpers.email_helper import stop_retry_timer
        stop_retry_timer(timer_mock)

        timer_mock.Stop.assert_called_once()


# ===========================================================================
# TestNoRecursionGuard
# ===========================================================================

class TestNoRecursionGuard:
    """Verify _attempt_send failure does NOT call enqueue_email_for_severity."""

    def test_attempt_send_failure_calls_log_error_but_not_enqueue_again(
        self, monkeypatch
    ):
        """
        When _attempt_send fails internally (SMTP raises), it should call
        log_error for the failure record but must NOT call enqueue_email_for_severity
        (which would create a recursive loop).
        """
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_PASSWORD", "test_pass")
        monkeypatch.setenv("PYTREEMANAGER_EMAIL_RECIPIENT", "test@example.com")

        # SMTP raises a connection error
        monkeypatch.setattr(
            smtplib,
            "SMTP_SSL",
            MagicMock(side_effect=ConnectionRefusedError("refused")),
        )

        from src.helpers import email_helper as email_helper_module

        log_error_calls: list = []
        enqueue_calls: list = []

        original_log_error = email_helper_module.log_error

        def capturing_log_error(*args, **kwargs):
            log_error_calls.append((args, kwargs))
            # Call real log_error but swallow writes (no log dir set up)
            try:
                return original_log_error(*args, **kwargs)
            except Exception:
                pass

        monkeypatch.setattr(email_helper_module, "log_error", capturing_log_error)
        monkeypatch.setattr(
            email_helper_module,
            "enqueue_email_for_severity",
            lambda *a, **kw: enqueue_calls.append((a, kw)) or False,
        )

        from src.helpers.email_helper import _attempt_send
        result = _attempt_send(_make_payload())

        assert result is False
        # log_error should have been called (best-effort failure record)
        assert len(log_error_calls) >= 1
        # enqueue_email_for_severity must NOT be called from inside _attempt_send
        assert len(enqueue_calls) == 0, (
            "_attempt_send must not call enqueue_email_for_severity "
            "(would create infinite recursion)"
        )
