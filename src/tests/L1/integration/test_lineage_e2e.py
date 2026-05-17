"""End-to-end integration tests for TreeService.rebuild_lineage().

All tests drive rebuild_lineage() against synthetic trees. ShortcutHelper
is stubbed (creates empty files) via the conftest autouse patch, so no COM
calls happen here. Tests assert on-disk folder/file structure.

Test cases:
  1  13-person tree: two subfolders, correct .lnk counts, chain-break verified
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
# Test 1 — 13-person tree, two subfolders, chain-break at great-grandfather
#           (maternal side enriched per ADR-016 §1.2 worked example)
# ---------------------------------------------------------------------------

class TestLineageE2ENinePersonTree:

    def test_nine_person_tree_two_subfolders_correct_member_counts(
        self, tmp_path, monkeypatch
    ):
        """13-person tree: father-surname/ has 8 .lnk, mother-maiden/ has 8 .lnk.

        Tree layout (placeholders, per ADR-016 §1.2):
          root (parents=[father, mother], spouse=[spouse], children=[child])
          spouse (parents=[])
          child (spouse=[child_spouse])
          child_spouse
          father (last_name=<fsurname>, parents=[gf_paternal, gm_paternal])
          mother (has_maiden=True, maiden_name=<mmaid>, parents=[gf_maternal, gm_maternal])
          gf_paternal (last_name=<fsurname>, parents=[ggf_paternal])
          gm_paternal (last_name=<unrelated>, has_maiden=True, maiden_name=<unrelated-maiden>)
          ggf_paternal (last_name=<other> != <fsurname>)             <- paternal chain breaks
          gf_maternal  (last_name=<unrelated-gfm>)                   <- no maiden match
          gm_maternal  (last_name=<unrelated-gmm>, has_maiden=True, maiden_name=<mmaid>)
          gggf_maternal (last_name=<unrelated-2>, maiden_name=<mmaid>, has_maiden=False)
                                                                      <- maternal chain breaks

        father-surname/ expected members (ADR-016 §1.2 trace):
          universal (root, spouse, child, child_spouse) = 4
          R3: father + mother (father's spouse) = 2
          R4: gf_paternal (matches fsurname) -> add gm_paternal as spouse-leaf; walk parents
              ggf_paternal: surname differs -> stop
          R4 yields: gf_paternal + gm_paternal = 2
          Total = 8 .lnk

        mother-maiden/ expected members (ADR-016 §1.2 trace):
          universal (root, spouse, child, child_spouse) = 4
          R3: mother + father (mother's spouse) = 2
          R4 walk from mother's parents:
            gf_maternal: lineage surname = <unrelated-gfm> (no maiden). No match. Stop.
            gm_maternal: lineage surname = <mmaid> (has_maiden=True). Match. Include.
              Add spouse-leaf gf_maternal. Walk gm_maternal's parents:
              gggf_maternal: has_maiden=False -> uses last_name=<unrelated-2>. No match. Stop.
          R4 yields: gm_maternal + gf_maternal (as spouse-leaf) = 2
          Total = 8 .lnk
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
        gf_maternal_uid = str(uuid.uuid4())
        gm_maternal_uid = str(uuid.uuid4())
        gggf_maternal_uid = str(uuid.uuid4())

        father_surname = "Mankin"
        mother_maiden = "Pastryk"

        # --- Paternal side ---
        ggf_folder = _write_person(tree_root, ggf_paternal_uid, "Karol Inny",
                                   last_name="Inny")
        gm_paternal_folder = _write_person(tree_root, gm_paternal_uid, "Helena Inna",
                                           last_name="Inna",
                                           maiden_name="InnaP",
                                           has_maiden_name=True,
                                           sex="Kobieta")
        gf_paternal_folder = _write_person(tree_root, gf_paternal_uid, "Stefan Mankin",
                                           last_name=father_surname,
                                           spouse_id=[gm_paternal_uid],
                                           parents_id=[ggf_paternal_uid])

        # --- Maternal side ---
        # gggf_maternal: has_maiden=False but maiden_name set — gate dominates, uses last_name
        gggf_maternal_folder = _write_person(
            tree_root, gggf_maternal_uid, "Waclaw Obcy",
            last_name="Obcy",
            maiden_name=mother_maiden,  # field set, but has_maiden=False -> last_name used
            has_maiden_name=False,
        )
        # gm_maternal: has_maiden=True, maiden_name matches mother_maiden -> included in walk
        gm_maternal_folder = _write_person(
            tree_root, gm_maternal_uid, "Zofia Inna",
            last_name="Inna",
            maiden_name=mother_maiden,
            has_maiden_name=True,
            sex="Kobieta",
            spouse_id=[gf_maternal_uid],
            parents_id=[gggf_maternal_uid],
        )
        # gf_maternal: last_name unrelated, no maiden -> no match; included as spouse-leaf only
        gf_maternal_folder = _write_person(
            tree_root, gf_maternal_uid, "Henryk Obcy",
            last_name="Obcy",
            spouse_id=[gm_maternal_uid],
        )

        # --- mother: has parents gf_maternal + gm_maternal ---
        mother_folder = _write_person(tree_root, mother_uid, "Anna Mankin",
                                      last_name=father_surname,
                                      maiden_name=mother_maiden,
                                      has_maiden_name=True,
                                      sex="Kobieta",
                                      spouse_id=[father_uid],
                                      parents_id=[gf_maternal_uid, gm_maternal_uid])

        # --- father: parents gf_paternal + gm_paternal; spouse = mother ---
        father_folder = _write_person(tree_root, father_uid, "Adam Mankin",
                                      last_name=father_surname,
                                      spouse_id=[mother_uid],
                                      parents_id=[gf_paternal_uid, gm_paternal_uid])

        child_spouse_folder = _write_person(tree_root, child_spouse_uid,
                                            "Marta Kowalska",
                                            last_name="Kowalska", sex="Kobieta")
        child_folder = _write_person(tree_root, child_uid, "Piotr Mankin",
                                     last_name=father_surname,
                                     spouse_id=[child_spouse_uid])
        spouse_folder = _write_person(tree_root, spouse_uid, "Maria Mankin",
                                      last_name=father_surname, sex="Kobieta")
        root_folder = _write_person(tree_root, root_uid, "Tomasz Mankin",
                                    last_name=father_surname,
                                    parents_id=[father_uid, mother_uid],
                                    spouse_id=[spouse_uid],
                                    children_id=[child_uid])

        for u, n, f in [
            (root_uid, "Tomasz Mankin", root_folder),
            (spouse_uid, "Maria Mankin", spouse_folder),
            (child_uid, "Piotr Mankin", child_folder),
            (child_spouse_uid, "Marta Kowalska", child_spouse_folder),
            (father_uid, "Adam Mankin", father_folder),
            (mother_uid, "Anna Mankin", mother_folder),
            (gf_paternal_uid, "Stefan Mankin", gf_paternal_folder),
            (gm_paternal_uid, "Helena Inna", gm_paternal_folder),
            (ggf_paternal_uid, "Karol Inny", ggf_folder),
            (gf_maternal_uid, "Henryk Obcy", gf_maternal_folder),
            (gm_maternal_uid, "Zofia Inna", gm_maternal_folder),
            (gggf_maternal_uid, "Waclaw Obcy", gggf_maternal_folder),
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

        # father-surname/ — 8 .lnk:
        # universal(4) + R3(2: father+mother) + R4(2: gf_paternal + gm_paternal spouse-leaf)
        # ggf_paternal excluded (surname differs)
        father_sub = lineage_root / father_surname
        father_lnks = [p for p in father_sub.iterdir() if p.suffix == ".lnk"]
        assert len(father_lnks) == 8, (
            f"father-surname/ expected 8 .lnk files, got {len(father_lnks)}: "
            f"{[p.name for p in father_lnks]}"
        )

        # ggf_paternal must NOT be in father_sub (chain breaks at him)
        assert not (father_sub / "Karol Inny.lnk").exists(), (
            "ggf_paternal should be excluded (surname differs)"
        )

        # mother-maiden/ — 8 .lnk:
        # universal(4) + R3(2: mother+father) + R4(2: gm_maternal + gf_maternal spouse-leaf)
        # gggf_maternal excluded (has_maiden=False, last_name unrelated)
        mother_sub = lineage_root / mother_maiden
        mother_lnks = [p for p in mother_sub.iterdir() if p.suffix == ".lnk"]
        assert len(mother_lnks) == 8, (
            f"mother-maiden/ expected 8 .lnk files, got {len(mother_lnks)}: "
            f"{[p.name for p in mother_lnks]}"
        )

        # gggf_maternal must NOT be in mother_sub (has_maiden=False -> last_name, no match)
        assert not (mother_sub / "Waclaw Obcy.lnk").exists(), (
            "gggf_maternal should be excluded (has_maiden=False gate)"
        )

        # build-log.txt at both levels
        assert (lineage_root / "build-log.txt").exists()
        assert (father_sub / "build-log.txt").exists()
        assert (mother_sub / "build-log.txt").exists()

        # total_written == 8 + 8 = 16
        assert written == 16, f"Expected 16 total shortcuts written, got {written}"


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
