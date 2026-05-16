"""Context-menu state machine tests.

Covers compute_menu_state() pure-function correctness and a Polish-label
codepoint check on add_person_frame.py source.

All tests are wx-free (no mainloop required).
"""

import pathlib
import pytest

from src.frames.menu_state import (
    MenuMode,
    compute_menu_state,
    ALL_MENU_KEYS,
    MENU_KEY_NEW_PERSON,
    MENU_KEY_SAVE_NEW,
    MENU_KEY_SAVE_AS_DRAFT,
    MENU_KEY_EDIT_FROM_TREE,
    MENU_KEY_SET_ROOT,
    MENU_KEY_SAVE_TREE_CHANGES,
    MENU_KEY_LOAD_DRAFT,
    MENU_KEY_UPDATE_DRAFT,
    MENU_KEY_PROMOTE_DRAFT,
    MENU_KEY_REFRESH_FOLDER_TREE,
    MENU_KEY_REFRESH_LINEAGE,
    MENU_KEY_EXIT,
)

# Path to the source file for codepoint checks
_FRAME_SOURCE = (
    pathlib.Path(__file__).parent.parent.parent / "frames" / "add_person_frame.py"
)

# ---------------------------------------------------------------------------
# State-machine matrix
# ---------------------------------------------------------------------------

class TestComputeMenuStateNEW:
    """NEW mode enable/disable matrix."""

    def test_new_mode_section1_saves_enabled(self):
        state = compute_menu_state(MenuMode.NEW)
        assert state[MENU_KEY_SAVE_NEW] is True, "Section 1 'Zapisz osobę i dodaj...' must be enabled in NEW"
        assert state[MENU_KEY_SAVE_AS_DRAFT] is True, "Section 1 'Zapisz osobę jako szkic' must be enabled in NEW"

    def test_new_mode_section2_save_disabled(self):
        state = compute_menu_state(MenuMode.NEW)
        assert state[MENU_KEY_SAVE_TREE_CHANGES] is False, "Section 2 'Zapisz zmiany...' must be DISABLED in NEW"

    def test_new_mode_section3_draft_actions_disabled(self):
        state = compute_menu_state(MenuMode.NEW)
        assert state[MENU_KEY_UPDATE_DRAFT] is False, "'Zaktualizuj szkic' must be DISABLED in NEW"
        assert state[MENU_KEY_PROMOTE_DRAFT] is False, "'Dodaj szkic...' must be DISABLED in NEW"

    def test_new_mode_always_on_items_enabled(self):
        state = compute_menu_state(MenuMode.NEW)
        for key in (
            MENU_KEY_NEW_PERSON,
            MENU_KEY_EDIT_FROM_TREE,
            MENU_KEY_SET_ROOT,
            MENU_KEY_LOAD_DRAFT,
            MENU_KEY_REFRESH_FOLDER_TREE,
            MENU_KEY_REFRESH_LINEAGE,
            MENU_KEY_EXIT,
        ):
            assert state[key] is True, f"Always-on key '{key}' must be enabled in NEW"

    def test_new_mode_covers_all_keys(self):
        state = compute_menu_state(MenuMode.NEW)
        for key in ALL_MENU_KEYS:
            assert key in state, f"Key '{key}' missing from NEW state matrix"


class TestComputeMenuStateEDIT_TREE:
    """EDIT_TREE mode enable/disable matrix."""

    def test_edit_tree_only_section2_save_enabled(self):
        state = compute_menu_state(MenuMode.EDIT_TREE)
        assert state[MENU_KEY_SAVE_TREE_CHANGES] is True, "'Zapisz zmiany...' must be enabled in EDIT_TREE"

    def test_edit_tree_section1_saves_disabled(self):
        state = compute_menu_state(MenuMode.EDIT_TREE)
        assert state[MENU_KEY_SAVE_NEW] is False, "Section 1 'Zapisz osobę i dodaj...' must be DISABLED in EDIT_TREE"
        assert state[MENU_KEY_SAVE_AS_DRAFT] is False, "Section 1 'Zapisz osobę jako szkic' must be DISABLED in EDIT_TREE"

    def test_edit_tree_section3_draft_actions_disabled(self):
        state = compute_menu_state(MenuMode.EDIT_TREE)
        assert state[MENU_KEY_UPDATE_DRAFT] is False, "'Zaktualizuj szkic' must be DISABLED in EDIT_TREE"
        assert state[MENU_KEY_PROMOTE_DRAFT] is False, "'Dodaj szkic...' must be DISABLED in EDIT_TREE"

    def test_edit_tree_covers_all_keys(self):
        state = compute_menu_state(MenuMode.EDIT_TREE)
        for key in ALL_MENU_KEYS:
            assert key in state, f"Key '{key}' missing from EDIT_TREE state matrix"


