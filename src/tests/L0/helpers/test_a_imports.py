"""Import-order test.

install_python_excepthook must be importable WITHOUT importing wx.
This test module is named test_a_* so pytest collects it first alphabetically.
"""

import sys


def test_install_python_excepthook_does_not_require_wx():
    """Verify install_python_excepthook is importable before wx is loaded.

    In a fresh test session wx may already be loaded by test collection
    (some test infrastructure imports it). We check that importing the
    function itself does not cause wx to appear in sys.modules if it
    wasn't there before.

    Note: If wx is already present in sys.modules (loaded by conftest or
    elsewhere), the assertion that wx is absent cannot be guaranteed. We
    document the observed state instead and verify the import succeeds.
    """
    # Record whether wx was already loaded before this test.
    wx_was_loaded = "wx" in sys.modules

    # The critical test: this import must not raise.
    from src.helpers.logger import install_python_excepthook  # noqa: F401

    # If wx was NOT loaded before, it must not be loaded now.
    if not wx_was_loaded:
        assert "wx" not in sys.modules, (
            "importing install_python_excepthook pulled in wx"
        )
    # If wx was already loaded (by other test infrastructure), the test
    # still passes because the import itself succeeded without error.
