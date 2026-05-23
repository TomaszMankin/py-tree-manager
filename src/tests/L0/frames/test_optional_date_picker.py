"""Optional date picker — day dropdown widget tests (Sprint 19 / issue #8).

Verifies that:
1. The 'day' dropdown is a wx.adv.OwnerDrawnComboBox (not a plain wx.ComboBox).
2. The 'day' dropdown has SetPopupMaxHeight set to a non-default (<= 500) value.
3. The 'day' dropdown still contains exactly 33 items in the correct order.
4. The death-date 'day' dropdown is also an OwnerDrawnComboBox.
5. All other date dropdowns (month, year_century, year_decade, year_unit) remain
   wx.ComboBox instances — the swap is surgical, day only.

Fixture pattern: module-scoped wx.App + wx.Frame (same approach as
test_multi_person_picker_control.py). A real AddPersonFrame is instantiated once
per test class (it needs wx + a writable LOCALAPPDATA and tempdir, which
monkeypatch provides per-test — but the frame is built once outside test methods).

Since AddPersonFrame.__init__ calls TreeService which may read LOCALAPPDATA, the
frame is constructed inside a method that patches those paths first.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import wx
import wx.adv

from src.frames.add_person_frame import AddPersonFrame


# ---------------------------------------------------------------------------
# Module-scoped wx infrastructure — one App + one invisible Frame per session
# ---------------------------------------------------------------------------

_wx_app_for_picker: wx.App | None = None
_wx_parent_for_picker: wx.Frame | None = None


def _ensure_wx_app_for_picker() -> wx.Frame:
    global _wx_app_for_picker, _wx_parent_for_picker
    if _wx_app_for_picker is None:
        _wx_app_for_picker = wx.App(False)
        _wx_parent_for_picker = wx.Frame(None)
    return _wx_parent_for_picker


# ---------------------------------------------------------------------------
# Helper: build a frame with a temp tree root so FileService bootstraps cleanly
# ---------------------------------------------------------------------------

def _make_frame(tmp_path: Path, monkeypatch) -> AddPersonFrame:
    """Instantiate AddPersonFrame with isolated LOCALAPPDATA + tempdir."""
    import tempfile as _tempfile

    app_tmp = tmp_path / "apptmp"
    app_tmp.mkdir(exist_ok=True)
    monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

    appdata = tmp_path / "appdata"
    appdata.mkdir(exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))

    tree_root = tmp_path / "tree"
    tree_root.mkdir()

    from src.services.tree_service import TreeService
    ts = TreeService()
    ts.set_root_location(str(tree_root))

    parent = _ensure_wx_app_for_picker()
    return AddPersonFrame(parent)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDayDropdownWidgetType:
    """Day dropdown must be wx.adv.OwnerDrawnComboBox (issue #8 fix)."""

    def test_day_dropdown_is_owner_drawn_combo_box(self, tmp_path, monkeypatch):
        """birth_date_picker['day'] must be wx.adv.OwnerDrawnComboBox."""
        frame = _make_frame(tmp_path, monkeypatch)
        day_widget = frame.birth_date_picker['day']
        assert isinstance(day_widget, wx.adv.OwnerDrawnComboBox), (
            f"Expected wx.adv.OwnerDrawnComboBox, got {type(day_widget).__name__}"
        )

    def test_day_dropdown_has_popup_max_height_set(self, tmp_path, monkeypatch):
        """DAY_DROPDOWN_POPUP_MAX_HEIGHT_PX must be defined, > 0, and <= 500.

        wx.adv.OwnerDrawnComboBox exposes SetPopupMaxHeight() (inherited from
        wx.ComboCtrl) but this version of wxPython does not expose a corresponding
        GetPopupMaxHeight() getter.  We therefore verify the module-level constant
        that drives the SetPopupMaxHeight() call: it must be in (0, 500] and the
        widget must be the class that supports the cap (OwnerDrawnComboBox).
        """
        from src.frames.add_person_frame import DAY_DROPDOWN_POPUP_MAX_HEIGHT_PX
        assert DAY_DROPDOWN_POPUP_MAX_HEIGHT_PX > 0, (
            "DAY_DROPDOWN_POPUP_MAX_HEIGHT_PX must be positive"
        )
        assert DAY_DROPDOWN_POPUP_MAX_HEIGHT_PX <= 500, (
            f"DAY_DROPDOWN_POPUP_MAX_HEIGHT_PX should be <= 500 px "
            f"(got {DAY_DROPDOWN_POPUP_MAX_HEIGHT_PX})"
        )
        # Also confirm the widget class supports the cap method (SetPopupMaxHeight
        # is only available on wx.adv.OwnerDrawnComboBox / wx.ComboCtrl hierarchy,
        # not on plain wx.ComboBox).
        frame = _make_frame(tmp_path, monkeypatch)
        day_widget = frame.birth_date_picker['day']
        assert hasattr(day_widget, 'SetPopupMaxHeight'), (
            "day dropdown must be a class that has SetPopupMaxHeight "
            "(wx.adv.OwnerDrawnComboBox or subclass)"
        )

    def test_day_dropdown_contains_all_31_days_plus_sentinels(self, tmp_path, monkeypatch):
        """birth_date_picker['day'] must have 33 items: 'Dzień', 'XX', '01'..'31'."""
        frame = _make_frame(tmp_path, monkeypatch)
        day_widget = frame.birth_date_picker['day']
        count = day_widget.GetCount()
        assert count == 33, f"Expected 33 items, got {count}"
        assert day_widget.GetString(0) == "Dzień", (
            f"First item must be 'Dzień', got '{day_widget.GetString(0)}'"
        )
        assert day_widget.GetString(count - 1) == "31", (
            f"Last item must be '31', got '{day_widget.GetString(count - 1)}'"
        )

    def test_death_day_dropdown_also_owner_drawn(self, tmp_path, monkeypatch):
        """death_date_picker['day'] must also be wx.adv.OwnerDrawnComboBox."""
        frame = _make_frame(tmp_path, monkeypatch)
        day_widget = frame.death_date_picker['day']
        assert isinstance(day_widget, wx.adv.OwnerDrawnComboBox), (
            f"Expected wx.adv.OwnerDrawnComboBox for death_date_picker['day'], "
            f"got {type(day_widget).__name__}"
        )

    def test_other_date_dropdowns_remain_wx_combobox(self, tmp_path, monkeypatch):
        """month/year_century/year_decade/year_unit must remain plain wx.ComboBox.

        wx.adv.OwnerDrawnComboBox descends from wx.ComboCtrl, NOT from wx.ComboBox;
        the two are unrelated by class lineage. This test locks the surgical-scope
        invariant: only 'day' was swapped, the other four dropdowns are untouched.
        """
        frame = _make_frame(tmp_path, monkeypatch)
        for key in ('month', 'year_century', 'year_decade', 'year_unit'):
            picker = frame.birth_date_picker[key]
            assert isinstance(picker, wx.ComboBox), (
                f"birth_date_picker['{key}'] should be wx.ComboBox, got {type(picker).__name__}"
            )
            assert not isinstance(picker, wx.adv.OwnerDrawnComboBox), (
                f"birth_date_picker['{key}'] must NOT be OwnerDrawnComboBox — "
                "the day-only swap must not affect other date dropdowns"
            )
