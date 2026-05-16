"""Real-pywin32 integration tests for helpers/shortcut_helper.py.

These tests exercise ShortcutHelper.create_shortcut() and remove_shortcut()
against the actual WScript.Shell COM dispatch on Windows. They are skipped
automatically when real pywin32 is not installed in the active environment.

Isolation:
- tests/conftest.py (root) installs a win32com.client stub at import time.
- tests/integration/conftest.py provides an autouse fixture that removes the
  stub before each test and restores it afterward, so the services tests that
  run in the same session still work.
- _has_real_pywin32() uses a subprocess to detect pywin32 without mutating
  sys.modules (the autouse fixture handles that at test execution time).

Skipping (not failing) when pywin32 is absent is the designed-for case.

To run integration tests explicitly:
    pytest -v tests/integration/

Install pywin32 if needed:
    python -m pip install pywin32
"""
import importlib
import subprocess
import sys
from pathlib import Path

import pytest


def _has_real_pywin32() -> bool:
    """Return True iff real pywin32 is installed in the active Python environment.

    Uses a subprocess so this check never mutates the current process's sys.modules.
    The integration conftest's autouse fixture handles actual stub removal at runtime.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import win32com.client, sys; "
                "f = getattr(sys.modules['win32com.client'], '__file__', None); "
                "exit(0 if (f and 'site-packages' in f.lower()) else 1)"
            ),
        ],
        capture_output=True,
    )
    return result.returncode == 0


_PYWIN32_AVAILABLE = _has_real_pywin32()

pytestmark = pytest.mark.skipif(
    not _PYWIN32_AVAILABLE,
    reason=(
        "Real pywin32 is not installed in this environment; integration test skipped. "
        "Install with: python -m pip install pywin32"
    ),
)


class TestShortcutRealPyWin32:
    """Integration tests that exercise WScript.Shell COM dispatch directly.

    The conftest autouse fixture in this directory ensures win32com.client is
    the real pywin32 for each test body. ShortcutHelper is reloaded so it
    re-binds to the real win32com.client rather than the stub it was
    originally imported with.
    """

    def test_create_shortcut_writes_real_lnk_pointing_at_target(self, tmp_path):
        """Creates a .lnk via ShortcutHelper, then re-opens it through WScript.Shell
        and asserts TargetPath matches the input target.

        Without real pywin32, the conftest stub creates an empty file with the right
        path but no actual shell-interpretable content. This test round-trips through
        the COM layer to confirm the file IS a real .lnk with correct TargetPath.
        """
        # Reload ShortcutHelper so it uses the real win32com.client (stub was popped
        # by the conftest autouse fixture before this test body runs).
        import src.helpers.shortcut_helper as sh_mod
        importlib.reload(sh_mod)
        ShortcutHelper = sh_mod.ShortcutHelper

        # Polish characters in the target dir name (Step 3: widen regression coverage).
        target = tmp_path / "Kowalski Rodzeństwo"
        target.mkdir()
        shortcut_path = tmp_path / "shortcut.lnk"

        ShortcutHelper.create_shortcut(str(target), str(shortcut_path))

        assert shortcut_path.is_file(), ".lnk file was not created"
        assert shortcut_path.stat().st_size > 0, (
            ".lnk file is empty -- likely a stub write, not a real COM-created shortcut"
        )

        # Round-trip: read back via IShellLinkW (Unicode-clean read).
        # WScript.Shell.CreateShortcut decodes TargetPath through ANSI on the
        # way out, mangling non-cp1252 chars in the target path even when the
        # .lnk file path itself is ASCII. IShellLinkW.GetPath returns the raw
        # UTF-16 stored value — the correct contract for a Unicode .lnk.
        import pythoncom
        from win32com.shell import shell as _win32_shell
        link2 = pythoncom.CoCreateInstance(
            _win32_shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            _win32_shell.IID_IShellLink,
        )
        link2.QueryInterface(pythoncom.IID_IPersistFile).Load(str(shortcut_path), 0)
        round_tripped_target = link2.GetPath(0)[0]
        assert round_tripped_target == str(target), (
            f"TargetPath mismatch: expected {str(target)!r}, got {round_tripped_target!r}"
        )

    def test_remove_shortcut_actually_deletes(self, tmp_path):
        """remove_shortcut() removes the .lnk file from disk entirely."""
        import src.helpers.shortcut_helper as sh_mod
        importlib.reload(sh_mod)
        ShortcutHelper = sh_mod.ShortcutHelper

        target = tmp_path / "Małgorzata Folder"
        target.mkdir()
        shortcut_path = tmp_path / "shortcut.lnk"

        ShortcutHelper.create_shortcut(str(target), str(shortcut_path))
        assert shortcut_path.is_file(), "Precondition: shortcut should exist before removal"

        ShortcutHelper.remove_shortcut(str(shortcut_path))
        assert not shortcut_path.exists(), ".lnk file still exists after remove_shortcut()"

    def test_create_shortcut_with_polish_chars_in_target_and_path(self, tmp_path):
        """Regression: create_shortcut must handle Polish characters (outside cp1252) in
        both the .lnk path and the target path.

        On the old WScript.Shell code path, chars such as 'ń' and 'ó' (Latin Extended-A,
        outside cp1252) cause HRESULT 0x80070003 (ERROR_PATH_NOT_FOUND) because the
        ANSI-era IShellLinkA/WshShortcut.Save() best-effort substitutes them and the
        kernel cannot find the resulting path.

        The new IShellLinkW + IPersistFile.Save() path bypasses ANSI conversion entirely.
        IShellLinkW + IPersistFile.Save() bypasses ANSI conversion entirely,
        handling Unicode paths on both read and write.

        TDD note: this test was written BEFORE the fix and verified to FAIL (HRESULT
        0x80070003 from shortcut.save()) on the old WScript.Shell code path.
        """
        import src.helpers.shortcut_helper as sh_mod
        importlib.reload(sh_mod)
        ShortcutHelper = sh_mod.ShortcutHelper

        # Target folder path with Polish characters outside cp1252 (ń, ó)
        target = tmp_path / "Rodzeństwo" / "Piotr Testowy"
        target.mkdir(parents=True)

        # Shortcut placed inside a Polish-character parent folder
        shortcut_dir = tmp_path / "Lista osób" / "Adam Kowalski" / "Rodzeństwo"
        shortcut_dir.mkdir(parents=True)
        shortcut_path = shortcut_dir / "Piotr Testowy.lnk"

        ShortcutHelper.create_shortcut(str(target), str(shortcut_path))

        assert shortcut_path.is_file(), (
            ".lnk file was not created — Polish-char path likely caused HRESULT 0x80070003"
        )
        assert shortcut_path.stat().st_size > 0, (
            ".lnk file is empty — stub write instead of real COM shortcut"
        )

        # Round-trip: read back via IShellLinkW (Unicode-clean read).
        # We use IShellLinkW here rather than WScript.Shell.CreateShortcut because
        # WScript.Shell's read path also goes through ANSI for the .lnk file path
        # itself — when the shortcut_path contains non-cp1252 chars, WScript.Shell
        # cannot load the file and returns an empty TargetPath. IShellLinkW handles
        # Unicode paths on both read and write.
        import pythoncom
        from win32com.shell import shell as _win32_shell
        link2 = pythoncom.CoCreateInstance(
            _win32_shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            _win32_shell.IID_IShellLink,
        )
        link2.QueryInterface(pythoncom.IID_IPersistFile).Load(str(shortcut_path), 0)
        round_tripped_target = link2.GetPath(0)[0]
        assert round_tripped_target == str(target), (
            f"TargetPath mismatch: expected {str(target)!r}, "
            f"got {round_tripped_target!r} — payload may be ANSI-mangled"
        )
