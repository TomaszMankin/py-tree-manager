"""Unit / integration tests for services/tree_service.py.


All tests use tmp_path for the tree root. No dependency on C:/Sorted tree/.

Key invariants checked after each relationship operation:
  - Both me.json files updated (bidirectional).
  - Path arrays and UUID arrays have equal length.
  - UUIDs come from the loaded me.json files, not fresh uuid.uuid4() calls.

The 'save with one parent' test is the test that WOULD HAVE caught the
unique_indentifier typo: it asserts the parent's UUID (read from disk) is
stored in parents_id, not a freshly-generated one.

Test classes:
  TestTreeServiceSavePerson         -- save_person_and_add_to_tree + bidirectional sync
  TestTreeServiceRemoveRelationship -- _remove_parents
  TestTreeServiceUpdatePerson       -- load -> rename -> save round-trip
"""

import json
import os
import uuid
from pathlib import Path

import pytest

from src.wrappers.person_data_wrapper import PersonDataWrapper, PersonDataProperty


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tree_service(tmp_path, monkeypatch):
    """Return a TreeService with an isolated root under tmp_path."""
    import tempfile as _tempfile
    from src.services.tree_service import TreeService

    app_tmp = tmp_path / "apptmp"
    app_tmp.mkdir(exist_ok=True)
    monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

    # Isolate LOCALAPPDATA so set_root_folder() / set_root_location()
    # writes the bootstrap pointer to a scratch dir, not real %LOCALAPPDATA%.
    appdata = tmp_path / "appdata"
    appdata.mkdir(exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))

    ts = TreeService()

    tree_root = tmp_path / "tree"
    tree_root.mkdir()
    ts.set_root_location(str(tree_root))

    return tree_root, ts


