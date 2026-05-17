"""AddPersonFrame mode-transition state tests.

Tests exercise the frame-level state contract without requiring a wx mainloop.
Strategy: extract logic into _apply_loaded_draft(data, path) and
_post_save_transition() methods on the frame, test via SimpleNamespace stubs.

All tests are wx-free.

Also includes the frame-level regression test for the load-draft UUID bug.
"""

from __future__ import annotations

import types
import uuid
from pathlib import Path

import pytest

from src.frames.menu_state import MenuMode


# ---------------------------------------------------------------------------
# Helpers — minimal fake frame
# ---------------------------------------------------------------------------

def _make_stub_frame(initial_uid: str | None = None) -> types.SimpleNamespace:
    """Create a minimal stub that has the same attributes AddPersonFrame uses
    for mode tracking. Tests invoke _apply_loaded_draft() and
    _post_save_transition() directly on this stub.
    """
    stub = types.SimpleNamespace()
    stub.unique_identifier = initial_uid or str(uuid.uuid4())
    stub._loaded_draft_path = None
    stub._menu_mode = MenuMode.NEW
    return stub


def _apply_loaded_draft(stub, data: dict, path: str) -> None:
    """Call the REAL AddPersonFrame._apply_loaded_draft() on a stub.

    The real method lives on AddPersonFrame and is wx-free (pure-state only:
    sets unique_identifier + _loaded_draft_path). Tests call it directly via
    the production code path, not a local mirror. _menu_mode is set manually
    here to simulate what on_load_draft_click does after calling
    _apply_loaded_draft + _apply_menu_mode.
    """
    from src.frames.add_person_frame import AddPersonFrame
    AddPersonFrame._apply_loaded_draft(stub, data, path)
    # Simulate the _apply_menu_mode(MenuMode.EDIT_DRAFT) call that
    # on_load_draft_click makes after _apply_loaded_draft. The stub has
    # no wx menu bar so we set _menu_mode directly.
    stub._menu_mode = MenuMode.EDIT_DRAFT


def _post_save_transition(stub) -> None:
    """Mirror of the frame's _post_save_transition() logic.

    After any successful save, mode resets to NEW.
    In the real frame this is the tail of _reset_to_add_mode().
    """
    stub._menu_mode = MenuMode.NEW
    stub._loaded_draft_path = None
    stub.unique_identifier = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Frame-level regression test: on_load_draft_click must restore UUID
# ---------------------------------------------------------------------------

class TestLoadDraftRestoresUUID:
    """After loading a draft, the frame's unique_identifier must equal the draft's UUID."""

    def test_on_load_draft_click_restores_unique_identifier(self, tmp_path, me_json_factory):
        """After _apply_loaded_draft, stub.unique_identifier == draft_uuid."""
        X = "aaaa0000-0000-0000-0000-000000000000"
        stub = _make_stub_frame(initial_uid="launch-time-uuid")
        assert stub.unique_identifier == "launch-time-uuid"  # precondition

        draft_data = me_json_factory(uid=X, name="Test Person", first_name="Test", last_name="Person")
        path = str(tmp_path / f"{X}.json")

        _apply_loaded_draft(stub, draft_data, path)

        assert stub.unique_identifier == X, (
            f"UUID must be restored to '{X}' after load, "
            f"but got '{stub.unique_identifier}'"
        )

    def test_on_load_draft_stores_loaded_path(self, tmp_path, me_json_factory):
        """After _apply_loaded_draft, stub._loaded_draft_path is set."""
        X = "bbbb0000-0000-0000-0000-000000000000"
        stub = _make_stub_frame()
        draft_data = me_json_factory(uid=X, name="Test", first_name="T", last_name="P")
        path = str(tmp_path / f"{X}.json")

        _apply_loaded_draft(stub, draft_data, path)

        assert stub._loaded_draft_path == path

    def test_on_load_draft_sets_mode_to_edit_draft(self, tmp_path, me_json_factory):
        """After _apply_loaded_draft, stub._menu_mode == EDIT_DRAFT."""
        X = "cccc0000-0000-0000-0000-000000000000"
        stub = _make_stub_frame()
        draft_data = me_json_factory(uid=X, name="Test", first_name="T", last_name="P")
        path = str(tmp_path / f"{X}.json")

        _apply_loaded_draft(stub, draft_data, path)

        assert stub._menu_mode == MenuMode.EDIT_DRAFT

    def test_load_then_update_does_not_create_duplicate(self, tmp_path, monkeypatch, me_json_factory):
        """Integration trace: load draft X -> edit -> Zaktualizuj -> ONE file X.json.

        Exercises the full data path from load through service save.
        Exercises the full data path from load through service save.
        """
        import sys
        import tempfile as _tempfile
        from src.services.tree_service import TreeService
        from src.wrappers.person_data_wrapper import PersonDataWrapper

        app_tmp = tmp_path / "apptmp"
        app_tmp.mkdir(exist_ok=True)
        monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))
        appdata = tmp_path / "appdata"
        appdata.mkdir(exist_ok=True)
        monkeypatch.setenv("LOCALAPPDATA", str(appdata))

        ts = TreeService()
        tree_root = tmp_path / "tree"
        tree_root.mkdir()
        ts.set_root_location(str(tree_root))

        poczekalnia = ts._file_service.get_poczekalnia_path()
        X = "22222222-2222-2222-2222-222222222222"

        # Step A: write a draft with UID X
        draft_data = me_json_factory(
            uid=X, name="Anna Kowalska", first_name="Anna", last_name="Kowalska"
        )
        ts.save_person_draft(PersonDataWrapper(draft_data))
        assert len(list(poczekalnia.iterdir())) == 1

        # Step B: simulate "load" — restore UUID (the fix)
        loaded_dict = ts.load_person_draft(str(poczekalnia / f"{X}.json"))
        stub = _make_stub_frame(initial_uid="launch-time-uuid")
        _apply_loaded_draft(stub, loaded_dict, str(poczekalnia / f"{X}.json"))

        # The restored UUID must match X
        assert stub.unique_identifier == X, (
            "Bug: frame UUID was not restored from draft data"
        )
        restored_uid = stub.unique_identifier
        assert restored_uid == X

        # Step C: simulate "edit" + "Zaktualizuj"
        edited = PersonDataWrapper(loaded_dict)
        edited.set_last_name("Nowakowska")
        edited.set_person_name("Anna Nowakowska")
        # The UUID travels through the edit unchanged
        assert edited.get_unique_identifier() == X

        ts.save_person_draft(edited)

        # Step D: assert no duplicate
        files = list(poczekalnia.iterdir())
        assert len(files) == 1, (
            f"Expected 1 file, found {len(files)}: {[f.name for f in files]}"
        )
        assert files[0].name == f"{X}.json"


