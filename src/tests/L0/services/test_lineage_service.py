"""L0 unit tests for services/lineage_service.py.

New contract: LineageService.compute_lineages accepts
List[FolderTreeMember] (already-computed Drzewo members) and groups them by
surname into Dict[str, List[FolderTreeMember]].  Generation / couple / gender
tokens are CARRIED THROUGH UNCHANGED from the FolderTreeMember objects —
LineageService does NOT recompute them.  The .lnk filename for each member
equals render_folder_tree_filename(member).

Test cases:
  1  Empty member list -> empty dict
  2  Single member, no surname -> empty dict, log entry
  3  Two members with distinct surnames -> two groups, correct assignment
  4  Generation carried unchanged (member.generation preserved in output)
  5  Couple index carried unchanged (member.couple_index preserved — no reindex)
  6  Gender carried unchanged (member.gender preserved)
  7  .lnk filename equals render_folder_tree_filename(member)
  8  H-B: couple-B member in a folder with no couple-A keeps B (no reindex)
  9  All spouses appear in the correct surname group
 10  Full descendant subtree members present in correct group
 11  Member with None surname excluded; log entry
 12  Multiple members same surname -> single group list
 13  Maiden-name rule: has_maiden_name=True -> maiden used as grouping key
 14  Diacritics in surname preserved in grouping key

All tests are L0: pure logic, no COM / disk side-effects for shortcut creation.
Uses tmp_root fixture + _write_person / _add_to_cache helpers.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import List, Optional

import pytest

from src.services.folder_tree_service import FolderTreeMember
from src.wrappers.person_data_wrapper import PersonDataProperty, PersonDataWrapper


# ---------------------------------------------------------------------------
# Helpers
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


def _make_member(
    uid: str,
    generation: int,
    couple_index: int,
    total_couples: int,
    gender: str,
    full_name: str,
    location: str = "",
    role: str = "ancestor",
) -> FolderTreeMember:
    """Construct a FolderTreeMember with given Drzewo attributes."""
    return FolderTreeMember(
        uid=uid,
        generation=generation,
        couple_index=couple_index,
        total_couples_in_generation=total_couples,
        role=role,
        gender=gender,
        full_name=full_name,
        location=location,
    )


# ---------------------------------------------------------------------------
# Test 1 — empty member list -> empty dict
# ---------------------------------------------------------------------------

class TestLineageEmptyMembers:

    def test_empty_member_list_returns_empty_dict(self, tmp_root):
        """compute_lineages([]) -> ({}, [])."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root
        svc = LineageService(fs)
        lineages, log = svc.compute_lineages([])

        assert lineages == {}
        assert log == [] or isinstance(log, list)


# ---------------------------------------------------------------------------
# Test 2 — member with no surname -> empty dict, log entry
# ---------------------------------------------------------------------------

class TestLineageMemberNoSurname:

    def test_member_with_unknown_surname_excluded_and_logged(self, tmp_root):
        """A member whose extract_lineage_surname returns None is excluded."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        uid = str(uuid.uuid4())
        folder = _write_person(root_path, uid, "Jan (nieznane)",
                               last_name="(nieznane)")
        _add_to_cache(fs, uid, "Jan (nieznane)", folder)

        member = _make_member(uid, generation=1, couple_index=0,
                              total_couples=1, gender="M",
                              full_name="Jan (nieznane)", location=str(folder))
        svc = LineageService(fs)
        lineages, log = svc.compute_lineages([member])

        assert lineages == {}
        assert any("no lineage surname" in e or "skipped" in e.lower() for e in log)


# ---------------------------------------------------------------------------
# Test 3 — two members with distinct surnames -> two groups
# ---------------------------------------------------------------------------

class TestLineageTwoDistinctSurnames:

    def test_two_members_distinct_surnames_produce_two_groups(self, tmp_root):
        """Members with different surnames end up in separate groups."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        uid_a = str(uuid.uuid4())
        uid_b = str(uuid.uuid4())

        folder_a = _write_person(root_path, uid_a, "Adam Mankin",
                                 last_name="Mankin", sex="Mezczyzna")
        folder_b = _write_person(root_path, uid_b, "Piotr Kowalski",
                                 last_name="Kowalski", sex="Mezczyzna")
        _add_to_cache(fs, uid_a, "Adam Mankin", folder_a)
        _add_to_cache(fs, uid_b, "Piotr Kowalski", folder_b)

        members = [
            _make_member(uid_a, 1, 0, 2, "M", "Adam Mankin", str(folder_a)),
            _make_member(uid_b, 1, 1, 2, "M", "Piotr Kowalski", str(folder_b)),
        ]
        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(members)

        assert "Mankin" in lineages
        assert "Kowalski" in lineages
        assert len(lineages) == 2

        mankin_uids = [m.uid for m in lineages["Mankin"]]
        kowalski_uids = [m.uid for m in lineages["Kowalski"]]
        assert uid_a in mankin_uids
        assert uid_b in kowalski_uids


