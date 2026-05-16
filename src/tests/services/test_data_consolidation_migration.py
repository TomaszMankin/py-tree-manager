"""Tests for the pointer-driven bootstrap and one-shot migration from %TEMP%.

Tests the pointer-driven bootstrap, one-shot migration from %TEMP%, fresh-install
path, and failure modes.

TDD order (riskiest first):
  T1-T3: migration happy-path + cached_people preservation + idempotency
  T4-T5: pointer authority + stale pointer
  T6:    fresh install
  T7-T8: set_root_folder writes pointer + orphan policy
  T9:    failure mode (corrupt JSON)
  T10:   degraded mode (%LOCALAPPDATA% unset)
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.services.file_service import (
    FileService,
    _bootstrap_pointer_path,
    _read_bootstrap_pointer,
    _write_bootstrap_pointer,
    _migrate_from_legacy_temp,
)
from src.wrappers.settings_wrapper import SettingsDataProperty


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_legacy_settings(path: Path, root_folder_path: str, cached_people: dict | None = None) -> None:
    """Write a legacy %TEMP%/PyTreeManager/settings.json at the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        SettingsDataProperty.ROOT_FOLDER_PATH.value: root_folder_path,
        SettingsDataProperty.SELECT_ROOT_FOLDER.value: False,
        SettingsDataProperty.FONT_SIZE.value: 20,
        SettingsDataProperty.CACHED_PEOPLE.value: cached_people or {},
        "drzewo_root_uuid": "4a91101e-0155-4452-bc35-07519707e706",
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _make_10_cached_people() -> dict:
    """Return a dict of 10 fake cached_people entries."""
    import uuid
    people = {}
    for i in range(10):
        uid = str(uuid.uuid4())
        people[uid] = {
            "unique_identifier": uid,
            "location": f"C:\\FakeTree\\Lista osob\\Person{i:02d}",
            "person_name": f"Osoba{i:02d} Testowa",
        }
    return people


def _isolated_fs(tmp_path, monkeypatch) -> tuple[Path, Path, Path]:
    """Set up isolated env vars and return (tree_root, legacy_dir, appdata_dir).

    Monkeypatches:
      - tempfile.gettempdir -> tmp_path/apptmp
      - LOCALAPPDATA env var -> tmp_path/appdata
    """
    import tempfile as _tempfile

    app_tmp = tmp_path / "apptmp"
    app_tmp.mkdir(exist_ok=True)
    monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

    appdata = tmp_path / "appdata"
    appdata.mkdir(exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))

    tree_root = tmp_path / "tree"
    tree_root.mkdir(exist_ok=True)

    return tree_root, app_tmp, appdata


# ---------------------------------------------------------------------------
# T1 — Migration runs when pointer absent and legacy settings present
# ---------------------------------------------------------------------------

