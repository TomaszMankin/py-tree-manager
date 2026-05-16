"""Folder tree membership computation and filename rendering.

Implements the hourglass selection algorithm and filename encoding
(multi-bracket couple-letter system).

Public API:
    FolderTreeMember -- data class for one person in the folder tree
    FolderTreeService    -- computes membership via hourglass BFS
    render_folder_tree_filename -- encodes (FolderTreeMember) -> filename string
    _couple_code         -- helper: base-26 couple letter with pre-detected width
"""

from __future__ import annotations

import math
import os
from collections import deque
from typing import Dict, List, Optional, Tuple

from src.services.file_service import FileService
from src.wrappers.person_data_wrapper import PersonDataProperty, PersonDataWrapper


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

class FolderTreeMember:
    """Resolved membership entry — one person in one rebuilt Drzewo."""

    def __init__(
        self,
        uid: str,
        generation: int,
        couple_index: int,
        total_couples_in_generation: int,
        role: str,
        gender: str,
        full_name: str,
        location: str,
        paired_descendant_uid: Optional[str] = None,
    ):
        self.uid = uid
        self.generation = generation
        # couple_index: 0-based index of the couple within this generation.
        # Ignored (and couple-code omitted) at gen == 0.
        self.couple_index = couple_index
        # total_couples_in_generation: total couple count for the generation.
        # Used to determine per-generation couple-code width.
        self.total_couples_in_generation = total_couples_in_generation
        # role: 'self' | 'spouse' | 'ancestor' | 'descendant' | 'descendant_spouse'
        self.role = role
        # gender: 'M' | 'F' | '' (unknown)
        self.gender = gender
        self.full_name = full_name
        self.location = location
        # paired_descendant_uid: for descendant_spouse only — the descendant they married
        self.paired_descendant_uid = paired_descendant_uid


# ---------------------------------------------------------------------------
# Sex mapping
# ---------------------------------------------------------------------------

def _sex_to_gender(sex: str) -> str:
    """Map me.json sex value to single-letter gender token.

    Tolerates both 'Mężczyzna' (with diacritic, from app dropdown) and
    'Mezczyzna' (without, used in test fixtures and create_test_tree.py).
    """
    if not sex:
        return ''
    s = sex.strip()
    # Male forms
    if s in ('Mężczyzna', 'Mezczyzna'):
        return 'M'
    # Female forms
    if s in ('Kobieta',):
        return 'F'
    return ''


# ---------------------------------------------------------------------------
# Couple-code helper
# ---------------------------------------------------------------------------

def _couple_code(couple_index: int, total_couples: int) -> str:
    """Return the couple letter(s) for a given couple index.

    Width is determined per-generation: ceil(log_26(total_couples)), minimum 1.

    Examples:
        _couple_code(0, 5)   -> 'A'   (5 couples -> width 1)
        _couple_code(0, 26)  -> 'A'   (26 couples -> width 1; log_26(26)=1)
        _couple_code(0, 27)  -> 'AA'  (27 couples -> width 2)
        _couple_code(26, 27) -> 'BA'  (index 26, width 2)
        _couple_code(0, 676) -> 'AA'  (676 couples -> width 2; log_26(676)=2)
        _couple_code(0, 677) -> 'AAA' (677 couples -> width 3)

    Encoding: most-significant digit first, A=0, B=1, ..., Z=25 (base-26).
    Boundary handling:
        - total_couples <= 0 treated as 1 (defensive).
        - log_26(N) via math.log with explicit boundary checks at 26 and 676
          to avoid floating-point rounding errors at exact powers.
    """
    n = max(1, total_couples)

    # Determine width with exact boundary handling to avoid float imprecision.
    # width = smallest w such that 26^w >= n
    if n <= 26:
        width = 1
    elif n <= 676:      # 26^2 = 676
        width = 2
    elif n <= 17576:    # 26^3 = 17576
        width = 3
    elif n <= 456976:   # 26^4 = 456976
        width = 4
    else:
        # General case for very large trees (unrealistic on human genealogy)
        width = math.ceil(math.log(n) / math.log(26))

    # Base-26 encode couple_index with the computed width, most-significant first.
    digits: List[str] = []
    idx = couple_index
    for _ in range(width):
        digits.append(chr(ord('A') + (idx % 26)))
        idx //= 26
    digits.reverse()
    return ''.join(digits)


# ---------------------------------------------------------------------------
# GenerationalTreeService
# ---------------------------------------------------------------------------

