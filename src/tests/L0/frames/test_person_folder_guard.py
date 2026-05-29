"""Person-folder me.json pre-check guard tests.

Guard B: before calling _load_person_for_edit, check that me.json exists.
If absent → Polish warning dialog + re-show dialog (loop).
If present → _load_person_for_edit called.
If user cancels dialog → no crash.

Four tests:
  1. Missing me.json → dialog shown, _load_person_for_edit NOT called.
  2. Present me.json → _load_person_for_edit called.
  3. User cancels DirDialog → no crash.
  4. Missing me.json on first attempt, cancel on second → _load_person_for_edit NOT called, no exception.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import wx


# ---------------------------------------------------------------------------
# Module-scoped wx infrastructure
# ---------------------------------------------------------------------------

_wx_app_person_guard: wx.App | None = None


def _ensure_wx_app_person() -> None:
    global _wx_app_person_guard
    if _wx_app_person_guard is None:
        _wx_app_person_guard = wx.App(False)


# ---------------------------------------------------------------------------
# Helper — build a minimal frame ready for on_open_person_click testing
# ---------------------------------------------------------------------------

def _build_frame(tmp_path: Path, monkeypatch) -> "AddPersonFrame":
    import tempfile as _tempfile

    _ensure_wx_app_person()

    app_tmp = tmp_path / "apptmp"
    app_tmp.mkdir(exist_ok=True)
    monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

    appdata = tmp_path / "appdata"
    appdata.mkdir(exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))

    tree_root = tmp_path / "tree"
    tree_root.mkdir()

    with patch("src.frames.add_person_frame.TreeService") as mock_ts_cls, \
         patch("src.frames.add_person_frame.init_logging"):

        mock_ts = MagicMock()
        mock_ts.is_root_location_set.return_value = True
        mock_ts.list_of_people = {}
        mock_ts._file_service.get_settings.return_value.get_font_size.return_value = 20
        mock_ts._file_service.get_settings.return_value.get_skipped_update_version.return_value = None
        mock_ts.get_people_folder.return_value = str(tree_root)
        mock_ts_cls.return_value = mock_ts

        parent = wx.Frame(None)
        from src.frames.add_person_frame import AddPersonFrame
        frame = AddPersonFrame(parent)

    return frame


# ---------------------------------------------------------------------------
# Test 1: Missing me.json → dialog shown, _load_person_for_edit NOT called
# ---------------------------------------------------------------------------

class TestOpenPersonMissingMeJson:

    def test_open_person_missing_me_json_shows_warning(self, tmp_path, monkeypatch):
        """A folder without me.json must trigger the warning dialog; load not called.

        The loop re-shows the dialog after the warning; the second ShowModal
        returns wx.ID_CANCEL so the loop exits cleanly.
        """
        frame = _build_frame(tmp_path, monkeypatch)

        person_folder = tmp_path / "Jan Kowalski"
        person_folder.mkdir()
        # me.json intentionally NOT created

        # First call: ID_OK with bad folder; second call: ID_CANCEL (exits loop)
        mock_dialog_cls = MagicMock()
        first_instance = MagicMock()
        first_instance.ShowModal.return_value = wx.ID_OK
        first_instance.GetPath.return_value = str(person_folder)

        second_instance = MagicMock()
        second_instance.ShowModal.return_value = wx.ID_CANCEL

        mock_dialog_cls.side_effect = [first_instance, second_instance]

        mock_load = MagicMock()
        mock_polish = MagicMock()

        expected_message = (
            "Wybrany folder nie zawiera informacji o żadnej osobie. "
            "Wybierz osobę bezpośrednio z folderu \"Lista osób\", nie głębiej."
        )

        with patch("src.frames.add_person_frame.wx.DirDialog", mock_dialog_cls), \
             patch.object(frame, "_load_person_for_edit", mock_load), \
             patch("src.frames.add_person_frame.polish_dialog", mock_polish):
            frame.on_open_person_click(MagicMock())

        mock_load.assert_not_called()
        assert mock_polish.called, "Expected polish_dialog (warning) to be called"
        actual_message = mock_polish.call_args[0][1]
        assert actual_message == expected_message, (
            f"Wrong Polish message.\nExpected: {expected_message!r}\nGot:      {actual_message!r}"
        )


# ---------------------------------------------------------------------------
# Test 2: Present me.json → _load_person_for_edit called
# ---------------------------------------------------------------------------

class TestOpenPersonValidFolder:

    def test_open_person_valid_folder_proceeds(self, tmp_path, monkeypatch):
        """A folder containing me.json must call _load_person_for_edit."""
        frame = _build_frame(tmp_path, monkeypatch)

        person_folder = tmp_path / "Maria Kowalska"
        person_folder.mkdir()
        (person_folder / "me.json").write_text('{"unique_identifier": "test-uuid"}', encoding="utf-8")

        mock_dialog_cls = MagicMock()
        mock_dialog_instance = MagicMock()
        mock_dialog_instance.ShowModal.return_value = wx.ID_OK
        mock_dialog_instance.GetPath.return_value = str(person_folder)
        mock_dialog_cls.return_value = mock_dialog_instance

        mock_load = MagicMock()

        with patch("src.frames.add_person_frame.wx.DirDialog", mock_dialog_cls), \
             patch.object(frame, "_load_person_for_edit", mock_load):
            frame.on_open_person_click(MagicMock())

        mock_load.assert_called_once_with(str(person_folder))


# ---------------------------------------------------------------------------
# Test 3: User cancels DirDialog → no crash
# ---------------------------------------------------------------------------

class TestOpenPersonCancel:

    def test_open_person_cancel_no_error(self, tmp_path, monkeypatch):
        """Cancelling the DirDialog must not raise any exception."""
        frame = _build_frame(tmp_path, monkeypatch)

        mock_dialog_cls = MagicMock()
        mock_dialog_instance = MagicMock()
        mock_dialog_instance.ShowModal.return_value = wx.ID_CANCEL
        mock_dialog_cls.return_value = mock_dialog_instance

        mock_load = MagicMock()
        with patch("src.frames.add_person_frame.wx.DirDialog", mock_dialog_cls), \
             patch.object(frame, "_load_person_for_edit", mock_load):
            # Should not raise
            frame.on_open_person_click(MagicMock())

        mock_load.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: Missing me.json on first attempt, cancel on second → clean exit
# ---------------------------------------------------------------------------

class TestOpenPersonMissingThenCancel:

    def test_open_person_missing_then_cancel_exits_cleanly(self, tmp_path, monkeypatch):
        """First ShowModal OK (bad folder), second ShowModal CANCEL → load never called, no exception."""
        frame = _build_frame(tmp_path, monkeypatch)

        person_folder = tmp_path / "Bad Folder"
        person_folder.mkdir()
        # me.json intentionally NOT created

        first_instance = MagicMock()
        first_instance.ShowModal.return_value = wx.ID_OK
        first_instance.GetPath.return_value = str(person_folder)

        second_instance = MagicMock()
        second_instance.ShowModal.return_value = wx.ID_CANCEL

        mock_dialog_cls = MagicMock()
        mock_dialog_cls.side_effect = [first_instance, second_instance]

        mock_load = MagicMock()
        mock_polish = MagicMock()

        with patch("src.frames.add_person_frame.wx.DirDialog", mock_dialog_cls), \
             patch.object(frame, "_load_person_for_edit", mock_load), \
             patch("src.frames.add_person_frame.polish_dialog", mock_polish):
            frame.on_open_person_click(MagicMock())

        mock_load.assert_not_called()
        # Warning was shown once (for the bad folder)
        assert mock_polish.call_count == 1, "Expected exactly one warning dialog"
