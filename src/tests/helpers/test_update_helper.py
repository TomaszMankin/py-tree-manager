"""L0 unit tests for src/helpers/update_helper.py.

Covers:
- Version comparison robustness (10 > 9, 1.10 > 1.9, etc.)
- check_for_update against the GitHub Releases /releases/latest JSON shape
- Network failure resilience (ALL shapes return None)
- Asset selection from the assets[] array (exact match + fallback)
- subprocess.Popen argv-order assertion for download_and_apply_update
- Skipped-version persistence round-trip
- Polish dialog string codepoints
- ensure_update_helper_present copies from _MEIPASS
"""

import json
import os
import socket
import sys
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _make_fake_response(body: str, status: int = 200) -> MagicMock:
    """Build a fake urllib response context-manager mock."""
    encoded = body.encode("utf-8")
    mock_response = MagicMock()
    mock_response.read.return_value = encoded
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


def _release_payload(
    tag_name: str = "v1.0.1",
    asset_name: str = "py-tree-manager-1.0.1.exe",
    asset_url: str = "https://github.com/TomaszMankin/py-tree-manager/releases/download/v1.0.1/py-tree-manager-1.0.1.exe",
    published_at: str = "2026-05-13T14:32:00Z",
    extra_assets: list = None,
) -> str:
    """Build a GitHub Releases /releases/latest JSON payload."""
    assets = [{
        "name": asset_name,
        "browser_download_url": asset_url,
        "size": 12345678,
        "content_type": "application/octet-stream",
    }]
    if extra_assets:
        assets.extend(extra_assets)
    return json.dumps({
        "tag_name": tag_name,
        "name": tag_name,
        "body": "Release notes go here.",
        "draft": False,
        "prerelease": False,
        "published_at": published_at,
        "assets": assets,
    })


_VALID_PAYLOAD = _release_payload()


# ---------------------------------------------------------------------------
# Version comparison
# ---------------------------------------------------------------------------

class TestCompareVersions:
    """Version comparison must be numeric, not lexicographic."""

    def test_10_greater_than_9_patch(self):
        from src.helpers.update_helper import _compare_versions
        assert _compare_versions("1.0.10", "1.0.9") is True

    def test_10_less_than_9_reverse(self):
        from src.helpers.update_helper import _compare_versions
        assert _compare_versions("1.0.9", "1.0.10") is False

    def test_minor_overflow(self):
        from src.helpers.update_helper import _compare_versions
        assert _compare_versions("1.10.0", "1.9.0") is True

    def test_major_wins_all(self):
        from src.helpers.update_helper import _compare_versions
        assert _compare_versions("2.0.0", "1.99.99") is True

    def test_equal_returns_false(self):
        from src.helpers.update_helper import _compare_versions
        assert _compare_versions("1.0.0", "1.0.0") is False

    def test_invalid_version_returns_false(self):
        from src.helpers.update_helper import _compare_versions
        assert _compare_versions("invalid-x", "1.0.0") is False

    def test_invalid_both_returns_false(self):
        from src.helpers.update_helper import _compare_versions
        assert _compare_versions("abc", "xyz") is False


# ---------------------------------------------------------------------------
# check_for_update happy path
# ---------------------------------------------------------------------------