class FolderTreeService:
    """Computes hourglass membership for GenerationalTree (revised 2026-05-08)."""

    def __init__(self, file_service: FileService):
        self._fs = file_service
        # Local read-cache: uid -> PersonDataWrapper (to avoid re-reading me.json)
        self._person_cache: Dict[str, Optional[PersonDataWrapper]] = {}

    # -------------------------------------------------------------------------
    # Public entry point
    # -------------------------------------------------------------------------

    def compute_membership(
        self, root_uuid: str
    ) -> Tuple[List[FolderTreeMember], List[str]]:
        """Compute the hourglass membership for the given root person.

        Returns:
            (members, build_log_messages)

        Algorithm overview (revised 2026-05-08):
        - Gen 0: root + spouses.  No couple-code (only one couple at gen 0).
        - Ancestors (gen >= +1): paternal-first DFS.  Couples are assigned
          sequential indices (A, B, C, ...) in DFS traversal order.
          Per-generation width is pre-detected after all couples are discovered.
        - Descendants (gen <= -1): birth-order DFS through me.json children
          arrays.  Same sequential letter assignment per generation.

        build_log_messages lists anomalies (cycle detection, gender fallback,
        missing me.json, etc.).
        """
        self._person_cache = {}
        log: List[str] = []

        # ── Gen 0: root + spouses ──────────────────────────────────────────
        root_data = self._read_person(root_uuid, log)
        if root_data is None:
            log.append(f"ERROR: root person {root_uuid} not found in cache or me.json unreadable.")
            return [], log

        root_gender = _sex_to_gender(root_data.get_sex() or '')
        root_name = root_data.get_full_name()
        root_location = root_data.get_location() or self._location_from_cache(root_uuid)

        # Gen-0 couple_index and total are unused for filename (no couple-code at gen 0)
        gen0_members: Dict[str, FolderTreeMember] = {}
        gen0_members[root_uuid] = FolderTreeMember(
            uid=root_uuid,
            generation=0,
            couple_index=0,
            total_couples_in_generation=1,
            role='self',
            gender=root_gender,
            full_name=root_name,
            location=root_location,
            paired_descendant_uid=None,
        )

        for spouse_uid in root_data.get_spouse_ids():
            if not spouse_uid or spouse_uid in gen0_members:
                continue
            spouse_data = self._read_person(spouse_uid, log)
            if spouse_data is None:
                continue
            gen0_members[spouse_uid] = FolderTreeMember(
                uid=spouse_uid,
                generation=0,
                couple_index=0,
                total_couples_in_generation=1,
                role='spouse',
                gender=_sex_to_gender(spouse_data.get_sex() or ''),
                full_name=spouse_data.get_full_name(),
                location=spouse_data.get_location() or self._location_from_cache(spouse_uid),
                paired_descendant_uid=None,
            )

        # ── Ancestor DFS (upward) — couple-letter assignment ─────────────
        # We need a two-pass approach:
        # Pass 1: DFS to discover all ancestor couples in order, recording
        #         (uid, generation, couple_index_within_gen) per couple.
        # Pass 2: after each generation is fully discovered, compute width
        #         and create FolderTreeMember objects.

        # Couples are pairs: each blood ancestor + their spouse (if present)
        # counts as one couple.  We walk paternal-first (father edges before
        # mother edges within each person's parent list).

        # ancestor_couples_by_gen: gen -> list of (blood_uid, spouse_uid_or_None)
        # in DFS order.
        ancestor_couples_by_gen: Dict[int, List[Tuple[str, Optional[str]]]] = {}
        ancestor_couple_uid_set: set = set()  # all UIDs assigned to a couple slot

        # DFS stack entries: (person_uid, gen_of_parents, branch_prefix_for_logging)
        # We replicate the BFS-style "paternal-first" ordering by ensuring that
        # within each person's parent list, we process father (M gender) before
        # mother (F gender), matching the paternal-first traversal rule.
        ancestor_visited_dfs: set = set()
        # Stack: process in DFS order; push items so that father is processed first.
        # Use a list as stack (LIFO) but push mother before father so father pops first.
        #
        # Spouse-seeded ancestor DFS (2026-05-09):
        # Push spouse(s) FIRST so root pops first (LIFO).  Root's parents register
        # as couple A at gen+1; each spouse's parents register as couple B, C, … in
        # the order spouses are pushed (last-pushed spouse pops next after root's
        # entire subtree is exhausted).
        dfs_stack: List[Tuple[str, int]] = []
        ancestor_visited_dfs.add(root_uuid)

        # Push spouses FIRST so root pops first via LIFO.
        for spouse_uid in root_data.get_spouse_ids():
            if spouse_uid and spouse_uid not in ancestor_visited_dfs:
                dfs_stack.append((spouse_uid, 1))
                ancestor_visited_dfs.add(spouse_uid)

        # Push root LAST so it pops first; root's parents form couple A at gen+1.
        dfs_stack.append((root_uuid, 1))

        while dfs_stack:
            person_uid, gen = dfs_stack.pop()

            person_data = self._read_person(person_uid, log)
            if person_data is None:
                continue

            parent_ids = person_data.get_parent_ids()
            if not parent_ids:
                continue

            # Classify parents by gender to determine paternal-first order.
            # Father (M) before mother (F); unknowns fall to list position.
            parents_with_edge: List[Tuple[str, str]] = []  # (uid, 'F' or 'M' edge)
            for i, pid in enumerate(parent_ids):
                if not pid:
                    continue
                p_data = self._read_person(pid, log)
                p_gender = _sex_to_gender(p_data.get_sex() or '') if p_data else ''
                if p_gender == 'M':
                    edge = 'F'   # male parent -> father edge
                elif p_gender == 'F':
                    edge = 'M'   # female parent -> mother edge
                else:
                    edge = 'F' if i == 0 else 'M'
                    log.append(
                        f"GENDER_FALLBACK: {pid} has unknown sex; "
                        f"assigned edge '{edge}' from list position {i}."
                    )
                parents_with_edge.append((pid, edge))

            # Sort: father edge ('F') before mother edge ('M') — paternal first
            parents_sorted = sorted(parents_with_edge, key=lambda x: x[1])

            # Each pair of (father, mother) within this person forms ONE couple
            # at generation `gen`.  A single parent with no partner still forms
            # a "couple" (singleton).  Pair them up: index 0 is father, index 1
            # is mother.
            father_uid = next((u for u, e in parents_sorted if e == 'F'), None)
            mother_uid = next((u for u, e in parents_sorted if e == 'M'), None)

            # Register as one couple if not already seen
            if father_uid and father_uid not in ancestor_couple_uid_set:
                if gen not in ancestor_couples_by_gen:
                    ancestor_couples_by_gen[gen] = []
                couple = (father_uid, mother_uid)
                ancestor_couples_by_gen[gen].append(couple)
                ancestor_couple_uid_set.add(father_uid)
                if mother_uid:
                    ancestor_couple_uid_set.add(mother_uid)
            elif mother_uid and mother_uid not in ancestor_couple_uid_set:
                # Only mother present (no father) — single-parent couple
                if gen not in ancestor_couples_by_gen:
                    ancestor_couples_by_gen[gen] = []
                couple = (mother_uid, None)
                ancestor_couples_by_gen[gen].append(couple)
                ancestor_couple_uid_set.add(mother_uid)

            # Push parents onto DFS stack (push mother first so father pops first)
            # Push in reverse paternal-first order so DFS processes father first
            for pid, _edge in reversed(parents_sorted):
                if pid not in ancestor_visited_dfs:
                    ancestor_visited_dfs.add(pid)
                    dfs_stack.append((pid, gen + 1))
                else:
                    log.append(
                        f"CYCLE detected at UUID {pid}; skipping to prevent infinite loop."
                    )

        # Now build FolderTreeMember objects for ancestors
        ancestor_members: Dict[str, FolderTreeMember] = {}
        for gen, couples in ancestor_couples_by_gen.items():
            total = len(couples)
            for couple_idx, (blood_uid, partner_uid) in enumerate(couples):
                if blood_uid and blood_uid not in ancestor_members:
                    b_data = self._read_person(blood_uid, log)
                    b_gender = _sex_to_gender(b_data.get_sex() or '') if b_data else ''
                    b_name = b_data.get_full_name() if b_data else blood_uid
                    b_location = (
                        (b_data.get_location() or self._location_from_cache(blood_uid))
                        if b_data else self._location_from_cache(blood_uid)
                    )
                    ancestor_members[blood_uid] = FolderTreeMember(
                        uid=blood_uid,
                        generation=gen,
                        couple_index=couple_idx,
                        total_couples_in_generation=total,
                        role='ancestor',
                        gender=b_gender,
                        full_name=b_name,
                        location=b_location,
                        paired_descendant_uid=None,
                    )
                if partner_uid and partner_uid not in ancestor_members:
                    p_data = self._read_person(partner_uid, log)
                    p_gender = _sex_to_gender(p_data.get_sex() or '') if p_data else ''
                    p_name = p_data.get_full_name() if p_data else partner_uid
                    p_location = (
                        (p_data.get_location() or self._location_from_cache(partner_uid))
                        if p_data else self._location_from_cache(partner_uid)
                    )
                    ancestor_members[partner_uid] = FolderTreeMember(
                        uid=partner_uid,
                        generation=gen,
                        couple_index=couple_idx,
                        total_couples_in_generation=total,
                        role='ancestor',
                        gender=p_gender,
                        full_name=p_name,
                        location=p_location,
                        paired_descendant_uid=None,
                    )

        # Cycle check: log any ancestor UIDs that would collide with gen-0 members
        for uid in ancestor_members:
            if uid in gen0_members:
                log.append(
                    f"CYCLE (ancestor): {uid} already in gen-0 members; "
                    f"gen-0 classification wins."
                )

        # ── Descendant DFS (downward) — couple-letter assignment ──────────
        # Same two-pass approach: collect couples per generation in birth-order
        # DFS, then assign letters.
        # descendant_couples_by_gen: gen -> list of (child_uid, spouse_uid_or_None)
        descendant_couples_by_gen: Dict[int, List[Tuple[str, Optional[str]]]] = {}
        descendant_couple_child_set: set = set()  # child UIDs already in a couple slot

        descendant_visited: set = {root_uuid}
        desc_dfs_stack: List[Tuple[str, int]] = []

        # Seed from root's children at gen -1
        for child_uid in root_data.get_children_ids():
            if not child_uid or child_uid in descendant_visited:
                continue
            descendant_visited.add(child_uid)
            if child_uid not in descendant_couple_child_set:
                if -1 not in descendant_couples_by_gen:
                    descendant_couples_by_gen[-1] = []
                child_data = self._read_person(child_uid, log)
                spouse_uids = child_data.get_spouse_ids() if child_data else []
                first_spouse = next(
                    (s for s in spouse_uids if s and s != root_uuid and s not in gen0_members),
                    None
                )
                descendant_couples_by_gen[-1].append((child_uid, first_spouse))
                descendant_couple_child_set.add(child_uid)
            desc_dfs_stack.append((child_uid, -2))

        while desc_dfs_stack:
            person_uid, next_gen = desc_dfs_stack.pop(0)  # BFS-like order for birth order
            person_data = self._read_person(person_uid, log)
            if person_data is None:
                continue

            for child_uid in person_data.get_children_ids():
                if not child_uid or child_uid in descendant_visited:
                    continue
                descendant_visited.add(child_uid)
                if child_uid not in descendant_couple_child_set:
                    if next_gen not in descendant_couples_by_gen:
                        descendant_couples_by_gen[next_gen] = []
                    child_data = self._read_person(child_uid, log)
                    spouse_uids = child_data.get_spouse_ids() if child_data else []
                    already_placed = gen0_members.keys() | ancestor_members.keys()
                    first_spouse = next(
                        (s for s in spouse_uids if s and s != root_uuid and s not in already_placed),
                        None
                    )
                    descendant_couples_by_gen[next_gen].append((child_uid, first_spouse))
                    descendant_couple_child_set.add(child_uid)
                desc_dfs_stack.append((child_uid, next_gen - 1))

        # Build FolderTreeMember objects for descendants
        descendant_members: Dict[str, FolderTreeMember] = {}
        for gen, couples in descendant_couples_by_gen.items():
            total = len(couples)
            for couple_idx, (child_uid, spouse_uid) in enumerate(couples):
                if child_uid and child_uid not in descendant_members:
                    c_data = self._read_person(child_uid, log)
                    c_gender = _sex_to_gender(c_data.get_sex() or '') if c_data else ''
                    c_name = c_data.get_full_name() if c_data else child_uid
                    c_location = (
                        (c_data.get_location() or self._location_from_cache(child_uid))
                        if c_data else self._location_from_cache(child_uid)
                    )
                    descendant_members[child_uid] = FolderTreeMember(
                        uid=child_uid,
                        generation=gen,
                        couple_index=couple_idx,
                        total_couples_in_generation=total,
                        role='descendant',
                        gender=c_gender,
                        full_name=c_name,
                        location=c_location,
                        paired_descendant_uid=None,
                    )
                if spouse_uid and spouse_uid not in descendant_members:
                    c_data = self._read_person(child_uid, log)
                    c_gender = _sex_to_gender(c_data.get_sex() or '') if c_data else ''
                    sp_data = self._read_person(spouse_uid, log)
                    sp_name = sp_data.get_full_name() if sp_data else spouse_uid
                    sp_location = (
                        (sp_data.get_location() or self._location_from_cache(spouse_uid))
                        if sp_data else self._location_from_cache(spouse_uid)
                    )
                    descendant_members[spouse_uid] = FolderTreeMember(
                        uid=spouse_uid,
                        generation=gen,
                        couple_index=couple_idx,
                        total_couples_in_generation=total,
                        role='descendant_spouse',
                        gender=c_gender,  # descendant-side gender (rule B)
                        full_name=sp_name,
                        location=sp_location,
                        paired_descendant_uid=child_uid,
                    )

        # Assemble final ordered list
        all_members: Dict[str, FolderTreeMember] = {}
        all_members.update(gen0_members)
        all_members.update(ancestor_members)
        all_members.update(descendant_members)

        return list(all_members.values()), log

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _read_person(self, uid: str, log: List[str]) -> Optional[PersonDataWrapper]:
        """Read and cache a person's me.json via the FileService cache.

        Returns None if the person is not in the cache or me.json is unreadable;
        logs a build warning in that case.
        """
        if uid in self._person_cache:
            return self._person_cache[uid]

        cached_people = self._fs.settings.get_cached_people()
        if uid not in cached_people:
            log.append(f"MISSING: {uid} not in cached_people — skipped.")
            self._person_cache[uid] = None
            return None

        location = cached_people[uid].get(PersonDataProperty.LOCATION.value, '')
        me_json_path = os.path.join(location, 'me.json')
        try:
            data = self._fs.read_me_file(me_json_path)
            wrapper = PersonDataWrapper(data)
            self._person_cache[uid] = wrapper
            return wrapper
        except Exception as exc:
            log.append(f"UNREADABLE: me.json for {uid} at {me_json_path} — {exc}")
            self._person_cache[uid] = None
            return None

    def _location_from_cache(self, uid: str) -> str:
        """Return the cached folder location for a person, or empty string."""
        cached = self._fs.settings.get_cached_people()
        entry = cached.get(uid, {})
        return entry.get(PersonDataProperty.LOCATION.value, '')


