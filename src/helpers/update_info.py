"""UpdateInfo dataclass — parsed payload of a GitHub Release."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateInfo:
    """Parsed metadata for the latest published release.

    Attributes:
        latest_version: PEP 440 version string (tag_name with leading "v" stripped).
        download_url:   Absolute HTTPS URL to the versioned .exe asset.
        published_at:   ISO-8601 timestamp from the GitHub release (display only).
        is_installer:   True when download_url points to a PyTreeManager-Setup-*.exe
                        Inno Setup installer; False for a raw PyInstaller .exe.
    """
    latest_version: str
    download_url: str
    published_at: str
    is_installer: bool = False
