"""L0 unit tests for services/lineage_service.py.

Test cases:
  1  Empty root (no parents, no spouses) -> empty dict
  2  Single-spouse, four-grandparents -> 4 lineage folders with correct contributors
  3  Mother carries maiden name -> maiden_name used (not last_name)
  4  Father has no recorded last_name -> contributes nothing; log entry; build succeeds
  5  Surname collision -> one folder, points to first contributor; log entry
  6  Multiple spouses -> collisions handled per first-contributor rule
  7  Diacritics preserved (Lukasiewicz round-trip)
  8  Universal members in one-parent case
  9  Universal members in zero-children case
 10  Ancestor walk happy path (3-gen matching)
 11  Ancestor walk termination on surname mismatch
 12  Ancestor spouse-leaf rule
 13  No spouse, no children — universal = {root}
 14  Surname collision across contributors (two contributors share a surname)
 15  Empty maiden case for mother (has_maiden=True, maiden_name="(nieznane)")
 16  All 4 contributors distinct — universal appears in all 4 folders
 17  Three-generation descendants recursion (root -> child -> grandchild)

All tests are L0: pure logic, no COM / disk side-effects for shortcut creation.
Uses tmp_root fixture + _write_person / _add_to_cache helpers.
"""

import json
import uuid
from pathlib import Path
from typing import List, Optional

import pytest

from src.wrappers.person_data_wrapper import PersonDataProperty, PersonDataWrapper


# ---------------------------------------------------------------------------
# Helpers (mirror existing test_folder_tree_service.py)
# ---------------------------------------------------------------------------

def _write_person(
    root: Path,
    uid: str,
    name: str,
    last_name: str = "",
    maiden_name: str = "",
    has_maiden_name: bool = False,
    sex: str = "Mezczyzna",
    parents: Optional[List[str]] = None,
    parents_id: Optional[List[str]] = None,
    spouse: Optional[List[str]] = None,
    spouse_id: Optional[List[str]] = None,
    children: Optional[List[str]] = None,
    children_id: Optional[List[str]] = None,
) -> Path:
    """Create a person folder under Lista osob and write me.json. Return folder path."""
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
    """Register a person in FileService's settings cache."""
    cached = fs.settings.get_cached_people()
    cached[uid] = {
        PersonDataProperty.UNIQUE_IDENTIFIER.value: uid,
        PersonDataProperty.LOCATION.value: str(folder),
        PersonDataProperty.PERSON_NAME.value: name,
    }
    fs.settings.set_cached_people(cached)


# ---------------------------------------------------------------------------
# Test 1 — empty root (no parents, no spouses)
# ---------------------------------------------------------------------------

