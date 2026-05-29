"""L0 unit tests for update-path observability log lines (sprint-20, ADR-018 §2.2).

Verifies that:
1. check_for_update emits "no result" INFO on network/parse error.
2. check_for_update emits "up to date" INFO when no newer version found.
3. check_for_update does NOT emit "up to date" when a newer version IS found.
4. download_and_apply_update emits "dev mode skip" INFO when not frozen.
5. download_and_apply_update emits "update.bat not found" INFO when bat is missing.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch
from urllib.error import URLError

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _release_payload_101() -> str:
    return json.dumps({
        "tag_name": "v1.0.1",
        "name": "v1.0.1",
        "body": "",
        "draft": False,
        "prerelease": False,
        "published_at": "2026-05-29T10:00:00Z",
        "assets": [{
            "name": "py-tree-manager-1.0.1.exe",
            "browser_download_url": "https://github.com/example/releases/download/v1.0.1/py-tree-manager-1.0.1.exe",
            "size": 12345678,
            "content_type": "application/octet-stream",
        }],
    })


def _make_fake_response(body: str) -> MagicMock:
    encoded = body.encode("utf-8")
    mock_response = MagicMock()
    mock_response.read.return_value = encoded
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


# ---------------------------------------------------------------------------
# Test 1: check_for_update logs "no result" on network error
# ---------------------------------------------------------------------------

class TestCheckForUpdateLogsNoResultOnNetworkError:
    """When network raises, an INFO 'no result' line must be emitted."""

    def test_check_for_update_logs_no_result_on_network_error(self):
        from src.helpers.update_helper import UpdateHelper

        with patch("urllib.request.urlopen", side_effect=URLError("Name or service not known")), \
             patch("src.helpers.update_helper._emit_info_raw") as mock_emit:
            result = UpdateHelper.check_for_update("1.0.0")

        assert result is None
        assert mock_emit.called, "Expected _emit_info_raw to be called on network error"
        all_payloads = [c.args[1] for c in mock_emit.call_args_list]
        assert any("no result" in p for p in all_payloads), (
            f"Expected a 'no result' log line; got: {all_payloads}"
        )


# ---------------------------------------------------------------------------
# Test 2: check_for_update logs "up to date" when no newer version
# ---------------------------------------------------------------------------

class TestCheckForUpdateLogsUpToDate:
    """When latest == current, an INFO 'up to date' line must be emitted."""

    def test_check_for_update_logs_up_to_date(self):
        from src.helpers.update_helper import UpdateHelper

        same_payload = json.dumps({
            "tag_name": "v1.0.0",
            "published_at": "2026-05-29T10:00:00Z",
            "assets": [{
                "name": "py-tree-manager-1.0.0.exe",
                "browser_download_url": "https://github.com/example/py-tree-manager-1.0.0.exe",
            }],
        })

        with patch("urllib.request.urlopen", return_value=_make_fake_response(same_payload)), \
             patch("src.helpers.update_helper._emit_info_raw") as mock_emit:
            result = UpdateHelper.check_for_update("1.0.0")

        assert result is None
        assert mock_emit.called, "Expected _emit_info_raw to be called when up to date"
        all_payloads = [c.args[1] for c in mock_emit.call_args_list]
        assert any("up to date" in p for p in all_payloads), (
            f"Expected an 'up to date' log line; got: {all_payloads}"
        )


# ---------------------------------------------------------------------------
# Test 3: check_for_update does NOT log "up to date" when newer is found
# ---------------------------------------------------------------------------

class TestCheckForUpdateNoUpToDateLogWhenNewer:
    """When a newer version IS found, the 'up to date' line must NOT be emitted."""

    def test_check_for_update_no_up_to_date_log_on_newer(self):
        from src.helpers.update_helper import UpdateHelper

        with patch("urllib.request.urlopen", return_value=_make_fake_response(_release_payload_101())), \
             patch("src.helpers.update_helper._emit_info_raw") as mock_emit:
            result = UpdateHelper.check_for_update("1.0.0")

        assert result is not None, "Expected UpdateInfo returned for newer version"
        all_payloads = [c.args[1] for c in mock_emit.call_args_list]
        assert not any("up to date" in p for p in all_payloads), (
            f"'up to date' must NOT be logged when a newer version exists; got: {all_payloads}"
        )


# ---------------------------------------------------------------------------
# Test 4: download_and_apply_update logs "dev mode skip" when not frozen
# ---------------------------------------------------------------------------

class TestDownloadAndApplyLogsDevModeSkip:
    """When sys.frozen is False, 'dev mode' INFO must be emitted."""

    def test_download_and_apply_logs_dev_mode_skip(self, monkeypatch):
        from src.helpers.update_helper import UpdateHelper
        from src.helpers.update_info import UpdateInfo

        monkeypatch.setattr(sys, "frozen", False, raising=False)
        fake_info = UpdateInfo(
            latest_version="1.0.1",
            download_url="https://example.com/py-tree-manager-1.0.1.exe",
            published_at="2026-05-29T10:00:00Z",
        )

        with patch("src.helpers.update_helper._emit_info_raw") as mock_emit:
            UpdateHelper.download_and_apply_update(fake_info)

        assert mock_emit.called, "Expected _emit_info_raw to be called in dev mode"
        all_payloads = [c.args[1] for c in mock_emit.call_args_list]
        assert any("dev mode" in p for p in all_payloads), (
            f"Expected a 'dev mode' log line; got: {all_payloads}"
        )


# ---------------------------------------------------------------------------
# Test 5: download_and_apply_update logs "update.bat not found" when bat missing
# ---------------------------------------------------------------------------

class TestDownloadAndApplyLogsUpdateBatNotFound:
    """When frozen but update.bat is absent, 'update.bat not found' INFO must fire."""

    def test_download_and_apply_logs_update_bat_not_found(self, tmp_path, monkeypatch):
        from src.helpers.update_helper import UpdateHelper
        from src.helpers.update_info import UpdateInfo

        fake_exe = tmp_path / "PyTreeManager.exe"
        fake_exe.write_bytes(b"fake exe")
        # update.bat intentionally NOT created

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", str(fake_exe))

        fake_info = UpdateInfo(
            latest_version="1.0.1",
            download_url="https://example.com/py-tree-manager-1.0.1.exe",
            published_at="2026-05-29T10:00:00Z",
        )

        with patch("src.helpers.update_helper._emit_info_raw") as mock_emit:
            UpdateHelper.download_and_apply_update(fake_info)

        assert mock_emit.called, "Expected _emit_info_raw to be called when bat missing"
        all_payloads = [c.args[1] for c in mock_emit.call_args_list]
        assert any("update.bat not found" in p for p in all_payloads), (
            f"Expected an 'update.bat not found' log line; got: {all_payloads}"
        )
