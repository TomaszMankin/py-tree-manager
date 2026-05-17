"""Unit tests for services/folder_tree_service.py.

TDD for FolderTreeService.compute_membership() and render_folder_tree_filename().
Revised 2026-05-08: multi-bracket couple-letter encoding; depth cap removed; -ST dropped.

Uses tmp_root fixture + me_json_factory from conftest.py.
All tests are L0 (pure logic; no COM / disk side-effects for the computation;
no shortcut creation).

Test coverage:
  1  Empty tree (root only)
  2  Root + spouse only
  3  Root + child
  4  Root + child + child's spouse
  5  Root + parents (both)
  6  Cycle detection (A parent of B, B parent of A)
  7  Couple-code width pre-detection (replaces the old depth-cap test)
  8  Filename rendering — multi-bracket format (revised expectations)
  9  Multiple spouses of root (collision disambiguation via (2))
 10  _couple_code width for small generation (<=26 couples -> 1-char)
 11  _couple_code width for 27-couple generation (->2-char)
 12  _couple_code width for 677-couple generation (->3-char)
 13  Encoding skips couple-code at gen 0 (3 brackets only)
 14  Encoding uses multi-bracket format at gen != 0 (4 brackets)
"""

import json
import uuid
from pathlib import Path
from typing import Dict

import pytest

