"""End-to-end integration tests for TreeService.rebuild_lineage().

All tests drive rebuild_lineage() against synthetic trees. ShortcutHelper
is stubbed (creates empty files) via the conftest autouse patch, so no COM
calls happen here. Tests assert on-disk folder/file structure.

Test cases:
  1  9-person tree: two subfolders, correct .lnk counts, chain-break verified
  2  Stale file wipe: second rebuild removes old subfolders
"""

import json
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
    children=None,
    children_id=None,
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
        "children": [str(p) for p in (children or [])],
        "children_id": [str(i) for i in (children_id or [])],
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
# Test 1 — 9-person tree, two subfolders, chain-break at great-grandfather
# ---------------------------------------------------------------------------

class TestLineageE2ENinePersonTree:

    def test_nine_person_tree_two_subfolders_correct_member_counts(
        self, tmp_path, monkeypatch
    ):
        """9-person tree: father-surname/ has 8 .lnk, mother-maiden/ has 4 .lnk;
        great-grandfather excluded (surname differs); both subfolders have build-log.txt.

        Tree layout (placeholders):
          root (parents=[father, mother], spouse=[spouse], children=[child])
          spouse (parents=[])
          child (spouse=[child_spouse])
          child_spouse
          father (last_name=<fsurname>, parents=[gf_paternal])
          mother (has_maiden=True, maiden_name=<mmaid>, parents=[])
          gf_paternal (last_name=<fsurname>, parents=[ggf_paternal])
          gm_paternal (last_name=<unrelated>, spouse=[gf_paternal])  <- spouse-leaf
          ggf_paternal (last_name=<other> != <fsurname>)             <- chain breaks here

        father-surname/ expected members:
          universal (root, spouse, child, child_spouse) = 4
          R3: father + mother (father's spouse) = 2
          R4: gf_paternal (matches) + gm_paternal (gf's spouse-leaf) = 2
          ggf_paternal: surname differs -> excluded
          Total = 8 .lnk

        mother-maiden/ expected members:
          universal (root, spouse, child, child_spouse) = 4
          R3: mother + father (mother's spouse) = 2 (dedup: father already in universal? no)
          mother has no parents in fixture -> R4 adds nothing
          Total = 6 .lnk

        Note: father is not in universal (he is not root's descendant). mother is not
        in universal either. So both R3 entries are net-new.
        """
        import tempfile as _tempfile
        from src.services.tree_service import TreeService

        app_tmp = tmp_path / "apptmp"
        app_tmp.mkdir()
        monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

        appdata = tmp_path / "appdata"
        appdata.mkdir()
        monkeypatch.setenv("LOCALAPPDATA", str(appdata))

        ts = TreeService()
        tree_root = tmp_path / "tree"
        tree_root.mkdir()
        ts.set_root_location(str(tree_root))
        fs = ts._file_service

        # UIDs
        root_uid = str(uuid.uuid4())
        spouse_uid = str(uuid.uuid4())
        child_uid = str(uuid.uuid4())
        child_spouse_uid = str(uuid.uuid4())
        father_uid = str(uuid.uuid4())
        mother_uid = str(uuid.uuid4())
        gf_paternal_uid = str(uuid.uuid4())
        gm_paternal_uid = str(uuid.uuid4())
        ggf_paternal_uid = str(uuid.uuid4())

        father_surname = "Mankin"
        mother_maiden = "Pastryk"

        # Leaf nodes first (no unresolved parents_id references)
        ggf_folder = _write_person(tree_root, ggf_paternal_uid, "Karol Inny",
                                   last_name="Inny")
        gm_folder = _write_person(tree_root, gm_paternal_uid, "Helena Inna",
                                  last_name="Inna", sex="Kobieta")
        gf_folder = _write_person(tree_root, gf_paternal_uid, "Stefan Mankin",
                                  last_name=father_surname,
                                  spouse=[str(gm_folder)],
                                  spouse_id=[gm_paternal_uid],
                                  parents=[str(ggf_folder)],
                                  parents_id=[ggf_paternal_uid])
        father_folder = _write_person(tree_root, father_uid, "Adam Mankin",
                                      last_name=father_surname,
                                      parents=[str(gf_folder)],
                                      parents_id=[gf_paternal_uid])
        mother_folder = _write_person(tree_root, mother_uid, "Anna Mankin",
                                      last_name=father_surname,
                                      maiden_name=mother_maiden,
                                      has_maiden_name=True,
                                      sex="Kobieta",
                                      spouse=[str(father_folder)],
                                      spouse_id=[father_uid])
        # Wire father's spouse back to mother
        # (re-write father's me.json with spouse link)
        father_folder = _write_person(tree_root, father_uid, "Adam Mankin",
                                      last_name=father_surname,
                                      parents=[str(gf_folder)],
                                      parents_id=[gf_paternal_uid],
                                      spouse=[str(mother_folder)],
                                      spouse_id=[mother_uid])
        child_spouse_folder = _write_person(tree_root, child_spouse_uid,
                                            "Marta Kowalska",
                                            last_name="Kowalska", sex="Kobieta")
        child_folder = _write_person(tree_root, child_uid, "Piotr Mankin",
                                     last_name=father_surname,
                                     spouse=[str(child_spouse_folder)],
                                     spouse_id=[child_spouse_uid])
        spouse_folder = _write_person(tree_root, spouse_uid, "Maria Mankin",
                                      last_name=father_surname, sex="Kobieta")
        root_folder = _write_person(tree_root, root_uid, "Tomasz Mankin",
                                    last_name=father_surname,
                                    parents=[str(father_folder), str(mother_folder)],
                                    parents_id=[father_uid, mother_uid],
                                    spouse=[str(spouse_folder)],
                                    spouse_id=[spouse_uid],
                                    children=[str(child_folder)],
                                    children_id=[child_uid])

        for u, n, f in [
            (root_uid, "Tomasz Mankin", root_folder),
            (spouse_uid, "Maria Mankin", spouse_folder),
            (child_uid, "Piotr Mankin", child_folder),
            (child_spouse_uid, "Marta Kowalska", child_spouse_folder),
            (father_uid, "Adam Mankin", father_folder),
            (mother_uid, "Anna Mankin", mother_folder),
            (gf_paternal_uid, "Stefan Mankin", gf_folder),
            (gm_paternal_uid, "Helena Inna", gm_folder),
            (ggf_paternal_uid, "Karol Inny", ggf_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        ts.set_folder_tree_root_person(root_uid)
        written, log = ts.rebuild_lineage()

        lineage_root = tree_root / "Rody"
        assert lineage_root.is_dir()

        # Exactly two subfolders (father_surname and mother_maiden)
        subfolders = [p for p in lineage_root.iterdir() if p.is_dir()]
        subfolder_names = sorted(p.name for p in subfolders)
        assert subfolder_names == sorted([father_surname, mother_maiden]), (
            f"Expected subfolders {[father_surname, mother_maiden]}, got {subfolder_names}"
        )

        # father-surname/ — 8 members:
        # universal(4) + R3(2: father+mother) + R4(2: gf_paternal + gm_paternal)
        father_sub = lineage_root / father_surname
        father_lnks = [p for p in father_sub.iterdir() if p.suffix == ".lnk"]
        assert len(father_lnks) == 8, (
            f"father-surname/ expected 8 .lnk files, got {len(father_lnks)}: "
            f"{[p.name for p in father_lnks]}"
        )

        # ggf_paternal must NOT be in father_sub (chain breaks at him)
        ggf_lnk_name = "Karol Inny.lnk"
        assert not (father_sub / ggf_lnk_name).exists(), (
            "ggf_paternal should be excluded (surname differs)"
        )

        # mother-maiden/ — 6 members: universal(4) + R3(2: mother+father)
        mother_sub = lineage_root / mother_maiden
        mother_lnks = [p for p in mother_sub.iterdir() if p.suffix == ".lnk"]
        assert len(mother_lnks) == 6, (
            f"mother-maiden/ expected 6 .lnk files, got {len(mother_lnks)}: "
            f"{[p.name for p in mother_lnks]}"
        )

        # build-log.txt at both levels (H-Sprint-D)
        assert (lineage_root / "build-log.txt").exists()
        assert (father_sub / "build-log.txt").exists()
        assert (mother_sub / "build-log.txt").exists()

        # total_written == 8 + 6 = 14
        assert written == 14, f"Expected 14 total shortcuts written, got {written}"


# ---------------------------------------------------------------------------
# Test 2 — Stale subfolder wipe: second rebuild removes old subfolders
# ---------------------------------------------------------------------------

class TestLineageE2EWipeOnRebuild:

    def test_second_rebuild_removes_stale_subfolder(
        self, tmp_path, monkeypatch
    ):
        """A second rebuild_lineage() call removes stale subfolders from first run."""
        import tempfile as _tempfile
        from src.services.tree_service import TreeService

        app_tmp = tmp_path / "apptmp2"
        app_tmp.mkdir()
        monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

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

        # First rebuild — creates Wiśniewski/ subfolder
        ts.rebuild_lineage()

        lineage_root = tree_root / "Rody"
        assert (lineage_root / "Wiśniewski").is_dir(), (
            "Wiśniewski/ subfolder must exist after first rebuild"
        )

        # Plant a stale subfolder with content
        stale_dir = lineage_root / "Stary"
        stale_dir.mkdir()
        (stale_dir / "stale.lnk").touch()

        # Second rebuild — stale subfolder must be gone
        ts.rebuild_lineage()

        subfolders = [p.name for p in lineage_root.iterdir() if p.is_dir()]
        assert "Stary" not in subfolders, "Stale subfolder must be wiped on rebuild"
        assert "Wiśniewski" in subfolders, "Wiśniewski/ must exist after second rebuild"

        # Wiśniewski/ must contain Jan and Adam .lnk files
        wisnicki_sub = lineage_root / "Wiśniewski"
        lnk_names = [p.name for p in wisnicki_sub.iterdir() if p.suffix == ".lnk"]
        assert "Jan Wiśniewski.lnk" in lnk_names, (
            f"Root person .lnk missing: {lnk_names}"
        )
        assert "Adam Wiśniewski.lnk" in lnk_names, (
            f"Father person .lnk missing: {lnk_names}"
        )
