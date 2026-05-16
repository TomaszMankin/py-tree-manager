"""Entry point for py-tree-manager.

Installs Python sys.excepthook BEFORE any wx import; uses a LoggingApp
subclass that overrides OnExceptionInMainLoop. Together these capture every
uncaught exception (startup-time via excepthook, event-handler-time via
OnExceptionInMainLoop).
"""

# install_python_excepthook MUST be importable WITHOUT importing wx.
# helpers/logger.py defines it at module scope before the wx-dependent
# LoggingApp class, so this import is wx-free.
from src.helpers.logger import install_python_excepthook
install_python_excepthook()

import wx  # noqa: E402 — wx imported AFTER hook is installed
from src.helpers.logger import LoggingApp  # noqa: E402

if __name__ == "__main__":
    app = LoggingApp(False)
    app.MainLoop()
