"""Menu state machine for AddPersonFrame.

Defines MenuMode enum and compute_menu_state() pure function so that:
  - The frame's _apply_menu_mode() delegates enable/disable decisions here.
  - Tests can import this module without wx being installed.

Key names match the SAVE_HANDLER_WHITELIST convention where applicable,
but these keys are menu-item labels (Polish), not handler names.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict


class MenuMode(Enum):
    NEW = "new"
    EDIT_TREE = "edit-tree"
    EDIT_DRAFT = "edit-draft"


# Key names used by _apply_menu_mode to map to wx menu-item references.
# These are stable identifiers — the Polish label visible to the user is
# stored on the frame's menu item, not here.
MENU_KEY_NEW_PERSON = "new_person"
MENU_KEY_SAVE_NEW = "save_new"           # "Zapisz osobę i dodaj do drzewa"
MENU_KEY_SAVE_AS_DRAFT = "save_as_draft"          # "Zapisz osobę jako szkic"
MENU_KEY_EDIT_FROM_TREE = "edit_from_tree"   # "Edytuj osobę z drzewa"
MENU_KEY_SET_ROOT = "set_root"          # "Ustaw osobę-korzeń drzewa"
MENU_KEY_SAVE_TREE_CHANGES = "save_tree_changes"        # "Zapisz zmiany dla osoby na drzewie"
MENU_KEY_LOAD_DRAFT = "load_draft"        # "Wczytaj szkic osoby"
MENU_KEY_UPDATE_DRAFT = "update_draft"  # "Zaktualizuj szkic osoby"
MENU_KEY_PROMOTE_DRAFT = "promote_draft"            # "Dodaj szkic osoby do drzewa"
MENU_KEY_REFRESH_FOLDER_TREE = "refresh_folder_tree"      # "Odśwież drzewo"
MENU_KEY_REFRESH_LINEAGE = "refresh_lineage"          # "Odśwież rody"
MENU_KEY_EXIT = "exit"                        # "Wyjdź"

# All menu keys in declaration order (for matrix completeness checks in tests)
ALL_MENU_KEYS = (
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


def compute_menu_state(mode: MenuMode) -> Dict[str, bool]:
    """Return the enable/disable matrix for all menu items given the current mode.

    Enable/disable matrix:

    | Action                       | NEW      | EDIT_TREE | EDIT_DRAFT |
    |------------------------------|----------|-----------|------------|
    | Nowa osoba                   | enabled  | enabled   | enabled    |
    | Zapisz osobę i dodaj...      | enabled  | disabled  | disabled   |
    | Zapisz osobę jako szkic      | enabled  | disabled  | disabled   |
    | Edytuj osobę z drzewa        | enabled  | enabled   | enabled    |
    | Ustaw osobę-korzeń drzewa    | enabled  | enabled   | enabled    |
    | Zapisz zmiany dla osoby...   | disabled | enabled   | disabled   |
    | Wczytaj szkic osoby          | enabled  | enabled   | enabled    |
    | Zaktualizuj szkic osoby      | disabled | disabled  | enabled    |
    | Dodaj szkic osoby do drzewa  | disabled | disabled  | enabled    |
    | Odśwież drzewo               | enabled  | enabled   | enabled    |
    | Odśwież rody                 | enabled  | enabled   | enabled    |
    | Wyjdź                        | enabled  | enabled   | enabled    |

    Raises:
        ValueError: If mode is not a recognised MenuMode member.
    """
    if not isinstance(mode, MenuMode):
        raise ValueError(f"Unknown mode: {mode!r}. Expected a MenuMode enum member.")

    # Always-enabled across all modes
    always_on = {
        MENU_KEY_NEW_PERSON: True,
        MENU_KEY_EDIT_FROM_TREE: True,
        MENU_KEY_SET_ROOT: True,
        MENU_KEY_LOAD_DRAFT: True,
        MENU_KEY_REFRESH_FOLDER_TREE: True,
        MENU_KEY_REFRESH_LINEAGE: True,
        MENU_KEY_EXIT: True,
    }

    if mode == MenuMode.NEW:
        return {
            **always_on,
            MENU_KEY_SAVE_NEW: True,
            MENU_KEY_SAVE_AS_DRAFT: True,
            MENU_KEY_SAVE_TREE_CHANGES: False,
            MENU_KEY_UPDATE_DRAFT: False,
            MENU_KEY_PROMOTE_DRAFT: False,
        }

    if mode == MenuMode.EDIT_TREE:
        return {
            **always_on,
            MENU_KEY_SAVE_NEW: False,
            MENU_KEY_SAVE_AS_DRAFT: False,
            MENU_KEY_SAVE_TREE_CHANGES: True,
            MENU_KEY_UPDATE_DRAFT: False,
            MENU_KEY_PROMOTE_DRAFT: False,
        }

    if mode == MenuMode.EDIT_DRAFT:
        return {
            **always_on,
            MENU_KEY_SAVE_NEW: False,
            MENU_KEY_SAVE_AS_DRAFT: False,
            MENU_KEY_SAVE_TREE_CHANGES: False,
            MENU_KEY_UPDATE_DRAFT: True,
            MENU_KEY_PROMOTE_DRAFT: True,
        }

    # Unreachable given the isinstance check above, but defensive:
    raise ValueError(f"Unhandled mode: {mode!r}")