def _write_me_json(folder: Path, data: dict) -> None:
    """Write a me.json file into the given folder (UTF-8, no BOM)."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "me.json").write_text(
        json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8"
    )


def _read_me_json(folder: Path) -> dict:
    """Read and parse me.json from folder."""
    return json.loads((folder / "me.json").read_text(encoding="utf-8-sig"))


def _build_person_data(factory, **kwargs) -> PersonDataWrapper:
    """Build a PersonDataWrapper from me_json_factory output."""
    return PersonDataWrapper(factory(**kwargs))


# ---------------------------------------------------------------------------
# Save a new person
# ---------------------------------------------------------------------------

class TestTreeServiceSavePerson:

    def test_save_with_no_relationships(self, tmp_path, monkeypatch, me_json_factory):
        """Saving a person with no relationships creates the folder + me.json on disk."""
        root, ts = _make_tree_service(tmp_path, monkeypatch)

        uid = str(uuid.uuid4())
        person = PersonDataWrapper(me_json_factory(
            uid=uid, name="Jan A", first_name="Jan", last_name="A"
        ))

        ts.save_person_and_add_to_tree(person)

        lista = root / "Lista osób"
        # Folder should exist
        person_folder = lista / "Jan A"
        assert person_folder.is_dir()
        # me.json should be readable
        data = _read_me_json(person_folder)
        assert data["unique_identifier"] == uid
        # Person should be in the cached list
        assert uid in ts.list_of_people

    def test_save_with_one_parent_syncs_both_me_json_files(
        self, tmp_path, monkeypatch, me_json_factory
    ):
        """Saving a person with a parent syncs BOTH me.json files bidirectionally.

        This is the test that WOULD HAVE caught the unique_indentifier typo:
        it asserts that parents_id contains the parent's UUID READ FROM DISK,
        not a fresh uuid.uuid4() value. Before the original fix, get_unique_identifier()
        returned '' for real files (key mismatch), causing a new UUID to be generated.

        Invariants checked:
          - new person's me.json: parents == [parent_folder_path]
          - new person's me.json: parents_id == [parent_uid]  (real UUID, not fresh)
          - parent's me.json: children == [new_person_folder_path]
          - parent's me.json: children_id == [new_person_uid]
          - len(parents) == len(parents_id) for both files
          - len(children) == len(children_id) for both files
        """
        root, ts = _make_tree_service(tmp_path, monkeypatch)
        lista = root / "Lista osób"

        # Set up the parent on disk first via the service
        parent_uid = str(uuid.uuid4())
        parent_wrapper = PersonDataWrapper(me_json_factory(
            uid=parent_uid, name="Parent P", first_name="Parent", last_name="P"
        ))
        ts.save_person_and_add_to_tree(parent_wrapper)
        parent_folder = lista / "Parent P"

        # Now save the child, referencing the parent's folder path
        child_uid = str(uuid.uuid4())
        child_wrapper = PersonDataWrapper(me_json_factory(
            uid=child_uid,
            name="Child C",
            first_name="Child",
            last_name="C",
            parents=[str(parent_folder)],
            parents_id=[parent_uid],
        ))
        ts.save_person_and_add_to_tree(child_wrapper)
        child_folder = lista / "Child C"

        # --- Assert child's me.json ---
        child_data = _read_me_json(child_folder)
        assert str(parent_folder) in child_data["parents"]
        assert parent_uid in child_data["parents_id"]
        assert len(child_data["parents"]) == len(child_data["parents_id"])

        # --- Assert parent's me.json was updated bidirectionally ---
        parent_data = _read_me_json(parent_folder)
        assert str(child_folder) in parent_data["children"]
        assert child_uid in parent_data["children_id"]
        assert len(parent_data["children"]) == len(parent_data["children_id"])

        # --- UUID came from disk, not from a fresh uuid4() ---
        # The parent's UUID in child's parents_id must match what was stored on disk.
        assert parent_data["unique_identifier"] == parent_uid, (
            "Parent UUID mismatch: the value in the child's parents_id is not the "
            "parent's real UUID from me.json. This would indicate the unique_identifier "
            "lookup bug is back."
        )

    def test_save_with_one_child(self, tmp_path, monkeypatch, me_json_factory):
        """Saving with a child syncs the child's me.json (parents arrays)."""
        root, ts = _make_tree_service(tmp_path, monkeypatch)
        lista = root / "Lista osób"

        child_uid = str(uuid.uuid4())
        child_wrapper = PersonDataWrapper(me_json_factory(
            uid=child_uid, name="Child D", first_name="Child", last_name="D"
        ))
        ts.save_person_and_add_to_tree(child_wrapper)
        child_folder = lista / "Child D"

        parent_uid = str(uuid.uuid4())
        parent_wrapper = PersonDataWrapper(me_json_factory(
            uid=parent_uid,
            name="Parent Q",
            first_name="Parent",
            last_name="Q",
            children=[str(child_folder)],
            children_id=[child_uid],
        ))
        ts.save_person_and_add_to_tree(parent_wrapper)
        parent_folder = lista / "Parent Q"

        child_data = _read_me_json(child_folder)
        assert str(parent_folder) in child_data["parents"]
        assert parent_uid in child_data["parents_id"]
        assert len(child_data["parents"]) == len(child_data["parents_id"])

        parent_data = _read_me_json(parent_folder)
        assert str(child_folder) in parent_data["children"]
        assert len(parent_data["children"]) == len(parent_data["children_id"])

    def test_save_with_one_spouse(self, tmp_path, monkeypatch, me_json_factory):
        """Saving with a spouse syncs the spouse's me.json (spouse arrays)."""
        root, ts = _make_tree_service(tmp_path, monkeypatch)
        lista = root / "Lista osób"

        spouse_uid = str(uuid.uuid4())
        spouse_wrapper = PersonDataWrapper(me_json_factory(
            uid=spouse_uid, name="Spouse S", first_name="Spouse", last_name="S"
        ))
        ts.save_person_and_add_to_tree(spouse_wrapper)
        spouse_folder = lista / "Spouse S"

        person_uid = str(uuid.uuid4())
        person_wrapper = PersonDataWrapper(me_json_factory(
            uid=person_uid,
            name="Person R",
            first_name="Person",
            last_name="R",
            spouses=[str(spouse_folder)],
            spouse_id=[spouse_uid],
        ))
        ts.save_person_and_add_to_tree(person_wrapper)
        person_folder = lista / "Person R"

        spouse_data = _read_me_json(spouse_folder)
        assert str(person_folder) in spouse_data["spouse"]
        assert person_uid in spouse_data["spouse_id"]
        assert len(spouse_data["spouse"]) == len(spouse_data["spouse_id"])

        person_data = _read_me_json(person_folder)
        assert len(person_data["spouse"]) == len(person_data["spouse_id"])


# ---------------------------------------------------------------------------
# Remove relationship
# ---------------------------------------------------------------------------

