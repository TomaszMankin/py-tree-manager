"""Lineages (family branches) — surname-derived flat shortcut directory.

Public API:
    extract_lineage_surname     -- module helper; returns the lineage surname for one person
    LineageService             -- compute_lineages(root_uuid) returns ({surname -> uid}, log)
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from src.services.file_service import FileService
from src.wrappers.person_data_wrapper import PersonDataProperty, PersonDataWrapper


def extract_lineage_surname(person_data: PersonDataWrapper) -> Optional[str]:
    """Return the lineage (family-branch) surname for a person, or None if unknown.

    Rule:
      - has_maiden_name == True  -> maiden_name (the family the person was born into).
      - else                     -> last_name.
      - "(nieznane)" sentinel and empty/whitespace-only strings -> None.

    other_last_names and other_maiden_names (the ";" suffixed alternates) are
    deliberately ignored — they are alternate display forms of the same family
    identity, not independent surnames.
    """
    if person_data.get_has_maiden_name():
        candidate = (person_data.get_maiden_name() or "").strip()
    else:
        candidate = (person_data.get_last_name() or "").strip()

    if not candidate or candidate == PersonDataWrapper.UNKNOWN:
        return None
    return candidate


class LineageService:
    """Compute lineage surname set.

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
    ) -> Tuple[Dict[str, str], List[str]]:
        """Return ({surname -> uid_of_first_contributor}, build_log).

        Keys are distinct surnames; values are the UUID of the first person
        encountered in the enumeration order that contributes that surname.
        The build_log contains informational / anomaly entries only.
        """
        self._person_cache = {}
        log: List[str] = []
        surnames: Dict[str, str] = {}  # surname -> person_uid

        root = self._read_person(root_uuid, log)
        if root is None:
            log.append(f"LINEAGE: root uid={root_uuid} unreadable.")
            return surnames, log

        def consider(uid: str, role_for_log: str) -> None:
            if not uid:
                return
            person = self._read_person(uid, log)
            if person is None:
                log.append(
                    f"LINEAGE: {role_for_log} (uid={uid}) not in cache; skipped."
                )
                return
            s = extract_lineage_surname(person)
            if s is None:
                log.append(
                    f"LINEAGE: {role_for_log} (uid={uid}) has no rod surname; skipped."
                )
                return
            if s in surnames:
                log.append(
                    f"LINEAGE: surname '{s}' already contributed by earlier slot; "
                    f"{role_for_log} (uid={uid}) does not add a shortcut."
                )
                return
            surnames[s] = uid

        # 1 + 2: root's parents (up to two, in parents_id list order)
        for i, parent_uid in enumerate(root.get_parent_ids()):
            consider(parent_uid, f"root.parent[{i}]")

        # 3: for each spouse, that spouse's parents (up to two per spouse)
        for j, spouse_uid in enumerate(root.get_spouse_ids()):
            spouse = self._read_person(spouse_uid, log)
            if spouse is None:
                log.append(
                    f"LINEAGE: spouse[{j}] uid={spouse_uid} not in cache; "
                    "their parents skipped."
                )
                continue
            for i, sp_parent_uid in enumerate(spouse.get_parent_ids()):
                consider(sp_parent_uid, f"spouse[{j}].parent[{i}]")

        return surnames, log

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _read_person(
        self, uid: str, log: List[str]
    ) -> Optional[PersonDataWrapper]:
        """Read and cache a person's me.json via the FileService cache.

        Returns None if the person is not in the cache or me.json is unreadable.
        A warning is NOT appended here — callers append context-specific messages.
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
