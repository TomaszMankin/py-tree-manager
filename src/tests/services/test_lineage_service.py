"""L0 unit tests for services/lineage_service.py.

Test cases:
  1  Empty root (no parents, no spouses) -> empty dict
  2  Single-spouse, four-grandparents -> 4 surnames
  3  Mother carries maiden name -> maiden_name used (not last_name)
  4  Father has no recorded last_name -> contributes nothing; log entry; build succeeds
  5  Surname collision -> one shortcut, points to first contributor; log entry
  6  Multiple spouses -> collisions handled per first-contributor rule
  7  Diacritics preserved (Lukasiewicz round-trip)

All tests are L0: pure logic, no COM / disk side-effects for shortcut creation.
Uses tmp_root fixture + _write_person / _add_to_cache helpers (mirrored from
test_folder_tree_service.py patterns).
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import pytest

from src.wrappers.person_data_wrapper import PersonDataProperty, PersonDataWrapper


# ---------------------------------------------------------------------------
# Helpers (mirror test_folder_tree_service.py)
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
        """Root with no parents and no spouses yields an empty surnames dict."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root
        root_uid = str(uuid.uuid4())
        folder = _write_person(root_path, root_uid, "Jan Kowalski",
                               last_name="Kowalski")
        _add_to_cache(fs, root_uid, "Jan Kowalski", folder)

        svc = LineageService(fs)
        surnames, log = svc.compute_lineages(root_uid)

        assert surnames == {}
        # No error-level log entries expected (no anomalies)
        assert not any("ERROR" in entry for entry in log)


# ---------------------------------------------------------------------------
# Test 2 — single spouse, four grandparents -> 4 surnames
# ---------------------------------------------------------------------------

class TestLineageFourGrandparents:

    def test_single_spouse_four_grandparents_yields_four_surnames(self, tmp_root):
        """Typical case: root has 2 parents, spouse has 2 parents -> 4 distinct surnames."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        # root's parents
        father_uid = str(uuid.uuid4())
        mother_uid = str(uuid.uuid4())
        # spouse's parents
        sp_father_uid = str(uuid.uuid4())
        sp_mother_uid = str(uuid.uuid4())
        # spouse
        spouse_uid = str(uuid.uuid4())
        # root
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
        surnames, log = svc.compute_lineages(root_uid)

        assert len(surnames) == 4
        assert "Mankin" in surnames      # father's last_name
        assert "Pastryk" in surnames     # mother's maiden_name
        assert "Kowalski" in surnames    # spouse's father's last_name
        assert "Nowak" in surnames       # spouse's mother's maiden_name

    def test_surname_values_point_to_first_contributor(self, tmp_root):
        """Each surname key maps to the UID of the first contributor."""
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
        surnames, log = svc.compute_lineages(root_uid)

        assert surnames.get("Mankin") == father_uid
        assert surnames.get("Rutowska") == mother_uid


# ---------------------------------------------------------------------------
# Test 3 — mother carries maiden name
# ---------------------------------------------------------------------------

class TestLineageMaidenNamePrecedence:

    def test_maiden_name_used_when_has_maiden_name_true(self, tmp_root):
        """If has_maiden_name is True, maiden_name is the rod surname, not last_name."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        mother_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        # Mother: last_name=Kowalska (married name), maiden_name=Nowak (birth name)
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
        surnames, log = svc.compute_lineages(root_uid)

        # "Nowak" (maiden) wins; "Kowalska" (last_name) is NOT present
        assert "Nowak" in surnames
        assert "Kowalska" not in surnames
        assert surnames["Nowak"] == mother_uid

    def test_unknown_sentinel_maiden_name_returns_none(self, tmp_root):
        """has_maiden_name=True but maiden_name='(nieznane)' yields no rod entry."""
        from src.services.lineage_service import LineageService, extract_lineage_surname

        root_path, fs = tmp_root

        uid = str(uuid.uuid4())
        folder = _write_person(root_path, uid, "Jan Testowy",
                               last_name="Testowy",
                               maiden_name="(nieznane)",
                               has_maiden_name=True)
        _add_to_cache(fs, uid, "Jan Testowy", folder)

        wrapper = PersonDataWrapper({
            "last_name": "Testowy",
            "maiden_name": "(nieznane)",
            "has_maiden_name": True,
        })
        result = extract_lineage_surname(wrapper)
        assert result is None


# ---------------------------------------------------------------------------
# Test 4 — father has no recorded last_name
# ---------------------------------------------------------------------------