# ---------------------------------------------------------------------------
# Test 4 — generation carried unchanged
# ---------------------------------------------------------------------------

class TestLineageGenerationCarriedUnchanged:

    def test_member_generation_identical_in_lineage_group(self, tmp_root):
        """member.generation in output group equals the value set in FolderTreeMember."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        uid = str(uuid.uuid4())
        folder = _write_person(root_path, uid, "Stefan Mankin", last_name="Mankin")
        _add_to_cache(fs, uid, "Stefan Mankin", folder)

        member = _make_member(uid, generation=3, couple_index=1,
                              total_couples=4, gender="M",
                              full_name="Stefan Mankin", location=str(folder))
        svc = LineageService(fs)
        lineages, log = svc.compute_lineages([member])

        assert "Mankin" in lineages
        out_member = lineages["Mankin"][0]
        assert out_member.generation == 3, (
            f"Expected generation=3, got {out_member.generation}"
        )


# ---------------------------------------------------------------------------
# Test 5 — couple index carried unchanged (no reindex)
# ---------------------------------------------------------------------------

class TestLineageCoupleIndexCarriedUnchanged:

    def test_couple_index_not_reindexed_in_output(self, tmp_root):
        """couple_index in output must equal the Drzewo couple_index (not reindexed)."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        uid = str(uuid.uuid4())
        folder = _write_person(root_path, uid, "Adam Mankin", last_name="Mankin")
        _add_to_cache(fs, uid, "Adam Mankin", folder)

        # couple_index=2 means couple C in the global Drzewo
        member = _make_member(uid, generation=2, couple_index=2,
                              total_couples=5, gender="M",
                              full_name="Adam Mankin", location=str(folder))
        svc = LineageService(fs)
        lineages, log = svc.compute_lineages([member])

        assert "Mankin" in lineages
        out_member = lineages["Mankin"][0]
        assert out_member.couple_index == 2, (
            f"Expected couple_index=2 (letter C), got {out_member.couple_index}"
        )
        assert out_member.total_couples_in_generation == 5


# ---------------------------------------------------------------------------
# Test 6 — gender carried unchanged
# ---------------------------------------------------------------------------

