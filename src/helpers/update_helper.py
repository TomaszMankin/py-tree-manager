"""In-app update detection and self-replace helper.

Public API:
    UpdateInfo             - frozen dataclass with release metadata (importable
                             from src.helpers.update_info)
    UpdateHelper           - static-method namespace for all update operations

    UpdateHelper.check_for_update()       - poll GitHub Releases API, compare versions,
                                            return UpdateInfo or None
    UpdateHelper.prompt_user_to_update()  - wx dialog in Polish; returns True on accept
    UpdateHelper.remember_skipped_version() - write skipped_update_version to SettingsWrapper
    UpdateHelper.download_and_apply_update() - download .new, launch .bat, sys.exit
    UpdateHelper.ensure_update_helper_present() - copy update.bat from _MEIPASS on first launch

    _compare_versions()    - numeric semver compare; packaging.version backed (module-private)
    _download_to()         - stream URL to file path (module-private)
    _pick_asset_url()      - select the .exe asset URL from the GitHub release payload

All network operations are wrapped so a failed check NEVER crashes the app.

Polish dialog constants:
    DIALOG_TITLE, DIALOG_BODY_NORMAL, DIALOG_YES_LABEL, DIALOG_NO_LABEL
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError

from packaging.version import InvalidVersion, parse as parse_version

from src.helpers.update_info import UpdateInfo


# ---------------------------------------------------------------------------
# Deferred logger import — keep wx-free at module level
# ---------------------------------------------------------------------------

def _emit_info_raw(label: str, payload: str) -> None:  # type: ignore[return]
    """Emit one INFO line to the journey log.

    Delegates to logger._emit_info_raw. Wrapped so a logging failure NEVER
    breaks the update path — all callers are already inside their own
    try/except safety nets, but belt-and-suspenders here too.
    """
    try:
        from src.helpers.logger import _emit_info_raw as _logger_emit_info_raw  # noqa: PLC0415
        _logger_emit_info_raw(label, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITHUB_RELEASES_API_URL = (
    "https://api.github.com/repos/TomaszMankin/py-tree-manager/releases/latest"
)
ASSET_NAME_PREFIX = "py-tree-manager-"
INSTALLER_ASSET_NAME_PREFIX = "PyTreeManager-Setup-"
ASSET_NAME_SUFFIX = ".exe"
FETCH_TIMEOUT_SECONDS: float = 10.0
DOWNLOAD_TIMEOUT_SECONDS: float = 600.0
DOWNLOAD_CHUNK_BYTES: int = 64 * 1024
USER_AGENT = "py-tree-manager-updater"

# Polish dialog strings.
# Codepoints verified:
#   ę U+0119 - "Dostępna", "zamknie", "tę"
#   ż U+017C - "może"
#   ś U+015B - "się"
#   ć U+0107 - "Zaktualizować"
DIALOG_TITLE = "Dostępna jest nowa wersja"

DIALOG_BODY_NORMAL = (
    "Dostępna jest nowa wersja aplikacji: {latest}.\n"
    "Twoja wersja: {current}.\n"
    "Wydana: {published_at}.\n\n"
    "Zaktualizować teraz? Aplikacja zamknie się i sama się otworzy."
)

DIALOG_YES_LABEL = "Tak, zaktualizuj"
DIALOG_NO_LABEL = "Pomiń tę wersję"


# ---------------------------------------------------------------------------
# UpdateHelper static-method namespace
# ---------------------------------------------------------------------------

class UpdateHelper:
    """Update detection and self-replace operations.

    All methods are staticmethods; the class exists as a namespace grouping
    (project convention - see EmailHelper for the same pattern).
    """

    @staticmethod
    def check_for_update(
        current_version: str,
        skipped_version: Optional[str] = None,
        *,
        url: str = GITHUB_RELEASES_API_URL,
        timeout: float = FETCH_TIMEOUT_SECONDS,
    ) -> Optional[UpdateInfo]:
        """Return UpdateInfo if a newer, non-skipped version is available.

        Polls the GitHub Releases API endpoint /releases/latest, which
        returns the most recent non-draft, non-prerelease release. PR
        prereleases are excluded server-side.

        Returns None for any of:
        - Any network / DNS / HTTP / timeout error
        - JSON malformed or required field missing
        - No .exe asset attached to the release
        - asset browser_download_url not HTTPS
        - latest_version <= current_version
        - latest_version == skipped_version
        """
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": USER_AGENT,
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
            data = json.loads(raw)

            tag_name = data.get("tag_name")
            if not isinstance(tag_name, str) or not tag_name:
                return None
            latest_version = tag_name.lstrip("v")

            try:
                parse_version(latest_version)
            except InvalidVersion:
                return None

            published_at = data.get("published_at") or ""

            assets = data.get("assets") or []
            if not isinstance(assets, list) or not assets:
                return None

            download_url, is_installer = _pick_asset_url(assets, latest_version)
            if download_url is None:
                return None
            if not download_url.startswith("https://"):
                return None

            if skipped_version and latest_version == skipped_version:
                return None

            if not _compare_versions(latest_version, current_version):
                _emit_info_raw(
                    "-",
                    f"Update check: up to date (latest={latest_version} current={current_version})",
                )
                return None

            return UpdateInfo(
                latest_version=latest_version,
                download_url=download_url,
                published_at=published_at,
                is_installer=is_installer,
            )

        except (socket.timeout, URLError, HTTPError, OSError,
                json.JSONDecodeError, KeyError, TypeError, ValueError):
            _emit_info_raw(
                "-",
                f"Update check: no result (network/parse) — staying on {current_version}",
            )
            return None
        except Exception:
            # Catch-all: update_helper MUST NEVER crash the app.
            _emit_info_raw(
                "-",
                f"Update check: no result (network/parse) — staying on {current_version}",
            )
            return None

    @staticmethod
    def prompt_user_to_update(parent_window, update_info: UpdateInfo) -> bool:
        """Show a wx.MessageDialog with Polish text. Return True if user clicked Yes.

        Caller is responsible for wx being available (this is only called from
        LoggingApp.OnInit inside the wx event loop).
        """
        import wx  # noqa: PLC0415 - deferred; wx not available in unit tests

        current_version: str = "?"
        try:
            from importlib.metadata import version as _pkg_version
            current_version = _pkg_version("py-tree-manager")
        except Exception:
            pass

        body = DIALOG_BODY_NORMAL.format(
            latest=update_info.latest_version,
            current=current_version,
            published_at=update_info.published_at,
        )

        dlg = wx.MessageDialog(
            parent_window, body, DIALOG_TITLE,
            wx.YES_NO | wx.ICON_INFORMATION,
        )
        dlg.SetYesNoLabels(DIALOG_YES_LABEL, DIALOG_NO_LABEL)
        result = dlg.ShowModal()
        dlg.Destroy()
        return result == wx.ID_YES

    @staticmethod
    def remember_skipped_version(settings_wrapper, version: str) -> None:
        """Write skipped_update_version to a SettingsWrapper in-memory.

        Caller must separately persist the settings to disk (via FileService).
        """
        settings_wrapper.set_skipped_update_version(version)

    @staticmethod
    def download_and_apply_update(update_info: UpdateInfo) -> None:
        """Download the update and apply it, then sys.exit(0).

        Installer flow (update_info.is_installer=True):
            Download PyTreeManager-Setup-<v>.exe to a temp dir,
            run it /VERYSILENT /NORESTART. Inno Setup replaces the exe
            in-place and recreates all shortcuts.

        Raw-exe fallback (is_installer=False):
            Download to <exe>.new, launch update.bat swap helper.

        In dev mode (sys.frozen is False): returns without doing anything.
        On any error before launch: log and return (app keeps running).
        """
        import tempfile  # noqa: PLC0415

        if not getattr(sys, "frozen", False):
            _emit_info_raw("-", "Update: dev mode (not frozen) — self-replace skipped")
            return

        if update_info.is_installer:
            tmp_dir = Path(tempfile.gettempdir()) / "PyTreeManagerUpdate"
            try:
                tmp_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            installer_path = tmp_dir / f"PyTreeManager-Setup-{update_info.latest_version}.exe"

            try:
                _download_to(update_info.download_url, installer_path,
                             timeout=DOWNLOAD_TIMEOUT_SECONDS)
            except Exception as e:
                _emit_info_raw("-", f"Update: download failed for {update_info.download_url} — {e}")
                try:
                    from src.helpers.email_helper import enqueue_email_for_severity  # noqa: PLC0415
                    enqueue_email_for_severity(
                        severity="ERROR",
                        headline=f"Auto-update download failed: {e}",
                        body_extra=f"version={update_info.latest_version} url={update_info.download_url}",
                        handler_name="download_and_apply_update",
                    )
                except Exception:
                    pass
                return

            try:
                _emit_info_raw("-", f"Update: launching installer silently; exiting")
                subprocess.Popen(
                    [str(installer_path), "/VERYSILENT", "/NORESTART"],
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                    close_fds=True,
                )
            except Exception as e:
                _emit_info_raw("-", f"Update: installer launch failed — {e}")
                try:
                    from src.helpers.email_helper import enqueue_email_for_severity  # noqa: PLC0415
                    enqueue_email_for_severity(
                        severity="ERROR",
                        headline=f"Auto-update installer launch failed: {e}",
                        body_extra=f"version={update_info.latest_version} installer={installer_path}",
                        handler_name="download_and_apply_update",
                    )
                except Exception:
                    pass
                return
            sys.exit(0)

        else:
            exe_path = Path(sys.executable).resolve()
            exe_dir = exe_path.parent
            new_exe_path = exe_path.with_suffix(".exe.new")
            bat_path = exe_dir / "update.bat"

            if not bat_path.exists():
                _emit_info_raw("-", f"Update: update.bat not found at {bat_path} — cannot self-replace")
                return

            try:
                _download_to(update_info.download_url, new_exe_path,
                             timeout=DOWNLOAD_TIMEOUT_SECONDS)
            except Exception:
                _emit_info_raw("-", f"Update: download failed for {update_info.download_url}")
                try:
                    if new_exe_path.exists():
                        new_exe_path.unlink()
                except OSError as e:
                    _emit_info_raw("-", f"Update: cleanup of partial download failed — {e}")
                return

            parent_pid = str(os.getpid())
            try:
                _emit_info_raw("-", "Update: launching update.bat; exiting for swap")
                subprocess.Popen(
                    ["cmd.exe", "/c", str(bat_path),
                     str(exe_path), str(new_exe_path), parent_pid],
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                    close_fds=True,
                )
            except Exception as e:
                _emit_info_raw("-", f"Update: update.bat launch failed — {e}")
                return
            sys.exit(0)

    @staticmethod
    def ensure_update_helper_present() -> None:
        """Copy update.bat from PyInstaller's _MEIPASS bundle into exe_dir.

        Called once per launch in LoggingApp.OnInit (before the update check).
        Dev mode: no-op. Frozen mode: copies the bundled update.bat next to
        the running .exe if the file isn't already there.
        """
        if not getattr(sys, "frozen", False):
            return

        exe_dir = Path(sys.executable).resolve().parent
        target = exe_dir / "update.bat"
        if target.exists():
            return

        meipass = getattr(sys, "_MEIPASS", None)
        if meipass is None:
            return
        bundled = Path(meipass) / "update.bat"
        if not bundled.exists():
            return

        try:
            shutil.copy2(str(bundled), str(target))
        except OSError:
            pass


# Module-level alias so tests importing _ensure_update_helper_present by name continue to work.
_ensure_update_helper_present = UpdateHelper.ensure_update_helper_present


# ---------------------------------------------------------------------------
# Internal helpers (module-private; not part of UpdateHelper namespace)
# ---------------------------------------------------------------------------

def _pick_asset_url(assets: list, version: str):
    """Pick the best .exe asset URL from a GitHub release's assets array.

    Returns (url: str, is_installer: bool) or (None, False).

    Strategy:
      1. Prefer Inno Setup installer: "PyTreeManager-Setup-<version>.exe"
      2. Fallback to raw exe: "py-tree-manager-<version>.exe"
      3. Fallback to any single .exe asset
      4. Otherwise (None, False)
    """
    installer_name = f"{INSTALLER_ASSET_NAME_PREFIX}{version}{ASSET_NAME_SUFFIX}"
    raw_name = f"{ASSET_NAME_PREFIX}{version}{ASSET_NAME_SUFFIX}"

    installer_url = None
    raw_url = None
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        url = asset.get("browser_download_url")
        if not isinstance(url, str):
            continue
        if name == installer_name:
            installer_url = url
        elif name == raw_name:
            raw_url = url

    if installer_url:
        return installer_url, True
    if raw_url:
        return raw_url, False

    exe_assets = [
        a for a in assets
        if isinstance(a, dict)
        and isinstance(a.get("name"), str)
        and a["name"].endswith(ASSET_NAME_SUFFIX)
        and isinstance(a.get("browser_download_url"), str)
    ]
    if len(exe_assets) == 1:
        return exe_assets[0]["browser_download_url"], False
    return None, False


def _compare_versions(a: str, b: str) -> bool:
    """Return True iff version a is strictly greater than version b.

    Uses packaging.version.parse for correct numeric comparison
    (guards against the string-compare bug where '1.0.10' < '1.0.9'
    lexicographically). Falls back to tuple int-split on InvalidVersion.
    Returns False on any parse failure (treat as 'no update').
    """
    try:
        return parse_version(a) > parse_version(b)
    except InvalidVersion:
        try:
            ta = tuple(int(x) for x in a.split("."))
            tb = tuple(int(x) for x in b.split("."))
            return ta > tb
        except (ValueError, TypeError):
            return False


def _download_to(url: str, dest: Path, *, timeout: float) -> None:
    """Stream the URL contents to a file. Raises on any error (caller handles).

    Sends a User-Agent header because GitHub's CDN occasionally rejects
    requests with no UA.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        with open(dest, "wb") as f:
            while True:
                chunk = response.read(DOWNLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                f.write(chunk)
