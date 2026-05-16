from pathlib import Path
from typing import Dict, List, Any, Union, Optional
from src.wrappers.person_data_wrapper import PersonDataProperty, PersonDataWrapper
import os
import tempfile
import json
import shutil

from src.wrappers.settings_wrapper import SettingsDataProperty, SettingsWrapper


# ---------------------------------------------------------------------------
# Bootstrap pointer helpers (module-level; no class membership required)
# ---------------------------------------------------------------------------

def _bootstrap_pointer_path() -> Path:
    """%LOCALAPPDATA%\\PyTreeManager\\last_root.txt, with tempdir fallback.

    If %LOCALAPPDATA% is unset (degraded mode), falls back to
    tempfile.gettempdir()/PyTreeManager/last_root.txt.  The caller is
    responsible for emitting a CRITICAL log line when the env var is
    missing (mirrors helpers/logger.py _localappdata_log_dir fallback).
    """
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "PyTreeManager" / "last_root.txt"
    # Degraded mode: %LOCALAPPDATA% unset.
    return Path(tempfile.gettempdir()) / "PyTreeManager" / "last_root.txt"


def _read_bootstrap_pointer(pointer_path: Path) -> Optional[Path]:
    """Return the root path from the pointer file, or None if absent/invalid/stale.

    Returns None when:
    - The pointer file does not exist.
    - The file cannot be read (permission error, etc.).
    - The file is empty or whitespace-only.
    - The path stored in the file does not exist on disk (stale pointer).
    """
    if not pointer_path.exists():
        return None
    try:
        content = pointer_path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not content:
        return None
    candidate = Path(content)
    if not candidate.exists():
        # Stale pointer — root moved or deleted.
        return None
    return candidate


def _write_bootstrap_pointer(pointer_path: Path, root_path: Path) -> None:
    """Write the absolute root path to the pointer file. Idempotent overwrite.

    Creates parent directories if they don't exist.
    """
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(str(root_path), encoding="utf-8")


def _migrate_from_legacy_temp(
    legacy_settings_path: Path,
    pointer_path: Path,
) -> Optional[Path]:
    """One-shot migration of %TEMP%/PyTreeManager/settings.json into <root>/.PyTreeManager/.

    Migration steps:
      1. Read legacy JSON and extract root_folder_path.
      2. Verify the root exists on disk.
      3. mkdir <root>/.PyTreeManager (parents=True, exist_ok=True).
      4. shutil.move legacy to <root>/.PyTreeManager/settings.json.
         (shutil.move handles cross-volume; os.replace does not.)
      5. Write pointer file.
      6. Best-effort rmdir of the now-empty legacy %TEMP%/PyTreeManager/ dir.

    Returns the root Path on success, None on any failure.
    Failure leaves the legacy file in place for forensic recovery.
    """
    try:
        with open(legacy_settings_path, 'r', encoding='utf-8-sig') as f:
            legacy = json.load(f)
        root_str = legacy.get(SettingsDataProperty.ROOT_FOLDER_PATH.value, "")
        if not root_str:
            return None
        root_path = Path(root_str)
        if not root_path.exists():
            return None

        new_dir = root_path / ".PyTreeManager"
        new_dir.mkdir(parents=True, exist_ok=True)
        new_settings_path = new_dir / "settings.json"

        shutil.move(str(legacy_settings_path), str(new_settings_path))

        _write_bootstrap_pointer(pointer_path, root_path)

        # Best-effort: remove the now-empty legacy dir.
        legacy_dir = legacy_settings_path.parent
        try:
            if not any(legacy_dir.iterdir()):
                legacy_dir.rmdir()
        except OSError:
            pass

        return root_path
    except Exception:
        # Migration failed. Leave legacy in place. Caller falls through to fresh-install.
        return None


