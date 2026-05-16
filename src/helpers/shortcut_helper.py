import win32com.client
import pythoncom
from win32com.shell import shell as win32_shell
from pathlib import Path
from typing import Protocol


class IWshShortcut(Protocol):
    """Type hint protocol for Windows Script Host Shortcut COM object.

    Provides IntelliSense support for shortcut properties.
    """
    TargetPath: str
    WorkingDirectory: str
    Description: str
    IconLocation: str

    def save(self) -> None:
        """Save the shortcut to disk."""
        ...


class ShortcutHelper():
    """Helper class for creating and managing Windows shortcuts (.lnk files).

    Provides utility methods for creating shortcuts to person folders and
    managing relationship folders (Dzieci, Rodzice, Małżonkowie, Rodzeństwo).
    """

    CHILDREN_FOLDER = "Dzieci"
    PARENTS_FOLDER = "Rodzice"
    SPOUSES_FOLDER = "Małżonkowie"
    SIBLINGS_FOLDER = "Rodzeństwo"

    @staticmethod
    def create_shortcut(target_path: str, shortcut_path: str) -> None:
        """Create a Windows shortcut (.lnk) file pointing to a target directory.

        Creates a .lnk shortcut file at the specified path that points to the
        target directory. Validates that the target exists and is a directory,
        and that the shortcut path ends with .lnk extension.

        Args:
            target_path: Absolute path to the target directory (e.g., person folder)
            shortcut_path: Absolute path where the shortcut should be created,
                          must end with '.lnk'

        Raises:
            ValueError: If shortcut_path is empty, doesn't end with .lnk,
                       parent directory doesn't exist, target_path is empty,
                       or target doesn't exist or isn't a directory

        Example:
            >>> ShortcutHelper.create_shortcut(
            ...     r"C:\TreeRoot\People\John Doe",
            ...     r"C:\TreeRoot\People\Jane Doe\Dzieci\John Doe.lnk"
            ... )
        """
        if not shortcut_path or not shortcut_path.strip():
            raise ValueError(f"Given shortcut creation location is not valid: <{shortcut_path}>")

        if not shortcut_path.lower().endswith('.lnk'):
            raise ValueError(f"Shortcut path should end with '<name>.lnk'. Given path: <{shortcut_path}>")
        
        parent_dir = Path(shortcut_path).parent
        if not parent_dir.exists():
            raise ValueError(f"Parent directory does not exist: <{parent_dir}>")

        if not target_path or not target_path.strip():
            raise ValueError(f"Given shortcut target location is not valid: <{target_path}>")
        
        if not Path(target_path).exists() or not Path(target_path).is_dir():
            raise ValueError(f"Given shortcut target location is not valid: <{target_path}>")

        # Use IShellLinkW + IPersistFile.Save directly (Unicode-clean).
        # WScript.Shell.CreateShortcut routes through IShellLinkA whose Save()
        # does a best-effort ANSI conversion, silently mangling non-cp1252 chars
        # (e.g. Polish ń, ł, ż) so the kernel returns ERROR_PATH_NOT_FOUND.
        # IShellLinkW marshals Python str as LPCOLESTR (UTF-16) — no ANSI step.
        # IShellLinkW marshals Python str as LPCOLESTR (UTF-16) — no ANSI step.
        link = pythoncom.CoCreateInstance(
            win32_shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            win32_shell.IID_IShellLink,
        )
        link.SetPath(target_path)
        link.QueryInterface(pythoncom.IID_IPersistFile).Save(shortcut_path, 0)

    @staticmethod
    def remove_shortcut(shortcut_path: str) -> None:
        """Remove an existing Windows shortcut (.lnk) file.

        Deletes the shortcut file at the specified path after validating
        that it exists and is a valid .lnk file.

        Args:
            shortcut_path: Absolute path to the shortcut file to remove,
                          must end with '.lnk'

        Raises:
            ValueError: If shortcut_path is empty or doesn't end with .lnk
            RuntimeError: If the path doesn't exist or is not a file

        Example:
            >>> ShortcutHelper.remove_shortcut(
            ...     r"C:\TreeRoot\People\Jane Doe\Dzieci\John Doe.lnk"
            ... )
        """
        if not shortcut_path or not shortcut_path.strip():
            raise ValueError(f"Given shortcut creation location is not valid: <{shortcut_path}>")

        if not shortcut_path.lower().endswith('.lnk'):
            raise ValueError(f"Shortcut path should end with '<name>.lnk'. Given path: <{shortcut_path}>")

        path = Path(shortcut_path)
        if not path.exists() or not path.is_file():
            raise RuntimeError("Given location is not a .lnk file or does not exists.")

        Path(shortcut_path).unlink()