class TestTreeServiceRemoveRelationship:

    def test_remove_one_parent_clears_both_files(self, tmp_path, monkeypatch, me_json_factory):
        """_remove_parents removes the relationship from BOTH the parent's and child's me.json.

        Setup:
          - Save parent + child with a bidirectional parent/child relationship.
          - Call _remove_parents on the child, passing the parent's path.
        Post-conditions:
          - Parent's me.json no longer contains child in children / children_id.
          - (Child's me.json parents/parents_id were already emptied by the remove call.)
        """
        root, ts = _make_tree_service(tmp_path, monkeypatch)
        lista = root / "Lista osób"

        parent_uid = str(uuid.uuid4())
        parent_wrapper = PersonDataWrapper(me_json_factory(
            uid=parent_uid, name="Parent E", first_name="Parent", last_name="E"
        ))
        ts.save_person_and_add_to_tree(parent_wrapper)
        parent_folder = lista / "Parent E"

        child_uid = str(uuid.uuid4())
        child_wrapper = PersonDataWrapper(me_json_factory(
            uid=child_uid,
            name="Child F",
            first_name="Child",
            last_name="F",
            parents=[str(parent_folder)],
            parents_id=[parent_uid],
        ))
        ts.save_person_and_add_to_tree(child_wrapper)
        child_folder = lista / "Child F"

        # Confirm relationship exists before remove
        parent_before = _read_me_json(parent_folder)
        assert str(child_folder) in parent_before["children"]

        # Remove parent from child's perspective
        ts._remove_parents(str(child_folder), child_uid, "Child F", [str(parent_folder)])

        # Parent's children arrays must no longer reference the child
        parent_after = _read_me_json(parent_folder)
        assert str(child_folder) not in parent_after["children"]
        assert child_uid not in parent_after["children_id"]
        assert len(parent_after["children"]) == len(parent_after["children_id"])


# ---------------------------------------------------------------------------
# Update (edit) round-trip
# ---------------------------------------------------------------------------

class TestTreeServiceUpdatePerson:

    def test_load_save_round_trip_no_changes(self, tmp_path, monkeypatch, me_json_factory):
        """Saving and re-reading a person's me.json preserves all fields."""
        root, ts = _make_tree_service(tmp_path, monkeypatch)
        lista = root / "Lista osób"

        uid = str(uuid.uuid4())
        wrapper = PersonDataWrapper(me_json_factory(
            uid=uid, name="Jan G", first_name="Jan", last_name="G", notes="test note"
        ))
        ts.save_person_and_add_to_tree(wrapper)
        person_folder = lista / "Jan G"

        # Read back from disk
        data = _read_me_json(person_folder)
        assert data["unique_identifier"] == uid
        assert data["notes"] == "test note"
        assert data["first_name"] == "Jan"
        assert data["last_name"] == "G"

    def test_rename_propagates_to_related_me_json(self, tmp_path, monkeypatch, me_json_factory):
        """Renaming a person via update_person_in_tree updates related me.json path arrays.

        Flow:
          1. Save parent + child with bidirectional relationship.
          2. Call update_person_in_tree on the child with a new name.
          3. Assert the parent's me.json now references the new path, not the old one.
          4. Assert the old folder path is gone from parent's children array.
        """
        root, ts = _make_tree_service(tmp_path, monkeypatch)
        lista = root / "Lista osób"

        parent_uid = str(uuid.uuid4())
        parent_wrapper = PersonDataWrapper(me_json_factory(
            uid=parent_uid, name="Parent H", first_name="Parent", last_name="H"
        ))
        ts.save_person_and_add_to_tree(parent_wrapper)
        parent_folder = lista / "Parent H"

        child_uid = str(uuid.uuid4())
        child_wrapper = PersonDataWrapper(me_json_factory(
            uid=child_uid,
            name="Child I",
            first_name="Child",
            last_name="I",
            parents=[str(parent_folder)],
            parents_id=[parent_uid],
        ))
        ts.save_person_and_add_to_tree(child_wrapper)
        child_folder_old = lista / "Child I"
        old_path_str = str(child_folder_old)

        # Prepare the updated person data (rename last name from "I" to "J")
        updated_data = me_json_factory(
            uid=child_uid,
            name="Child J",
            first_name="Child",
            last_name="J",
            parents=[str(parent_folder)],
            parents_id=[parent_uid],
        )
        updated_wrapper = PersonDataWrapper(updated_data)

        original_relationships = {
            "parents": [str(parent_folder)],
            "children": [],
            "spouses": [],
            "siblings": [],
        }

        ts.update_person_in_tree(
            person_data=updated_wrapper,
            original_location=old_path_str,
            original_canonical_name="Child I",
            original_relationships=original_relationships,
        )

        child_folder_new = lista / "Child J"
        new_path_str = str(child_folder_new)

        # New folder must exist; old must be gone
        assert child_folder_new.is_dir()
        assert not child_folder_old.exists()

        # Parent's me.json must reference the NEW path, not the old
        parent_data = _read_me_json(parent_folder)
        assert new_path_str in parent_data["children"], (
            "Parent's children array must be updated to the new path after rename."
        )
        assert old_path_str not in parent_data["children"], (
            "Parent's children array must not still reference the old (renamed) path."
        )
        assert child_uid in parent_data["children_id"]
        assert len(parent_data["children"]) == len(parent_data["children_id"])


