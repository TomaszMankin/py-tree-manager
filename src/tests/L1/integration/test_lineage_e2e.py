"""End-to-end integration tests for TreeService.rebuild_lineage().

rebuild_lineage calls FolderTreeService.compute_membership to get
List[FolderTreeMember], feeds them into LineageService.compute_lineages,
and writes .lnk files named via render_folder_tree_filename.  The generation /
couple / gender token in a lineage .lnk filename MUST MATCH the token in the
corresponding Drzewo .lnk filename for the same person (generation-parity).

Test cases:
  1  Generation-parity e2e: for a multi-generation tree, each person's lineage
     .lnk encoded prefix matches that person's Drzewo .lnk encoded prefix
  2  Couple-letter parity (H-B): the only member of a surname folder keeps
     their Drzewo couple letter (not reindexed to A)
  3  Stale subfolder wipe: second rebuild removes old subfolders
  4  Member count: .lnk count in surname folder matches members assigned by
     FolderTreeService
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import List, Optional

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


def _setup_tree_service(tmp_path, monkeypatch):
    """Bootstrap TreeService with a fresh root, return (ts, tree_root, fs)."""
    import tempfile as _tempfile
    from src.services.tree_service import TreeService

    app_tmp = tmp_path / "apptmp"
    app_tmp.mkdir(exist_ok=True)
    monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

    appdata = tmp_path / "appdata"
    appdata.mkdir(exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))

    ts = TreeService()
    tree_root = tmp_path / "tree"
    tree_root.mkdir(exist_ok=True)
    ts.set_root_location(str(tree_root))
    return ts, tree_root, ts._file_service


# ---------------------------------------------------------------------------
# Test 1 — Generation-parity e2e (H-A)
# ---------------------------------------------------------------------------

class TestLineageE2EGenerationParity:
    """H-A: same person's encoded .lnk prefix matches in Drzewo and lineage."""

    def test_ancestor_encoded_prefix_matches_in_drzewo_and_lineage(
        self, tmp_path, monkeypatch
    ):
        """For the grandfather (gen=+1), his encoded prefix in Drzewo == in his surname lineage.

        Tree:
          root (Mankin) -- parents: [grandfather_mankin, grandmother_mankin]
          grandfather_mankin: last_name=Mankin, gen=+1 in Drzewo
          grandmother_mankin: last_name=Inna (different), gen=+1 in Drzewo

        Both Drzewo and the Mankin lineage folder use render_folder_tree_filename.
        grandfather_mankin's .lnk prefix in Drzewo/ must match his .lnk name
        in Rody/Mankin/.
        """
        ts, tree_root, fs = _setup_tree_service(tmp_path, monkeypatch)

        root_uid = str(uuid.uuid4())
        gf_uid = str(uuid.uuid4())
        gm_uid = str(uuid.uuid4())

        gf_folder = _write_person(tree_root, gf_uid, "Stefan Mankin",
                                  last_name="Mankin", sex="Mezczyzna")
        gm_folder = _write_person(tree_root, gm_uid, "Helena Inna",
                                  last_name="Inna", sex="Kobieta",
                                  spouse_id=[gf_uid])
        root_folder = _write_person(tree_root, root_uid, "Jan Mankin",
                                    last_name="Mankin", sex="Mezczyzna",
                                    parents_id=[gf_uid, gm_uid],
                                    parents=[str(gf_folder), str(gm_folder)])

        for u, n, f in [(root_uid, "Jan Mankin", root_folder),
                        (gf_uid, "Stefan Mankin", gf_folder),
                        (gm_uid, "Helena Inna", gm_folder)]:
            _add_to_cache(fs, u, n, f)

        ts.set_folder_tree_root_person(root_uid)

        # Build Drzewo — this sets the Drzewo .lnk names on disk
        ts.rebuild_folder_tree()

        # Now build lineage
        ts.rebuild_lineage()

        drzewo_root = tree_root / "Drzewo"
        lineage_root = tree_root / "Rody"

        # Find grandfather's Drzewo .lnk
        drzewo_lnks = [p.name for p in drzewo_root.iterdir()
                       if p.suffix == ".lnk" and "Stefan Mankin" in p.name]
        assert len(drzewo_lnks) >= 1, (
            f"Stefan Mankin .lnk not found in Drzewo/: {list(drzewo_root.iterdir())}"
        )
        drzewo_gf_name = drzewo_lnks[0]

        # Find grandfather's lineage .lnk in Rody/Mankin/
        mankin_sub = lineage_root / "Mankin"
        assert mankin_sub.is_dir(), f"Rody/Mankin/ not found: {list(lineage_root.iterdir())}"
        lineage_lnks = [p.name for p in mankin_sub.iterdir()
                        if p.suffix == ".lnk" and "Stefan Mankin" in p.name]
        assert len(lineage_lnks) >= 1, (
            f"Stefan Mankin .lnk not found in Rody/Mankin/: {list(mankin_sub.iterdir())}"
        )
        lineage_gf_name = lineage_lnks[0]

        # H-A: the encoded prefix must be identical
        assert drzewo_gf_name == lineage_gf_name, (
            f"Generation-parity FAIL: Drzewo='{drzewo_gf_name}' vs "
            f"Lineage='{lineage_gf_name}' — same person must have same encoded prefix"
        )


