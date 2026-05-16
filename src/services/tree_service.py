from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from src.services.file_service import FileService
import shutil
import uuid
import os

from src.data_types.optional_date import OptionalDate
from src.wrappers.person_data_wrapper import PersonDataWrapper, PersonDataProperty
from src.helpers.shortcut_helper import ShortcutHelper

def throw_if_root_not_set(func):
    def wrapper(*args, **kwargs):
        self: TreeService = args[0]
        if not self.is_root_location_set():
            raise RuntimeError("Please set tree location first.")
        return func(*args, **kwargs)
    return wrapper

class TreeService():

    ME_JSON = "me.json"
    LNK = '.lnk'

    def __init__(self):

        self._file_service = FileService()

        if self._file_service.is_root_location_set():
            self._file_service.scan_drafts_location()
            self._file_service.scan_root_location()

        self.list_of_people = self._file_service.get_list_of_people()

    def set_root_location(self, root_location: str) -> None:
        self._file_service.set_root_folder(root_location)
        self._file_service.scan_root_location()

    def is_root_location_set(self) -> bool:
        return self._file_service.is_root_location_set()

    def get_people_folder(self) -> str:
        """Return the path to the 'Lista osób' folder inside the tree root."""
        import os
        return os.path.join(self._file_service._get_root_folder(), "Lista osób")

    @throw_if_root_not_set
    def save_person_draft(self, person_draft: PersonDataWrapper) -> None:
        id: str = person_draft.get_unique_identifier() # Should not be empty from the beginning
        if not id:
            raise ValueError("Given person has no unique_identifier.")

        draft_name = str(id) + ".json"
        target = self._file_service.get_poczekalnia_path() / draft_name
        self._file_service.write_me_file(target, person_draft)

    @throw_if_root_not_set
    def load_person_draft(self, path: str) -> Dict[str, Any]:
        return self._file_service.read_me_file(path)
    
    @throw_if_root_not_set
    def get_list_of_drafts(self) -> List[str]:
        self._file_service.scan_drafts_location()
        return self._file_service.saved_drafts_locations.copy()
    
    @throw_if_root_not_set
    def save_person_and_add_to_tree(self, person_data: PersonDataWrapper) -> None:

        if not person_data:
            raise ValueError("Person data can't be null.")
        
        self._validate_person_data(person_data)

        new_person_path = self._file_service.create_person_folder(person_data.get_person_name(), person_data)
        new_person_unique_identifier = person_data.get_unique_identifier()
        new_person_folder_name = person_data.get_person_name()

        self._add_children(new_person_path, new_person_unique_identifier, new_person_folder_name, person_data.get_children())
        self._add_parents(new_person_path, new_person_unique_identifier, new_person_folder_name, person_data.get_parents())
        self._add_spouses(new_person_path, new_person_unique_identifier, new_person_folder_name, person_data.get_spouses())
        self._add_siblings(new_person_path, new_person_unique_identifier, new_person_folder_name, person_data.get_siblings())
        # TODO TBC?

    @throw_if_root_not_set
    def update_person_in_tree(
        self,
        person_data: PersonDataWrapper,
        original_location: str,
        original_canonical_name: str,
        original_relationships: Dict[str, List[str]],
    ) -> None:
        """Save changes to an existing person already in the tree.

        Handles: relationship diffs (add/remove shortcuts + me.json sync),
        folder rename, path-reference updates across the tree, and me.json rewrite.

        Args:
            person_data: Updated person data collected from the form.
            original_location: Folder path as it was when the person was loaded.
            original_canonical_name: person_name field from the original me.json
                (used to detect renames and to find old shortcuts).
            original_relationships: Dict with keys 'parents', 'children', 'spouses',
                'siblings', each a list of folder paths from the original me.json.
        """
        if not person_data:
            raise ValueError("Person data can't be null.")
        self._validate_person_data(person_data)

        new_canonical_name = person_data.get_full_name()
        name_changed = new_canonical_name != original_canonical_name

        orig_parents  = original_relationships.get('parents',  [])
        orig_children = original_relationships.get('children', [])
        orig_spouses  = original_relationships.get('spouses',  [])
        orig_siblings = original_relationships.get('siblings', [])

        new_parents  = person_data.get_parents()
        new_children = person_data.get_children()
        new_spouses  = person_data.get_spouses()
        new_siblings = person_data.get_siblings()

        orig_parents_set  = set(orig_parents)
        orig_children_set = set(orig_children)
        orig_spouses_set  = set(orig_spouses)
        orig_siblings_set = set(orig_siblings)

        removed_parents  = [p for p in orig_parents  if p not in set(new_parents)]
        removed_children = [p for p in orig_children if p not in set(new_children)]
        removed_spouses  = [p for p in orig_spouses  if p not in set(new_spouses)]
        removed_siblings = [p for p in orig_siblings if p not in set(new_siblings)]

        person_uid  = person_data.get_unique_identifier()
        person_name = person_data.get_person_name()

        # Step 1: remove dropped relationships (shortcuts + me.json sync)
        self._remove_children(original_location, person_uid, original_canonical_name, removed_children)
        self._remove_parents(original_location, person_uid, original_canonical_name, removed_parents)
        self._remove_spouses(original_location, person_uid, original_canonical_name, removed_spouses)
        self._remove_siblings(original_location, person_uid, original_canonical_name, removed_siblings)

        # Step 2: rename folder if name changed
        current_location = original_location
        if name_changed:
            current_location = self._file_service.rename_person_folder(original_location, new_canonical_name)
            person_data.set_location(current_location)
            # Delete old shortcuts (pointing to old folder, named after old canonical name)
            # from all remaining related people's folders
            remaining_parents  = [p for p in orig_parents  if p in set(new_parents)]
            remaining_children = [p for p in orig_children if p in set(new_children)]
            remaining_spouses  = [p for p in orig_spouses  if p in set(new_spouses)]
            remaining_siblings = [p for p in orig_siblings if p in set(new_siblings)]
            self._delete_old_shortcuts_after_rename(
                original_canonical_name,
                remaining_parents, remaining_children, remaining_spouses, remaining_siblings,
            )
            # Update path arrays in all related me.json files
            self._file_service.update_path_references(original_location, current_location)
        else:
            person_data.set_location(original_location)

        # Step 3: write updated me.json for this person
        me_file_path = os.path.join(current_location, self.ME_JSON)
        self._file_service.write_me_file(me_file_path, person_data)

        # Step 4: add new relationships (and recreate shortcuts for unchanged ones if renamed)
        if name_changed:
            # Pass all current relationships — _add_* will skip path-array duplicates
            # but always recreate shortcuts (needed to point to new folder / use new name)
            self._add_children(current_location, person_uid, person_name, new_children)
            self._add_parents(current_location, person_uid, person_name, new_parents)
            self._add_spouses(current_location, person_uid, person_name, new_spouses)
            self._add_siblings(current_location, person_uid, person_name, new_siblings)
        else:
            added_parents  = [p for p in new_parents  if p not in orig_parents_set]
            added_children = [p for p in new_children if p not in orig_children_set]
            added_spouses  = [p for p in new_spouses  if p not in orig_spouses_set]
            added_siblings = [p for p in new_siblings if p not in orig_siblings_set]
            self._add_children(current_location, person_uid, person_name, added_children)
            self._add_parents(current_location, person_uid, person_name, added_parents)
            self._add_spouses(current_location, person_uid, person_name, added_spouses)
            self._add_siblings(current_location, person_uid, person_name, added_siblings)

        self.list_of_people = self._file_service.get_list_of_people()

    def _delete_old_shortcuts_after_rename(
        self,
        old_person_name: str,
        remaining_parents: List[str],
        remaining_children: List[str],
        remaining_spouses: List[str],
        remaining_siblings: List[str],
    ) -> None:
        """Delete shortcuts named after old_person_name from all remaining related folders."""
        old_lnk = old_person_name + self.LNK

        def try_remove(path: str) -> None:
            try:
                ShortcutHelper.remove_shortcut(path)
            except (ValueError, RuntimeError):
                pass

        for parent_path in remaining_parents:
            try_remove(os.path.join(parent_path, ShortcutHelper.CHILDREN_FOLDER, old_lnk))
        for child_path in remaining_children:
            try_remove(os.path.join(child_path, ShortcutHelper.PARENTS_FOLDER, old_lnk))
        for spouse_path in remaining_spouses:
            try_remove(os.path.join(spouse_path, ShortcutHelper.SPOUSES_FOLDER, old_lnk))
        for sibling_path in remaining_siblings:
            try_remove(os.path.join(sibling_path, ShortcutHelper.SIBLINGS_FOLDER, old_lnk))

    def _remove_children(self, person_path: str, person_uid: str, person_name: str, children_paths_list: List[str]) -> None:
        for child_path in children_paths_list:
            child_me_file_path = os.path.join(child_path, self.ME_JSON)
            child_me_object = PersonDataWrapper(self._file_service.read_me_file(child_me_file_path))

            parents_paths = child_me_object.get_parents()
            if person_path in parents_paths:
                parents_paths.remove(person_path)
            parents_ids = child_me_object.get_parent_ids()
            if person_uid in parents_ids:
                parents_ids.remove(person_uid)

            child_name = child_me_object.get_person_name()
            try:
                ShortcutHelper.remove_shortcut(
                    os.path.join(person_path, ShortcutHelper.CHILDREN_FOLDER, child_name + self.LNK))
            except (ValueError, RuntimeError):
                pass
            try:
                ShortcutHelper.remove_shortcut(
                    os.path.join(child_path, ShortcutHelper.PARENTS_FOLDER, person_name + self.LNK))
            except (ValueError, RuntimeError):
                pass

            self._file_service.write_me_file(child_me_file_path, child_me_object)

    def _remove_parents(self, person_path: str, person_uid: str, person_name: str, parents_paths_list: List[str]) -> None:
        for parent_path in parents_paths_list:
            parent_me_file_path = os.path.join(parent_path, self.ME_JSON)
            parent_me_object = PersonDataWrapper(self._file_service.read_me_file(parent_me_file_path))

            children_paths = parent_me_object.get_children()
            if person_path in children_paths:
                children_paths.remove(person_path)
            children_ids = parent_me_object.get_children_ids()
            if person_uid in children_ids:
                children_ids.remove(person_uid)

            parent_name = parent_me_object.get_person_name()
            try:
                ShortcutHelper.remove_shortcut(
                    os.path.join(person_path, ShortcutHelper.PARENTS_FOLDER, parent_name + self.LNK))
            except (ValueError, RuntimeError):
                pass
            try:
                ShortcutHelper.remove_shortcut(
                    os.path.join(parent_path, ShortcutHelper.CHILDREN_FOLDER, person_name + self.LNK))
            except (ValueError, RuntimeError):
                pass

            self._file_service.write_me_file(parent_me_file_path, parent_me_object)

    def _remove_spouses(self, person_path: str, person_uid: str, person_name: str, spouses_paths_list: List[str]) -> None:
        for spouse_path in spouses_paths_list:
            spouse_me_file_path = os.path.join(spouse_path, self.ME_JSON)
            spouse_me_object = PersonDataWrapper(self._file_service.read_me_file(spouse_me_file_path))

            spouses_paths = spouse_me_object.get_spouses()
            if person_path in spouses_paths:
                spouses_paths.remove(person_path)
            spouses_ids = spouse_me_object.get_spouse_ids()
            if person_uid in spouses_ids:
                spouses_ids.remove(person_uid)

            spouse_name = spouse_me_object.get_person_name()
            try:
                ShortcutHelper.remove_shortcut(
                    os.path.join(person_path, ShortcutHelper.SPOUSES_FOLDER, spouse_name + self.LNK))
            except (ValueError, RuntimeError):
                pass
            try:
                ShortcutHelper.remove_shortcut(
                    os.path.join(spouse_path, ShortcutHelper.SPOUSES_FOLDER, person_name + self.LNK))
            except (ValueError, RuntimeError):
                pass

            self._file_service.write_me_file(spouse_me_file_path, spouse_me_object)

    def _remove_siblings(self, person_path: str, person_uid: str, person_name: str, siblings_paths_list: List[str]) -> None:
        for sibling_path in siblings_paths_list:
            sibling_me_file_path = os.path.join(sibling_path, self.ME_JSON)
            sibling_me_object = PersonDataWrapper(self._file_service.read_me_file(sibling_me_file_path))

            siblings_paths = sibling_me_object.get_siblings()
            if person_path in siblings_paths:
                siblings_paths.remove(person_path)
            siblings_ids = sibling_me_object.get_sibling_ids()
            if person_uid in siblings_ids:
                siblings_ids.remove(person_uid)

            sibling_name = sibling_me_object.get_person_name()
            try:
                ShortcutHelper.remove_shortcut(
                    os.path.join(person_path, ShortcutHelper.SIBLINGS_FOLDER, sibling_name + self.LNK))
            except (ValueError, RuntimeError):
                pass
            try:
                ShortcutHelper.remove_shortcut(
                    os.path.join(sibling_path, ShortcutHelper.SIBLINGS_FOLDER, person_name + self.LNK))
            except (ValueError, RuntimeError):
                pass

            self._file_service.write_me_file(sibling_me_file_path, sibling_me_object)

    def _add_children(self, new_person_path: str, new_person_unique_identifier: str, new_person_name: str, children_paths_list: List[str]):
        # Relate person with each child
        child_path: str
        for child_path in children_paths_list:
            child_me_file_path: str = os.path.join(child_path, self.ME_JSON)
            child_me_object = PersonDataWrapper(self._file_service.read_me_file(child_me_file_path))
            child_parents_paths: List[str] = child_me_object.get(PersonDataProperty.PARENTS)
            if new_person_path not in child_parents_paths:
                child_parents_paths.append(new_person_path)

            child_parents_ids: List[str] = child_me_object.get(PersonDataProperty.PARENTS_ID)
            if new_person_unique_identifier not in child_parents_ids:
                child_parents_ids.append(new_person_unique_identifier)

            # person -> child
            child_shortcut_name: str = child_me_object.get(PersonDataProperty.PERSON_NAME) + self.LNK
            ShortcutHelper.create_shortcut(
                child_path, 
                os.path.join(new_person_path, ShortcutHelper.CHILDREN_FOLDER, child_shortcut_name))
            
            # child -> person
            person_shortcut_name: str = new_person_name + self.LNK
            ShortcutHelper.create_shortcut(
                new_person_path, 
                os.path.join(child_path, ShortcutHelper.PARENTS_FOLDER, person_shortcut_name))

            self._file_service.write_me_file(child_me_file_path, child_me_object)
        
    def _add_parents(self, new_person_path: str, new_person_unique_identifier: str, new_person_name: str, parents_paths_list: List[str]):
        # Relate person with each parent
        parent_path: str
        for parent_path in parents_paths_list:
            parent_me_file_path: str = os.path.join(parent_path, self.ME_JSON)
            parent_me_object = PersonDataWrapper(self._file_service.read_me_file(parent_me_file_path))
            parent_children_paths: List[str] = parent_me_object.get(PersonDataProperty.CHILDREN)
            if new_person_path not in parent_children_paths:
                parent_children_paths.append(new_person_path)

            parent_children_ids: List[str] = parent_me_object.get(PersonDataProperty.CHILDREN_ID)
            if new_person_unique_identifier not in parent_children_ids:
                parent_children_ids.append(new_person_unique_identifier)

            # person -> parent
            parent_shortcut_name: str = parent_me_object.get(PersonDataProperty.PERSON_NAME) + self.LNK
            ShortcutHelper.create_shortcut(
                parent_path, 
                os.path.join(new_person_path, ShortcutHelper.PARENTS_FOLDER, parent_shortcut_name))
            
            # parent -> person
            person_shortcut_name: str = new_person_name + self.LNK
            ShortcutHelper.create_shortcut(
                new_person_path, 
                os.path.join(parent_path, ShortcutHelper.CHILDREN_FOLDER, person_shortcut_name))

            self._file_service.write_me_file(parent_me_file_path, parent_me_object)

    def _add_spouses(self, new_person_path: str, new_person_unique_identifier: str, new_person_name: str, spouses_paths_list: List[str]):
         # Relate person with each spouse
        spouse_path: str
        for spouse_path in spouses_paths_list:
            spouse_me_file_path: str = os.path.join(spouse_path, self.ME_JSON)
            spouse_me_object = PersonDataWrapper(self._file_service.read_me_file(spouse_me_file_path))
            spouse_spouses_paths: List[str] = spouse_me_object.get(PersonDataProperty.SPOUSES)
            if new_person_path not in spouse_spouses_paths:
                spouse_spouses_paths.append(new_person_path)

            spouse_spouses_ids: List[str] = spouse_me_object.get(PersonDataProperty.SPOUSE_ID)
            if new_person_unique_identifier not in spouse_spouses_ids:
                spouse_spouses_ids.append(new_person_unique_identifier)

            # person -> spouse
            spouse_shortcut_name: str = spouse_me_object.get(PersonDataProperty.PERSON_NAME) + self.LNK
            ShortcutHelper.create_shortcut(
                spouse_path, 
                os.path.join(new_person_path, ShortcutHelper.SPOUSES_FOLDER, spouse_shortcut_name))
            
            # spouse -> person
            person_shortcut_name: str = new_person_name + self.LNK
            ShortcutHelper.create_shortcut(
                new_person_path, 
                os.path.join(spouse_path, ShortcutHelper.SPOUSES_FOLDER, person_shortcut_name))

            self._file_service.write_me_file(spouse_me_file_path, spouse_me_object)

    def _add_siblings(self, new_person_path: str, new_person_unique_identifier: str, new_person_name: str, siblings_paths_list: List[str]):
         # Relate person with each sibling
        sibling_path: str
        for sibling_path in siblings_paths_list:
            sibling_me_file_path: str = os.path.join(sibling_path, self.ME_JSON)
            sibling_me_object = PersonDataWrapper(self._file_service.read_me_file(sibling_me_file_path))
            sibling_siblings_paths: List[str] = sibling_me_object.get(PersonDataProperty.SIBLINGS)
            if new_person_path not in sibling_siblings_paths:
                sibling_siblings_paths.append(new_person_path)

            sibling_siblings_ids: List[str] = sibling_me_object.get(PersonDataProperty.SIBLINGS_ID)
            if new_person_unique_identifier not in sibling_siblings_ids:
                sibling_siblings_ids.append(new_person_unique_identifier)

            # person -> sibling
            sibling_shortcut_name: str = sibling_me_object.get(PersonDataProperty.PERSON_NAME) + self.LNK
            ShortcutHelper.create_shortcut(
                sibling_path, 
                os.path.join(new_person_path, ShortcutHelper.SIBLINGS_FOLDER, sibling_shortcut_name))
            
            # sibling -> person
            person_shortcut_name: str = new_person_name + self.LNK
            ShortcutHelper.create_shortcut(
                new_person_path, 
                os.path.join(sibling_path, ShortcutHelper.SIBLINGS_FOLDER, person_shortcut_name))

            self._file_service.write_me_file(sibling_me_file_path, sibling_me_object)
      
    @throw_if_root_not_set
    def set_folder_tree_root_person(self, person_uuid: str) -> None:
        """Persist the root-person UUID.

        Caller is responsible for invoking rebuild_folder_tree() after this returns.
        Two-step API so the UI can show a confirmation dialog between persist
        and rebuild.
        """
        self._file_service.set_folder_tree_root_uuid(person_uuid)

    @throw_if_root_not_set
    def rebuild_folder_tree(self) -> Tuple[int, List[str]]:
        """Wipe <root>/Drzewo/ and rebuild from the current root-person UUID.

        Returns:
            (count_written, build_log_messages)

        Raises:
            RuntimeError: if no Drzewo root person is set in settings.
        """
        from src.services.folder_tree_service import FolderTreeService, render_folder_tree_filename

        root_uuid = self._file_service.get_folder_tree_root_uuid()
        if not root_uuid:
            raise RuntimeError("Drzewo root person is not set.")

        folder_tree_path = Path(self._file_service._get_root_folder()) / "Drzewo"
        folder_tree_path.mkdir(exist_ok=True)

        # Wipe existing contents (best-effort — log but do not crash on stragglers)
        for item in list(folder_tree_path.iterdir()):
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except OSError:
                pass  # Build log will surface anything odd

        # Compute membership
        drzewo = FolderTreeService(self._file_service)
        members, log = drzewo.compute_membership(root_uuid)

        # Write shortcuts with collision disambiguation
        seen_filenames: Set[str] = set()
        written = 0
        for m in members:
            fname = render_folder_tree_filename(m)
            candidate = fname
            n = 2
            while candidate in seen_filenames:
                stem, ext = candidate[:-4], candidate[-4:]  # strip .lnk
                candidate = f"{stem} ({n}){ext}"
                n += 1
            seen_filenames.add(candidate)
            ShortcutHelper.create_shortcut(m.location, str(folder_tree_path / candidate))
            written += 1

        # Persist build log
        log_path = folder_tree_path / "build-log.txt"
        log_path.write_text(
            "\n".join(log) if log else "(no anomalies)\n",
            encoding="utf-8",
        )

        return written, log

    @throw_if_root_not_set
    def rebuild_lineage(self) -> Tuple[int, List[str]]:
        """Wipe <root>/Rody/ and rebuild from the current Drzewo root-person UUID.

        Rody shares the root anchor with Drzewo.

        Returns:
            (count_written, build_log_messages)

        Raises:
            RuntimeError: if no Drzewo root person is set in settings.
        """
        from src.services.lineage_service import LineageService

        root_uuid = self._file_service.get_folder_tree_root_uuid()
        if not root_uuid:
            raise RuntimeError(
                "Drzewo root person is not set (Rody shares the root)."
            )

        lineage_path = Path(self._file_service._get_root_folder()) / "Rody"
        lineage_path.mkdir(exist_ok=True)

        # Wipe existing contents (best-effort)
        for item in list(lineage_path.iterdir()):
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except OSError:
                pass

        # Compute surname set
        rody = LineageService(self._file_service)
        surnames_to_uid, log = rody.compute_lineages(root_uuid)

        # Write one shortcut per distinct surname (alphabetically sorted)
        cached = self._file_service.settings.get_cached_people()
        written = 0
        for surname in sorted(surnames_to_uid.keys()):
            uid = surnames_to_uid[surname]
            target_location = cached.get(uid, {}).get(
                PersonDataProperty.LOCATION.value, ""
            )
            if not target_location:
                log.append(
                    f"RODY: surname '{surname}' contributor uid={uid} "
                    "has no cached location; shortcut skipped."
                )
                continue
            shortcut_path = str(lineage_path / f"{surname}.lnk")
            ShortcutHelper.create_shortcut(target_location, shortcut_path)
            written += 1

        # Persist build log
        log_path = lineage_path / "build-log.txt"
        log_path.write_text(
            "\n".join(log) if log else "(no anomalies)\n",
            encoding="utf-8",
        )

        return written, log

    def _validate_person_data(self, person_data: PersonDataWrapper):

        if not self._is_valid_guid(person_data.get_unique_identifier()):
            self.throw_value_error_for_property(PersonDataProperty.UNIQUE_IDENTIFIER)
        
        if not person_data.get_person_name():
            self.throw_value_error_for_property(PersonDataProperty.PERSON_NAME)
        
        # Empty or None until created
        # if not data.get(PersonDataProperty.LOCATION):
        #     self.throw_value_error_for_property(PersonDataProperty.LOCATION)
        
        if not self._is_valid_list_of_strings(person_data.get_spouses()):
            self.throw_value_error_for_property(PersonDataProperty.SPOUSES)

        if not self._is_valid_list_of_guids(person_data.get_spouse_ids()):
            self.throw_value_error_for_property(PersonDataProperty.SPOUSE_ID)

        if not self._is_valid_list_of_strings(person_data.get_children()):
            self.throw_value_error_for_property(PersonDataProperty.CHILDREN)

        if not self._is_valid_list_of_guids(person_data.get_children_ids()):
            self.throw_value_error_for_property(PersonDataProperty.CHILDREN_ID)

        if not self._is_valid_list_of_strings(person_data.get_parents()):
            self.throw_value_error_for_property(PersonDataProperty.PARENTS)

        if not self._is_valid_list_of_guids(person_data.get_parent_ids()):
            self.throw_value_error_for_property(PersonDataProperty.PARENTS_ID)

        if not self._is_valid_list_of_strings(person_data.get_siblings()):
            self.throw_value_error_for_property(PersonDataProperty.SIBLINGS)

        if not self._is_valid_list_of_guids(person_data.get_sibling_ids()):
            self.throw_value_error_for_property(PersonDataProperty.SIBLINGS_ID)

        if len(person_data.get_spouses()) != len(person_data.get_spouse_ids()):
            raise ValueError("Spouse lists have different lengths.")
        
        if len(person_data.get_children()) != len(person_data.get_children_ids()):
            raise ValueError("Children lists have different lengths.")
        
        if len(person_data.get_parents()) != len(person_data.get_parent_ids()):
            raise ValueError("Parents lists have different lengths.")
        
        if len(person_data.get_siblings()) != len(person_data.get_sibling_ids()):
            raise ValueError("Siblings lists have different lengths.")
        
        if person_data.get_notes() is None:
            self.throw_value_error_for_property(PersonDataProperty.NOTES)

        if not self._is_valid_optional_date(person_data.get_date_of_birth()):
            self.throw_value_error_for_property(PersonDataProperty.DATE_OF_BIRTH)

        if not self._is_valid_optional_date(person_data.get_date_of_death()):
            self.throw_value_error_for_property(PersonDataProperty.DATE_OF_DEATH)

    @staticmethod
    def throw_value_error_for_property(property: PersonDataProperty) -> None:
        raise ValueError(f"Invalid value for <{property.name}>.")

    @staticmethod
    def _is_valid_guid(id: Any) -> bool:
      """Check if a string is a valid UUID format."""
      try:
          uuid.UUID(id)
          return True
      except (ValueError, AttributeError, TypeError):
          return False
      
    @staticmethod
    def _is_valid_list_of_strings(list: List[Any]) -> bool:
        if list is None:
            return False
        
        for item in list:
            if not str(item).strip():
                return False

        return True
    
    def _is_valid_list_of_guids(self, list: List[Any]) -> bool:
        if list is None:
            return False
        
        for item in list:
            if not self._is_valid_guid(item):
                return False

        return True
    
    @staticmethod
    def _is_valid_optional_date(value: str | None) -> bool:
        if value is None:
            return True
        
        try:
            OptionalDate.from_string(value)
        except (ValueError, Exception):
            return False

        return True

    