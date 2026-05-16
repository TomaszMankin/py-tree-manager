"""Integration-test conftest.

Isolation note: tests/conftest.py (root) patches ShortcutHelper.create_shortcut
with a no-op stub at import time. Integration tests need the REAL create_shortcut.

This conftest provides an autouse fixture that:
1. Reloads helpers.shortcut_helper before each integration test so it runs the
   real IShellLinkW + IPersistFile.Save implementation.
2. Re-installs the stub after each integration test so service-layer tests that
   run in the same pytest session continue to get the no-op stub.

pywin32 is installed and the implementation uses pythoncom + win32com.shell
directly — no stub for those modules is needed.
"""
import importlib

import pytest


@pytest.fixture(autouse=True)
def _integration_real_shortcut_helper():
    """Function-scoped fixture: restore real ShortcutHelper; re-stub after.

    Applied automatically to every test in tests/integration/ only.
    """
    import src.helpers.shortcut_helper as sh_mod

    # Reload to get the real (un-stubbed) staticmethod definition.
    importlib.reload(sh_mod)

    yield

    # Re-install the stub so subsequent (non-integration) tests still work.
    from src.tests.conftest import _install_shortcut_stub
    _install_shortcut_stub()