# ---------------------------------------------------------------------------
# Test 2 — H-B: couple-letter global (couple-B member keeps B)
# ---------------------------------------------------------------------------

class TestLineageE2ECoupleBParity:
    """H-B: couple letter is Drzewo-global — no reindexing per surname folder."""

    def test_couple_b_ancestor_keeps_b_in_lineage_folder(
        self, tmp_path, monkeypatch
    ):
        """Grandfather at Drzewo couple B keeps [B] in his lineage .lnk name.

        Tree:
          root (Mankin) -- parents: [gf_mankin(M), gm_mankin(F)]
          root also has spouse whose parents are the A couple
          The B couple (gf_mankin) appears in Mankin/
          The B letter must be in gf_mankin's lineage .lnk name.

        Setup so that Drzewo assigns couple B to gf_mankin:
          root's ancestor DFS: spouse's parents registered first (couple A),
          then root's own parents (couple B) — achieved by spouse pushed first.

        Wait — Drzewo pushes spouses FIRST so root pops FIRST, meaning root's
        parents = couple A. Spouse's parents = couple B.

        So to get couple B in Mankin/:
          - root has last_name=Mankin
          - gf_mankin is root's SPOUSE'S father (couple B in Drzewo)
          - gf_mankin has last_name=Mankin
          - Mankin lineage folder contains gf_mankin who is couple B
          - No couple A for Mankin in Drzewo (root's own parents have different surnames)
        """
        ts, tree_root, fs = _setup_tree_service(tmp_path, monkeypatch)

        root_uid = str(uuid.uuid4())
        spouse_uid = str(uuid.uuid4())
        root_father_uid = str(uuid.uuid4())    # root's father — different surname (couple A)
        spouse_father_uid = str(uuid.uuid4())  # spouse's father — Mankin (couple B)
        spouse_mother_uid = str(uuid.uuid4())  # spouse's mother — different surname

        # root's father: different surname -> couple A (will NOT appear in Mankin/)
        rf_folder = _write_person(tree_root, root_father_uid, "Jan Kowalski",
                                  last_name="Kowalski", sex="Mezczyzna")
        # spouse's father: Mankin -> couple B (WILL appear in Mankin/)
        sf_folder = _write_person(tree_root, spouse_father_uid, "Adam Mankin",
                                  last_name="Mankin", sex="Mezczyzna")
        # spouse's mother: different surname
        sm_folder = _write_person(tree_root, spouse_mother_uid, "Helena Inna",
                                  last_name="Inna", sex="Kobieta",
                                  spouse_id=[spouse_father_uid])
        # spouse
        spouse_folder = _write_person(tree_root, spouse_uid, "Maria Kowalska",
                                      last_name="Kowalska", sex="Kobieta",
                                      parents_id=[spouse_father_uid, spouse_mother_uid],
                                      parents=[str(sf_folder), str(sm_folder)])
        # root: Mankin last_name; parents: only root_father (Kowalski = couple A)
        root_folder = _write_person(tree_root, root_uid, "Tomasz Mankin",
                                    last_name="Mankin", sex="Mezczyzna",
                                    parents_id=[root_father_uid],
                                    parents=[str(rf_folder)],
                                    spouse_id=[spouse_uid],
                                    spouse=[str(spouse_folder)])

        for u, n, f in [
            (root_uid, "Tomasz Mankin", root_folder),
            (spouse_uid, "Maria Kowalska", spouse_folder),
            (root_father_uid, "Jan Kowalski", rf_folder),
            (spouse_father_uid, "Adam Mankin", sf_folder),
            (spouse_mother_uid, "Helena Inna", sm_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        ts.set_folder_tree_root_person(root_uid)
        ts.rebuild_folder_tree()
        ts.rebuild_lineage()

        drzewo_root = tree_root / "Drzewo"
        lineage_root = tree_root / "Rody"
        mankin_sub = lineage_root / "Mankin"

        assert mankin_sub.is_dir(), (
            f"Rody/Mankin/ not found: {list(lineage_root.iterdir())}"
        )

        # Find Adam Mankin's Drzewo .lnk name
        drzewo_adam_lnks = [p.name for p in drzewo_root.iterdir()
                            if p.suffix == ".lnk" and "Adam Mankin" in p.name]
        assert len(drzewo_adam_lnks) >= 1, (
            f"Adam Mankin .lnk not found in Drzewo/: {list(drzewo_root.iterdir())}"
        )
        drzewo_adam_name = drzewo_adam_lnks[0]

        # Find Adam Mankin's lineage .lnk name in Rody/Mankin/
        lineage_adam_lnks = [p.name for p in mankin_sub.iterdir()
                             if p.suffix == ".lnk" and "Adam Mankin" in p.name]
        assert len(lineage_adam_lnks) >= 1, (
            f"Adam Mankin .lnk not found in Rody/Mankin/: {list(mankin_sub.iterdir())}"
        )
        lineage_adam_name = lineage_adam_lnks[0]

        # H-A + H-B: names must be identical (global couple letter preserved)
        assert drzewo_adam_name == lineage_adam_name, (
            f"H-B FAIL: Drzewo='{drzewo_adam_name}' vs "
            f"Lineage='{lineage_adam_name}' — couple letter must be global"
        )

        # Confirm the couple letter in Adam Mankin's Drzewo name is B (couple_index=1)
        # Drzewo: root pops first (LIFO; root pushed last), so root's parents = couple A.
        # Spouse pushed first, so spouse's parents = couple B.
        # Adam Mankin is spouse's father -> should be [B] in Drzewo.
        assert "[B]" in drzewo_adam_name, (
            f"Adam Mankin should be couple B in Drzewo, got '{drzewo_adam_name}'"
        )
        assert "[B]" in lineage_adam_name, (
            f"Adam Mankin should be couple B in Rody/Mankin/, got '{lineage_adam_name}'"
        )


# ---------------------------------------------------------------------------
# Test 3 — Stale subfolder wipe: second rebuild removes old subfolders
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

        # Wiśniewski/ must contain encoded .lnk files (not bare names)
        wisnicki_sub = lineage_root / "Wiśniewski"
        lnk_names = [p.name for p in wisnicki_sub.iterdir() if p.suffix == ".lnk"]
        assert len(lnk_names) >= 1, f"No .lnk files in Wiśniewski/: {lnk_names}"

        # All .lnk files should have the encoded prefix format [NN][...]
        for lnk_name in lnk_names:
            assert lnk_name.startswith("["), (
                f"Expected encoded .lnk name starting with '[', got '{lnk_name}'"
            )


# ---------------------------------------------------------------------------
# Test 4 — Member count: .lnk count matches FolderTreeService output
# ---------------------------------------------------------------------------

class TestLineageE2EMemberCount:

    def test_lnk_count_in_surname_folder_matches_drzewo_membership(
        self, tmp_path, monkeypatch
    ):
        """The number of .lnk files in a surname folder equals the number of
        FolderTreeMember objects with that surname.

        Tree: root(Mankin) + father(Mankin) + grandfather(Mankin, chain-breaks above)
        All three have surname Mankin -> Mankin/ should have exactly 3 .lnk files.
        """
        ts, tree_root, fs = _setup_tree_service(tmp_path, monkeypatch)

        gf_uid = str(uuid.uuid4())
        father_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        gf_folder = _write_person(tree_root, gf_uid, "Andrzej Mankin",
                                  last_name="Mankin", sex="Mezczyzna")
        father_folder = _write_person(tree_root, father_uid, "Adam Mankin",
                                      last_name="Mankin", sex="Mezczyzna",
                                      parents_id=[gf_uid],
                                      parents=[str(gf_folder)])
        root_folder = _write_person(tree_root, root_uid, "Jan Mankin",
                                    last_name="Mankin", sex="Mezczyzna",
                                    parents_id=[father_uid],
                                    parents=[str(father_folder)])

        for u, n, f in [
            (root_uid, "Jan Mankin", root_folder),
            (father_uid, "Adam Mankin", father_folder),
            (gf_uid, "Andrzej Mankin", gf_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        ts.set_folder_tree_root_person(root_uid)
        ts.rebuild_lineage()

        lineage_root = tree_root / "Rody"
        mankin_sub = lineage_root / "Mankin"
        assert mankin_sub.is_dir(), f"Rody/Mankin/ not found"

        lnk_names = [p.name for p in mankin_sub.iterdir() if p.suffix == ".lnk"]
        assert len(lnk_names) == 3, (
            f"Expected 3 .lnk files (root + father + grandfather), got {len(lnk_names)}: "
            f"{lnk_names}"
        )