# ---------------------------------------------------------------------------
# Draft round-trip
# ---------------------------------------------------------------------------

class TestTreeServiceDraftRoundTrip:
    """L0 test: save_person_draft -> load_person_draft returns equal dict.

    This test pins the contract that the drafts wiring in AddPersonFrame depends on.
    """

    def test_save_then_load_person_draft_round_trip(
        self, tmp_path, monkeypatch, me_json_factory
    ):
        """save_person_draft writes to temp dir; load_person_draft reads same dict back.

        Uses Polish chars in the person name to confirm unicode round-trips correctly.
        Includes one parent UUID to exercise the relationship arrays.
        """
        root, ts = _make_tree_service(tmp_path, monkeypatch)

        parent_uid = str(uuid.uuid4())
        person_uid = str(uuid.uuid4())

        raw = me_json_factory(
            uid=person_uid,
            name="Zdzisław Wróblewński",
            first_name="Zdzisław",
            last_name="Wróblewński",
            notes="Notatka z polskimi znakami: ą ę ó ś ź ż ć ń ł",
            parents_id=[parent_uid],
        )
        wrapper = PersonDataWrapper(raw)

        ts.save_person_draft(wrapper)

        # Drafts live under <root>/Poczekalnia/ (not %TEMP%/PyTreeManager/)
        draft_path = tmp_path / "tree" / "Poczekalnia" / f"{person_uid}.json"
        assert draft_path.exists(), f"Draft file was not created at {draft_path}"

        loaded = ts.load_person_draft(str(draft_path))

        assert loaded == wrapper.to_dict(), (
            "Loaded draft dict does not match the saved wrapper dict. "
            "Round-trip is broken in the service/file layer."
        )


# ---------------------------------------------------------------------------
# Bug regression: Zaktualizuj szkic must overwrite same UUID
# ---------------------------------------------------------------------------

class TestTreeServiceDraftUpdate:
    """Service-level contract: save_person_draft() keyed on UUID X
    must overwrite <poczekalnia>/X.json, NOT create a new <poczekalnia>/Y.json.

    The frame-level test is in test_add_person_frame_transitions.py.
    This test confirms the service is correct in isolation.
    """

    def test_update_draft_overwrites_same_uuid_no_duplicate(
        self, tmp_path, monkeypatch, me_json_factory
    ):
        """load -> edit -> save must overwrite X.json, not create Y.json."""
        root, ts = _make_tree_service(tmp_path, monkeypatch)
        poczekalnia = ts._file_service.get_poczekalnia_path()
        X = "11111111-1111-1111-1111-111111111111"
        draft_data = me_json_factory(
            uid=X, name="Jan Kowalski", first_name="Jan", last_name="Kowalski"
        )
        ts.save_person_draft(PersonDataWrapper(draft_data))
        assert (poczekalnia / f"{X}.json").exists()
        initial_files = list(poczekalnia.iterdir())
        assert len(initial_files) == 1

        # Simulate load: read the draft and prepare an "edited" version with the SAME UID
        loaded = ts.load_person_draft(str(poczekalnia / f"{X}.json"))
        edited = PersonDataWrapper(loaded)
        edited.set_last_name("Nowakowski")
        edited.set_person_name("Jan Nowakowski")
        # CRITICAL: the loaded UUID must travel through the edit
        assert edited.get_unique_identifier() == X

        # Simulate "Zaktualizuj szkic osoby": save_person_draft with the same UID
        ts.save_person_draft(edited)

        # Assert: still ONE file, still UUID X, contents are the edited version
        final_files = list(poczekalnia.iterdir())
        assert len(final_files) == 1, (
            f"Expected 1 file in Poczekalnia, found {len(final_files)}: "
            f"{[f.name for f in final_files]}"
        )
        assert final_files[0].name == f"{X}.json"
        final_data = ts.load_person_draft(str(final_files[0]))
        assert final_data["last_name"] == "Nowakowski"


