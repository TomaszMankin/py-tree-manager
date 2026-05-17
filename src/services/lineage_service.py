"""Lineages (family branches) — surname-grouped subfolder layout.

Public API:
    extract_lineage_surname       -- module helper; lineage surname for one person
    encode_lineage_folder_name    -- surname -> filesystem-safe folder name
    encode_person_lnk_name        -- person display name -> .lnk filename
    LineageMembers                -- dataclass: surname + contributor UID + member UID list
    LineageService                -- compute_lineages(root_uuid) -> Dict[str, LineageMembers]
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from src.services.file_service import FileService
from src.wrappers.person_data_wrapper import PersonDataProperty, PersonDataWrapper


# ---------------------------------------------------------------------------
# Module-level helpers (encoding)
# ---------------------------------------------------------------------------

_FORBIDDEN: Set[str] = set('\\/:*?"<>|')


def extract_lineage_surname(person_data: PersonDataWrapper) -> Optional[str]:
    """Return the lineage (family-branch) surname for a person, or None if unknown.

    Rule:
      - has_maiden_name == True  -> maiden_name (the family the person was born into).
      - else                     -> last_name.
      - "(nieznane)" sentinel and empty/whitespace-only strings -> None.

    other_last_names and other_maiden_names (the ";" suffixed alternates) are
    deliberately ignored — alternate display forms, not independent surnames.
    """
    if person_data.get_has_maiden_name():
        candidate = (person_data.get_maiden_name() or "").strip()
    else:
        candidate = (person_data.get_last_name() or "").strip()

    if not candidate or candidate == PersonDataWrapper.UNKNOWN:
        return None
    return candidate


def encode_lineage_folder_name(surname: str) -> str:
    """Surname -> filesystem-safe subfolder name under Rody/. Polish diacritics kept."""
    s = surname.strip()
    return "".join(("_" if c in _FORBIDDEN else c) for c in s)


def encode_person_lnk_name(person_name: str) -> str:
    """Person display name -> .lnk filename. Polish diacritics kept."""
    s = (person_name or "").strip()
    return "".join(("_" if c in _FORBIDDEN else c) for c in s) + ".lnk"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class LineageMembers:
    """All members belonging to one lineage subfolder.

    member_uids is ordered: universal members first (root + full descendant
    subtree + their spouses), then contributing parent + their spouse, then
    ancestors in walk order. Duplicates suppressed via insertion-order dict.
    """

    surname: str
    contributor_uid: str
    member_uids: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class LineageService:
    """Compute lineage surname set with full membership (R1-R4).

    Enumeration order (deterministic):
      1. root.parents[0]   (typically father)
      2. root.parents[1]   (typically mother)
      3. for each spouse in root.spouses (me.json list order):
             spouse.parents[0]
             spouse.parents[1]

    On collision (same surname from a later contributor), the FIRST entry
    wins; the later contributor's UID is dropped and a log entry is appended.
    """

    def __init__(self, file_service: FileService):
        self._fs = file_service
        self._person_cache: Dict[str, Optional[PersonDataWrapper]] = {}

    def compute_lineages(
        self, root_uuid: str
    ) -> Tuple[Dict[str, LineageMembers], List[str]]:
        """Return ({surname -> LineageMembers}, build_log).

        Keys are distinct lineage surnames. Values hold the contributor UID
        and the ordered, deduplicated member UID list (universal + R3 + R4 walk).
        The build_log contains informational / anomaly entries only.
        """
        self._person_cache = {}
        log: List[str] = []
        lineages: Dict[str, LineageMembers] = {}

        root = self._read_person(root_uuid, log)
        if root is None:
            log.append(f"LINEAGE: root uid={root_uuid} unreadable.")
            return lineages, log

        # --- Step 1: universal members (root + full descendant subtree) ---
        universal: List[str] = []
        universal_seen: Set[str] = set()

        def universal_add(uid: str) -> None:
            if uid and uid not in universal_seen:
                universal.append(uid)
                universal_seen.add(uid)

        def walk_descendants(person_uid: str) -> None:
            # Cycle-safe: already-added UID is not re-walked.
            if person_uid in universal_seen:
                return
            person = self._read_person(person_uid, log)
            if person is None:
                log.append(
                    f"LINEAGE: descendant uid={person_uid} not in cache; "
                    "subtree below skipped."
                )
                return
            uid = person.get_unique_identifier() or person_uid
            universal_add(uid)
            for sp in person.get_spouse_ids():
                universal_add(sp)       # spouses as leaves; not walked further
            for ch in person.get_children_ids():
                walk_descendants(ch)

        walk_descendants(root.get_unique_identifier() or root_uuid)

        # --- Step 2: enumerate contributing parents (deterministic order) ---
        contributors: List[Tuple[str, str]] = []
        for i, p_uid in enumerate(root.get_parent_ids()):
            contributors.append((p_uid, f"root.parent[{i}]"))
        for j, sp_uid in enumerate(root.get_spouse_ids()):
            spouse = self._read_person(sp_uid, log)
            if spouse is None:
                log.append(
                    f"LINEAGE: spouse[{j}] uid={sp_uid} not readable; "
                    "their parents skipped."
                )
                continue
            for i, sp_p_uid in enumerate(spouse.get_parent_ids()):
                contributors.append((sp_p_uid, f"spouse[{j}].parent[{i}]"))

        # --- Step 3: per-contributor, build the lineage member list ---
        for contributor_uid, role in contributors:
            if not contributor_uid:
                continue
            contributor = self._read_person(contributor_uid, log)
            if contributor is None:
                log.append(
                    f"LINEAGE: {role} (uid={contributor_uid}) not in cache; skipped."
                )
                continue

            lineage_surname = extract_lineage_surname(contributor)
            if lineage_surname is None:
                log.append(
                    f"LINEAGE: {role} (uid={contributor_uid}) has no lineage surname; skipped."
                )
                continue

            # Collision: first contributor wins
            if lineage_surname in lineages:
                log.append(
                    f"LINEAGE: surname '{lineage_surname}' already contributed by earlier slot; "
                    f"{role} (uid={contributor_uid}) does not create a new folder."
                )
                continue

            members: List[str] = []
            seen: Set[str] = set()

            def add(uid: str) -> None:
                if uid and uid not in seen:
                    members.append(uid)
                    seen.add(uid)

            # R1+R2: universal members in fixed order
            for u in universal:
                add(u)

            # R3: contributing parent + their spouse
            add(contributor_uid)
            for sp_of_contrib in contributor.get_spouse_ids():
                add(sp_of_contrib)

            # R4: ancestor walk — matching-surname ancestors only
            _walk_lineage_ancestors(
                contributor, lineage_surname, add, log, self._read_person
            )

            lineages[lineage_surname] = LineageMembers(
                surname=lineage_surname,
                contributor_uid=contributor_uid,
                member_uids=members,
            )

        return lineages, log

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _read_person(
        self, uid: str, log: List[str]
    ) -> Optional[PersonDataWrapper]:
        """Read and cache a person's me.json via the FileService cache.

        Returns None if the person is not in the cache or me.json is unreadable.
        Warning is NOT appended here — callers append context-specific messages.
        """
        if uid in self._person_cache:
            return self._person_cache[uid]

        cached_people = self._fs.settings.get_cached_people()
        if uid not in cached_people:
            self._person_cache[uid] = None
            return None

        location = cached_people[uid].get(PersonDataProperty.LOCATION.value, "")
        me_json_path = os.path.join(location, "me.json")
        try:
            data = self._fs.read_me_file(me_json_path)
            wrapper = PersonDataWrapper(data)
            self._person_cache[uid] = wrapper
            return wrapper
        except Exception as exc:
            log.append(
                f"LINEAGE: me.json for {uid} at {me_json_path} unreadable — {exc}"
            )
            self._person_cache[uid] = None
            return None


# ---------------------------------------------------------------------------
# Module-level ancestor walk (R4)
# ---------------------------------------------------------------------------

def _walk_lineage_ancestors(
    start_person: PersonDataWrapper,
    lineage_surname: str,
    add,
    log: List[str],
    read_person,
) -> None:
    """BFS through start_person's parents. Include only ancestors whose
    extract_lineage_surname matches lineage_surname. Each matching ancestor's
    spouse is included as a leaf (no further walk through them). Branches
    whose surname diverges stop immediately.
    """
    stack = list(start_person.get_parent_ids())
    visited: Set[str] = set()
    while stack:
        anc_uid = stack.pop(0)
        if not anc_uid or anc_uid in visited:
            continue
        visited.add(anc_uid)
        anc = read_person(anc_uid, log)
        if anc is None:
            log.append(
                f"LINEAGE: ancestor uid={anc_uid} not readable; branch stopped."
            )
            continue
        anc_surname = extract_lineage_surname(anc)
        if anc_surname != lineage_surname:
            continue  # branch terminates here
        add(anc_uid)
        # Spouse-leaf: include but do NOT walk further
        for sp_uid in anc.get_spouse_ids():
            add(sp_uid)
        # Continue walking this ancestor's parents
        for pp_uid in anc.get_parent_ids():
            stack.append(pp_uid)