class TestLineageMissingLastName:

    def test_contributor_with_no_last_name_adds_nothing_and_logs(self, tmp_root):
        """A contributor with empty last_name yields no rod entry; build succeeds."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        father_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        # Father: last_name empty (unknown surname)
        father_folder = _write_person(root_path, father_uid, "Adam (nieznane)",
                                      last_name="(nieznane)")
        root_folder = _write_person(root_path, root_uid, "Jan Testowy",
                                    last_name="Testowy",
                                    parents_id=[father_uid],
                                    parents=[str(father_folder)])

        _add_to_cache(fs, father_uid, "Adam (nieznane)", father_folder)
        _add_to_cache(fs, root_uid, "Jan Testowy", root_folder)

        svc = LineageService(fs)
        surnames, log = svc.compute_lineages(root_uid)

        # Father contributes nothing because "(nieznane)" is the sentinel
        assert "Nieznane" not in surnames
        assert "(nieznane)" not in surnames
        # Log must contain a skip entry about father
        assert any("has no rod surname" in entry for entry in log)
        # Build completed (no exception)

    def test_contributor_with_whitespace_only_last_name_adds_nothing(self, tmp_root):
        """A contributor with whitespace-only last_name yields no rod entry."""
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

        # Both fathers have last_name "Kowalski"
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
        surnames, log = svc.compute_lineages(root_uid)

        # Exactly one "Kowalski" entry
        assert "Kowalski" in surnames
        assert surnames["Kowalski"] == root_father_uid  # first contributor

        # Log must have a collision entry for spouse's father
        assert any(
            "already contributed" in entry and spouse_father_uid in entry
            for entry in log
        )


# ---------------------------------------------------------------------------
# Test 6 — multiple spouses
# ---------------------------------------------------------------------------

class TestLineageMultipleSpouses:

    def test_two_spouses_contribute_up_to_four_additional_surnames(self, tmp_root):
        """Root with two spouses, each with two parents, can yield up to 6 surname slots."""
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
        surnames, log = svc.compute_lineages(root_uid)

        # Root has no parents -> 0 from root side
        # spouse1 contributes "Nowak" (father's last_name) + "Wisniewski" (mother's maiden)
        # spouse2 contributes "Zielinski" (father's last_name) + "Lewandowski" (mother's maiden)
        assert "Nowak" in surnames
        assert "Wisniewski" in surnames
        assert "Zielinski" in surnames
        assert "Lewandowski" in surnames
        assert len(surnames) == 4

    def test_collision_across_two_spouses_first_wins(self, tmp_root):
        """If spouse1's father and spouse2's father share surname, spouse1's father wins."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        root_uid = str(uuid.uuid4())
        spouse1_uid = str(uuid.uuid4())
        spouse2_uid = str(uuid.uuid4())
        s1_father_uid = str(uuid.uuid4())
        s2_father_uid = str(uuid.uuid4())

        # Both fathers share "Nowak"
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
        surnames, log = svc.compute_lineages(root_uid)

        assert "Nowak" in surnames
        # First spouse's father (s1_father_uid) wins
        assert surnames["Nowak"] == s1_father_uid
        # Collision log entry present for second spouse's father
        assert any("already contributed" in e and s2_father_uid in e for e in log)


# ---------------------------------------------------------------------------
# Test 7 — Polish diacritics preserved
# ---------------------------------------------------------------------------

class TestLineageDiacriticsPreserved:

    def test_diacritic_surname_round_trips_correctly(self, tmp_root):
        """Surname 'Lukasiewicz' (with Polish L) round-trips through extract_rod_surname."""
        from src.services.lineage_service import LineageService, extract_lineage_surname

        # Test the extraction function directly
        wrapper = PersonDataWrapper({
            "last_name": "Łukasiewicz",  # Łukasiewicz
            "has_maiden_name": False,
        })
        result = extract_lineage_surname(wrapper)
        assert result == "Łukasiewicz"

    def test_diacritic_surname_appears_in_compute_lineages(self, tmp_root):
        """Diacritic surname 'Wisniewski' survives the full compute_lineages path."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        father_uid = str(uuid.uuid4())
        root_uid = str(uuid.uuid4())

        # Use a diacritic surname: Wiśniewski
        father_folder = _write_person(root_path, father_uid, "Jan Wisniewski",
                                      last_name="Wiśniewski")  # Wiśniewski
        root_folder = _write_person(root_path, root_uid, "Piotr Wisniewski",
                                    last_name="Wiśniewski",
                                    parents=[str(father_folder)],
                                    parents_id=[father_uid])

        _add_to_cache(fs, father_uid, "Jan Wisniewski", father_folder)
        _add_to_cache(fs, root_uid, "Piotr Wisniewski", root_folder)

        svc = LineageService(fs)
        surnames, log = svc.compute_lineages(root_uid)

        assert "Wiśniewski" in surnames
        assert surnames["Wiśniewski"] == father_uid
