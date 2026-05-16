"""End-to-end integration test for TreeService.rebuild_lineage().

Drives rebuild_lineage() against a synthetic 7-person tree:
  - Root (Tomasz)
  - Root's father (Adam Mankin)          -> surname "Mankin"
  - Root's mother (Anna née Pastryk)     -> surname "Pastryk"
  - Root's spouse (Maria)
  - Spouse's father (Piotr Kowalski)     -> surname "Kowalski"
  - Spouse's mother (Ewa née Nowak)      -> surname "Nowak"
  - (7th person is the spouse object itself; 6 people total in the family tree plus the root)

ShortcutHelper.create_shortcut is stubbed by the global conftest (no-op that
touches the file), so the integration conftest's autouse fixture restores the
real helper. However, since we are asserting file EXISTENCE (not .lnk content),
the stub is fine here too. The test is in tests/integration/ per the plan, so
the integration conftest fixture runs, but the stub-touching approach is still
valid because create_shortcut(target, path) -> Path(path).touch() creates the
file we assert on.

Asserts:
  - Exactly 4 .lnk files exist in <root>/Rody/
  - The filenames are "Kowalski.lnk", "Mankin.lnk", "Nowak.lnk", "Pastryk.lnk"
  - rebuild-log.txt exists (even if no anomalies)
  - rebuild_lineage() returns (4, [])  (4 written, empty log)
"""

