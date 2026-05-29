"""Date prefix markers — Przed (<) and Około (~) on birth/death dates (Sprint 21 / issue #25).

Verifies that:
1. Birth Przed + Około checkboxes round-trip through _build_optional_date /
   _deconstruct_optional_date: set both, build → "~<YYYY-MM-DD", deconstruct → okolo=True, przed=True.
2. A bare date "1942-03-24" loads without prefix (okolo=False, przed=False).
3. "~1900-XX-XX" → okolo=True, przed=False.
4. "<1900-XX-XX" → okolo=False, przed=True.
5. Death checkboxes are disabled when death date is not active.
6. Prefix-only with no date body → _build_optional_date returns None.
7. The "Około" label contains ł (U+0142).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import wx
import wx.adv

from src.frames.add_person_frame import AddPersonFrame


# ---------------------------------------------------------------------------
# Module-scoped wx infrastructure
# ---------------------------------------------------------------------------

_wx_app_for_prefix: wx.App | None = None
_wx_parent_for_prefix: wx.Frame | None = None


def _ensure_wx_app_for_prefix() -> wx.Frame:
    global _wx_app_for_prefix, _wx_parent_for_prefix
    if _wx_app_for_prefix is None:
        _wx_app_for_prefix = wx.App(False)
        _wx_parent_for_prefix = wx.Frame(None)
    return _wx_parent_for_prefix


# ---------------------------------------------------------------------------
# Helper: build a frame with isolated LOCALAPPDATA + temp tree root
# ---------------------------------------------------------------------------

def _make_frame(tmp_path: Path, monkeypatch) -> AddPersonFrame:
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

    parent = _ensure_wx_app_for_prefix()
    return AddPersonFrame(parent)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDatePrefixMarkers:
    """Przed / Około checkbox integration with date builder/deconstructor."""

    def test_birth_okolo_przed_round_trip(self, tmp_path, monkeypatch):
        """Set both Przed + Około, build a date string, deconstruct it back.

        Round-trip: checkboxes → _build_optional_date → "~<YYYY-MM-DD" form;
        then _deconstruct_optional_date → okolo=True, przed=True.
        """
        frame = _make_frame(tmp_path, monkeypatch)

        # Set checkboxes
        frame.birth_date_picker['okolo'].SetValue(True)
        frame.birth_date_picker['przed'].SetValue(True)

        # Pick a date so the body is non-empty: year_century=19, month=04
        frame.birth_date_picker['year_century'].SetStringSelection("19")
        frame.birth_date_picker['month'].SetStringSelection("04")

        result = frame._build_optional_date(
            frame.birth_date_picker,
            okolo=frame.birth_date_picker['okolo'].GetValue(),
            przed=frame.birth_date_picker['przed'].GetValue(),
        )
        assert result is not None, "_build_optional_date returned None with date fields set"
        assert result.startswith("~<"), f"Expected '~<' prefix, got: {result!r}"

        # Deconstruct back
        day, month, century, decade, unit, okolo_out, przed_out = (
            frame._deconstruct_optional_date(result)
        )
        assert okolo_out is True, f"Expected okolo=True after round-trip, got {okolo_out!r}"
        assert przed_out is True, f"Expected przed=True after round-trip, got {przed_out!r}"
        assert century == "19", f"Expected century '19', got {century!r}"

    def test_bare_date_loads_without_prefix(self, tmp_path, monkeypatch):
        """Bare date string '1942-03-24' must load with okolo=False, przed=False."""
        frame = _make_frame(tmp_path, monkeypatch)

        day, month, century, decade, unit, okolo, przed = (
            frame._deconstruct_optional_date("1942-03-24")
        )
        assert okolo is False, f"Expected okolo=False for bare date, got {okolo!r}"
        assert przed is False, f"Expected przed=False for bare date, got {przed!r}"
        assert century == "19"
        assert decade == "4"
        assert unit == "2"
        assert month == "03"
        assert day == "24"

    def test_okolo_only_prefix(self, tmp_path, monkeypatch):
        """'~1900-XX-XX' must decode to okolo=True, przed=False."""
        frame = _make_frame(tmp_path, monkeypatch)

        day, month, century, decade, unit, okolo, przed = (
            frame._deconstruct_optional_date("~1900-XX-XX")
        )
        assert okolo is True, f"Expected okolo=True for '~' prefix, got {okolo!r}"
        assert przed is False, f"Expected przed=False for '~' prefix, got {przed!r}"
        assert century == "19"
        assert decade == "0"
        assert unit == "0"

    def test_przed_only_prefix(self, tmp_path, monkeypatch):
        """'<1900-XX-XX' must decode to okolo=False, przed=True."""
        frame = _make_frame(tmp_path, monkeypatch)

        day, month, century, decade, unit, okolo, przed = (
            frame._deconstruct_optional_date("<1900-XX-XX")
        )
        assert okolo is False, f"Expected okolo=False for '<' prefix, got {okolo!r}"
        assert przed is True, f"Expected przed=True for '<' prefix, got {przed!r}"
        assert century == "19"

    def test_death_checkboxes_disabled_when_death_inactive(self, tmp_path, monkeypatch):
        """death_date_picker['przed'] and ['okolo'] must be disabled at frame creation."""
        frame = _make_frame(tmp_path, monkeypatch)

        # is_dead_checkbox defaults to False → death controls disabled
        assert not frame.is_dead_checkbox.GetValue(), (
            "is_dead_checkbox should be unchecked by default"
        )
        assert not frame.death_date_picker['przed'].IsEnabled(), (
            "death_date_picker['przed'] must be disabled when death is not active"
        )
        assert not frame.death_date_picker['okolo'].IsEnabled(), (
            "death_date_picker['okolo'] must be disabled when death is not active"
        )

    def test_prefix_only_no_body_returns_none(self, tmp_path, monkeypatch):
        """Checkboxes checked but no date dropdowns selected → _build_optional_date returns None."""
        frame = _make_frame(tmp_path, monkeypatch)

        # Both checkboxes on, but all dropdowns at index 0 (sentinel / placeholder)
        frame.birth_date_picker['okolo'].SetValue(True)
        frame.birth_date_picker['przed'].SetValue(True)
        # All dropdowns remain at their default (selection index 0 = hint placeholder)
        for key in ('day', 'month', 'year_century', 'year_decade', 'year_unit'):
            frame.birth_date_picker[key].SetSelection(0)

        result = frame._build_optional_date(
            frame.birth_date_picker,
            okolo=frame.birth_date_picker['okolo'].GetValue(),
            przed=frame.birth_date_picker['przed'].GetValue(),
        )
        assert result is None, (
            f"_build_optional_date must return None when no date fields are selected, "
            f"got {result!r}"
        )

    def test_okolo_label_codepoint(self, tmp_path, monkeypatch):
        """birth_date_picker['okolo'] label must contain 'Około' with ł (U+0142)."""
        frame = _make_frame(tmp_path, monkeypatch)

        label = frame.birth_date_picker['okolo'].GetLabel()
        assert "ł" in label, (
            f"Expected ł (U+0142) in 'okolo' checkbox label, got: {label!r}"
        )
        assert "Około" in label or "Około" in label, (
            f"Expected 'Około' in label, got: {label!r}"
        )