# ---------------------------------------------------------------------------
# Filename renderer
# ---------------------------------------------------------------------------

def render_folder_tree_filename(member: FolderTreeMember) -> str:
    """Encode a FolderTreeMember into a Drzewo shortcut filename.

    Format (sign-flipped second bracket, revised 2026-05-09):

    For gen == 0 (root self / spouse):
        [NN][0][gender] FullName.lnk
        e.g. [50][0][F] Jadwiga Mankin.lnk
             [50][0][M] Zbigniew Mankin.lnk
        No couple-code bracket — only one couple at gen 0.

    For gen != 0 (ancestors and descendants):
        [NN][display][couple-code][gender] FullName.lnk
        where display = -gen (sign-flipped; negative values keep '-', non-negative bare)
        e.g. [51][-1][A][M] Adam Mankin.lnk          (gen=+1 ancestor)
             [49][1][A][F] Katarzyna Szafran zd. Mankin.lnk  (gen=-1 descendant)
             [48][2][AB][F] Anna.lnk                 (gen=-2, >26 couples)

    Sign-flip rationale: Father reads positive numbers as "older = higher";
    ancestors at gen+1 display as -1 so that the visible number grows negative
    with depth, matching his mental model. NN sort key is unchanged (still gen+50)
    so Windows Explorer physical sort order is identical.

    No -ST suffix.  By-marriage spouses are encoded identically to blood
    relatives — the shared couple-code letter provides the pairing context.

    Gender defaults to 'M' when unknown (defensive fallback).

    Boundary cases:
        internal gen=-2: [48][2][couple][gender]
        internal gen=-1: [49][1][couple][gender]
        internal gen= 0: [50][0][gender]
        internal gen=+1: [51][-1][couple][gender]
        internal gen=+2: [52][-2][couple][gender]
    """
    gen = member.generation
    nn = f"{gen + 50:02d}"
    gender_token = member.gender if member.gender else 'M'

    # display = -gen (sign flip); bare number (no '+' prefix).
    display = -gen
    gs = f"{display}"   # negative values keep '-'; non-negative values are bare (0, 1, 2, …)

    if gen == 0:
        return f"[{nn}][{gs}][{gender_token}] {member.full_name}.lnk"
    else:
        code = _couple_code(member.couple_index, member.total_couples_in_generation)
        return f"[{nn}][{gs}][{code}][{gender_token}] {member.full_name}.lnk"