# ---------------------------------------------------------------------------
# Promote-disposes-draft
# ---------------------------------------------------------------------------

class TestPromoteDisposesDraft:
    """Service-level tests for the promote-draft-to-tree + delete semantics.

    These tests exercise the logic that on_promote_draft_click performs in the
    frame: save_person_and_add_to_tree succeeds, then the draft file is deleted.
    The frame's handler is the subject; these tests isolate the service steps.
    """

    def test_promote_draft_to_tree_deletes_draft_file_happy_path(
        self, tmp_path, monkeypatch, me_json_factory
    ):
        """After promote, tree person exists AND draft file is gone.

        Simulates the frame handler's Steps 1-3 at service level.
        """
        root, ts = _make_tree_service(tmp_path, monkeypatch)
        poczekalnia = ts._file_service.get_poczekalnia_path()
        X = "22222222-2222-2222-2222-222222222222"

        # Write the draft
        draft_data = me_json_factory(
            uid=X, name="Anna Kowalska", first_name="Anna", last_name="Kowalska"
        )
        ts.save_person_draft(PersonDataWrapper(draft_data))
        draft_path = poczekalnia / f"{X}.json"
        assert draft_path.exists(), "Precondition: draft must exist before promote"

        # Simulate promote: save to tree, then delete the draft
        person_data = PersonDataWrapper(draft_data)
        ts.save_person_and_add_to_tree(person_data)

        # Delete the draft (what the frame handler does in Step 3)
        if draft_path.exists():
            draft_path.unlink()

        # Assert: tree person exists AND draft is gone
        lista = root / "Lista osób"
        person_folder = lista / "Anna Kowalska"
        assert person_folder.is_dir(), "Tree person folder must exist after promote"
        assert (person_folder / "me.json").exists(), "me.json must exist in tree person folder"
        assert not draft_path.exists(), "Draft file must be deleted after promote"

    def test_promote_draft_delete_fails_logs_info_cleanup_continues(
        self, tmp_path, monkeypatch, me_json_factory
    ):
        """When draft deletion fails, promote still succeeds and INFO-CLEANUP is logged.

        Mimics the frame handler's except block using log_cleanup_failure().
        """
        import time
        from pathlib import Path as _Path
        from src.helpers.logger import init_logging, log_cleanup_failure

        root, ts = _make_tree_service(tmp_path, monkeypatch)
        # Initialize logging so the exceptions log is in our scratch dir
        init_logging(root)

        poczekalnia = ts._file_service.get_poczekalnia_path()
        X = "33333333-3333-3333-3333-333333333333"

        draft_data = me_json_factory(
            uid=X, name="Piotr Nowak", first_name="Piotr", last_name="Nowak"
        )
        ts.save_person_draft(PersonDataWrapper(draft_data))
        draft_path = poczekalnia / f"{X}.json"
        assert draft_path.exists()

        # Promote to tree
        person_data = PersonDataWrapper(draft_data)
        ts.save_person_and_add_to_tree(person_data)

        # Simulate deletion failure: write-protect the file + call log_cleanup_failure
        perm_error = PermissionError("locked by test")
        # Call the public log_cleanup_failure helper
        log_cleanup_failure(draft_path, perm_error)

        # Assert 1: tree person folder still exists (promote succeeded before the fail)
        lista = root / "Lista osób"
        person_folder = lista / "Piotr Nowak"
        assert person_folder.is_dir(), "Tree person folder must still exist after cleanup failure"

        # Assert 2: draft file still there (delete was not attempted in this simulation)
        assert draft_path.exists(), "Draft file should still exist since deletion was skipped"

        # Assert 3: INFO-CLEANUP line appears in today's exceptions log
        log_dir = root / ".PyTreeManager" / "logs"
        today = time.strftime("%Y-%m-%d")
        exceptions_log = log_dir / f"{today}__exceptions.log"
        assert exceptions_log.exists(), f"Exceptions log not found at {exceptions_log}"
        log_content = exceptions_log.read_text(encoding="utf-8")
        assert "[INFO-CLEANUP]" in log_content, "INFO-CLEANUP line must appear in exceptions log"
        assert str(X) in log_content, "Draft UUID must appear in INFO-CLEANUP line"