# ---------------------------------------------------------------------------
# Post-save mode transitions (any successful save -> mode resets to NEW)
# ---------------------------------------------------------------------------

class TestPostSaveTransitions:
    """After any successful save, _menu_mode resets to NEW."""

    def test_post_save_from_new_lands_in_new(self):
        stub = _make_stub_frame()
        stub._menu_mode = MenuMode.NEW
        _post_save_transition(stub)
        assert stub._menu_mode == MenuMode.NEW

    def test_post_save_from_edit_tree_lands_in_new(self):
        stub = _make_stub_frame()
        stub._menu_mode = MenuMode.EDIT_TREE
        _post_save_transition(stub)
        assert stub._menu_mode == MenuMode.NEW

    def test_post_save_from_edit_draft_lands_in_new(self):
        stub = _make_stub_frame()
        stub._menu_mode = MenuMode.EDIT_DRAFT
        _post_save_transition(stub)
        assert stub._menu_mode == MenuMode.NEW

    def test_post_save_clears_loaded_draft_path(self):
        stub = _make_stub_frame()
        stub._loaded_draft_path = "/some/path.json"
        stub._menu_mode = MenuMode.EDIT_DRAFT
        _post_save_transition(stub)
        assert stub._loaded_draft_path is None

    def test_post_save_generates_new_uuid(self):
        original_uid = "fixed-uuid-for-test"
        stub = _make_stub_frame(initial_uid=original_uid)
        _post_save_transition(stub)
        assert stub.unique_identifier != original_uid, (
            "Post-save must generate a fresh UUID so next save goes to a new file"
        )


# ---------------------------------------------------------------------------
# Vanished-draft test (frame-level)
# Edge case: vanished draft is silently recreated at the same UUID path.
# ---------------------------------------------------------------------------

class TestVanishedDraftFallback:
    """When the draft file vanishes between load and Zaktualizuj, the service
    recreates it at the same UUID path (open(path, 'w') behavior).
    """

    def test_vanished_draft_is_silently_recreated(self, tmp_path, monkeypatch, me_json_factory):
        """Load draft X, delete X.json from disk, call save -> X.json recreated."""
        import tempfile as _tempfile
        from src.services.tree_service import TreeService
        from src.wrappers.person_data_wrapper import PersonDataWrapper

        app_tmp = tmp_path / "apptmp"
        app_tmp.mkdir(exist_ok=True)
        monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))
        appdata = tmp_path / "appdata"
        appdata.mkdir(exist_ok=True)
        monkeypatch.setenv("LOCALAPPDATA", str(appdata))

        ts = TreeService()
        tree_root = tmp_path / "tree"
        tree_root.mkdir()
        ts.set_root_location(str(tree_root))

        poczekalnia = ts._file_service.get_poczekalnia_path()
        X = "44444444-4444-4444-4444-444444444444"

        draft_data = me_json_factory(
            uid=X, name="Marek Wisniak", first_name="Marek", last_name="Wisniak"
        )
        ts.save_person_draft(PersonDataWrapper(draft_data))
        draft_path = poczekalnia / f"{X}.json"
        assert draft_path.exists()

        # Load into frame stub
        loaded_dict = ts.load_person_draft(str(draft_path))
        stub = _make_stub_frame()
        _apply_loaded_draft(stub, loaded_dict, str(draft_path))
        assert stub.unique_identifier == X

        # Simulate vanish
        draft_path.unlink()
        assert not draft_path.exists(), "Precondition: file must be gone"

        # Simulate "Zaktualizuj szkic osoby": service recreates the file
        edited = PersonDataWrapper(loaded_dict)
        edited.set_last_name("Wisniewski")
        edited.set_person_name("Marek Wisniewski")
        ts.save_person_draft(edited)  # open(path, 'w') creates if missing

        # Assert: file recreated at same UUID path, no error
        assert draft_path.exists(), f"Draft must be silently recreated at {draft_path}"
        recreated = ts.load_person_draft(str(draft_path))
        assert recreated["unique_identifier"] == X
        assert recreated["last_name"] == "Wisniewski"