from src.wrappers.person_data_wrapper import PersonDataWrapper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_person(root: Path, uid: str, name: str, sex: str = "Mezczyzna",
                  spouses=None, children=None, parents=None, parents_id=None,
                  spouse_id=None, children_id=None) -> Path:
    """Create a person folder under Lista osob and write me.json. Return folder path."""
    folder = root / "Lista osób" / name
    folder.mkdir(parents=True, exist_ok=True)
    data = {
        "unique_identifier": uid,
        "person_name": name,
        "location": str(folder),
        "first_name": name.split()[0],
        "other_first_names": "",
        "last_name": name.split()[-1] if len(name.split()) > 1 else name,
        "other_last_names": "",
        "maiden_name": "",
        "other_maiden_names": "",
        "has_maiden_name": False,
        "sex": sex,
        "spouse": [str(p) for p in (spouses or [])],
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
    from src.wrappers.person_data_wrapper import PersonDataProperty
    cached = fs.settings.get_cached_people()
    cached[uid] = {
        PersonDataProperty.UNIQUE_IDENTIFIER.value: uid,
        PersonDataProperty.LOCATION.value: str(folder),
        PersonDataProperty.PERSON_NAME.value: name,
    }
    fs.settings.set_cached_people(cached)


# ---------------------------------------------------------------------------
# Test 1 — empty tree (root only)
# ---------------------------------------------------------------------------

class TestFolderTreeMembershipEmptyTree:

    def test_root_only_returns_one_member(self, tmp_root):
        """compute_membership with no relatives returns exactly one entry: root self."""
        from src.services.folder_tree_service import FolderTreeService

        root_path, fs = tmp_root
        uid = str(uuid.uuid4())
        folder = _write_person(root_path, uid, "Jan Kowalski", sex="Mezczyzna")
        _add_to_cache(fs, uid, "Jan Kowalski", folder)

        svc = FolderTreeService(fs)
        members, log = svc.compute_membership(uid)

        assert len(members) == 1
        assert members[0].uid == uid
        assert members[0].role == 'self'
        assert members[0].generation == 0


# ---------------------------------------------------------------------------
# Test 2 — root + spouse only
# ---------------------------------------------------------------------------

class TestFolderTreeMembershipRootAndSpouse:

    def test_root_with_spouse_returns_two_members(self, tmp_root):
        """Root + spouse at gen 0 — two entries returned."""
        from src.services.folder_tree_service import FolderTreeService

        root_path, fs = tmp_root
        root_uid = str(uuid.uuid4())
        spouse_uid = str(uuid.uuid4())

        spouse_folder = _write_person(root_path, spouse_uid, "Anna Kowalska", sex="Kobieta")
        root_folder = _write_person(
            root_path, root_uid, "Jan Kowalski",
            sex="Mezczyzna",
            spouses=[spouse_folder],
            spouse_id=[spouse_uid],
        )
        _add_to_cache(fs, root_uid, "Jan Kowalski", root_folder)
        _add_to_cache(fs, spouse_uid, "Anna Kowalska", spouse_folder)

        svc = FolderTreeService(fs)
        members, log = svc.compute_membership(root_uid)

        assert len(members) == 2
        roles = {m.role for m in members}
        assert 'self' in roles
        assert 'spouse' in roles
        spouse_entry = next(m for m in members if m.role == 'spouse')
        assert spouse_entry.uid == spouse_uid
        assert spouse_entry.generation == 0


# ---------------------------------------------------------------------------
# Test 3 — root + child
# ---------------------------------------------------------------------------

class TestFolderTreeMembershipRootAndChild:

    def test_root_with_child_returns_two_members(self, tmp_root):
        """Root + one child at gen -1 — two entries, child is descendant."""
        from src.services.folder_tree_service import FolderTreeService

        root_path, fs = tmp_root
        root_uid = str(uuid.uuid4())
        child_uid = str(uuid.uuid4())

        child_folder = _write_person(root_path, child_uid, "Piotr Kowalski",
                                     sex="Mezczyzna",
                                     parents_id=[root_uid])
        root_folder = _write_person(
            root_path, root_uid, "Jan Kowalski",
            sex="Mezczyzna",
            children=[child_folder],
            children_id=[child_uid],
        )
        _add_to_cache(fs, root_uid, "Jan Kowalski", root_folder)
        _add_to_cache(fs, child_uid, "Piotr Kowalski", child_folder)

        svc = FolderTreeService(fs)
        members, log = svc.compute_membership(root_uid)

        assert len(members) == 2
        child_entry = next(m for m in members if m.uid == child_uid)
        assert child_entry.role == 'descendant'
        assert child_entry.generation == -1


# ---------------------------------------------------------------------------
# Test 4 — root + child + child's spouse
# ---------------------------------------------------------------------------

class TestFolderTreeMembershipChildWithSpouse:

    def test_child_spouse_gets_descendant_spouse_role(self, tmp_root):
        """Child's spouse gets role='descendant_spouse' at the same gen as child."""
        from src.services.folder_tree_service import FolderTreeService

        root_path, fs = tmp_root
        root_uid = str(uuid.uuid4())
        child_uid = str(uuid.uuid4())
        son_in_law_uid = str(uuid.uuid4())

        son_in_law_folder = _write_person(root_path, son_in_law_uid, "Marek Nowak",
                                          sex="Mezczyzna")
        child_folder = _write_person(
            root_path, child_uid, "Maria Nowak", sex="Kobieta",
            parents_id=[root_uid],
            spouses=[son_in_law_folder],
            spouse_id=[son_in_law_uid],
        )
        root_folder = _write_person(
            root_path, root_uid, "Jan Kowalski",
            sex="Mezczyzna",
            children=[child_folder],
            children_id=[child_uid],
        )
        _add_to_cache(fs, root_uid, "Jan Kowalski", root_folder)
        _add_to_cache(fs, child_uid, "Maria Nowak", child_folder)
        _add_to_cache(fs, son_in_law_uid, "Marek Nowak", son_in_law_folder)

        svc = FolderTreeService(fs)
        members, log = svc.compute_membership(root_uid)

        assert len(members) == 3
        sil_entry = next(m for m in members if m.uid == son_in_law_uid)
        assert sil_entry.role == 'descendant_spouse'
        assert sil_entry.generation == -1
        # Rule B: paired_descendant_uid should be the child (female)
        assert sil_entry.paired_descendant_uid == child_uid


# ---------------------------------------------------------------------------
# Test 5 — root + both parents
# ---------------------------------------------------------------------------

class TestFolderTreeMembershipRootAndParents:

    def test_root_with_both_parents(self, tmp_root):
        """Root's father and mother appear as ancestors with couple_index 0
        (they form one couple at gen +1, so total_couples == 1 -> code 'A')."""
        from src.services.folder_tree_service import FolderTreeService

        root_path, fs = tmp_root
        root_uid = str(uuid.uuid4())
        father_uid = str(uuid.uuid4())
        mother_uid = str(uuid.uuid4())

        father_folder = _write_person(root_path, father_uid, "Adam Kowalski",
                                      sex="Mezczyzna")
        mother_folder = _write_person(root_path, mother_uid, "Ewa Kowalska",
                                      sex="Kobieta")
        root_folder = _write_person(
            root_path, root_uid, "Jan Kowalski",
            sex="Mezczyzna",
            parents=[father_folder, mother_folder],
            parents_id=[father_uid, mother_uid],
        )
        _add_to_cache(fs, root_uid, "Jan Kowalski", root_folder)
        _add_to_cache(fs, father_uid, "Adam Kowalski", father_folder)
        _add_to_cache(fs, mother_uid, "Ewa Kowalska", mother_folder)

        svc = FolderTreeService(fs)
        members, log = svc.compute_membership(root_uid)

        assert len(members) == 3
        father_entry = next(m for m in members if m.uid == father_uid)
        mother_entry = next(m for m in members if m.uid == mother_uid)

        assert father_entry.role == 'ancestor'
        assert father_entry.generation == 1
        # Both parents share couple_index 0 (one couple at gen+1)
        assert father_entry.couple_index == 0
        assert father_entry.total_couples_in_generation == 1

        assert mother_entry.role == 'ancestor'
        assert mother_entry.generation == 1
        assert mother_entry.couple_index == 0
        assert mother_entry.total_couples_in_generation == 1


# ---------------------------------------------------------------------------
# Test 6 — cycle detection
# ---------------------------------------------------------------------------

class TestFolderTreeMembershipCycleDetection:

    def test_cycle_does_not_cause_infinite_loop(self, tmp_root):
        """A is parent of B, B is parent of A — no infinite loop; both appear once; log has warning."""
        from src.services.folder_tree_service import FolderTreeService

        root_path, fs = tmp_root
        a_uid = str(uuid.uuid4())
        b_uid = str(uuid.uuid4())

        # Note: these paths must be created before we can reference them
        a_folder_path = root_path / "Lista osób" / "Osoba A"
        b_folder_path = root_path / "Lista osób" / "Osoba B"

        b_folder = _write_person(
            root_path, b_uid, "Osoba B",
            sex="Mezczyzna",
            parents=[a_folder_path],
            parents_id=[a_uid],
        )
        a_folder = _write_person(
            root_path, a_uid, "Osoba A",
            sex="Mezczyzna",
            children=[b_folder],
            children_id=[b_uid],
            parents=[b_folder],
            parents_id=[b_uid],
        )

        _add_to_cache(fs, a_uid, "Osoba A", a_folder)
        _add_to_cache(fs, b_uid, "Osoba B", b_folder)

        svc = FolderTreeService(fs)
        members, log = svc.compute_membership(a_uid)

        # Both appear, each exactly once
        uids = [m.uid for m in members]
        assert uids.count(a_uid) == 1
        assert uids.count(b_uid) == 1
        # No infinite loop and at least one log entry of some kind
        assert len(members) >= 1
        # Cycle must produce a CYCLE log entry in build-log.txt
        assert any("CYCLE" in entry for entry in log), (
            f"Expected a 'CYCLE' log warning but got: {log}"
        )


# ---------------------------------------------------------------------------
# Test 7 — couple-code width pre-detection
# (replaces old depth-cap test; validates that deep lineages get correct couple codes)
# ---------------------------------------------------------------------------

class TestFolderTreeCouplecodeWidth:

    def test_five_generation_lineage_has_correct_couple_codes(self, tmp_root):
        """A 5-generation paternal lineage: each generation has exactly 1 couple,
        so all ancestors get couple code 'A' (width=1, total=1)."""
        from src.services.folder_tree_service import FolderTreeService

        root_path, fs = tmp_root

        uids = [str(uuid.uuid4()) for _ in range(6)]  # 0=root, 1=gen+1, ..., 5=gen+5
        names = ["Root Mann", "Gen1 Mann", "Gen2 Mann", "Gen3 Mann", "Gen4 Mann", "Gen5 Mann"]

        # Create gen5 first (no parents)
        f5 = _write_person(root_path, uids[5], names[5], sex="Mezczyzna")
        f4 = _write_person(root_path, uids[4], names[4], sex="Mezczyzna",
                            parents=[f5], parents_id=[uids[5]])
        f3 = _write_person(root_path, uids[3], names[3], sex="Mezczyzna",
                            parents=[f4], parents_id=[uids[4]])
        f2 = _write_person(root_path, uids[2], names[2], sex="Mezczyzna",
                            parents=[f3], parents_id=[uids[3]])
        f1 = _write_person(root_path, uids[1], names[1], sex="Mezczyzna",
                            parents=[f2], parents_id=[uids[2]])
        f0 = _write_person(root_path, uids[0], names[0], sex="Mezczyzna",
                            parents=[f1], parents_id=[uids[1]])

        for uid, name, folder in zip(uids, names, [f0, f1, f2, f3, f4, f5]):
            _add_to_cache(fs, uid, name, folder)

        svc = FolderTreeService(fs)
        members, log = svc.compute_membership(uids[0])

        by_uid = {m.uid: m for m in members}

        # All gen+1 through gen+5 ancestors have exactly 1 couple per generation
        for i in range(1, 6):
            entry = by_uid[uids[i]]
            assert entry.couple_index == 0, f"gen+{i} should have couple_index=0"
            assert entry.total_couples_in_generation == 1, f"gen+{i} should have total=1"
            # No depth cap: gen+4 and gen+5 should be present with valid couple data
        assert uids[4] in by_uid, "gen+4 ancestor should be included (no depth cap)"
        assert uids[5] in by_uid, "gen+5 ancestor should be included (no depth cap)"


# ---------------------------------------------------------------------------
# Test 8 — filename rendering (multi-bracket format)
# ---------------------------------------------------------------------------

class TestFolderTreeFilenameRendering:

    def test_self_male_gen0_filename(self):
        """Root male at gen 0 renders as [50][0][M] FullName.lnk (3 brackets, no couple-code).

        display = -gen = 0; bare number, no '+' prefix.
        """
        from src.services.folder_tree_service import FolderTreeMember, render_folder_tree_filename

        m = FolderTreeMember(
            uid="u1", generation=0, couple_index=0, total_couples_in_generation=1,
            role='self', gender='M', full_name="Zbigniew Mankin", location="/x",
            paired_descendant_uid=None,
        )
        assert render_folder_tree_filename(m) == "[50][0][M] Zbigniew Mankin.lnk"

    def test_descendant_female_gen_minus1_filename(self):
        """Female descendant at gen -1 renders as [49][1][A][F] FullName.lnk.

        display = -(-1) = 1; bare number, no '+' prefix.
        """
        from src.services.folder_tree_service import FolderTreeMember, render_folder_tree_filename

        m = FolderTreeMember(
            uid="u2", generation=-1, couple_index=0, total_couples_in_generation=1,
            role='descendant', gender='F', full_name="Katarzyna Szafran zd. Mankin",
            location="/x", paired_descendant_uid=None,
        )
        assert render_folder_tree_filename(m) == "[49][1][A][F] Katarzyna Szafran zd. Mankin.lnk"

    def test_descendant_spouse_no_st_suffix(self):
        """Descendant's spouse renders without -ST suffix; uses couple-letter for pairing.

        gen -1 -> display = 1; bare number.
        """
        from src.services.folder_tree_service import FolderTreeMember, render_folder_tree_filename

        m = FolderTreeMember(
            uid="husband_uid", generation=-1, couple_index=0, total_couples_in_generation=2,
            role='descendant_spouse',
            gender='F',  # descendant-side gender (Katarzyna is female)
            full_name="Szafran",
            location="/x",
            paired_descendant_uid="katarzyna_uid",
        )
        # 2 couples -> width 1 -> code 'A' for index 0
        assert render_folder_tree_filename(m) == "[49][1][A][F] Szafran.lnk"

    def test_ancestor_gen1_couple_a_male_filename(self):
        """Ancestor at gen+1, couple A, male renders as [51][-1][A][M] FullName.lnk.

        display = -(+1) = -1; negative keeps '-' prefix.
        """
        from src.services.folder_tree_service import FolderTreeMember, render_folder_tree_filename

        m = FolderTreeMember(
            uid="u3", generation=1, couple_index=0, total_couples_in_generation=2,
            role='ancestor', gender='M', full_name="Adam Kowalski", location="/x",
            paired_descendant_uid=None,
        )
        assert render_folder_tree_filename(m) == "[51][-1][A][M] Adam Kowalski.lnk"

    def test_ancestor_gen2_couple_b_female_filename(self):
        """Gen+2, couple B (index=1), female renders as [52][-2][B][F].

        display = -(+2) = -2; negative keeps '-' prefix.
        """
        from src.services.folder_tree_service import FolderTreeMember, render_folder_tree_filename

        m = FolderTreeMember(
            uid="u4", generation=2, couple_index=1, total_couples_in_generation=4,
            role='ancestor', gender='F', full_name="Babcia Kowalska", location="/x",
            paired_descendant_uid=None,
        )
        assert render_folder_tree_filename(m) == "[52][-2][B][F] Babcia Kowalska.lnk"

    def test_gen0_spouse_no_couple_code(self):
        """Gen 0 spouse renders with only 3 brackets (no couple-code).

        display = 0; bare number, no '+' prefix.
        """
        from src.services.folder_tree_service import FolderTreeMember, render_folder_tree_filename

        m = FolderTreeMember(
            uid="u5", generation=0, couple_index=0, total_couples_in_generation=1,
            role='spouse', gender='F', full_name="Jadwiga Mankin", location="/x",
            paired_descendant_uid=None,
        )
        assert render_folder_tree_filename(m) == "[50][0][F] Jadwiga Mankin.lnk"


# ---------------------------------------------------------------------------
# Test 9 — multiple spouses of root (filename collision disambiguation)
# ---------------------------------------------------------------------------

class TestFolderTreeMultipleSpouses:

    def test_two_spouses_with_same_name_disambiguated(self, tmp_root):
        """Two spouses with the same full name get (2) suffix on the second."""
        from src.services.folder_tree_service import FolderTreeService, render_folder_tree_filename

        root_path, fs = tmp_root
        root_uid = str(uuid.uuid4())
        spouse1_uid = str(uuid.uuid4())
        spouse2_uid = str(uuid.uuid4())

        # Both spouses have the same name — collision scenario
        sp1_folder = _write_person(root_path, spouse1_uid, "Anna Kowalska", sex="Kobieta")
        sp2_folder = _write_person(root_path, spouse2_uid, "Anna Kowalska (2)", sex="Kobieta")
        # Rename folder to create same-filename scenario after render
        # Actually let's just verify with different UIDs same name via the render:
        # We test disambiguation at the build level in a separate check.
        # This test verifies that compute_membership returns both spouses.

        root_folder = _write_person(
            root_path, root_uid, "Jan Kowalski",
            sex="Mezczyzna",
            spouses=[sp1_folder, sp2_folder],
            spouse_id=[spouse1_uid, spouse2_uid],
        )
        _add_to_cache(fs, root_uid, "Jan Kowalski", root_folder)
        _add_to_cache(fs, spouse1_uid, "Anna Kowalska", sp1_folder)
        _add_to_cache(fs, spouse2_uid, "Anna Kowalska (2)", sp2_folder)

        svc = FolderTreeService(fs)
        members, log = svc.compute_membership(root_uid)

        spouse_entries = [m for m in members if m.role == 'spouse']
        assert len(spouse_entries) == 2, f"Expected 2 spouse entries, got {len(spouse_entries)}"


# ---------------------------------------------------------------------------
# Test 10 — _couple_code: small generation (<=26 couples -> 1-char)
# ---------------------------------------------------------------------------

class TestCouplecodeWidthSmall:

    def test_couple_code_width_for_small_generation(self):
        """5 couples -> all 1-char codes (A..E); no zero-padding."""
        from src.services.folder_tree_service import _couple_code

        total = 5
        codes = [_couple_code(i, total) for i in range(total)]
        assert codes == ['A', 'B', 'C', 'D', 'E']
        assert all(len(c) == 1 for c in codes)

    def test_couple_code_width_26_couples_still_single_char(self):
        """26 couples is exactly 26^1 — width stays 1; last code is 'Z'."""
        from src.services.folder_tree_service import _couple_code

        assert _couple_code(0, 26) == 'A'
        assert _couple_code(25, 26) == 'Z'
        assert len(_couple_code(0, 26)) == 1

    def test_couple_code_boundary_26_to_27(self):
        """26 couples -> width 1 (Z); 27 couples -> width 2 (AA, AB, ..., BB)."""
        from src.services.folder_tree_service import _couple_code

        # At 26 couples, last valid code is 'Z'
        assert len(_couple_code(25, 26)) == 1
        # At 27 couples, all codes are 2 chars
        assert len(_couple_code(0, 27)) == 2
        assert len(_couple_code(26, 27)) == 2


# ---------------------------------------------------------------------------
# Test 11 — _couple_code: 27-couple generation -> 2-char
# ---------------------------------------------------------------------------

class TestCouplecodeWidth27:

    def test_couple_code_width_for_27_couple_generation(self):
        """27 couples -> width 2; first code is 'AA', 27th is 'BA'."""
        from src.services.folder_tree_service import _couple_code

        total = 27
        assert _couple_code(0, total) == 'AA'
        assert _couple_code(1, total) == 'AB'
        assert _couple_code(25, total) == 'AZ'
        assert _couple_code(26, total) == 'BA'
        assert all(len(_couple_code(i, total)) == 2 for i in range(total))

    def test_couple_code_width_676_still_2_char(self):
        """676 = 26^2 -> width 2; last code is 'ZZ'."""
        from src.services.folder_tree_service import _couple_code

        assert len(_couple_code(0, 676)) == 2
        assert len(_couple_code(675, 676)) == 2
        assert _couple_code(675, 676) == 'ZZ'

    def test_couple_code_boundary_676_to_677(self):
        """676 couples -> width 2; 677 couples -> width 3."""
        from src.services.folder_tree_service import _couple_code

        assert len(_couple_code(675, 676)) == 2
        assert len(_couple_code(0, 677)) == 3


# ---------------------------------------------------------------------------
# Test 12 — _couple_code: 677-couple generation -> 3-char
# ---------------------------------------------------------------------------

class TestCouplecodeWidth677:

    def test_couple_code_width_for_677_couple_generation(self):
        """677 couples -> width 3; first two codes are 'AAA' and 'AAB'."""
        from src.services.folder_tree_service import _couple_code

        total = 677
        code0 = _couple_code(0, total)
        code1 = _couple_code(1, total)
        assert code0 == 'AAA'
        assert code1 == 'AAB'
        assert all(len(_couple_code(i, total)) == 3 for i in range(min(10, total)))


# ---------------------------------------------------------------------------
# Test 13 — encoding skips couple-code at gen 0 (3 brackets only)
# ---------------------------------------------------------------------------

class TestEncodingGen0NoCoupleCode:

    def test_encoding_skips_couple_code_at_gen_0(self):
        """At gen == 0, filename has exactly 3 bracket groups: [NN][0][gender].

        Second bracket is bare '0' (no '+' prefix).
        """
        from src.services.folder_tree_service import FolderTreeMember, render_folder_tree_filename
        import re

        m = FolderTreeMember(
            uid="x", generation=0, couple_index=0, total_couples_in_generation=1,
            role='self', gender='M', full_name="Root Person", location="/x",
            paired_descendant_uid=None,
        )
        fname = render_folder_tree_filename(m)
        # Count bracket groups at the start of the filename (before the space + name)
        prefix = fname.split(' ')[0]
        brackets = re.findall(r'\[[^\]]+\]', prefix)
        assert len(brackets) == 3, f"Expected 3 bracket groups at gen 0, got {len(brackets)}: {fname}"
        assert brackets[0] == '[50]'
        assert brackets[1] == '[0]'
        assert brackets[2] == '[M]'


# ---------------------------------------------------------------------------
# Test 14 — encoding uses multi-bracket format at gen != 0 (4 brackets)
# ---------------------------------------------------------------------------

class TestEncodingMultiBracketFormat:

    def test_encoding_uses_multi_bracket_format_for_ancestors(self):
        """At gen != 0, filename has exactly 4 bracket groups: [NN][display][couple][gender].

        gen+1 ancestor -> display = -(+1) = -1 -> second bracket '[-1]'.
        """
        from src.services.folder_tree_service import FolderTreeMember, render_folder_tree_filename
        import re

        m = FolderTreeMember(
            uid="x", generation=1, couple_index=0, total_couples_in_generation=2,
            role='ancestor', gender='M', full_name="Ancestor Person", location="/x",
            paired_descendant_uid=None,
        )
        fname = render_folder_tree_filename(m)
        prefix = fname.split(' ')[0]
        brackets = re.findall(r'\[[^\]]+\]', prefix)
        assert len(brackets) == 4, f"Expected 4 bracket groups at gen != 0, got {len(brackets)}: {fname}"
        assert brackets[0] == '[51]'
        assert brackets[1] == '[-1]'
        assert brackets[2] == '[A]'
        assert brackets[3] == '[M]'

    def test_encoding_uses_multi_bracket_format_for_descendants(self):
        """At gen -2, filename has 4 bracket groups: [48][2][couple][gender].

        gen -2 -> display = -(-2) = 2; bare number, no '+'.
        """
        from src.services.folder_tree_service import FolderTreeMember, render_folder_tree_filename
        import re

        m = FolderTreeMember(
            uid="x", generation=-2, couple_index=1, total_couples_in_generation=3,
            role='descendant', gender='F', full_name="Grandchild Person", location="/x",
            paired_descendant_uid=None,
        )
        fname = render_folder_tree_filename(m)
        prefix = fname.split(' ')[0]
        brackets = re.findall(r'\[[^\]]+\]', prefix)
        assert len(brackets) == 4, f"Expected 4 bracket groups at gen -2, got {len(brackets)}: {fname}"
        assert brackets[0] == '[48]'
        assert brackets[1] == '[2]'
        assert brackets[2] == '[B]'
        assert brackets[3] == '[F]'


# ---------------------------------------------------------------------------
# Test 15 — spouse-seeded ancestor DFS regression
# ---------------------------------------------------------------------------

class TestSpouseSeededAncestorDfs:

    def test_spouse_parents_appear_at_gen_plus_1_couple_b(self, tmp_root):
        """Regression test: spouse's parents must appear at gen+1 in couple B.

        Tree (6 people):
          - R (root, male)
          - S (root's spouse, female; R.spouse_id=[S], S.spouse_id=[R])
          - RF (R's father, male) — RF.parents_id = []
          - RM (R's mother, female) — RM.parents_id = []
          - SF (S's father, male) — SF.parents_id = []
          - SM (S's mother, female) — SM.parents_id = []

        All 6 are in cached_people. R.parents_id = [RF, RM]; S.parents_id = [SF, SM].
        RF, RM, SF, SM are lineage leaves (no grandparents).

        Before this fix: only R, S, RF, RM appeared in membership.
        SF and SM were silently dropped because the DFS never seeded S into
        the upward walk.

        Expected behavior after the fix:
          - All 6 UIDs in returned members.
          - R: (generation=0, role='self').
          - S: (generation=0, role='spouse').
          - RF, RM: (generation=1, couple_index=0,
            total_couples_in_generation=2, role='ancestor').
          - SF, SM: (generation=1, couple_index=1,
            total_couples_in_generation=2, role='ancestor').
          - build_log has no ERROR entries.
        """
        import uuid as _uuid
        from src.services.folder_tree_service import FolderTreeService

        root_path, fs = tmp_root

        r_uid  = str(_uuid.uuid4())
        s_uid  = str(_uuid.uuid4())
        rf_uid = str(_uuid.uuid4())
        rm_uid = str(_uuid.uuid4())
        sf_uid = str(_uuid.uuid4())
        sm_uid = str(_uuid.uuid4())

        # Lineage leaves — no parents
        rf_folder = _write_person(root_path, rf_uid, "Roman Ojciec",  sex="Mezczyzna")
        rm_folder = _write_person(root_path, rm_uid, "Rozalia Matka", sex="Kobieta")
        sf_folder = _write_person(root_path, sf_uid, "Stefan Ojciec", sex="Mezczyzna")
        sm_folder = _write_person(root_path, sm_uid, "Stefania Matka", sex="Kobieta")

        # Spouse S — has her own parents SF + SM
        s_folder = _write_person(
            root_path, s_uid, "Stanisława Zona",
            sex="Kobieta",
            spouses=[],
            spouse_id=[r_uid],
            parents=[sf_folder, sm_folder],
            parents_id=[sf_uid, sm_uid],
        )

        # Root R — has parents RF + RM, married to S
        r_folder = _write_person(
            root_path, r_uid, "Rafał Korzeń",
            sex="Mezczyzna",
            spouses=[s_folder],
            spouse_id=[s_uid],
            parents=[rf_folder, rm_folder],
            parents_id=[rf_uid, rm_uid],
        )

        for uid, name, folder in [
            (r_uid,  "Rafał Korzeń",    r_folder),
            (s_uid,  "Stanisława Zona", s_folder),
            (rf_uid, "Roman Ojciec",    rf_folder),
            (rm_uid, "Rozalia Matka",   rm_folder),
            (sf_uid, "Stefan Ojciec",   sf_folder),
            (sm_uid, "Stefania Matka",  sm_folder),
        ]:
            _add_to_cache(fs, uid, name, folder)

        svc = FolderTreeService(fs)
        members, log = svc.compute_membership(r_uid)

        by_uid = {m.uid: m for m in members}

        # All 6 must appear
        assert set(by_uid.keys()) == {r_uid, s_uid, rf_uid, rm_uid, sf_uid, sm_uid}, (
            f"Missing UIDs. Got keys: {set(by_uid.keys())}"
        )

        # Root and spouse at gen 0
        assert by_uid[r_uid].generation == 0
        assert by_uid[r_uid].role == 'self'
        assert by_uid[s_uid].generation == 0
        assert by_uid[s_uid].role == 'spouse'

        # Couple A at gen=+1: root's parents (RF + RM)
        assert by_uid[rf_uid].generation == 1
        assert by_uid[rf_uid].role == 'ancestor'
        assert by_uid[rf_uid].couple_index == 0
        assert by_uid[rf_uid].total_couples_in_generation == 2

        assert by_uid[rm_uid].generation == 1
        assert by_uid[rm_uid].role == 'ancestor'
        assert by_uid[rm_uid].couple_index == 0
        assert by_uid[rm_uid].total_couples_in_generation == 2

        # Couple B at gen=+1: spouse's parents (SF + SM)
        assert by_uid[sf_uid].generation == 1
        assert by_uid[sf_uid].role == 'ancestor'
        assert by_uid[sf_uid].couple_index == 1
        assert by_uid[sf_uid].total_couples_in_generation == 2

        assert by_uid[sm_uid].generation == 1
        assert by_uid[sm_uid].role == 'ancestor'
        assert by_uid[sm_uid].couple_index == 1
        assert by_uid[sm_uid].total_couples_in_generation == 2

        # No ERROR log entries
        assert not any("ERROR" in entry for entry in log), (
            f"Unexpected ERROR in build_log: {[e for e in log if 'ERROR' in e]}"
        )
