"""Lineages (family branches) — surname-grouped subfolder layout.

LineageService is an assignment-over-Drzewo-members layer.
compute_lineages() accepts List[FolderTreeMember] (already computed by
FolderTreeService.compute_membership) and groups members by surname.
Generation / couple / gender tokens are CARRIED THROUGH UNCHANGED from the
FolderTreeMember objects. The .lnk filename for each member is produced by
render_folder_tree_filename (the same Drzewo encoder, reused verbatim).
LineageService does NOT compute generation, couple index, or gender — it
consumes them from the Drzewo hourglass output.

Public API:
    extract_lineage_surname       -- module helper; lineage surname for one person
    encode_lineage_folder_name    -- surname -> filesystem-safe folder name
    LineageService                -- compute_lineages(members) -> Dict[str, List[FolderTreeMember]]
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Set, Tuple

from src.services.file_service import FileService
from src.services.folder_tree_service import FolderTreeMember
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


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class LineageService:
    """Assign Drzewo members into surname groups for Rody/ folder layout.

    Takes List[FolderTreeMember] (already-computed Drzewo output), groups members
    by surname via extract_lineage_surname, and carries generation / couple / gender
    tokens through UNCHANGED.

    .lnk filenames are produced by render_folder_tree_filename (the Drzewo encoder),
    consumed by tree_service.rebuild_lineage.

    Couple letters are Drzewo-GLOBAL: a member at couple B in Drzewo stays couple B
    in his surname folder, even if that folder contains no couple A. LineageService
    does NOT reindex couple letters per surname folder.
    """

    def __init__(self, file_service: FileService):
        self._fs = file_service
        self._person_cache: Dict[str, Optional[PersonDataWrapper]] = {}

    def compute_lineages(
        self, members: List[FolderTreeMember]
    ) -> Tuple[Dict[str, List[FolderTreeMember]], List[str]]:
        """Group Drzewo members into surname folders.

        Args:
            members: List[FolderTreeMember] as returned by
                     FolderTreeService.compute_membership. Generation, couple
                     index, and gender tokens are consumed verbatim — never
                     recomputed.

        Returns:
            ({surname -> List[FolderTreeMember]}, build_log_messages)

        Each member appears in exactly the surname group matching its
        extract_lineage_surname (read from the person's me.json). Members
        whose extract_lineage_surname returns None are excluded; a log entry
        is appended for each such exclusion.
        """
        self._person_cache = {}
        log: List[str] = []
        lineages: Dict[str, List[FolderTreeMember]] = {}

        for member in members:
            uid = member.uid
            person_data = self._read_person(uid, log)
            if person_data is None:
                log.append(
                    f"LINEAGE: member uid={uid} not readable from cache; skipped."
                )
                continue

            surname = extract_lineage_surname(person_data)
            if surname is None:
                log.append(
                    f"LINEAGE: member uid={uid} has no lineage surname; skipped."
                )
                continue

            if surname not in lineages:
                lineages[surname] = []
            lineages[surname].append(member)

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