class FileService:
    """Service for managing file system operations and application settings.

    This service handles:
    - Settings file management (stored under <root>/.PyTreeManager/)
    - Bootstrap pointer read/write (%LOCALAPPDATA%/PyTreeManager/last_root.txt)
    - One-shot migration from legacy %TEMP%/PyTreeManager/settings.json
    - Root folder configuration
    - Person folder creation and management
    - Scanning and caching people from the root location
    - Generic JSON file reading/writing
    - File moving operations

    Attributes:
        _settings_file_path (Optional[Path]): Path to settings.json; None until
            set_root_folder() is called on a fresh install.
        saved_drafts_locations (List[str]): List of existing json drafts
        settings (SettingsWrapper): Loaded settings wrapper
        _forbidden_locations (List[str]): Folder names to skip during scanning
    """

    def __init__(self) -> None:
        """Initialize the FileService using pointer-driven bootstrap.

        Bootstrap sequence:
          1. Read pointer from %LOCALAPPDATA%/PyTreeManager/last_root.txt.
          2. If no pointer, check for legacy %TEMP%/PyTreeManager/settings.json
             and run one-shot migration.
          3. Load settings from <root>/.PyTreeManager/settings.json if found.
          4. Otherwise fall through to in-memory default (fresh install); defer
             disk write until set_root_folder() is called.
        """
        self.saved_drafts_locations = []
        self._settings_file_path: Optional[Path] = None

        # 1. Try the pointer.
        pointer_path = _bootstrap_pointer_path()
        candidate_root: Optional[Path] = _read_bootstrap_pointer(pointer_path)

        # 2. If no pointer, check for legacy %TEMP% settings to migrate.
        if candidate_root is None:
            legacy_settings = Path(tempfile.gettempdir()) / "PyTreeManager" / "settings.json"
            if legacy_settings.exists():
                candidate_root = _migrate_from_legacy_temp(legacy_settings, pointer_path)
                # _migrate_from_legacy_temp returns root path on success, None on failure.

        # 3. Load settings from new location, or fall through to fresh install.
        if candidate_root is not None:
            new_settings_path = candidate_root / ".PyTreeManager" / "settings.json"
            if new_settings_path.exists():
                with open(new_settings_path, 'r', encoding='utf-8-sig') as f:
                    self.settings: SettingsWrapper = SettingsWrapper(json.load(f))
                self._settings_file_path = new_settings_path
            else:
                # Pointer pointed somewhere with no settings — treat as fresh install
                # on the recorded root (don't re-migrate; pointer says already migrated).
                self.settings = SettingsWrapper(self._get_default_settings_json())
                self._settings_file_path = None
        else:
            # Fresh install — defer disk write until set_root_folder().
            self.settings = SettingsWrapper(self._get_default_settings_json())
            self._settings_file_path = None

        self._forbidden_locations: List[str] = [
            "Pozostałe nieuporządkowane",
            "Rutowscy - dane ogólne",
            "Do ustalenia",
            "Wspólne"
        ]
            
    def _get_default_settings_json(self) -> Dict[str, Any]:
        """Get the default settings structure.

        Returns:
            Dict[str, Any]: Dictionary containing default settings:
                - tree_location: Empty string (no root folder selected yet)
                - select_root_folder: True (user needs to select root folder)
                - font_size: Default font size of 20
                - cached_people: Empty dict (will be populated after scanning)
        """
        return {
            SettingsDataProperty.ROOT_FOLDER_PATH.value: "",
            SettingsDataProperty.SELECT_ROOT_FOLDER.value: True,
            SettingsDataProperty.FONT_SIZE.value: 20,
            SettingsDataProperty.CACHED_PEOPLE.value: {}
        }

    def _create_default_settings(self, path: Path) -> Dict[str, Any]:
        """Create a new settings file with default values.

        Args:
            path (Path): Path where the settings file should be created

        Returns:
            Dict[str, Any]: The default settings dictionary
        """
        path.touch()
        settings = self._get_default_settings_json()
        self._dump_json_data(path, settings)

        return settings
    
    def get_settings(self) -> SettingsWrapper:
        return SettingsWrapper(self.settings.to_dict().copy())

    def save_settings(self) -> None:
        """Flush the in-memory settings to disk (settings.json).

        No-op if _settings_file_path is not yet set (fresh install where
        set_root_folder has not been called yet).  Called by callers
        (e.g. the update_helper) that mutate self.settings and need to persist.
        """
        if self._settings_file_path is not None:
            self._dump_json_data(self._settings_file_path, self.settings.to_dict())
        
    def set_root_folder(self, path: str) -> None:
        """Set the root folder for the family tree and create necessary subdirectories.

        Creates subdirectories (including .PyTreeManager/):
        - "Lista osób" (People List): Contains all person folders
        - "Drzewo" (Tree): For tree visualizations
        - "Poczekalnia" (Waiting Room): For pending/unprocessed data
        - "Rody" (Clans): Family-branch surname shortcuts
        - ".PyTreeManager/": Runtime state (settings + logs + email queue)
        - ".PyTreeManager/logs/": Log files

        Also writes/updates the bootstrap pointer at
        %LOCALAPPDATA%/PyTreeManager/last_root.txt and relocates the logger.

        Args:
            path (str): Absolute path to the root folder

        Raises:
            FileNotFoundError: If the specified path does not exist
        """
        root_path = Path(path)

        if not root_path.exists():
            raise FileNotFoundError(f"Selected path: <{path}> does not exist.")

        self._set_root_folder(root_path)
        self._set_root_selected_flag(False)

        (root_path / "Lista osób").mkdir(exist_ok=True)
        (root_path / "Drzewo").mkdir(exist_ok=True)
        (root_path / "Poczekalnia").mkdir(exist_ok=True)
        (root_path / "Rody").mkdir(exist_ok=True)
        # Consolidate runtime state under .PyTreeManager/
        (root_path / ".PyTreeManager").mkdir(exist_ok=True)
        (root_path / ".PyTreeManager" / "logs").mkdir(exist_ok=True)

        self._settings_file_path = root_path / ".PyTreeManager" / "settings.json"
        self._dump_json_data(self._settings_file_path, self.settings.to_dict())

        _write_bootstrap_pointer(_bootstrap_pointer_path(), root_path)

        # Relocate the logger to the new .PyTreeManager/logs/ directory.
        try:
            from src.helpers.logger import init_logging  # noqa: PLC0415 — deferred
            init_logging(root_path)
        except Exception:
            pass  # logger init must NEVER crash the app

    def _get_unique_folder_name(self, base_name: str) -> str:
        """Return the first available folder name in "Lista osób".

        If base_name does not exist, returns it unchanged.
        Otherwise appends (2), (3), ... until a free name is found.

        Args:
            base_name (str): Desired folder name (person's full name)

        Returns:
            str: Unique folder name safe to use for mkdir()
        """
        root = Path(self._get_root_folder()) / 'Lista osób'
        if not (root / base_name).exists():
            return base_name
        counter = 2
        while (root / f"{base_name} ({counter})").exists():
            counter += 1
        return f"{base_name} ({counter})"

    def create_person_folder(self, folder_name: str, person_data: PersonDataWrapper) -> str:
        """Create a new person folder with me.json and relationship subfolders.

        Creates the person folder in "Lista osób" directory, then creates four
        relationship subfolders (Dzieci, Rodzice, Małżonkowie, Rodzeństwo) and
        writes the person data to me.json.

        If a folder with the same name already exists, appends (2), (3), etc.

        Args:
            folder_name (str): Base name of the person folder to create
            person_data (PersonDataWrapper): Dictionary containing person data for me.json

        Raises:
            RuntimeError: If root folder has not been set

        Returns:
            str: Path to newly created person folder.
        """
        if not self._get_root_selected_flag():
            raise RuntimeError("Root path is not set.")

        root = Path(self._get_root_folder())

        folder_name = self._get_unique_folder_name(folder_name)
        root_person_path = root / 'Lista osób' / folder_name
        root_person_path.mkdir()

        person_data.set_location(str(root_person_path))
        cached_people = self.settings.get_cached_people()
        new_cached_person = {
            PersonDataProperty.UNIQUE_IDENTIFIER.value: person_data.get_unique_identifier(),
            PersonDataProperty.LOCATION.value: person_data.get_location(),
            PersonDataProperty.PERSON_NAME.value: folder_name
        }
        cached_people[person_data.get_unique_identifier()] = new_cached_person
        self.settings.set_cached_people(cached_people)

        self._ensure_all_person_folders_created(root_person_path)

        me_file_path = root / 'Lista osób' / folder_name / "me.json"
        me_file_path.touch()

        self._dump_json_data(me_file_path, person_data.to_dict())

        return person_data.get_location()

    def get_list_of_people(self) -> Dict[str, Dict[str, str]]:
        return self._get_list_of_people()

    def scan_root_location(self) -> None:
        """Scan the "Lista osób" directory and cache all people.

        Iterates through all folders in "Lista osób", reads their me.json files,
        and builds a cached list of people with their paths and UUIDs. Skips
        forbidden folders and invalid directories.

        The cached list is stored in settings and persisted to disk.

        Raises:
            RuntimeError: If root folder has not been set  
        """
        if not self._get_root_selected_flag():
            raise RuntimeError("Root path is not set.")

        root_location = Path(self._get_root_folder())

        for folder in (root_location / "Lista osób").iterdir():
            if not folder.is_dir():
                continue

            if folder.name in self._forbidden_locations:
                continue

            me_json = folder / "me.json"
            if me_json.exists():
                with open(me_json, "r", encoding="utf-8-sig") as file:
                    person = json.load(file)
                    person_wrapper = PersonDataWrapper(person)
                    self._append_person_to_list_of_people(str(folder), person_wrapper.get_unique_identifier(), person_wrapper.get_full_name())

        if self._settings_file_path is not None:
            self._dump_json_data(self._settings_file_path, self.settings.to_dict())

    def get_poczekalnia_path(self) -> Path:
        """Return path to <root>/Poczekalnia/ — guaranteed to exist (created in set_root_folder).

        Raises:
            RuntimeError: If root path is not set.
        """
        if not self._get_root_selected_flag():
            raise RuntimeError("Root path is not set.")
        return Path(self._get_root_folder()) / "Poczekalnia"

    def scan_drafts_location(self) -> None:
        """Scan <root>/Poczekalnia/ for draft JSON files and populate saved_drafts_locations.

        Drafts live in <root>/Poczekalnia/ (JSON files, one per draft UUID).
        Settings.json lives at <root>/.PyTreeManager/ — it is not in Poczekalnia.
        """
        self.saved_drafts_locations = []
        if not self._get_root_selected_flag():
            # Root not set yet — drafts unreachable; keep list empty
            return
        poczekalnia = self.get_poczekalnia_path()
        if not poczekalnia.exists():
            return
        for item in poczekalnia.iterdir():
            if not item.is_file():
                continue
            if not item.name.endswith(".json"):
                continue
            self.saved_drafts_locations.append(str(item))

    def get_folder_tree_root_uuid(self) -> str | None:
        """Return the UUID of the designated Drzewo root person, or None if not set."""
        return self.settings.get_folder_tree_root_uuid()

    def set_folder_tree_root_uuid(self, value: str | None) -> None:
        """Persist the Drzewo root person UUID to settings.json."""
        self.settings.set_folder_tree_root_uuid(value)
        if self._settings_file_path is not None:
            self._dump_json_data(self._settings_file_path, self.settings.to_dict())

    def is_root_location_set(self) -> bool:
        return self._get_root_selected_flag()

    def read_me_file(self, path: str) -> Dict[str, Any]:
        """Read and parse a me.json file.

        Args:
            path (str): Path to the me.json file

        Returns:
            Dict[str, Any]: Parsed JSON data from the me.json file

        Raises:
            FileNotFoundError: If the file does not exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        return self._read_json_data(path)

    def write_me_file(self, path: str, content: PersonDataWrapper) -> None:
        """Write data to a me.json file.

        Args:
            path (str): Path to the me.json file
            content (Dict[str, Any]): Dictionary containing person data to write

        Raises:
            IOError: If the file cannot be written
        """
        self._dump_json_data(path, content.to_dict())

    def move_files(self, from_location: str, to_location: str) -> None:
        """Move all contents from one folder to another.

        Iterates through all items in the source folder and moves them to the
        destination folder. Both source and destination must exist and be directories.

        Args:
            from_location (str): Path to source folder
            to_location (str): Path to destination folder

        Raises:
            FileNotFoundError: If either path does not exist
            NotADirectoryError: If either path is not a directory
            shutil.Error: If move operation fails
        """
        from_path = Path(from_location)
        if not from_path.exists():
            raise FileNotFoundError(f"Given path: <{from_path}> does not exist.")

        if not from_path.is_dir():
            raise NotADirectoryError(f"Given path: <{from_path}> is not a folder.")

        to_path = Path(to_location)
        if not to_path.exists():
            raise FileNotFoundError(f"Given path: <{to_path}> does not exist.")

        if not to_path.is_dir():
            raise NotADirectoryError(f"Given path: <{to_path}> is not a folder.")

        for item in from_path.iterdir():
            shutil.move(str(item), str(to_path / item.name))

    def _ensure_all_person_folders_created(self, path: Union[str, Path]) -> None:
        """Create all required relationship subfolders for a person.

        Creates four subfolders:
        - Dzieci (Children)
        - Rodzice (Parents)
        - Małżonkowie (Spouses)
        - Rodzeństwo (Siblings)

        Args:
            path (Union[str, Path]): Path to the person's folder
        """
        target_path = Path(path)
        (target_path / "Dzieci").mkdir(exist_ok=True)
        (target_path / "Rodzice").mkdir(exist_ok=True)
        (target_path / "Małżonkowie").mkdir(exist_ok=True)
        (target_path / "Rodzeństwo").mkdir(exist_ok=True)

    def _set_root_folder(self, path: Path) -> None:
        """Set the root folder path in settings.

        Args:
            path (Path): Root folder path
        """
        self.settings.set_root_folder_path(str(path))

    def _set_root_selected_flag(self, root_set: bool) -> None:
        """Set the flag indicating whether root folder has been selected.

        Args:
            root_set (bool): True if root folder is selected, False otherwise
        """
        self.settings.set_select_root_folder(root_set)

    def _get_root_folder(self) -> str:
        """Get the root folder path from settings.

        Returns:
            str: Root folder path
        """
        return self.settings.get_root_folder_path()

    def _get_root_selected_flag(self) -> bool:
        """Check if root folder has been selected.

        Returns:
            bool: True if root folder is selected, False otherwise
        """

        # The flag in settings keep info whether root path should be selected (True) or not (False)
        # so answer to question 'Is root path set?' should return reverse (should set -> False; therefore is set -> True)
        return not self.settings.get_select_root_folder()

    def _dump_json_data(self, path: Union[str, Path], data: Dict[str, Any]) -> None:
        """Write JSON data to a file with proper formatting.

        Uses 4-space indentation and UTF-8 encoding to support Polish characters.

        Args:
            path (Union[str, Path]): Path to the JSON file
            data (Dict[str, Any]): Data to write
        """
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def _read_json_data(self, path: str) -> Dict[str, Any]:
        """Read and parse JSON data from a file.

        Args:
            path (str): Path to the JSON file

        Returns:
            Dict[str, Any]: Parsed JSON data
        """
        with open(path, 'r', encoding='utf-8-sig') as file:
            data = json.load(file)

        return data

    def _append_person_to_list_of_people(self, person_path: str, person_id: str, person_name: str) -> None:
        """Add a person to the cached list of people.

        Args:
            person_path (Union[str, Path]): Path to the person's folder
            person_id (str): UUID of the person,
            person_name (str): Full person name
        """
        if self.settings.get_cached_people() is None:
            self.settings.set_cached_people({})

        cache = self.settings.get_cached_people()

        new_cached_person: Dict[str, str] = {
            PersonDataProperty.LOCATION.value: str(person_path), # Is also a folder path
            PersonDataProperty.UNIQUE_IDENTIFIER.value: person_id,
            PersonDataProperty.PERSON_NAME.value: person_name, # Is also a folder name
        }
        cache[person_id] = new_cached_person
        self.settings.set_cached_people(cache)

    def _get_list_of_people(self) -> Dict[str, Dict[str, str]]:
        """Get the cached list of people.

        Returns:
            List[Dict[str, str]]: List of people, each with 'path' and 'unique_identifier'
        """
        if self.settings.get_cached_people() is None:
            self.settings.set_cached_people({})

        return self.settings.get_cached_people()

    def rename_person_folder(self, old_path: str, new_name: str) -> str:
        """Rename a person's folder, applying duplicate-numbering if needed.

        Updates the person's entry in the cache to reflect the new path and name.

        Args:
            old_path: Current absolute path of the person's folder.
            new_name: Desired new canonical folder name (without any (2) suffix).

        Returns:
            str: Absolute path of the renamed folder.
        """
        old = Path(old_path)
        unique_name = self._get_unique_folder_name(new_name)
        new_path = old.parent / unique_name
        old.rename(new_path)

        cached = self.settings.get_cached_people()
        for uid, person in cached.items():
            if person.get(PersonDataProperty.LOCATION.value) == old_path:
                person[PersonDataProperty.LOCATION.value] = str(new_path)
                person[PersonDataProperty.PERSON_NAME.value] = unique_name
                break
        self.settings.set_cached_people(cached)
        return str(new_path)

    def update_path_references(self, old_path: str, new_path: str) -> None:
        """Replace old_path with new_path in all other people's me.json relationship arrays.

        Scans every cached person's me.json and rewrites it if any relationship
        path array contained old_path.

        Args:
            old_path: The folder path that was renamed (now invalid).
            new_path: The new folder path to substitute in.
        """
        path_fields = [
            PersonDataProperty.SPOUSES.value,
            PersonDataProperty.CHILDREN.value,
            PersonDataProperty.PARENTS.value,
            PersonDataProperty.SIBLINGS.value,
        ]
        cached = self.settings.get_cached_people()
        for uid, person in cached.items():
            location = person.get(PersonDataProperty.LOCATION.value, '')
            if not location or location == new_path:
                continue
            me_json_path = Path(location) / "me.json"
            if not me_json_path.exists():
                continue
            data = self.read_me_file(str(me_json_path))
            changed = False
            for key in path_fields:
                if key in data and isinstance(data[key], list):
                    for i, p in enumerate(data[key]):
                        if p == old_path:
                            data[key][i] = new_path
                            changed = True
            if changed:
                self.write_me_file(str(me_json_path), PersonDataWrapper(data))
            