class TestComputeMenuStateEDIT_DRAFT:
    """EDIT_DRAFT mode enable/disable matrix."""

    def test_edit_draft_section3_both_draft_actions_enabled(self):
        state = compute_menu_state(MenuMode.EDIT_DRAFT)
        assert state[MENU_KEY_UPDATE_DRAFT] is True, "'Zaktualizuj szkic' must be enabled in EDIT_DRAFT"
        assert state[MENU_KEY_PROMOTE_DRAFT] is True, "'Dodaj szkic...' must be enabled in EDIT_DRAFT"

    def test_edit_draft_section1_saves_disabled(self):
        state = compute_menu_state(MenuMode.EDIT_DRAFT)
        assert state[MENU_KEY_SAVE_NEW] is False, "Section 1 saves must be DISABLED in EDIT_DRAFT"
        assert state[MENU_KEY_SAVE_AS_DRAFT] is False, "Section 1 saves must be DISABLED in EDIT_DRAFT"

    def test_edit_draft_section2_save_disabled(self):
        state = compute_menu_state(MenuMode.EDIT_DRAFT)
        assert state[MENU_KEY_SAVE_TREE_CHANGES] is False, "Section 2 save must be DISABLED in EDIT_DRAFT"

    def test_edit_draft_covers_all_keys(self):
        state = compute_menu_state(MenuMode.EDIT_DRAFT)
        for key in ALL_MENU_KEYS:
            assert key in state, f"Key '{key}' missing from EDIT_DRAFT state matrix"


class TestComputeMenuStateAllModesLoadActionsEnabled:
    """Load/navigation actions are always enabled across all modes."""

    @pytest.mark.parametrize("mode", list(MenuMode))
    def test_new_person_always_enabled(self, mode):
        assert compute_menu_state(mode)[MENU_KEY_NEW_PERSON] is True

    @pytest.mark.parametrize("mode", list(MenuMode))
    def test_edit_from_tree_always_enabled(self, mode):
        assert compute_menu_state(mode)[MENU_KEY_EDIT_FROM_TREE] is True

    @pytest.mark.parametrize("mode", list(MenuMode))
    def test_load_draft_always_enabled(self, mode):
        assert compute_menu_state(mode)[MENU_KEY_LOAD_DRAFT] is True

    @pytest.mark.parametrize("mode", list(MenuMode))
    def test_refresh_folder_tree_always_enabled(self, mode):
        assert compute_menu_state(mode)[MENU_KEY_REFRESH_FOLDER_TREE] is True

    @pytest.mark.parametrize("mode", list(MenuMode))
    def test_exit_always_enabled(self, mode):
        assert compute_menu_state(mode)[MENU_KEY_EXIT] is True


class TestComputeMenuStateUnknownMode:
    """Defensive: passing a non-MenuMode raises ValueError."""

    def test_string_raises_value_error(self):
        with pytest.raises(ValueError):
            compute_menu_state("new")  # type: ignore[arg-type]

    def test_none_raises_value_error(self):
        with pytest.raises(ValueError):
            compute_menu_state(None)  # type: ignore[arg-type]

    def test_int_raises_value_error(self):
        with pytest.raises(ValueError):
            compute_menu_state(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Polish-label codepoint check
#
# Read frames/add_person_frame.py as text and assert each menu label is
# present verbatim. Catches ASCII-transliteration drift in diacritics.
# ---------------------------------------------------------------------------

class TestMenuLabelDiacritics:
    """Assert all 9 menu labels appear verbatim in the frame source."""

    @pytest.fixture(scope="class")
    def frame_source(self):
        return _FRAME_SOURCE.read_text(encoding="utf-8")

    # Section 1
    def test_new_person_present(self, frame_source):
        assert "Nowa osoba" in frame_source

    def test_save_new_person_present(self, frame_source):
        # ę (U+0119) in "osobę"
        assert "Zapisz osobę i dodaj do drzewa" in frame_source

    def test_save_as_draft_present(self, frame_source):
        # ę (U+0119) in "osobę"
        assert "Zapisz osobę jako szkic" in frame_source

    # Section 2
    def test_edit_from_tree_present(self, frame_source):
        # ę (U+0119) in "osobę"
        assert "Edytuj osobę z drzewa" in frame_source

    def test_set_root_present(self, frame_source):
        # ę (U+0119) in "osobę", ń (U+0144) in "korzeń"
        assert "Ustaw osobę-korzeń drzewa" in frame_source

    def test_save_tree_changes_dla_osoby_present(self, frame_source):
        assert "Zapisz zmiany dla osoby na drzewie" in frame_source

    # Section 3
    def test_load_draft_osoby_present(self, frame_source):
        assert "Wczytaj szkic osoby" in frame_source

    def test_update_draft_osoby_present(self, frame_source):
        assert "Zaktualizuj szkic osoby" in frame_source

    def test_promote_draft_osoby_do_drzewa_present(self, frame_source):
        assert "Dodaj szkic osoby do drzewa" in frame_source

    def test_e_with_ogonek_codepoint_correct(self, frame_source):
        """ę must be U+0119, not the ASCII 'e' transliteration."""
        # 'osobe' without diacritic should NOT appear in any of our new labels
        # (It may appear in comments, but the string literals must use ę)
        import re
        # Find all Append calls with menu strings in the new 3-section block
        new_labels = [
            "Zapisz osobę i dodaj do drzewa",
            "Zapisz osobę jako szkic",
            "Edytuj osobę z drzewa",
            "Ustaw osobę-korzeń drzewa",
            "Zaktualizuj szkic osoby",
            "Dodaj szkic osoby do drzewa",
        ]
        for label in new_labels:
            assert label in frame_source, f"Label not found verbatim: {label!r}"

    def test_n_with_acute_codepoint_correct(self, frame_source):
        """ń must be U+0144 in 'korzeń', not ASCII 'n'."""
        assert "korzeń" in frame_source, "korzeń must use ń (U+0144)"

    def test_person_degradation_comment_present(self, frame_source):
        """Forward-compat 'person degradation' comment must be present in the frame source."""
        assert "person degradation" in frame_source