class TestLineageGenderCarriedUnchanged:

    def test_gender_token_not_modified_by_lineage_service(self, tmp_root):
        """member.gender in output equals the Drzewo-assigned gender token."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        uid = str(uuid.uuid4())
        folder = _write_person(root_path, uid, "Anna Mankin",
                               last_name="Mankin", sex="Kobieta")
        _add_to_cache(fs, uid, "Anna Mankin", folder)

        member = _make_member(uid, generation=1, couple_index=0,
                              total_couples=1, gender="F",
                              full_name="Anna Mankin", location=str(folder))
        svc = LineageService(fs)
        lineages, log = svc.compute_lineages([member])

        assert "Mankin" in lineages
        out_member = lineages["Mankin"][0]
        assert out_member.gender == "F", (
            f"Expected gender=F, got {out_member.gender}"
        )


# ---------------------------------------------------------------------------
# Test 7 — .lnk filename equals render_folder_tree_filename(member)
# ---------------------------------------------------------------------------

class TestLineageLnkFilenameMatchesDrzewoEncoder:

    def test_lnk_name_equals_render_folder_tree_filename_output(self, tmp_root):
        """The .lnk filename for a member must equal render_folder_tree_filename(member)."""
        from src.services.folder_tree_service import render_folder_tree_filename
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        uid = str(uuid.uuid4())
        folder = _write_person(root_path, uid, "Stefan Mankin", last_name="Mankin")
        _add_to_cache(fs, uid, "Stefan Mankin", folder)

        # gen=1, couple_index=0, total=1 -> [51][-1][A][M] Stefan Mankin.lnk
        member = _make_member(uid, generation=1, couple_index=0,
                              total_couples=1, gender="M",
                              full_name="Stefan Mankin", location=str(folder))

        expected_filename = render_folder_tree_filename(member)

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages([member])

        assert "Mankin" in lineages
        out_member = lineages["Mankin"][0]
        actual_filename = render_folder_tree_filename(out_member)

        assert actual_filename == expected_filename, (
            f"Expected .lnk name '{expected_filename}', got '{actual_filename}'"
        )


# ---------------------------------------------------------------------------
# Test 8 — H-B: couple-B member keeps B (no per-folder reindex)
# ---------------------------------------------------------------------------

class TestLineageCoupleLetterGlobalNotReindexed:
    """H-B: couple-letter-global invariant.

    Scenario: a surname folder's only member is at Drzewo couple_index=1 (letter B).
    No couple_index=0 (letter A) member shares the same surname.
    The output member MUST still carry couple_index=1 (letter B).
    LineageService must NOT reindex to A just because it is the first entry
    in the group.
    """

    def test_couple_b_without_couple_a_keeps_b_letter(self, tmp_root):
        """Sole Wiśniewski-surname member at couple_index=1 (B) keeps B, not A."""
        from src.services.folder_tree_service import render_folder_tree_filename
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        uid_b = str(uuid.uuid4())
        # A second member with a DIFFERENT surname (Kowalski) at couple_index=0 (A)
        # to make total_couples=2 meaningful — ensures [B] width is still 1 char.
        uid_a = str(uuid.uuid4())

        folder_b = _write_person(root_path, uid_b, "Henryk Wiśniewski",
                                 last_name="Wiśniewski", sex="Mezczyzna")
        folder_a = _write_person(root_path, uid_a, "Jan Kowalski",
                                 last_name="Kowalski", sex="Mezczyzna")
        _add_to_cache(fs, uid_b, "Henryk Wiśniewski", folder_b)
        _add_to_cache(fs, uid_a, "Jan Kowalski", folder_a)

        # uid_b: Drzewo couple_index=1 (B), total=2 — only Wiśniewski surname
        member_b = _make_member(uid_b, generation=2, couple_index=1,
                                total_couples=2, gender="M",
                                full_name="Henryk Wiśniewski", location=str(folder_b))
        # uid_a: Drzewo couple_index=0 (A), different surname Kowalski
        member_a = _make_member(uid_a, generation=2, couple_index=0,
                                total_couples=2, gender="M",
                                full_name="Jan Kowalski", location=str(folder_a))

        svc = LineageService(fs)
        # member_b (Wiśniewski) is couple B; member_a (Kowalski) is couple A
        # Wiśniewski group has NO couple-A entry — only member_b at couple B
        lineages, log = svc.compute_lineages([member_b, member_a])

        assert "Wiśniewski" in lineages, (
            "Wiśniewski group must exist even with no couple-A member in this group"
        )
        assert "Kowalski" in lineages

        wisnicki_members = lineages["Wiśniewski"]
        assert len(wisnicki_members) == 1, "Only Henryk should be in Wiśniewski group"

        out_member = wisnicki_members[0]
        assert out_member.uid == uid_b
        assert out_member.couple_index == 1, (
            f"Expected couple_index=1 (B), got {out_member.couple_index} "
            "— couple letter must NOT be reindexed"
        )

        # Verify the encoded filename contains B, not A
        filename = render_folder_tree_filename(out_member)
        assert "[B]" in filename, (
            f"Expected [B] in filename '{filename}' — global couple letter must be preserved"
        )
        assert "[A]" not in filename, (
            f"[A] must NOT appear in filename '{filename}' — no reindexing allowed"
        )


# ---------------------------------------------------------------------------
# Test 9 — All spouses appear in the correct surname group
# ---------------------------------------------------------------------------

class TestLineageAllSpousesPresent:
    """D-1=A: all spouses appear in groups where their surname qualifies them."""

    def test_spouse_with_matching_surname_appears_in_group(self, tmp_root):
        """A gen-0 spouse whose surname matches a group is included."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        root_uid = str(uuid.uuid4())
        spouse_uid = str(uuid.uuid4())

        root_folder = _write_person(root_path, root_uid, "Jan Mankin",
                                    last_name="Mankin")
        spouse_folder = _write_person(root_path, spouse_uid, "Maria Mankin",
                                      last_name="Mankin",
                                      maiden_name="Pastryk",
                                      has_maiden_name=True,
                                      sex="Kobieta")
        _add_to_cache(fs, root_uid, "Jan Mankin", root_folder)
        _add_to_cache(fs, spouse_uid, "Maria Mankin", spouse_folder)

        # root: gen=0 role=self; surname=Mankin -> goes into Mankin
        m_root = _make_member(root_uid, generation=0, couple_index=0,
                              total_couples=1, gender="M",
                              full_name="Jan Mankin", location=str(root_folder),
                              role="self")
        # spouse: gen=0 role=spouse; has_maiden=True -> surname=Pastryk -> goes into Pastryk
        m_spouse = _make_member(spouse_uid, generation=0, couple_index=0,
                                total_couples=1, gender="F",
                                full_name="Maria Mankin", location=str(spouse_folder),
                                role="spouse")

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages([m_root, m_spouse])

        # Root's last_name=Mankin -> Mankin group
        assert "Mankin" in lineages
        mankin_uids = [m.uid for m in lineages["Mankin"]]
        assert root_uid in mankin_uids

        # Spouse has has_maiden=True, maiden_name=Pastryk -> Pastryk group
        assert "Pastryk" in lineages
        pastryk_uids = [m.uid for m in lineages["Pastryk"]]
        assert spouse_uid in pastryk_uids