class TestMigrationHappyPath:
    def test_migration_runs_when_pointer_absent_and_legacy_settings_present(
        self, tmp_path, monkeypatch
    ):
        """T1: When pointer absent and legacy %TEMP% settings exist, migration runs.

        Post FileService():
        - <tmp_root>/.PyTreeManager/settings.json exists
        - pointer file contains tmp_root
        - legacy %TEMP% dir is gone or empty
        - settings dict survived (root_folder_path intact)
        """
        tree_root, app_tmp, appdata = _isolated_fs(tmp_path, monkeypatch)

        # Write legacy settings at %TEMP%/PyTreeManager/settings.json
        legacy_settings = app_tmp / "PyTreeManager" / "settings.json"
        _make_legacy_settings(legacy_settings, str(tree_root))

        # No pointer exists yet
        pointer_path = appdata / "PyTreeManager" / "last_root.txt"
        assert not pointer_path.exists()

        fs = FileService()

        # New settings file exists
        new_settings = tree_root / ".PyTreeManager" / "settings.json"
        assert new_settings.exists(), f"New settings missing at {new_settings}"

        # Pointer was written
        assert pointer_path.exists(), f"Pointer not written at {pointer_path}"
        pointer_content = pointer_path.read_text(encoding="utf-8").strip()
        assert pointer_content == str(tree_root), (
            f"Pointer content mismatch: expected {tree_root}, got {pointer_content}"
        )

        # Legacy dir is gone or empty
        legacy_dir = app_tmp / "PyTreeManager"
        if legacy_dir.exists():
            remaining = list(legacy_dir.iterdir())
            assert "settings.json" not in [f.name for f in remaining], (
                "Legacy settings.json should have been moved"
            )

        # Settings dict survived — root_folder_path intact
        with open(new_settings, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        assert data.get(SettingsDataProperty.ROOT_FOLDER_PATH.value) == str(tree_root)

        # FileService reports root as set
        assert fs.is_root_location_set() is True


# ---------------------------------------------------------------------------
# T2 — Migration preserves cached_people
# ---------------------------------------------------------------------------

class TestMigrationPreservesCachedPeople:
    def test_migration_preserves_cached_people(self, tmp_path, monkeypatch):
        """T2: 10 cached_people entries survive migration with identical keys."""
        tree_root, app_tmp, appdata = _isolated_fs(tmp_path, monkeypatch)

        original_people = _make_10_cached_people()
        legacy_settings = app_tmp / "PyTreeManager" / "settings.json"
        _make_legacy_settings(legacy_settings, str(tree_root), cached_people=original_people)

        fs = FileService()

        new_settings = tree_root / ".PyTreeManager" / "settings.json"
        assert new_settings.exists()

        with open(new_settings, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)

        migrated_people = data.get(SettingsDataProperty.CACHED_PEOPLE.value, {})
        assert len(migrated_people) == 10, (
            f"Expected 10 cached_people, got {len(migrated_people)}"
        )
        for uid in original_people:
            assert uid in migrated_people, f"UID {uid} missing from migrated settings"
            assert migrated_people[uid]["location"] == original_people[uid]["location"]


# ---------------------------------------------------------------------------
# T3 — Migration idempotent on second call
# ---------------------------------------------------------------------------

class TestMigrationIdempotent:
    def test_migration_idempotent_on_second_call(self, tmp_path, monkeypatch):
        """T3: Running FileService() a second time after migration is a no-op.

        The legacy %TEMP% dir must NOT be recreated; settings are loaded cleanly.
        """
        tree_root, app_tmp, appdata = _isolated_fs(tmp_path, monkeypatch)

        legacy_settings = app_tmp / "PyTreeManager" / "settings.json"
        _make_legacy_settings(legacy_settings, str(tree_root))

        # First run — migration happens
        fs1 = FileService()
        assert fs1.is_root_location_set() is True

        # Legacy dir should be gone
        legacy_dir = app_tmp / "PyTreeManager"
        legacy_gone = not legacy_dir.exists() or "settings.json" not in [
            f.name for f in legacy_dir.iterdir()
        ]
        assert legacy_gone, "Legacy settings.json should not exist after migration"

        # Second run — no migration; no exception; same final state
        fs2 = FileService()
        assert fs2.is_root_location_set() is True

        # Legacy settings.json was NOT recreated
        if legacy_dir.exists():
            remaining = list(legacy_dir.iterdir())
            assert "settings.json" not in [f.name for f in remaining], (
                "Legacy settings.json was recreated — idempotency broken"
            )


# ---------------------------------------------------------------------------
# T4 — Pointer authoritative when present
# ---------------------------------------------------------------------------

class TestPointerAuthority:
    def test_pointer_authoritative_when_present(self, tmp_path, monkeypatch):
        """T4: When pointer exists, it wins — legacy is ignored, not migrated."""
        tree_root, app_tmp, appdata = _isolated_fs(tmp_path, monkeypatch)

        # Set up new-layout settings at tree_root
        (tree_root / ".PyTreeManager").mkdir(exist_ok=True)
        new_settings = tree_root / ".PyTreeManager" / "settings.json"
        canonical_people = _make_10_cached_people()
        _make_legacy_settings(new_settings, str(tree_root), cached_people=canonical_people)

        # Write pointer
        pointer_path = appdata / "PyTreeManager" / "last_root.txt"
        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        pointer_path.write_text(str(tree_root), encoding="utf-8")

        # Also write legacy settings with DIFFERENT root and data
        fake_root = tmp_path / "fake_root"
        fake_root.mkdir()
        legacy_settings = app_tmp / "PyTreeManager" / "settings.json"
        _make_legacy_settings(legacy_settings, str(fake_root), cached_people={})

        fs = FileService()

        # Must have loaded from pointer's location (canonical_people), not legacy
        loaded = fs.settings.get_cached_people()
        assert len(loaded) == 10, (
            f"Expected 10 people from pointer-location settings, got {len(loaded)}"
        )

        # Legacy must NOT have been moved or deleted (pointer was authoritative; migration skipped)
        assert legacy_settings.exists(), "Legacy settings should remain when pointer is present"

        # Root folder path from pointer's settings
        assert fs._get_root_folder() == str(tree_root)


# ---------------------------------------------------------------------------
# T5 — Stale pointer falls through to fresh install
# ---------------------------------------------------------------------------

class TestStalePointer:
    def test_stale_pointer_falls_through_to_fresh_install(self, tmp_path, monkeypatch):
        """T5: Pointer pointing at a non-existent path -> treat as fresh install.

        is_root_location_set() returns False. No crash.
        """
        tree_root, app_tmp, appdata = _isolated_fs(tmp_path, monkeypatch)

        # Write pointer to a non-existent path
        pointer_path = appdata / "PyTreeManager" / "last_root.txt"
        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        pointer_path.write_text(r"C:\does\not\exist\anywhere\xyz", encoding="utf-8")

        fs = FileService()

        assert fs.is_root_location_set() is False, (
            "Stale pointer should result in fresh-install (root not set)"
        )


# ---------------------------------------------------------------------------
# T6 — Fresh install: no pointer, no legacy
# ---------------------------------------------------------------------------

class TestFreshInstall:
    def test_fresh_install_no_pointer_no_legacy(self, tmp_path, monkeypatch):
        """T6: No pointer, no legacy -> fresh install; no settings file created yet."""
        tree_root, app_tmp, appdata = _isolated_fs(tmp_path, monkeypatch)

        # Confirm nothing exists
        pointer_path = appdata / "PyTreeManager" / "last_root.txt"
        assert not pointer_path.exists()
        legacy_settings = app_tmp / "PyTreeManager" / "settings.json"
        assert not legacy_settings.exists()

        fs = FileService()

        # Root not set
        assert fs.is_root_location_set() is False

        # No settings file on disk yet (deferred to set_root_folder)
        assert fs._settings_file_path is None, (
            "_settings_file_path should be None until set_root_folder() is called"
        )


# ---------------------------------------------------------------------------
# T7 — set_root_folder writes pointer and relocates settings
# ---------------------------------------------------------------------------

class TestSetRootFolderPointerAndSettings:
    def test_set_root_folder_writes_pointer_and_relocates_settings(
        self, tmp_path, monkeypatch
    ):
        """T7: After set_root_folder():
        - pointer file contains tree_root
        - <tree_root>/.PyTreeManager/settings.json exists
        - <tree_root>/.PyTreeManager/logs/ dir exists
        """
        tree_root, app_tmp, appdata = _isolated_fs(tmp_path, monkeypatch)

        fs = FileService()
        fs.set_root_folder(str(tree_root))

        pointer_path = appdata / "PyTreeManager" / "last_root.txt"
        assert pointer_path.exists(), "Pointer not written by set_root_folder"
        assert pointer_path.read_text(encoding="utf-8").strip() == str(tree_root)

        new_settings = tree_root / ".PyTreeManager" / "settings.json"
        assert new_settings.exists(), f"settings.json missing at {new_settings}"

        logs_dir = tree_root / ".PyTreeManager" / "logs"
        assert logs_dir.exists() and logs_dir.is_dir(), (
            f".PyTreeManager/logs/ missing at {logs_dir}"
        )


# ---------------------------------------------------------------------------
# T8 — set_root_folder called twice rewrites pointer; orphan policy
# ---------------------------------------------------------------------------

class TestSetRootFolderOrphanPolicy:
    def test_set_root_folder_called_twice_rewrites_pointer(self, tmp_path, monkeypatch):
        """T8: Changing root: pointer updated; old .PyTreeManager left in place."""
        tree_root, app_tmp, appdata = _isolated_fs(tmp_path, monkeypatch)

        root_a = tmp_path / "rootA"
        root_a.mkdir()
        root_b = tmp_path / "rootB"
        root_b.mkdir()

        fs = FileService()
        fs.set_root_folder(str(root_a))
        fs.set_root_folder(str(root_b))

        pointer_path = appdata / "PyTreeManager" / "last_root.txt"
        assert pointer_path.read_text(encoding="utf-8").strip() == str(root_b), (
            "Pointer should point to rootB after second set_root_folder"
        )

        # rootA/.PyTreeManager left in place (orphan policy §3.5)
        assert (root_a / ".PyTreeManager").exists(), (
            "rootA/.PyTreeManager should remain (orphan policy)"
        )

        # rootB/.PyTreeManager/settings.json exists
        assert (root_b / ".PyTreeManager" / "settings.json").exists(), (
            "rootB/.PyTreeManager/settings.json must exist"
        )


# ---------------------------------------------------------------------------
# T9 — Migration failure falls through cleanly
# ---------------------------------------------------------------------------

class TestMigrationFailure:
    def test_migration_failure_falls_through_cleanly(self, tmp_path, monkeypatch):
        """T9: Corrupt legacy JSON -> no crash; no migration; is_root_location_set() False."""
        tree_root, app_tmp, appdata = _isolated_fs(tmp_path, monkeypatch)

        # Write corrupt JSON
        legacy_dir = app_tmp / "PyTreeManager"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_settings = legacy_dir / "settings.json"
        legacy_settings.write_text("{ this is not valid JSON !!! }", encoding="utf-8")

        # No pointer
        pointer_path = appdata / "PyTreeManager" / "last_root.txt"
        assert not pointer_path.exists()

        # Must not raise
        fs = FileService()

        assert fs.is_root_location_set() is False, (
            "After corrupt-legacy, should fall through to fresh install"
        )

        # Legacy file still in place (not deleted on failed migration)
        assert legacy_settings.exists(), (
            "Corrupt legacy should remain in place for forensic recovery"
        )


# ---------------------------------------------------------------------------
# T10 — Degraded mode: %LOCALAPPDATA% unset
# ---------------------------------------------------------------------------

class TestDegradedMode:
    def test_localappdata_unset_falls_back_to_tempdir(self, tmp_path, monkeypatch):
        """T10: When LOCALAPPDATA is unset, pointer path falls back to tempdir.

        _bootstrap_pointer_path() must return a path under tempfile.gettempdir()
        instead of %LOCALAPPDATA%.
        """
        import tempfile as _tempfile

        app_tmp = tmp_path / "apptmp"
        app_tmp.mkdir(exist_ok=True)
        monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

        # Remove LOCALAPPDATA from env
        monkeypatch.delenv("LOCALAPPDATA", raising=False)

        # _bootstrap_pointer_path should fall back to tempdir
        pointer_path = _bootstrap_pointer_path()
        expected_base = Path(app_tmp)
        assert str(pointer_path).startswith(str(expected_base)), (
            f"Expected pointer under {app_tmp}, got {pointer_path}"
        )
        assert "PyTreeManager" in str(pointer_path)
        assert "last_root.txt" in pointer_path.name

        # FileService should construct without crashing
        fs = FileService()
        assert fs.is_root_location_set() is False  # fresh install in degraded mode


# ---------------------------------------------------------------------------
# Helper function unit tests
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    """Direct unit tests for the four module-level helpers."""

    def test_bootstrap_pointer_path_uses_localappdata(self, tmp_path, monkeypatch):
        appdata = tmp_path / "appdata"
        appdata.mkdir()
        monkeypatch.setenv("LOCALAPPDATA", str(appdata))

        result = _bootstrap_pointer_path()
        assert result == appdata / "PyTreeManager" / "last_root.txt"

    def test_bootstrap_pointer_path_falls_back_when_localappdata_unset(
        self, tmp_path, monkeypatch
    ):
        import tempfile as _tempfile
        app_tmp = tmp_path / "apptmp"
        app_tmp.mkdir()
        monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))
        monkeypatch.delenv("LOCALAPPDATA", raising=False)

        result = _bootstrap_pointer_path()
        assert result == app_tmp / "PyTreeManager" / "last_root.txt"

    def test_read_bootstrap_pointer_returns_none_when_absent(self, tmp_path):
        p = tmp_path / "nonexistent.txt"
        assert _read_bootstrap_pointer(p) is None

    def test_read_bootstrap_pointer_returns_none_when_path_does_not_exist_on_disk(
        self, tmp_path
    ):
        p = tmp_path / "pointer.txt"
        p.write_text(r"C:\does\not\exist\anywhere", encoding="utf-8")
        assert _read_bootstrap_pointer(p) is None

    def test_read_bootstrap_pointer_returns_path_when_valid(self, tmp_path):
        target = tmp_path / "target"
        target.mkdir()
        p = tmp_path / "pointer.txt"
        p.write_text(str(target), encoding="utf-8")
        result = _read_bootstrap_pointer(p)
        assert result == target

    def test_write_bootstrap_pointer_creates_file_and_parent(self, tmp_path):
        pointer_path = tmp_path / "subdir" / "PyTreeManager" / "last_root.txt"
        root = tmp_path / "myroot"
        _write_bootstrap_pointer(pointer_path, root)
        assert pointer_path.exists()
        assert pointer_path.read_text(encoding="utf-8") == str(root)

    def test_write_bootstrap_pointer_idempotent_overwrite(self, tmp_path):
        pointer_path = tmp_path / "pointer.txt"
        root_a = tmp_path / "rootA"
        root_b = tmp_path / "rootB"
        _write_bootstrap_pointer(pointer_path, root_a)
        _write_bootstrap_pointer(pointer_path, root_b)
        assert pointer_path.read_text(encoding="utf-8") == str(root_b)

    def test_migrate_from_legacy_temp_moves_file(self, tmp_path, monkeypatch):
        """Happy-path migration: file moves, pointer written, root returned."""
        tree_root = tmp_path / "tree"
        tree_root.mkdir()

        legacy_dir = tmp_path / "legacy_pytreemanager"
        legacy_dir.mkdir()
        legacy_settings = legacy_dir / "settings.json"
        _make_legacy_settings(legacy_settings, str(tree_root))

        pointer_path = tmp_path / "pointer.txt"

        result = _migrate_from_legacy_temp(legacy_settings, pointer_path)

        assert result == tree_root, f"Expected {tree_root}, got {result}"
        assert (tree_root / ".PyTreeManager" / "settings.json").exists()
        assert pointer_path.exists()
        assert not legacy_settings.exists(), "Legacy should have been moved"

    def test_migrate_from_legacy_temp_returns_none_on_corrupt_json(self, tmp_path):
        """Migration of corrupt JSON returns None, does not crash."""
        tree_root = tmp_path / "tree"
        tree_root.mkdir()
        legacy = tmp_path / "settings.json"
        legacy.write_text("{ NOT VALID JSON", encoding="utf-8")
        pointer_path = tmp_path / "pointer.txt"

        result = _migrate_from_legacy_temp(legacy, pointer_path)
        assert result is None

    def test_migrate_from_legacy_temp_returns_none_when_root_missing(self, tmp_path):
        """Migration returns None when root_folder_path in legacy doesn't exist on disk."""
        legacy = tmp_path / "settings.json"
        _make_legacy_settings(legacy, r"C:\does\not\exist\anywhere\xyz")
        pointer_path = tmp_path / "pointer.txt"

        result = _migrate_from_legacy_temp(legacy, pointer_path)
        assert result is None