class TestCheckForUpdateHappyPath:
    """Happy-path scenarios that should return UpdateInfo."""

    def test_newer_version_returns_update_info(self):
        from src.helpers.update_helper import UpdateHelper
        from src.helpers.update_info import UpdateInfo
        with patch("urllib.request.urlopen", return_value=_make_fake_response(_VALID_PAYLOAD)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is not None
        assert isinstance(result, UpdateInfo)
        assert result.latest_version == "1.0.1"
        assert result.download_url.startswith("https://")
        assert result.published_at == "2026-05-13T14:32:00Z"

    def test_tag_name_strips_leading_v(self):
        """tag_name with v-prefix -> stored as plain version string."""
        from src.helpers.update_helper import UpdateHelper
        payload = _release_payload(tag_name="v2.5.7", asset_name="py-tree-manager-2.5.7.exe",
                                    asset_url="https://example.com/py-tree-manager-2.5.7.exe")
        with patch("urllib.request.urlopen", return_value=_make_fake_response(payload)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is not None
        assert result.latest_version == "2.5.7"


# ---------------------------------------------------------------------------
# check_for_update no-update / skip
# ---------------------------------------------------------------------------

class TestCheckForUpdateNoUpdate:
    """Scenarios that should return None (no prompt)."""

    def test_same_version_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        payload = _release_payload(tag_name="v1.0.0",
                                    asset_name="py-tree-manager-1.0.0.exe",
                                    asset_url="https://example.com/py-tree-manager-1.0.0.exe")
        with patch("urllib.request.urlopen", return_value=_make_fake_response(payload)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_downgrade_scenario_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        payload = _release_payload(tag_name="v0.9.0",
                                    asset_name="py-tree-manager-0.9.0.exe",
                                    asset_url="https://example.com/py-tree-manager-0.9.0.exe")
        with patch("urllib.request.urlopen", return_value=_make_fake_response(payload)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_skipped_version_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        with patch("urllib.request.urlopen", return_value=_make_fake_response(_VALID_PAYLOAD)):
            result = UpdateHelper.check_for_update("1.0.0", skipped_version="1.0.1")
        assert result is None

    def test_skipped_older_version_does_not_suppress_newer(self):
        from src.helpers.update_helper import UpdateHelper
        from src.helpers.update_info import UpdateInfo
        payload = _release_payload(tag_name="v1.0.2",
                                    asset_name="py-tree-manager-1.0.2.exe",
                                    asset_url="https://example.com/py-tree-manager-1.0.2.exe")
        with patch("urllib.request.urlopen", return_value=_make_fake_response(payload)):
            result = UpdateHelper.check_for_update("1.0.0", skipped_version="1.0.1")
        assert result is not None
        assert isinstance(result, UpdateInfo)
        assert result.latest_version == "1.0.2"

    def test_http_url_rejected(self):
        from src.helpers.update_helper import UpdateHelper
        payload = _release_payload(
            asset_url="http://example.com/py-tree-manager-1.0.1.exe"
        )
        with patch("urllib.request.urlopen", return_value=_make_fake_response(payload)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None


# ---------------------------------------------------------------------------
# Network failures
# ---------------------------------------------------------------------------

class TestCheckForUpdateNetworkFailures:
    """Every network-failure shape returns None; no exception propagated."""

    def test_socket_timeout_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        with patch("urllib.request.urlopen", side_effect=socket.timeout("timed out")):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_urlerror_dns_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        with patch("urllib.request.urlopen", side_effect=URLError("Name or service not known")):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_httperror_404_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            url="https://example.com", code=404, msg="Not Found", hdrs=None, fp=None
        )):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_httperror_500_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            url="https://example.com", code=500, msg="Server Error", hdrs=None, fp=None
        )):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_json_malformed_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        with patch("urllib.request.urlopen", return_value=_make_fake_response("not json at all")):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_missing_tag_name_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        partial = json.dumps({"assets": [{"name": "x.exe", "browser_download_url": "https://x"}]})
        with patch("urllib.request.urlopen", return_value=_make_fake_response(partial)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_missing_assets_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        partial = json.dumps({"tag_name": "v1.0.1", "published_at": "2026-05-13T14:32:00Z"})
        with patch("urllib.request.urlopen", return_value=_make_fake_response(partial)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_empty_assets_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        payload = json.dumps({
            "tag_name": "v1.0.1",
            "published_at": "2026-05-13T14:32:00Z",
            "assets": [],
        })
        with patch("urllib.request.urlopen", return_value=_make_fake_response(payload)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_unparseable_version_in_tag_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        payload = _release_payload(tag_name="v-not-a-version")
        with patch("urllib.request.urlopen", return_value=_make_fake_response(payload)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_os_error_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None


# ---------------------------------------------------------------------------
# Asset selection
# ---------------------------------------------------------------------------

class TestAssetSelection:
    """The asset list may contain multiple assets; pick the right .exe."""

    def test_exact_name_match(self):
        from src.helpers.update_helper import UpdateHelper
        payload = _release_payload(
            asset_name="py-tree-manager-1.0.1.exe",
            asset_url="https://example.com/correct.exe",
            extra_assets=[
                {"name": "checksums.txt", "browser_download_url": "https://example.com/sums",
                 "size": 100, "content_type": "text/plain"},
                {"name": "source.zip", "browser_download_url": "https://example.com/src.zip",
                 "size": 1000, "content_type": "application/zip"},
            ],
        )
        with patch("urllib.request.urlopen", return_value=_make_fake_response(payload)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is not None
        assert result.download_url == "https://example.com/correct.exe"

    def test_single_exe_fallback(self):
        """If exact name does NOT match but exactly one .exe exists, use it."""
        from src.helpers.update_helper import UpdateHelper
        payload = _release_payload(
            asset_name="differently-named.exe",
            asset_url="https://example.com/the.exe",
        )
        with patch("urllib.request.urlopen", return_value=_make_fake_response(payload)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is not None
        assert result.download_url == "https://example.com/the.exe"

    def test_multiple_exes_no_match_returns_none(self):
        """Two .exe assets, none matching expected name -> ambiguous -> None."""
        from src.helpers.update_helper import UpdateHelper
        payload = _release_payload(
            asset_name="foo.exe",
            asset_url="https://example.com/foo.exe",
            extra_assets=[
                {"name": "bar.exe", "browser_download_url": "https://example.com/bar.exe",
                 "size": 1, "content_type": "application/octet-stream"},
            ],
        )
        with patch("urllib.request.urlopen", return_value=_make_fake_response(payload)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None

    def test_no_exe_at_all_returns_none(self):
        from src.helpers.update_helper import UpdateHelper
        payload = json.dumps({
            "tag_name": "v1.0.1",
            "published_at": "2026-05-13T14:32:00Z",
            "assets": [
                {"name": "checksums.txt", "browser_download_url": "https://x/sums",
                 "size": 100, "content_type": "text/plain"},
            ],
        })
        with patch("urllib.request.urlopen", return_value=_make_fake_response(payload)):
            result = UpdateHelper.check_for_update("1.0.0")
        assert result is None


# ---------------------------------------------------------------------------
# subprocess.Popen argv-order assertion
# ---------------------------------------------------------------------------

class TestDownloadAndApplyUpdateArgvOrder:
    """Argv order must be exactly
    ["cmd.exe", "/c", bat_path, exe_path, new_exe_path, parent_pid]."""

    def test_argv_order_matches_spec(self, tmp_path, monkeypatch):
        from src.helpers.update_helper import UpdateHelper
        from src.helpers.update_info import UpdateInfo

        fake_exe = tmp_path / "py-tree-manager.exe"
        fake_exe.write_bytes(b"fake exe")
        fake_bat = tmp_path / "update.bat"
        fake_bat.write_text("@echo off\n")

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        monkeypatch.setattr(sys, "executable", str(fake_exe))

        fake_info = UpdateInfo(
            latest_version="1.0.1",
            download_url="https://example.com/py-tree-manager-1.0.1.exe",
            published_at="2026-05-13T14:32:00Z",
        )

        captured_args = []

        def fake_popen(args, **kwargs):
            captured_args.extend(args)
            return MagicMock()

        with patch("src.helpers.update_helper.subprocess.Popen", side_effect=fake_popen), \
             patch("src.helpers.update_helper._download_to"), \
             patch("sys.exit"):
            UpdateHelper.download_and_apply_update(fake_info)

        new_exe = fake_exe.with_suffix(".exe.new")

        assert len(captured_args) == 6, f"Expected 6 argv items, got {len(captured_args)}: {captured_args}"
        assert captured_args[0] == "cmd.exe"
        assert captured_args[1] == "/c"
        assert captured_args[2] == str(fake_bat.resolve())
        assert captured_args[3] == str(fake_exe.resolve())
        assert captured_args[4] == str(new_exe.resolve())
        assert captured_args[5].isdigit(), f"Expected numeric PID, got: {captured_args[5]}"

    def test_dev_mode_skips_without_calling_popen(self, monkeypatch):
        from src.helpers.update_helper import UpdateHelper
        from src.helpers.update_info import UpdateInfo

        monkeypatch.setattr(sys, "frozen", False, raising=False)

        fake_info = UpdateInfo(
            latest_version="1.0.1",
            download_url="https://example.com/py-tree-manager-1.0.1.exe",
            published_at="2026-05-13T14:32:00Z",
        )

        with patch("src.helpers.update_helper.subprocess.Popen") as mock_popen:
            UpdateHelper.download_and_apply_update(fake_info)
        mock_popen.assert_not_called()

    def test_missing_helper_skips_without_calling_popen(self, tmp_path, monkeypatch):
        from src.helpers.update_helper import UpdateHelper
        from src.helpers.update_info import UpdateInfo

        fake_exe = tmp_path / "py-tree-manager.exe"
        fake_exe.write_bytes(b"fake exe")
        # update.bat intentionally NOT created

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", str(fake_exe))

        fake_info = UpdateInfo(
            latest_version="1.0.1",
            download_url="https://example.com/py-tree-manager-1.0.1.exe",
            published_at="2026-05-13T14:32:00Z",
        )

        with patch("src.helpers.update_helper.subprocess.Popen") as mock_popen:
            UpdateHelper.download_and_apply_update(fake_info)
        mock_popen.assert_not_called()


# ---------------------------------------------------------------------------
# ensure_update_helper_present
# ---------------------------------------------------------------------------

class TestEnsureUpdateHelperPresent:
    """ensure_update_helper_present copies update.bat from _MEIPASS to exe_dir."""

    def test_copies_from_meipass_when_missing(self, tmp_path, monkeypatch):
        from src.helpers.update_helper import UpdateHelper

        meipass_dir = tmp_path / "meipass"
        meipass_dir.mkdir()
        (meipass_dir / "update.bat").write_text("@echo off\n")

        exe_dir = tmp_path / "exedir"
        exe_dir.mkdir()
        fake_exe = exe_dir / "py-tree-manager.exe"
        fake_exe.write_bytes(b"")

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(meipass_dir), raising=False)
        monkeypatch.setattr(sys, "executable", str(fake_exe))

        UpdateHelper.ensure_update_helper_present()

        assert (exe_dir / "update.bat").exists()

    def test_skips_when_already_present(self, tmp_path, monkeypatch):
        from src.helpers.update_helper import UpdateHelper

        meipass_dir = tmp_path / "meipass"
        meipass_dir.mkdir()
        (meipass_dir / "update.bat").write_text("@echo off\nREM meipass version\n")

        exe_dir = tmp_path / "exedir"
        exe_dir.mkdir()
        existing = exe_dir / "update.bat"
        existing.write_text("@echo off\nREM existing version\n")
        fake_exe = exe_dir / "py-tree-manager.exe"
        fake_exe.write_bytes(b"")

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(meipass_dir), raising=False)
        monkeypatch.setattr(sys, "executable", str(fake_exe))

        UpdateHelper.ensure_update_helper_present()

        assert existing.read_text() == "@echo off\nREM existing version\n"

    def test_dev_mode_is_no_op(self, monkeypatch):
        from src.helpers.update_helper import UpdateHelper

        monkeypatch.setattr(sys, "frozen", False, raising=False)
        UpdateHelper.ensure_update_helper_present()


# ---------------------------------------------------------------------------
# Polish dialog codepoints
# ---------------------------------------------------------------------------

class TestPolishDialogCodepoints:
    """Polish dialog strings must contain verified Unicode codepoints."""

    def test_title_contains_e_with_ogonek(self):
        from src.helpers.update_helper import DIALOG_TITLE
        assert "ę" in DIALOG_TITLE, f"Expected ę (U+0119) in DIALOG_TITLE: {repr(DIALOG_TITLE)}"

    def test_no_label_contains_e_with_ogonek_in_te(self):
        from src.helpers.update_helper import DIALOG_NO_LABEL
        assert "ę" in DIALOG_NO_LABEL, (
            f"Expected ę (U+0119) in DIALOG_NO_LABEL for 'tę': {repr(DIALOG_NO_LABEL)}"
        )

    def test_body_contains_c_with_acute(self):
        from src.helpers.update_helper import DIALOG_BODY_NORMAL
        assert "ć" in DIALOG_BODY_NORMAL, (
            f"Expected ć (U+0107) in DIALOG_BODY_NORMAL for 'Zaktualizować': {repr(DIALOG_BODY_NORMAL)}"
        )

    def test_yes_label_is_polish(self):
        from src.helpers.update_helper import DIALOG_YES_LABEL
        assert isinstance(DIALOG_YES_LABEL, str)
        assert len(DIALOG_YES_LABEL) > 0

    def test_no_label_is_polish(self):
        from src.helpers.update_helper import DIALOG_NO_LABEL
        assert isinstance(DIALOG_NO_LABEL, str)
        assert len(DIALOG_NO_LABEL) > 0


# ---------------------------------------------------------------------------
# remember_skipped_version round-trip
# ---------------------------------------------------------------------------

class TestRememberSkippedVersion:
    """Skipped version persistence round-trip."""

    def test_round_trip_via_settings_wrapper(self):
        from src.helpers.update_helper import UpdateHelper
        from src.wrappers.settings_wrapper import SettingsWrapper

        wrapper = SettingsWrapper({})
        UpdateHelper.remember_skipped_version(wrapper, "1.0.1")
        assert wrapper.get_skipped_update_version() == "1.0.1"

    def test_overwrite_clears_old_skipped(self):
        from src.helpers.update_helper import UpdateHelper
        from src.wrappers.settings_wrapper import SettingsWrapper

        wrapper = SettingsWrapper({})
        UpdateHelper.remember_skipped_version(wrapper, "1.0.1")
        UpdateHelper.remember_skipped_version(wrapper, "1.0.2")
        assert wrapper.get_skipped_update_version() == "1.0.2"

    def test_skipped_version_suppresses_same_version(self):
        from src.helpers.update_helper import UpdateHelper
        with patch("urllib.request.urlopen", return_value=_make_fake_response(_VALID_PAYLOAD)):
            result = UpdateHelper.check_for_update("1.0.0", skipped_version="1.0.1")
        assert result is None


# ---------------------------------------------------------------------------
# _download_to helper
# ---------------------------------------------------------------------------

class TestDownloadTo:
    """_download_to streams to file correctly."""

    def test_happy_path_writes_bytes(self, tmp_path):
        from src.helpers.update_helper import _download_to

        expected = b"fake exe content" * 100
        mock_response = MagicMock()
        mock_response.read.side_effect = [expected, b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        dest = tmp_path / "py-tree-manager.exe.new"
        with patch("urllib.request.urlopen", return_value=mock_response):
            _download_to("https://example.com/file.exe", dest, timeout=30)

        assert dest.exists()
        assert dest.read_bytes() == expected

    def test_timeout_propagates(self, tmp_path):
        from src.helpers.update_helper import _download_to

        with patch("urllib.request.urlopen", side_effect=socket.timeout("timed out")):
            with pytest.raises(socket.timeout):
                _download_to("https://example.com/file.exe", tmp_path / "out.new", timeout=1)