# ---------------------------------------------------------------------------
# Test 10 — Full descendant subtree members present
# ---------------------------------------------------------------------------

class TestLineageFullDescendantSubtreePresent:
    """D-2=B: all descendant generations appear in the group, not just direct children."""

    def test_grandchild_member_appears_in_lineage_group(self, tmp_root):
        """Grandchild at gen=-2 is included in the appropriate surname group."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        root_uid = str(uuid.uuid4())
        child_uid = str(uuid.uuid4())
        grandchild_uid = str(uuid.uuid4())

        root_folder = _write_person(root_path, root_uid, "Jan Mankin",
                                    last_name="Mankin")
        child_folder = _write_person(root_path, child_uid, "Piotr Mankin",
                                     last_name="Mankin")
        grandchild_folder = _write_person(root_path, grandchild_uid, "Anna Mankin",
                                          last_name="Mankin", sex="Kobieta")
        _add_to_cache(fs, root_uid, "Jan Mankin", root_folder)
        _add_to_cache(fs, child_uid, "Piotr Mankin", child_folder)
        _add_to_cache(fs, grandchild_uid, "Anna Mankin", grandchild_folder)

        m_root = _make_member(root_uid, 0, 0, 1, "M", "Jan Mankin",
                              str(root_folder), role="self")
        m_child = _make_member(child_uid, -1, 0, 1, "M", "Piotr Mankin",
                               str(child_folder), role="descendant")
        m_grandchild = _make_member(grandchild_uid, -2, 0, 1, "F", "Anna Mankin",
                                    str(grandchild_folder), role="descendant")

        svc = LineageService(fs)
        lineages, log = svc.compute_lineages([m_root, m_child, m_grandchild])

        assert "Mankin" in lineages
        uids = [m.uid for m in lineages["Mankin"]]
        assert root_uid in uids
        assert child_uid in uids
        assert grandchild_uid in uids, (
            "Grandchild (gen=-2) must appear in lineage group (D-2=B: full subtree)"
        )


# ---------------------------------------------------------------------------
# Test 11 — member with None surname excluded; log entry
# ---------------------------------------------------------------------------

class TestLineageMemberNoneSurnameExcluded:

    def test_member_with_nieznane_last_name_excluded(self, tmp_root):
        """A member with '(nieznane)' last_name is excluded; log entry present."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        uid = str(uuid.uuid4())
        folder = _write_person(root_path, uid, "Unknown Person",
                               last_name="(nieznane)",
                               has_maiden_name=False)
        _add_to_cache(fs, uid, "Unknown Person", folder)

        member = _make_member(uid, generation=1, couple_index=0,
                              total_couples=1, gender="M",
                              full_name="Unknown Person", location=str(folder))
        svc = LineageService(fs)
        lineages, log = svc.compute_lineages([member])

        assert lineages == {}
        assert len(log) > 0


