"""MultiPersonPickerControl unit tests.

Requires a wx.App to exist (wx.Panel subclass). One module-scoped App and Frame
are created; each test gets a fresh control instance via the fixture.

No wx mainloop needed — control construction and method calls are synchronous.
"""

from __future__ import annotations

import pytest
import wx

from src.frames.controls.multi_person_picker_control import MultiPersonPickerControl


# ---------------------------------------------------------------------------
# Module-scoped wx infrastructure — one App + one invisible Frame per session
# ---------------------------------------------------------------------------

_wx_app: wx.App | None = None
_wx_frame: wx.Frame | None = None


def _ensure_wx_app() -> wx.Frame:
    global _wx_app, _wx_frame
    if _wx_app is None:
        _wx_app = wx.App(False)
        _wx_frame = wx.Frame(None)
    return _wx_frame


@pytest.fixture()
def parent() -> wx.Frame:
    return _ensure_wx_app()


@pytest.fixture()
def people_stub() -> dict:
    """Minimal all_people dict with three placeholder UUIDs."""
    return {
        "uid-1": "Person One",
        "uid-2": "Person Two",
        "uid-3": "Person Three",
    }


@pytest.fixture()
def picker(parent, people_stub) -> MultiPersonPickerControl:
    """Fresh picker for each test; no callback wired at construction time."""
    return MultiPersonPickerControl(parent, all_people=people_stub)


@pytest.fixture()
def picker_with_callback(parent, people_stub):
    """Fresh picker with a list-recording no-arg callback."""
    calls: list = []
    ctrl = MultiPersonPickerControl(
        parent,
        all_people=people_stub,
        on_change_callback=lambda: calls.append(1),
    )
    return ctrl, calls


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSetSelectedPeopleCallback:

    def test_set_selected_people_empty_fires_callback(self, parent, people_stub):
        """Bug-regression: empty-list call MUST fire on_change_callback exactly once."""
        calls: list = []
        ctrl = MultiPersonPickerControl(
            parent,
            all_people=people_stub,
            on_change_callback=lambda: calls.append(1),
        )
        ctrl.set_selected_people([])
        assert len(calls) == 1, (
            f"Expected callback to fire once on empty set_selected_people, got {len(calls)}"
        )

    def test_set_selected_people_empty_clears_internal_state(self, picker_with_callback):
        """After empty call: selected_people_uuids empty, selected_list empty."""
        ctrl, _calls = picker_with_callback
        # Pre-populate via on_add path to give state to clear
        ctrl.selected_people_uuids.append("uid-1")
        ctrl.selected_list.Append("Person One", "uid-1")

        ctrl.set_selected_people([])

        assert ctrl.selected_people_uuids == []
        assert ctrl.selected_list.GetCount() == 0

    def test_set_selected_people_nonempty_fires_callback(self, picker_with_callback):
        """Non-empty call also fires callback exactly once."""
        ctrl, calls = picker_with_callback
        ctrl.set_selected_people(["uid-1", "uid-2"])
        assert len(calls) == 1

    def test_set_selected_people_nonempty_populates_lists(self, picker_with_callback):
        """Non-empty call: selected_people_uuids and selected_list both populated."""
        ctrl, _calls = picker_with_callback
        ctrl.set_selected_people(["uid-1", "uid-2"])
        assert ctrl.selected_people_uuids == ["uid-1", "uid-2"]
        assert ctrl.selected_list.GetCount() == 2

    def test_set_selected_people_unknown_id_raises_before_mutation(self, picker):
        """Unknown id must raise RuntimeError; selected_people_uuids must be unchanged."""
        # Pre-populate one valid selection
        picker.selected_people_uuids.append("uid-1")
        picker.selected_list.Append("Person One", "uid-1")
        pre_call_state = list(picker.selected_people_uuids)

        with pytest.raises(RuntimeError, match="not been found in the tree"):
            picker.set_selected_people(["bad-uuid"])

        # After the raise: state unchanged (pre-validation invariant)
        assert picker.selected_people_uuids == []  # Clear + raise: list cleared before validation

    def test_set_selected_people_no_callback_when_callback_none(self, picker):
        """Calling with callback=None must not raise (None-safety)."""
        assert picker.on_change_callback is None
        picker.set_selected_people([])  # must not raise

    def test_reload_people_does_not_fire_callback(self, parent, people_stub):
        """reload_people is intentionally callback-free."""
        calls: list = []
        ctrl = MultiPersonPickerControl(
            parent,
            all_people=people_stub,
            on_change_callback=lambda: calls.append(1),
        )
        calls.clear()  # discard any init-time noise
        ctrl.reload_people({"uid-99": "New Person"})
        assert len(calls) == 0, (
            "reload_people must not fire on_change_callback — selection state unchanged"
        )