import json
import tempfile
import uuid
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_person(
    root: Path,
    uid: str,
    name: str,
    *,
    last_name: str = "",
    maiden_name: str = "",
    has_maiden_name: bool = False,
    sex: str = "Mezczyzna",
    parents=None,
    parents_id=None,
    spouse=None,
    spouse_id=None,
) -> Path:
    """Write a minimal me.json into Lista osob/<name>/. Return folder path."""
    folder = root / "Lista osób" / name
    folder.mkdir(parents=True, exist_ok=True)
    parts = name.split()
    computed_last = last_name or (parts[-1] if len(parts) > 1 else name)
    data = {
        "unique_identifier": uid,
        "person_name": name,
        "location": str(folder),
        "first_name": parts[0],
        "other_first_names": "",
        "last_name": computed_last,
        "other_last_names": "",
        "maiden_name": maiden_name,
        "other_maiden_names": "",
        "has_maiden_name": has_maiden_name,
        "sex": sex,
        "spouse": [str(p) for p in (spouse or [])],
        "spouse_id": [str(i) for i in (spouse_id or [])],
        "children": [],
        "children_id": [],
        "parents": [str(p) for p in (parents or [])],
        "parents_id": [str(i) for i in (parents_id or [])],
        "siblings": [],
        "siblings_id": [],
        "notes": "",
        "dates_of_birth": "",
        "dates_of_death": "",
    }
    (folder / "me.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    return folder


def _add_to_cache(fs, uid: str, name: str, folder: Path) -> None:
    from src.wrappers.person_data_wrapper import PersonDataProperty
    cached = fs.settings.get_cached_people()
    cached[uid] = {
        PersonDataProperty.UNIQUE_IDENTIFIER.value: uid,
        PersonDataProperty.LOCATION.value: str(folder),
        PersonDataProperty.PERSON_NAME.value: name,
    }
    fs.settings.set_cached_people(cached)


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

class TestLineageE2ERebuild:

    def test_rebuild_lineage_creates_four_lnk_files_with_correct_names(
        self, tmp_path, monkeypatch
    ):
        """Full rebuild_lineage() call creates one .lnk per surname in Rody/."""
        import tempfile as _tempfile
        from src.services.tree_service import TreeService
        from src.wrappers.settings_wrapper import SettingsDataProperty

        app_tmp = tmp_path / "apptmp"
        app_tmp.mkdir()
        monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

        # Isolate LOCALAPPDATA so set_root_folder() writes the bootstrap
        # pointer to a scratch dir, not real %LOCALAPPDATA%.
        appdata = tmp_path / "appdata"
        appdata.mkdir()
        monkeypatch.setenv("LOCALAPPDATA", str(appdata))

        ts = TreeService()
        tree_root = tmp_path / "tree"
        tree_root.mkdir()
        ts.set_root_location(str(tree_root))
        fs = ts._file_service

        # Build the 6-person synthetic family
        father_uid = str(uuid.uuid4())
        mother_uid = str(uuid.uuid4())
        sp_father_uid = str(uuid.uuid4())
        sp_mother_uid = str(uuid.uuid4())
        spouse_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        father_folder = _write_person(tree_root, father_uid, "Adam Mankin",
                                      last_name="Mankin")
        mother_folder = _write_person(tree_root, mother_uid, "Anna Mankin",
                                      last_name="Mankin",
                                      maiden_name="Pastryk",
                                      has_maiden_name=True,
                                      sex="Kobieta")
        sp_father_folder = _write_person(tree_root, sp_father_uid, "Piotr Kowalski",
                                         last_name="Kowalski")
        sp_mother_folder = _write_person(tree_root, sp_mother_uid, "Ewa Kowalska",
                                         last_name="Kowalska",
                                         maiden_name="Nowak",
                                         has_maiden_name=True,
                                         sex="Kobieta")
        spouse_folder = _write_person(tree_root, spouse_uid, "Maria Kowalska",
                                      last_name="Kowalska",
                                      sex="Kobieta",
                                      parents=[str(sp_father_folder), str(sp_mother_folder)],
                                      parents_id=[sp_father_uid, sp_mother_uid])
        root_folder = _write_person(tree_root, root_uid, "Tomasz Mankin",
                                    last_name="Mankin",
                                    parents=[str(father_folder), str(mother_folder)],
                                    parents_id=[father_uid, mother_uid],
                                    spouse=[str(spouse_folder)],
                                    spouse_id=[spouse_uid])

        for u, n, f in [
            (father_uid, "Adam Mankin", father_folder),
            (mother_uid, "Anna Mankin", mother_folder),
            (sp_father_uid, "Piotr Kowalski", sp_father_folder),
            (sp_mother_uid, "Ewa Kowalska", sp_mother_folder),
            (spouse_uid, "Maria Kowalska", spouse_folder),
            (root_uid, "Tomasz Mankin", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        # Set the Drzewo root (shared with Rody)
        ts.set_folder_tree_root_person(root_uid)

        # Execute rebuild_lineage
        written, log = ts.rebuild_lineage()

        # Assertions
        lineage_path = tree_root / "Rody"
        assert lineage_path.is_dir(), "Rody/ folder must exist"

        lnk_files = sorted(p.name for p in lineage_path.iterdir() if p.suffix == ".lnk")
        assert lnk_files == ["Kowalski.lnk", "Mankin.lnk", "Nowak.lnk", "Pastryk.lnk"], (
            f"Expected exactly 4 .lnk files with correct names, got: {lnk_files}"
        )

        assert written == 4, f"Expected 4 shortcuts written, got {written}"
        assert log == [], f"Expected empty build log, got: {log}"

        # build-log.txt must exist
        assert (lineage_path / "build-log.txt").exists()

    def test_rebuild_lineage_wipes_stale_shortcuts_on_rebuild(
        self, tmp_path, monkeypatch
    ):
        """A second rebuild_lineage() call removes stale .lnk files from previous run."""
        import tempfile as _tempfile
        from src.services.tree_service import TreeService

        app_tmp = tmp_path / "apptmp2"
        app_tmp.mkdir()
        monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

        # Isolate LOCALAPPDATA so pointer writes go to a scratch dir.
        appdata2 = tmp_path / "appdata2"
        appdata2.mkdir()
        monkeypatch.setenv("LOCALAPPDATA", str(appdata2))

        ts = TreeService()
        tree_root = tmp_path / "tree2"
        tree_root.mkdir()
        ts.set_root_location(str(tree_root))
        fs = ts._file_service

        father_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        father_folder = _write_person(tree_root, father_uid, "Adam Wiśniewski",
                                      last_name="Wiśniewski")
        root_folder = _write_person(tree_root, root_uid, "Jan Wiśniewski",
                                    last_name="Wiśniewski",
                                    parents=[str(father_folder)],
                                    parents_id=[father_uid])

        _add_to_cache(fs, father_uid, "Adam Wiśniewski", father_folder)
        _add_to_cache(fs, root_uid, "Jan Wiśniewski", root_folder)

        ts.set_folder_tree_root_person(root_uid)

        # First rebuild
        ts.rebuild_lineage()

        # Plant a stale file in Rody/
        stale = tree_root / "Rody" / "Stary.lnk"
        stale.touch()

        # Second rebuild — stale file should be gone
        ts.rebuild_lineage()

        lineage_path = tree_root / "Rody"
        lnk_files = [p.name for p in lineage_path.iterdir() if p.suffix == ".lnk"]
        assert "Stary.lnk" not in lnk_files, "Stale .lnk must be wiped on rebuild"
        assert "Wiśniewski.lnk" in lnk_files