class TestLineageEmptyRoot:

    def test_empty_root_returns_empty_dict(self, tmp_root):
        """Root with no parents and no spouses yields an empty lineages dict."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root
        root_uid = str(uuid.uuid4())
        folder = _write_person(root_path, root_uid, "Jan Kowalski",
                               last_name="Kowalski")
        _add_to_cache(fs, root_uid, "Jan Kowalski", folder)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert lineages == {}
        assert not any("ERROR" in entry for entry in log)


# ---------------------------------------------------------------------------
# Test 2 — single spouse, four grandparents -> 4 lineage folders
# ---------------------------------------------------------------------------

class TestLineageFourGrandparents:

    def test_single_spouse_four_grandparents_yields_four_lineages(self, tmp_root):
        """Typical case: root has 2 parents, spouse has 2 parents -> 4 distinct lineages."""
        from src.services.lineage_service import LineageService, LineageMembers

        root_path, fs = tmp_root

        father_uid = str(uuid.uuid4())
        mother_uid = str(uuid.uuid4())
        sp_father_uid = str(uuid.uuid4())
        sp_mother_uid = str(uuid.uuid4())
        spouse_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        father_folder = _write_person(root_path, father_uid, "Adam Mankin",
                                      last_name="Mankin", sex="Mezczyzna")
        mother_folder = _write_person(root_path, mother_uid, "Anna Mankin",
                                      last_name="Mankin",
                                      maiden_name="Pastryk",
                                      has_maiden_name=True,
                                      sex="Kobieta")
        sp_father_folder = _write_person(root_path, sp_father_uid, "Piotr Kowalski",
                                         last_name="Kowalski", sex="Mezczyzna")
        sp_mother_folder = _write_person(root_path, sp_mother_uid, "Ewa Kowalska",
                                         last_name="Kowalska",
                                         maiden_name="Nowak",
                                         has_maiden_name=True,
                                         sex="Kobieta")
        spouse_folder = _write_person(root_path, spouse_uid, "Maria Kowalska",
                                      last_name="Kowalska",
                                      sex="Kobieta",
                                      parents=[str(sp_father_folder), str(sp_mother_folder)],
                                      parents_id=[sp_father_uid, sp_mother_uid])
        root_folder = _write_person(root_path, root_uid, "Tomasz Mankin",
                                    last_name="Mankin",
                                    sex="Mezczyzna",
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

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert len(lineages) == 4
        assert "Mankin" in lineages       # father's last_name
        assert "Pastryk" in lineages      # mother's maiden_name
        assert "Kowalski" in lineages     # spouse's father's last_name
        assert "Nowak" in lineages        # spouse's mother's maiden_name
        # Each value is a LineageMembers instance
        assert isinstance(lineages["Mankin"], LineageMembers)

    def test_lineage_contributor_uid_points_to_first_contributor(self, tmp_root):
        """Each lineage's contributor_uid is the UID of the first contributor."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        father_uid = str(uuid.uuid4())
        mother_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        father_folder = _write_person(root_path, father_uid, "Adam Mankin",
                                      last_name="Mankin")
        mother_folder = _write_person(root_path, mother_uid, "Zofia Rutowska",
                                      last_name="Rutowska",
                                      maiden_name="Rutowska",
                                      has_maiden_name=True,
                                      sex="Kobieta")
        root_folder = _write_person(root_path, root_uid, "Jan Mankin",
                                    last_name="Mankin",
                                    parents=[str(father_folder), str(mother_folder)],
                                    parents_id=[father_uid, mother_uid])

        _add_to_cache(fs, father_uid, "Adam Mankin", father_folder)
        _add_to_cache(fs, mother_uid, "Zofia Rutowska", mother_folder)
        _add_to_cache(fs, root_uid, "Jan Mankin", root_folder)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert lineages["Mankin"].contributor_uid == father_uid
        assert lineages["Rutowska"].contributor_uid == mother_uid


# ---------------------------------------------------------------------------
# Test 3 — mother carries maiden name
# ---------------------------------------------------------------------------

class TestLineageMaidenNamePrecedence:

    def test_maiden_name_used_when_has_maiden_name_true(self, tmp_root):
        """If has_maiden_name is True, maiden_name is the lineage surname, not last_name."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        mother_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        mother_folder = _write_person(root_path, mother_uid, "Jadwiga Kowalska",
                                      last_name="Kowalska",
                                      maiden_name="Nowak",
                                      has_maiden_name=True,
                                      sex="Kobieta")
        root_folder = _write_person(root_path, root_uid, "Jan Kowalski",
                                    last_name="Kowalski",
                                    parents_id=[mother_uid],
                                    parents=[str(mother_folder)])

        _add_to_cache(fs, mother_uid, "Jadwiga Kowalska", mother_folder)
        _add_to_cache(fs, root_uid, "Jan Kowalski", root_folder)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Nowak" in lineages
        assert "Kowalska" not in lineages
        assert lineages["Nowak"].contributor_uid == mother_uid

    def test_unknown_sentinel_maiden_name_returns_none(self, tmp_root):
        """has_maiden_name=True but maiden_name='(nieznane)' -> extract returns None."""
        from src.services.lineage_service import extract_lineage_surname

        wrapper = PersonDataWrapper({
            "last_name": "Testowy",
            "maiden_name": "(nieznane)",
            "has_maiden_name": True,
        })
        assert extract_lineage_surname(wrapper) is None


# ---------------------------------------------------------------------------
# Test 4 — father has no recorded last_name
# ---------------------------------------------------------------------------

class TestLineageMissingLastName:

    def test_contributor_with_no_last_name_adds_nothing_and_logs(self, tmp_root):
        """A contributor with empty last_name yields no lineage entry; build succeeds."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        father_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        father_folder = _write_person(root_path, father_uid, "Adam (nieznane)",
                                      last_name="(nieznane)")
        root_folder = _write_person(root_path, root_uid, "Jan Testowy",
                                    last_name="Testowy",
                                    parents_id=[father_uid],
                                    parents=[str(father_folder)])

        _add_to_cache(fs, father_uid, "Adam (nieznane)", father_folder)
        _add_to_cache(fs, root_uid, "Jan Testowy", root_folder)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Nieznane" not in lineages
        assert "(nieznane)" not in lineages
        assert any("has no lineage surname" in entry for entry in log)

    def test_contributor_with_whitespace_only_last_name_adds_nothing(self, tmp_root):
        """A contributor with whitespace-only last_name yields no lineage entry."""
        from src.services.lineage_service import extract_lineage_surname

        wrapper = PersonDataWrapper({
            "last_name": "   ",
            "has_maiden_name": False,
        })
        assert extract_lineage_surname(wrapper) is None


