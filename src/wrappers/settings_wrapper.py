
from enum import Enum
from typing import Any, Dict


class SettingsDataProperty(Enum):
    FONT_SIZE = "font_size"
    ROOT_FOLDER_PATH = "root_folder_path"
    CACHED_PEOPLE = "cached_people"
    SELECT_ROOT_FOLDER = "select_root_folder"
    # JSON value kept as "drzewo_root_uuid" for back-compat with existing user settings files.
    # Python identifier is English per the project-wide code-vs-UI naming rule.
    FOLDER_TREE_ROOT_UUID = "drzewo_root_uuid"  # None means no root person designated
    SKIPPED_UPDATE_VERSION = "skipped_update_version"

class SettingsWrapper():

    def __init__(self, settings: Dict[str, Any] | None):
        self.settings = {} if settings is None else settings

    # -------------------------------------------------------------------------
    # Generic interface
    # -------------------------------------------------------------------------

    def get(self, property: SettingsDataProperty) -> Any | None:
        """Get property value, returns None if not found."""
        return self.settings.get(property.value)

    def set(self, property: SettingsDataProperty, value: Any) -> None:
        """Set property value."""
        self.settings[property.value] = value

    def to_dict(self) -> Dict[str, Any]:
        """Return underlying dictionary."""
        return self.settings
    
    # -------------------------------------------------------------------------
    # Settings
    # -------------------------------------------------------------------------

    def get_font_size(self) -> int | None:
        return self.settings.get(SettingsDataProperty.FONT_SIZE.value, None)

    def set_font_size(self, value: int) -> None:
        self.settings[SettingsDataProperty.FONT_SIZE.value] = value

    def get_root_folder_path(self) -> str | None:
        return self.settings.get(SettingsDataProperty.ROOT_FOLDER_PATH.value, None)

    def set_root_folder_path(self, value: str) -> None:
        self.settings[SettingsDataProperty.ROOT_FOLDER_PATH.value] = value

    def get_cached_people(self) -> Dict[str, Dict[str, str]]:
        return self.settings.get(SettingsDataProperty.CACHED_PEOPLE.value, {})

    def set_cached_people(self, value: Dict[str, Dict[str, str]]) -> None:
        self.settings[SettingsDataProperty.CACHED_PEOPLE.value] = value

    def get_select_root_folder(self) -> bool:
        return self.settings.get(SettingsDataProperty.SELECT_ROOT_FOLDER.value, True)

    def set_select_root_folder(self, value: bool) -> None:
        self.settings[SettingsDataProperty.SELECT_ROOT_FOLDER.value] = value

    def get_folder_tree_root_uuid(self) -> str | None:
        return self.settings.get(SettingsDataProperty.FOLDER_TREE_ROOT_UUID.value, None)

    def set_folder_tree_root_uuid(self, value: str | None) -> None:
        self.settings[SettingsDataProperty.FOLDER_TREE_ROOT_UUID.value] = value

    def get_skipped_update_version(self) -> str | None:
        """Return the version string the user last declined, or None."""
        return self.settings.get(SettingsDataProperty.SKIPPED_UPDATE_VERSION.value, None)

    def set_skipped_update_version(self, value: str | None) -> None:
        """Persist the skipped version in-memory. Call FileService.save_settings() to flush."""
        self.settings[SettingsDataProperty.SKIPPED_UPDATE_VERSION.value] = value
    