# ---------------------------------------------------------------------------
# Test 12 — multiple members same surname -> single group list
# ---------------------------------------------------------------------------

class TestLineageMultipleMembersSameSurname:

    def test_three_members_same_surname_in_single_group(self, tmp_root):
        """Three members with same surname all end up in one group."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        uids = [str(uuid.uuid4()) for _ in range(3)]
        folders = []
        for i, uid in enumerate(uids):
            name = f"Person{i} Mankin"
            folder = _write_person(root_path, uid, name, last_name="Mankin")
            _add_to_cache(fs, uid, name, folder)
            folders.append(folder)

        members = [
            _make_member(uids[0], 0, 0, 1, "M", "Person0 Mankin",
                         str(folders[0]), role="self"),
            _make_member(uids[1], -1, 0, 1, "M", "Person1 Mankin",
                         str(folders[1]), role="descendant"),
            _make_member(uids[2], 1, 0, 1, "M", "Person2 Mankin",
                         str(folders[2]), role="ancestor"),
        ]
        svc = LineageService(fs)
        lineages, log = svc.compute_lineages(members)

        assert "Mankin" in lineages
        assert len(lineages) == 1
        assert len(lineages["Mankin"]) == 3


# ---------------------------------------------------------------------------
# Test 13 — maiden-name rule: has_maiden_name=True -> maiden used as grouping key
# ---------------------------------------------------------------------------

class TestLineageMaidenNameGroupingRule:

    def test_has_maiden_name_true_uses_maiden_name_as_grouping_key(self, tmp_root):
        """Member with has_maiden_name=True goes into maiden_name group, not last_name."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        uid = str(uuid.uuid4())
        folder = _write_person(root_path, uid, "Anna Kowalska",
                               last_name="Kowalska",
                               maiden_name="Nowak",
                               has_maiden_name=True,
                               sex="Kobieta")
        _add_to_cache(fs, uid, "Anna Kowalska", folder)

        member = _make_member(uid, generation=1, couple_index=0,
                              total_couples=1, gender="F",
                              full_name="Anna Kowalska", location=str(folder))
        svc = LineageService(fs)
        lineages, log = svc.compute_lineages([member])

        assert "Nowak" in lineages, "maiden_name must be used as group key"
        assert "Kowalska" not in lineages, "last_name must NOT be used when has_maiden_name=True"


# ---------------------------------------------------------------------------
# Test 14 — Diacritics in surname preserved
# ---------------------------------------------------------------------------

class TestLineageDiacriticsPreservedInGroupingKey:

    def test_diacritic_surname_preserved_as_grouping_key(self, tmp_root):
        """Surname with Polish diacritics is preserved as-is in the grouping key."""
        from src.services.lineage_service import LineageService

        root_path, fs = tmp_root

        uid = str(uuid.uuid4())
        folder = _write_person(root_path, uid, "Jan Łukasiewicz",
                               last_name="Łukasiewicz")
        _add_to_cache(fs, uid, "Jan Łukasiewicz", folder)

        member = _make_member(uid, generation=1, couple_index=0,
                              total_couples=1, gender="M",
                              full_name="Jan Łukasiewicz", location=str(folder))
        svc = LineageService(fs)
        lineages, log = svc.compute_lineages([member])

        assert "Łukasiewicz" in lineages, (
            "Polish diacritics must be preserved in surname grouping key"
        )