# ---------------------------------------------------------------------------
# Test 5 — surname collision: first contributor wins
# ---------------------------------------------------------------------------

class TestLineageSurnameCollision:

    def test_collision_keeps_first_contributor_and_logs(self, tmp_root):
        """When root's father and spouse's father share a surname, first-contributor wins."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        root_father_uid = str(uuid.uuid4())
        spouse_father_uid = str(uuid.uuid4())
        spouse_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        root_father_folder = _write_person(root_path, root_father_uid,
                                           "Adam Kowalski", last_name="Kowalski")
        spouse_father_folder = _write_person(root_path, spouse_father_uid,
                                             "Piotr Kowalski", last_name="Kowalski")
        spouse_folder = _write_person(root_path, spouse_uid, "Maria Kowalska",
                                      last_name="Kowalska",
                                      sex="Kobieta",
                                      parents=[str(spouse_father_folder)],
                                      parents_id=[spouse_father_uid])
        root_folder = _write_person(root_path, root_uid, "Jan Kowalski",
                                    last_name="Kowalski",
                                    parents=[str(root_father_folder)],
                                    parents_id=[root_father_uid],
                                    spouse=[str(spouse_folder)],
                                    spouse_id=[spouse_uid])

        for u, n, f in [
            (root_father_uid, "Adam Kowalski", root_father_folder),
            (spouse_father_uid, "Piotr Kowalski", spouse_father_folder),
            (spouse_uid, "Maria Kowalska", spouse_folder),
            (root_uid, "Jan Kowalski", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Kowalski" in lineages
        assert lineages["Kowalski"].contributor_uid == root_father_uid

        assert any(
            "already contributed" in entry and spouse_father_uid in entry
            for entry in log
        )


# ---------------------------------------------------------------------------
# Test 6 — multiple spouses
# ---------------------------------------------------------------------------

class TestLineageMultipleSpouses:

    def test_two_spouses_contribute_up_to_four_additional_lineages(self, tmp_root):
        """Root with two spouses, each with two parents, yields up to 4 additional lineages."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        root_uid = str(uuid.uuid4())
        spouse1_uid = str(uuid.uuid4())
        spouse2_uid = str(uuid.uuid4())
        s1_father_uid = str(uuid.uuid4())
        s1_mother_uid = str(uuid.uuid4())
        s2_father_uid = str(uuid.uuid4())
        s2_mother_uid = str(uuid.uuid4())

        s1_father_folder = _write_person(root_path, s1_father_uid, "Jan Nowak",
                                         last_name="Nowak")
        s1_mother_folder = _write_person(root_path, s1_mother_uid, "Anna Nowak",
                                         last_name="Nowak",
                                         maiden_name="Wisniewski",
                                         has_maiden_name=True,
                                         sex="Kobieta")
        s2_father_folder = _write_person(root_path, s2_father_uid, "Piotr Zielinski",
                                         last_name="Zielinski")
        s2_mother_folder = _write_person(root_path, s2_mother_uid, "Maria Zielinska",
                                         last_name="Zielinska",
                                         maiden_name="Lewandowski",
                                         has_maiden_name=True,
                                         sex="Kobieta")
        spouse1_folder = _write_person(root_path, spouse1_uid, "Ewa Nowak",
                                       last_name="Nowak", sex="Kobieta",
                                       parents=[str(s1_father_folder), str(s1_mother_folder)],
                                       parents_id=[s1_father_uid, s1_mother_uid])
        spouse2_folder = _write_person(root_path, spouse2_uid, "Zofia Zielinska",
                                       last_name="Zielinska", sex="Kobieta",
                                       parents=[str(s2_father_folder), str(s2_mother_folder)],
                                       parents_id=[s2_father_uid, s2_mother_uid])
        root_folder = _write_person(root_path, root_uid, "Tomasz Kowalski",
                                    last_name="Kowalski",
                                    spouse=[str(spouse1_folder), str(spouse2_folder)],
                                    spouse_id=[spouse1_uid, spouse2_uid])

        for u, n, f in [
            (s1_father_uid, "Jan Nowak", s1_father_folder),
            (s1_mother_uid, "Anna Nowak", s1_mother_folder),
            (s2_father_uid, "Piotr Zielinski", s2_father_folder),
            (s2_mother_uid, "Maria Zielinska", s2_mother_folder),
            (spouse1_uid, "Ewa Nowak", spouse1_folder),
            (spouse2_uid, "Zofia Zielinska", spouse2_folder),
            (root_uid, "Tomasz Kowalski", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Nowak" in lineages
        assert "Wisniewski" in lineages
        assert "Zielinski" in lineages
        assert "Lewandowski" in lineages
        assert len(lineages) == 4

    def test_collision_across_two_spouses_first_wins(self, tmp_root):
        """If spouse1's father and spouse2's father share surname, spouse1's father wins."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        root_uid = str(uuid.uuid4())
        spouse1_uid = str(uuid.uuid4())
        spouse2_uid = str(uuid.uuid4())
        s1_father_uid = str(uuid.uuid4())
        s2_father_uid = str(uuid.uuid4())

        s1_father_folder = _write_person(root_path, s1_father_uid, "Jan Nowak",
                                         last_name="Nowak")
        s2_father_folder = _write_person(root_path, s2_father_uid, "Piotr Nowak",
                                         last_name="Nowak")
        spouse1_folder = _write_person(root_path, spouse1_uid, "Ewa Nowak",
                                       last_name="Nowak", sex="Kobieta",
                                       parents=[str(s1_father_folder)],
                                       parents_id=[s1_father_uid])
        spouse2_folder = _write_person(root_path, spouse2_uid, "Maria Nowak",
                                       last_name="Nowak", sex="Kobieta",
                                       parents=[str(s2_father_folder)],
                                       parents_id=[s2_father_uid])
        root_folder = _write_person(root_path, root_uid, "Tomasz Kowalski",
                                    last_name="Kowalski",
                                    spouse=[str(spouse1_folder), str(spouse2_folder)],
                                    spouse_id=[spouse1_uid, spouse2_uid])

        for u, n, f in [
            (s1_father_uid, "Jan Nowak", s1_father_folder),
            (s2_father_uid, "Piotr Nowak", s2_father_folder),
            (spouse1_uid, "Ewa Nowak", spouse1_folder),
            (spouse2_uid, "Maria Nowak", spouse2_folder),
            (root_uid, "Tomasz Kowalski", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Nowak" in lineages
        assert lineages["Nowak"].contributor_uid == s1_father_uid
        assert any("already contributed" in e and s2_father_uid in e for e in log)


# ---------------------------------------------------------------------------
# Test 7 — Polish diacritics preserved
# ---------------------------------------------------------------------------

class TestLineageDiacriticsPreserved:

    def test_diacritic_surname_round_trips_correctly(self, tmp_root):
        """Surname 'Lukasiewicz' (with Polish L) round-trips through extract_lineage_surname."""
        from src.services.lineage_service import extract_lineage_surname

        wrapper = PersonDataWrapper({
            "last_name": "Łukasiewicz",
            "has_maiden_name": False,
        })
        assert extract_lineage_surname(wrapper) == "Łukasiewicz"

    def test_diacritic_surname_appears_in_compute_lineages(self, tmp_root):
        """Diacritic surname 'Wisniewski' survives the full compute_lineages path."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        father_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        father_folder = _write_person(root_path, father_uid, "Jan Wisniewski",
                                      last_name="Wiśniewski")
        root_folder = _write_person(root_path, root_uid, "Piotr Wisniewski",
                                    last_name="Wiśniewski",
                                    parents=[str(father_folder)],
                                    parents_id=[father_uid])

        _add_to_cache(fs, father_uid, "Jan Wisniewski", father_folder)
        _add_to_cache(fs, root_uid, "Piotr Wisniewski", root_folder)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Wiśniewski" in lineages
        assert lineages["Wiśniewski"].contributor_uid == father_uid


# ---------------------------------------------------------------------------
# Test 8 — Universal members in one-parent case
# ---------------------------------------------------------------------------

class TestUniversalMembersOneParent:

    def test_root_child_and_spouses_appear_in_lineage_folder(self, tmp_root):
        """Root + spouse + child + child-spouse all appear in the father lineage folder."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        father_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())
        spouse_uid = str(uuid.uuid4())
        child_uid = str(uuid.uuid4())
        child_spouse_uid = str(uuid.uuid4())

        father_folder = _write_person(root_path, father_uid, "Adam Nowak",
                                      last_name="Nowak")
        child_spouse_folder = _write_person(root_path, child_spouse_uid, "Marta Kowalska",
                                            last_name="Kowalska", sex="Kobieta")
        child_folder = _write_person(root_path, child_uid, "Ewa Nowak",
                                     last_name="Nowak", sex="Kobieta",
                                     spouse=[str(child_spouse_folder)],
                                     spouse_id=[child_spouse_uid])
        spouse_folder = _write_person(root_path, spouse_uid, "Halina Nowak",
                                      last_name="Nowak", sex="Kobieta")
        root_folder = _write_person(root_path, root_uid, "Jan Nowak",
                                    last_name="Nowak",
                                    parents=[str(father_folder)],
                                    parents_id=[father_uid],
                                    spouse=[str(spouse_folder)],
                                    spouse_id=[spouse_uid],
                                    children=[str(child_folder)],
                                    children_id=[child_uid])

        for u, n, f in [
            (father_uid, "Adam Nowak", father_folder),
            (root_uid, "Jan Nowak", root_folder),
            (spouse_uid, "Halina Nowak", spouse_folder),
            (child_uid, "Ewa Nowak", child_folder),
            (child_spouse_uid, "Marta Kowalska", child_spouse_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Nowak" in lineages
        members = lineages["Nowak"].member_uids
        # Universal: root + spouse + child + child_spouse
        assert root_uid in members
        assert spouse_uid in members
        assert child_uid in members
        assert child_spouse_uid in members
        # Father is the contributor (R3)
        assert father_uid in members


# ---------------------------------------------------------------------------
# Test 9 — Universal members in zero-children case
# ---------------------------------------------------------------------------

class TestUniversalMembersZeroChildren:

    def test_root_and_spouse_appear_when_no_children(self, tmp_root):
        """Root + spouse appear in lineage folder even when root has no children."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        father_uid = str(uuid.uuid4())
        spouse_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        father_folder = _write_person(root_path, father_uid, "Adam Zielinski",
                                      last_name="Zielinski")
        spouse_folder = _write_person(root_path, spouse_uid, "Marta Zielinska",
                                      last_name="Zielinska", sex="Kobieta")
        root_folder = _write_person(root_path, root_uid, "Jan Zielinski",
                                    last_name="Zielinski",
                                    parents=[str(father_folder)],
                                    parents_id=[father_uid],
                                    spouse=[str(spouse_folder)],
                                    spouse_id=[spouse_uid])

        for u, n, f in [
            (father_uid, "Adam Zielinski", father_folder),
            (spouse_uid, "Marta Zielinska", spouse_folder),
            (root_uid, "Jan Zielinski", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Zielinski" in lineages
        members = lineages["Zielinski"].member_uids
        assert root_uid in members
        assert spouse_uid in members
        # No children to assert on — just root + spouse + father
        assert father_uid in members


# ---------------------------------------------------------------------------
# Test 10 — Ancestor walk happy path (3-gen matching)
# ---------------------------------------------------------------------------

class TestAncestorWalkHappyPath:

    def test_three_generations_of_matching_surname_included(self, tmp_root):
        """Father + grandfather + great-grandfather all with matching surname -> all included."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        ggf_uid = str(uuid.uuid4())      # great-grandfather
        gf_uid = str(uuid.uuid4())       # grandfather
        father_uid = str(uuid.uuid4())   # father (contributor)
        root_uid = str(uuid.uuid4())

        ggf_folder = _write_person(root_path, ggf_uid, "Andrzej Mankin",
                                   last_name="Mankin")
        gf_folder = _write_person(root_path, gf_uid, "Stanislaw Mankin",
                                  last_name="Mankin",
                                  parents=[str(ggf_folder)],
                                  parents_id=[ggf_uid])
        father_folder = _write_person(root_path, father_uid, "Adam Mankin",
                                      last_name="Mankin",
                                      parents=[str(gf_folder)],
                                      parents_id=[gf_uid])
        root_folder = _write_person(root_path, root_uid, "Jan Mankin",
                                    last_name="Mankin",
                                    parents=[str(father_folder)],
                                    parents_id=[father_uid])

        for u, n, f in [
            (ggf_uid, "Andrzej Mankin", ggf_folder),
            (gf_uid, "Stanislaw Mankin", gf_folder),
            (father_uid, "Adam Mankin", father_folder),
            (root_uid, "Jan Mankin", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Mankin" in lineages
        members = lineages["Mankin"].member_uids
        assert father_uid in members    # contributor
        assert gf_uid in members        # grandfather (matching)
        assert ggf_uid in members       # great-grandfather (matching)


# ---------------------------------------------------------------------------
# Test 11 — Ancestor walk termination on surname mismatch
# ---------------------------------------------------------------------------

class TestAncestorWalkTerminatesOnMismatch:

    def test_grandparent_with_different_surname_excluded(self, tmp_root):
        """Grandfather's surname differs -> he and his line excluded from father's lineage."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        ggf_uid = str(uuid.uuid4())      # great-grandfather (surname matches but unreachable)
        gf_uid = str(uuid.uuid4())       # grandfather (surname DIFFERS -> stops walk)
        father_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        ggf_folder = _write_person(root_path, ggf_uid, "Andrzej Mankin",
                                   last_name="Mankin")
        # Grandfather has different surname
        gf_folder = _write_person(root_path, gf_uid, "Henryk Inny",
                                  last_name="Inny",
                                  parents=[str(ggf_folder)],
                                  parents_id=[ggf_uid])
        father_folder = _write_person(root_path, father_uid, "Adam Mankin",
                                      last_name="Mankin",
                                      parents=[str(gf_folder)],
                                      parents_id=[gf_uid])
        root_folder = _write_person(root_path, root_uid, "Jan Mankin",
                                    last_name="Mankin",
                                    parents=[str(father_folder)],
                                    parents_id=[father_uid])

        for u, n, f in [
            (ggf_uid, "Andrzej Mankin", ggf_folder),
            (gf_uid, "Henryk Inny", gf_folder),
            (father_uid, "Adam Mankin", father_folder),
            (root_uid, "Jan Mankin", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Mankin" in lineages
        members = lineages["Mankin"].member_uids
        assert father_uid in members
        # Grandfather's surname differs -> excluded
        assert gf_uid not in members
        # Great-grandfather is reachable only via grandfather -> also excluded
        assert ggf_uid not in members


# ---------------------------------------------------------------------------
# Test 12 — Ancestor spouse-leaf rule
# ---------------------------------------------------------------------------

class TestAncestorSpouseLeafRule:

    def test_spouse_of_matching_ancestor_included_but_her_parents_not_walked(
        self, tmp_root
    ):
        """Grandfather matches; grandmother's surname differs. Both included. Her parents not walked."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        # Grandmother's parent (should NOT appear)
        gm_parent_uid = str(uuid.uuid4())
        gm_uid = str(uuid.uuid4())   # grandmother — surname differs
        gf_uid = str(uuid.uuid4())   # grandfather — surname matches
        father_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        gm_parent_folder = _write_person(root_path, gm_parent_uid, "Unknown Inny",
                                         last_name="Inny")
        gm_folder = _write_person(root_path, gm_uid, "Zofia Inna",
                                  last_name="Inna",
                                  sex="Kobieta",
                                  parents=[str(gm_parent_folder)],
                                  parents_id=[gm_parent_uid])
        gf_folder = _write_person(root_path, gf_uid, "Stanislaw Mankin",
                                  last_name="Mankin",
                                  spouse=[str(gm_folder)],
                                  spouse_id=[gm_uid])
        father_folder = _write_person(root_path, father_uid, "Adam Mankin",
                                      last_name="Mankin",
                                      parents=[str(gf_folder)],
                                      parents_id=[gf_uid])
        root_folder = _write_person(root_path, root_uid, "Jan Mankin",
                                    last_name="Mankin",
                                    parents=[str(father_folder)],
                                    parents_id=[father_uid])

        for u, n, f in [
            (gm_parent_uid, "Unknown Inny", gm_parent_folder),
            (gm_uid, "Zofia Inna", gm_folder),
            (gf_uid, "Stanislaw Mankin", gf_folder),
            (father_uid, "Adam Mankin", father_folder),
            (root_uid, "Jan Mankin", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Mankin" in lineages
        members = lineages["Mankin"].member_uids
        # Grandfather included via walk
        assert gf_uid in members
        # Grandmother included as spouse-leaf of grandfather
        assert gm_uid in members
        # Grandmother's parent must NOT be walked
        assert gm_parent_uid not in members


# ---------------------------------------------------------------------------
# Test 13 — No spouse, no children — universal = {root}
# ---------------------------------------------------------------------------

class TestNoSpouseNoChildren:

    def test_universal_set_is_root_only_when_isolated(self, tmp_root):
        """Root with parents but no spouse and no children -> universal = {root}."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        father_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        father_folder = _write_person(root_path, father_uid, "Adam Lewandowski",
                                      last_name="Lewandowski")
        root_folder = _write_person(root_path, root_uid, "Jan Lewandowski",
                                    last_name="Lewandowski",
                                    parents=[str(father_folder)],
                                    parents_id=[father_uid])

        for u, n, f in [
            (father_uid, "Adam Lewandowski", father_folder),
            (root_uid, "Jan Lewandowski", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Lewandowski" in lineages
        members = lineages["Lewandowski"].member_uids
        # Universal = {root} only; no spouse, no children
        assert root_uid in members
        # Father added via R3
        assert father_uid in members
        # Total: root (universal) + father (R3) + no other
        # Father has no spouse in this fixture, so exactly 2 members
        assert len(members) == 2


# ---------------------------------------------------------------------------
# Test 14 — Surname collision across contributors
# ---------------------------------------------------------------------------

class TestSurnameCollisionAcrossContributors:

    def test_second_contributor_with_same_surname_not_added(self, tmp_root):
        """Two contributors with same surname: second contributor not in first's folder."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        root_father_uid = str(uuid.uuid4())
        root_mother_uid = str(uuid.uuid4())  # second contributor, same surname
        root_uid = str(uuid.uuid4())

        # Both parents share surname "Kowalski"
        root_father_folder = _write_person(root_path, root_father_uid, "Adam Kowalski",
                                           last_name="Kowalski")
        root_mother_folder = _write_person(root_path, root_mother_uid, "Zofia Kowalska",
                                           last_name="Kowalska",
                                           maiden_name="Kowalski",
                                           has_maiden_name=True,
                                           sex="Kobieta")
        root_folder = _write_person(root_path, root_uid, "Jan Kowalski",
                                    last_name="Kowalski",
                                    parents=[str(root_father_folder), str(root_mother_folder)],
                                    parents_id=[root_father_uid, root_mother_uid])

        for u, n, f in [
            (root_father_uid, "Adam Kowalski", root_father_folder),
            (root_mother_uid, "Zofia Kowalska", root_mother_folder),
            (root_uid, "Jan Kowalski", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        # Only one "Kowalski" folder
        assert len(lineages) == 1
        assert "Kowalski" in lineages
        # First contributor wins
        assert lineages["Kowalski"].contributor_uid == root_father_uid
        # Second contributor (mother) NOT added as R3 in the folder
        members = lineages["Kowalski"].member_uids
        # root_mother_uid is NOT in members (she would only be via R3 if she were the contributor)
        # She might appear as root_father's spouse IF they are linked; they are not in this fixture.
        # Root itself IS universal.
        assert root_uid in members
        assert root_father_uid in members
        # Collision log entry present
        assert any("already contributed" in e and root_mother_uid in e for e in log)


# ---------------------------------------------------------------------------
# Test 15 — Empty maiden case (has_maiden=True, maiden_name="(nieznane)")
# ---------------------------------------------------------------------------

class TestEmptyMaidenNoFolder:

    def test_nieznane_maiden_name_contributes_no_subfolder(self, tmp_root):
        """Mother has has_maiden=True but maiden_name='(nieznane)' -> no lineage folder."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        mother_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        mother_folder = _write_person(root_path, mother_uid, "Zofia (nieznane)",
                                      last_name="Kowalska",
                                      maiden_name="(nieznane)",
                                      has_maiden_name=True,
                                      sex="Kobieta")
        root_folder = _write_person(root_path, root_uid, "Jan Kowalski",
                                    last_name="Kowalski",
                                    parents=[str(mother_folder)],
                                    parents_id=[mother_uid])

        for u, n, f in [
            (mother_uid, "Zofia (nieznane)", mother_folder),
            (root_uid, "Jan Kowalski", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        # No folder created for "(nieznane)"
        assert len(lineages) == 0
        # Log entry must mention the skip
        assert any("has no lineage surname" in e for e in log)


# ---------------------------------------------------------------------------
# Test 16 — All 4 contributors distinct; universal appears in all 4 folders
# ---------------------------------------------------------------------------

class TestAllFourContributorsUniversalRule:

    def test_universal_members_appear_in_all_four_lineage_folders(self, tmp_root):
        """Root + spouse + child + child-spouse all appear in every lineage folder."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        father_uid = str(uuid.uuid4())
        mother_uid = str(uuid.uuid4())
        sp_father_uid = str(uuid.uuid4())
        sp_mother_uid = str(uuid.uuid4())
        spouse_uid = str(uuid.uuid4())
        child_uid = str(uuid.uuid4())
        child_spouse_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        father_folder = _write_person(root_path, father_uid, "Adam Mankin",
                                      last_name="Mankin")
        mother_folder = _write_person(root_path, mother_uid, "Anna Pastryk",
                                      last_name="Pastryk",
                                      maiden_name="Pastryk",
                                      has_maiden_name=True,
                                      sex="Kobieta")
        sp_father_folder = _write_person(root_path, sp_father_uid, "Piotr Kowalski",
                                         last_name="Kowalski")
        sp_mother_folder = _write_person(root_path, sp_mother_uid, "Ewa Nowak",
                                         last_name="Nowak",
                                         maiden_name="Nowak",
                                         has_maiden_name=True,
                                         sex="Kobieta")
        child_spouse_folder = _write_person(root_path, child_spouse_uid, "Maria Inna",
                                            last_name="Inna", sex="Kobieta")
        child_folder = _write_person(root_path, child_uid, "Piotr Mankin",
                                     last_name="Mankin",
                                     spouse=[str(child_spouse_folder)],
                                     spouse_id=[child_spouse_uid])
        spouse_folder = _write_person(root_path, spouse_uid, "Halina Kowalska",
                                      last_name="Kowalska", sex="Kobieta",
                                      parents=[str(sp_father_folder), str(sp_mother_folder)],
                                      parents_id=[sp_father_uid, sp_mother_uid])
        root_folder = _write_person(root_path, root_uid, "Tomasz Mankin",
                                    last_name="Mankin",
                                    parents=[str(father_folder), str(mother_folder)],
                                    parents_id=[father_uid, mother_uid],
                                    spouse=[str(spouse_folder)],
                                    spouse_id=[spouse_uid],
                                    children=[str(child_folder)],
                                    children_id=[child_uid])

        for u, n, f in [
            (father_uid, "Adam Mankin", father_folder),
            (mother_uid, "Anna Pastryk", mother_folder),
            (sp_father_uid, "Piotr Kowalski", sp_father_folder),
            (sp_mother_uid, "Ewa Nowak", sp_mother_folder),
            (spouse_uid, "Halina Kowalska", spouse_folder),
            (child_uid, "Piotr Mankin", child_folder),
            (child_spouse_uid, "Maria Inna", child_spouse_folder),
            (root_uid, "Tomasz Mankin", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert len(lineages) == 4
        universal_uids = [root_uid, spouse_uid, child_uid, child_spouse_uid]

        for surname in ["Mankin", "Pastryk", "Kowalski", "Nowak"]:
            assert surname in lineages
            members = lineages[surname].member_uids
            for uid in universal_uids:
                assert uid in members, (
                    f"Universal member {uid} missing from '{surname}' lineage"
                )


# ---------------------------------------------------------------------------
# Test 17 — Three-generation descendants recursion
# ---------------------------------------------------------------------------

class TestWalkDescendantsRecursesThreeGens:

    def test_grandchild_and_spouse_appear_in_lineage_as_universal_members(
        self, tmp_root
    ):
        """root -> child -> grandchild; grandchild + grandchild-spouse in every lineage."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        father_uid = str(uuid.uuid4())
        grandchild_spouse_uid = str(uuid.uuid4())
        grandchild_uid = str(uuid.uuid4())
        child_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        father_folder = _write_person(root_path, father_uid, "Adam Wisnicki",
                                      last_name="Wisnicki")
        grandchild_spouse_folder = _write_person(
            root_path, grandchild_spouse_uid, "Marta Inna",
            last_name="Inna", sex="Kobieta"
        )
        grandchild_folder = _write_person(root_path, grandchild_uid, "Karol Wisnicki",
                                          last_name="Wisnicki",
                                          spouse=[str(grandchild_spouse_folder)],
                                          spouse_id=[grandchild_spouse_uid])
        child_folder = _write_person(root_path, child_uid, "Ewa Wisnicki",
                                     last_name="Wisnicki", sex="Kobieta",
                                     children=[str(grandchild_folder)],
                                     children_id=[grandchild_uid])
        root_folder = _write_person(root_path, root_uid, "Jan Wisnicki",
                                    last_name="Wisnicki",
                                    parents=[str(father_folder)],
                                    parents_id=[father_uid],
                                    children=[str(child_folder)],
                                    children_id=[child_uid])

        for u, n, f in [
            (father_uid, "Adam Wisnicki", father_folder),
            (grandchild_spouse_uid, "Marta Inna", grandchild_spouse_folder),
            (grandchild_uid, "Karol Wisnicki", grandchild_folder),
            (child_uid, "Ewa Wisnicki", child_folder),
            (root_uid, "Jan Wisnicki", root_folder),
        ]:
            _add_to_cache(fs, u, n, f)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(root_uid)

        assert "Wisnicki" in lineages
        members = lineages["Wisnicki"].member_uids
        # All three generations as universal members
        assert root_uid in members          # generation 0
        assert child_uid in members         # generation 1
        assert grandchild_uid in members    # generation 2
        assert grandchild_spouse_uid in members  # generation 2 spouse (leaf)
