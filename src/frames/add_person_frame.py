from pathlib import Path
from typing import Any, Callable, List, Tuple, Dict, Optional
import uuid
import wx
import wx.adv
import re

from src.frames.controls.auto_resize_text_box_control import AutoResizeTextCtrl
from src.frames.controls.multi_person_picker_control import MultiPersonPickerControl
import src.constants.constants as CONSTANTS
from src.frames.dialogs.draft_picker_dialog import DraftPickerDialog
from src.frames.dialogs.polish_dialog import polish_dialog
from src.frames.dialogs.root_person_picker_dialog import RootPersonPickerDialog
from src.wrappers.person_data_wrapper import PersonDataProperty, PersonDataWrapper
from src.services.tree_service import TreeService
import json
from src.helpers.logger import log_user_action, set_current_person_label, log_error, init_logging, log_cleanup_failure, PERSON_PLACEHOLDER
from src.frames.menu_state import MenuMode, compute_menu_state

# Issue #8: day dropdown popup must scroll, not screen-clip.  wx.ComboBox uses
# the native Win32 ComboBox whose popup is positioned by the OS and clipped at
# the screen edge — at font_size=20 with 33 items the popup overflows 1920x1080
# screens and days 25-31 become unreachable.  wx.adv.OwnerDrawnComboBox uses an
# internal VListBox popup whose height SetPopupMaxHeight caps, forcing a
# scrollbar regardless of screen position.  400 px ≈ 10 rows at font_size=20.
DAY_DROPDOWN_POPUP_MAX_HEIGHT_PX = 400


class AddPersonFrame(wx.Frame):
    """
    Main frame for adding a new person to the family tree.

    This frame provides a form with:
    - Basic information fields (names, sex, dates)
    - Notes section
    - Relationship pickers (parents, children, spouses, siblings)
    """

    UNKNOWN = "(nieznane)"

    # Mode visuals — background colors and Polish labels for the three form modes.
    # Material 50-shade hues; distinct from all four relationship-picker hues
    # (#E3F2FD, #E8F5E9, #FCE4EC, #FFF3E0).
    MODE_ADD_NEW    = ('add-new',    '#F3E5F5', 'Dodawanie nowej osoby')   # Material Purple 50
    MODE_EDIT_TREE  = ('edit-tree',  '#E0F7FA', 'Edycja osoby z drzewa')   # Material Cyan 50
    MODE_EDIT_DRAFT = ('edit-draft', '#F9FBE7', 'Edycja szkicu osoby')     # Material Lime 50

    def __init__(self, parent: Optional[wx.Window]) -> None:
        """
        Initialize the Add Person frame.

        Args:
            parent: Parent window, or None for top-level frame
        """
        super().__init__(parent, title="Dodaj osobę do drzewa", size=(1000, 800))
        self._tree_service = TreeService()

        if not self._tree_service.is_root_location_set():
            folder_path = self.select_folder()

            if folder_path is not None:
                self._tree_service.set_root_location(folder_path)
                init_logging(root_folder=Path(folder_path))
            else:
                raise RuntimeError("Root folder has to be selected or set.")
            
                    
        self.ALL_PEOPLE: Dict[str, str] = {
            uid: person[PersonDataProperty.PERSON_NAME.value]
            for uid, person in self._tree_service.list_of_people.items()
        }

        # Font size from settings — used throughout _create_* helpers.
        # Default 20 matches CLAUDE.md spec; get_font_size() returns None when
        # the settings file has no entry yet.
        font_size_setting: int = self._tree_service._file_service.get_settings().get_font_size() or 20
        self._font_size: int = font_size_setting
        # Header/title font: proportional bump of +6 matches current constants ratio
        # (HEADER_SIZE=24, PARAGRAPH_SIZE=18 => gap of 6).
        self._header_size: int = font_size_setting + 6

        self._create_menu()
        # Status bar for click feedback — must be called before Maximize()
        # so the frame layout accounts for it.
        self.CreateStatusBar()

        self.root_panel = wx.ScrolledWindow(self)
        self.root_panel.SetBackgroundColour("#F5F5F5")  # Light gray background for contrast

        # Red "Zgłoś błąd" error-report button.
        self._report_button = self._create_report_button()

        basic_info_and_notes_section = self._create_basic_info_and_notes_section()

        pickers_box_sizer = self._create_relation_pickers_section()

        # Mode header strip (U2)
        self._mode_label = wx.StaticText(self.root_panel, label="Dodawanie nowej osoby")
        mode_font = wx.Font(self._header_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self._mode_label.SetFont(mode_font)

        # ===== ASSEMBLE LAYOUT =====
        # Report button row at the very top, right-aligned.
        report_button_row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        report_button_row_sizer.AddStretchSpacer()
        report_button_row_sizer.Add(
            self._report_button, 0,
            wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5,
        )

        sections_sizer = wx.BoxSizer(wx.VERTICAL)
        sections_sizer.Add(report_button_row_sizer, 0, wx.EXPAND | wx.ALL, 5)  # NEW: top row
        sections_sizer.Add(self._mode_label, 0, wx.ALL | wx.EXPAND, 10)
        sections_sizer.Add(wx.StaticLine(self.root_panel), 0, wx.EXPAND | wx.ALL, 5)
        sections_sizer.Add(basic_info_and_notes_section, 0, wx.ALL | wx.EXPAND, 10)
        sections_sizer.Add(wx.StaticLine(self.root_panel), 0, wx.EXPAND | wx.ALL, 5)
        sections_sizer.Add(pickers_box_sizer, 1, wx.EXPAND | wx.ALL, 10)

        self.root_panel.SetSizer(sections_sizer)
        self.root_panel.SetScrollRate(0, 20)
        self.Layout()

        # Apply font size from settings at the frame level as a catch-all for any
        # controls the _create_* helpers may have missed.
        self.SetFont(wx.Font(
            self._font_size,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        ))

        # Person-specific variables — UUID generated once on open, reused for drafts and final save
        self.location: str = ''
        self.unique_identifier: str = str(uuid.uuid4())
        # Path of the currently loaded draft file; None when in NEW or EDIT_TREE mode.
        self._loaded_draft_path: Optional[str] = None

        # 3-mode state machine.  _menu_mode is the single source of truth.
        self._menu_mode: MenuMode = MenuMode.NEW

        # Edit-mode state — populated when a person is loaded for editing
        # _is_edit_mode is kept as a @property alias for back-compat.
        self._original_name: str = ''
        self._original_relationships: Dict[str, List[str]] = {}

        # Dirty tracking — set True on any form change; cleared on successful save/load
        self._is_dirty: bool = False
        self._wire_dirty_tracking()
        self.Bind(wx.EVT_CLOSE, self._on_close)

        # Sentinel for the journey-log decorator.
        # Updated at every person-state transition by set_current_person_label().
        self._current_person_label: str = PERSON_PLACEHOLDER

        self.Maximize()
        # Initialize state machine to NEW on launch.
        # _apply_menu_mode calls _apply_mode_visuals internally, so the separate
        # call below is redundant — but kept for clarity and because _apply_mode_visuals
        # is called first as a safe fallback if menu items aren't wired yet.
        self._apply_mode_visuals('add-new')
        self._apply_menu_mode(MenuMode.NEW)

    def select_folder(self) -> str | None:
        dialog = wx.DirDialog(
            self,
            message="Wybierz folder gdzie Twoje drzewo ma się znajdować",
            defaultPath="",
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
        )

        if dialog.ShowModal() == wx.ID_OK:
            selected_path = dialog.GetPath()
            dialog.Destroy()
            return selected_path
        else:
            dialog.Destroy()
            return None

    def on_relationship_change(self, event: wx.Event) -> None:
        """
        Called when any picker's selection changes - update all pickers.

        Args:
            event: The wx event that triggered this callback
        """
        self.update_all_picker_exclusions()

    def update_all_picker_exclusions(self) -> None:
        """
        Update each picker to exclude people selected in other pickers.

        This ensures a person can only appear in one relationship category at a time.
        """

        # Gather all selected people from all pickers
        parents_selected = self.parents_picker.get_selected_people()
        children_selected = self.children_picker.get_selected_people()
        spouses_selected = self.spouses_picker.get_selected_people()
        siblings_selected = self.siblings_picker.get_selected_people()

        # Each picker excludes people selected in OTHER pickers
        self.parents_picker.set_excluded_people(
            children_selected + spouses_selected + siblings_selected
        )
        self.children_picker.set_excluded_people(
            parents_selected + spouses_selected + siblings_selected
        )
        self.spouses_picker.set_excluded_people(
            parents_selected + children_selected + siblings_selected
        )
        self.siblings_picker.set_excluded_people(
            parents_selected + children_selected + spouses_selected
        )

    def _create_basic_info_and_notes_section(self) -> wx.GridBagSizer:
        """
        Create the top section containing basic info form and notes.

        Returns:
            GridBagSizer with basic info (2/3 width) and notes (1/3 width)
        """
        basic_info_grid = self._create_basic_info_grid()
        notes_grid = self._create_notes_grid()
        upper_section_grid = wx.GridBagSizer(hgap=10, vgap=5)

        upper_section_grid.Add(basic_info_grid, pos=(0,0), flag=wx.EXPAND)
        upper_section_grid.Add(notes_grid, pos=(0,1), flag=wx.EXPAND)

        upper_section_grid.AddGrowableCol(0, proportion=2)
        upper_section_grid.AddGrowableCol(1, proportion=1)
        upper_section_grid.AddGrowableRow(0)

        return upper_section_grid

    def _create_basic_info_grid(self) -> wx.GridBagSizer:
        """
        Create the grid with name fields, sex, and date pickers.

        Returns:
            GridBagSizer containing all basic person information fields
        """
        basic_info_grid = wx.GridBagSizer(hgap=5, vgap=5)

        # First name
        self.first_name_text_box: wx.TextCtrl = self._add_form_field(
            basic_info_grid, 
            row=1, 
            label_text="Imię:",
            control_creator=lambda parent: self._create_single_line_text_control(
                parent, 
                self._font_size
            )
        )

        # Other first names
        self.other_first_names_text_box: AutoResizeTextCtrl = self._add_form_field(
            basic_info_grid, 
            row=2, 
            label_text="Pozostałe imiona:",
            control_creator=lambda parent: self._create_multi_line_text_control(
                parent, 
                "Wpisz kolejne imiona, każde w nowej linii...", 
                self._font_size
            )
        )

        # Last name
        self.last_name_text_box: wx.TextCtrl = self._add_form_field(
            basic_info_grid, 
            row=3, 
            label_text="Nazwisko:",
            control_creator=lambda parent: self._create_single_line_text_control(
                parent, 
                self._font_size
            )
        )

        # Other last names
        self.other_last_names_text_box: AutoResizeTextCtrl = self._add_form_field(
            basic_info_grid, 
            row=4, 
            label_text="Inne nazwiska:",
            control_creator=lambda parent: self._create_multi_line_text_control(
                parent, 
                "Wpisz kolejne nazwiska, każde w nowej linii...", 
                self._font_size
            )
        )

        # Has maiden name?
        self.has_maiden_name_checkbox: wx.CheckBox = self._add_form_field(
            basic_info_grid,
            row=5,
            label_text="Ma nazwisko panieńskie:",
            control_creator=lambda parent: self._create_check_box_control(
                parent,
                "",
                self._font_size)
        )

        self.has_maiden_name_checkbox.Bind(wx.EVT_CHECKBOX, self.on_maiden_name_toggle)

        # Maiden name
        self.maiden_name_text_box: wx.TextCtrl = self._add_form_field(
            basic_info_grid, 
            row=6, 
            label_text="Nazwisko panieńskie:",
            control_creator=lambda parent: self._create_single_line_text_control(
                parent, 
                self._font_size
            )
        )

        self.maiden_name_text_box.Enable(False)


        # Other maiden names
        self.other_maiden_names_text_box: AutoResizeTextCtrl = self._add_form_field(
            basic_info_grid,
            row=7,
            label_text="Inne nazwiska panieńskie:",
            control_creator=lambda parent: self._create_multi_line_text_control(
                parent,
                "",  # Start with no hint - will be set when checkbox is checked
                self._font_size
            )
        )

        self.other_maiden_names_text_box.Enable(False)

        # Sex
        self.sex_dropdown: wx.ComboBox = self._add_form_field(
            basic_info_grid, 
            row=8, 
            label_text="Płeć:",
            control_creator=lambda parent: self._create_dropdown_control(
                parent, 
                ["Nieznana", "Kobieta", "Mężczyzna"], 
                self._font_size
            )
        )

        # Birth date
        self.birth_date_picker: Dict[str, wx.ComboBox] = self._add_form_field(
            basic_info_grid, 
            row=9, 
            label_text="Data urodzin:",
            control_creator=lambda parent: self._create_optional_date_picker(
                parent, 
                self._font_size
            )
        )

        # Is dead
        self.is_dead_checkbox: wx.CheckBox = self._add_form_field(
            basic_info_grid,
            row=10,
            label_text="Osoba nieżyje:",
            control_creator=lambda parent: self._create_check_box_control(
                parent,
                "",
                self._font_size)
        )

        self.is_dead_checkbox.Bind(wx.EVT_CHECKBOX, self.on_is_dead_toggle)

        # Death date
        self.death_date_picker: Dict[str, wx.ComboBox] = self._add_form_field(
            basic_info_grid, 
            row=11, 
            label_text="Data śmierci:",
            control_creator=lambda parent: self._create_optional_date_picker(
                parent, 
                self._font_size
            )
        )

        for combo_box in self.death_date_picker.values():
            combo_box.Enable(False)
        
        basic_info_grid.AddGrowableCol(1)

        return basic_info_grid

    def _create_notes_grid(self) -> wx.GridBagSizer:
        """
        Create the notes section grid with title and multiline textbox.

        Returns:
            GridBagSizer containing notes title and text area
        """
        notes_grid = wx.GridBagSizer(hgap=5, vgap=5)

        notes_title_sizer = self._create_frame_label_with_sizer(self.root_panel, "Notatki:", self._header_size, bold=True)
        self.notes_textbox, notes_textbox_sizer = self._create_multi_line_textbox_control(self.root_panel, self._font_size)

        notes_grid.Add(notes_title_sizer, pos=(0, 0))
        notes_grid.Add(notes_textbox_sizer, pos=(1, 0), flag=wx.EXPAND)
        notes_grid.AddGrowableCol(0)
        notes_grid.AddGrowableRow(1)

        return notes_grid

    def _create_relation_pickers_section(self) -> wx.BoxSizer:
        """
        Create the 2x2 grid of relationship pickers with separators.

        Creates four color-coded picker panels for:
        - Parents (blue)
        - Spouses (pink)
        - Children (green)
        - Siblings (orange)

        Returns:
            BoxSizer containing the entire relationship section with label
        """

        # Create pickers with labels and distinctive colors
        self.parents_picker: MultiPersonPickerControl = MultiPersonPickerControl(
            self.root_panel,
            self.ALL_PEOPLE,
            header_size=self._header_size,
            font_size=self._font_size,
            on_change_callback=self.update_all_picker_exclusions,
            label="Rodzice",
            bg_color="#E3F2FD"  # Light blue for parents
        )
        self.children_picker: MultiPersonPickerControl = MultiPersonPickerControl(
            self.root_panel,
            self.ALL_PEOPLE,
            header_size=self._header_size,
            font_size=self._font_size,
            on_change_callback=self.update_all_picker_exclusions,
            label="Dzieci",
            bg_color="#E8F5E9"  # Light green for children
        )
        self.spouses_picker: MultiPersonPickerControl = MultiPersonPickerControl(
            self.root_panel,
            self.ALL_PEOPLE,
            header_size=self._header_size,
            font_size=self._font_size,
            on_change_callback=self.update_all_picker_exclusions,
            label="Małżonkowie",
            bg_color="#FCE4EC"  # Light pink for spouses
        )
        self.siblings_picker: MultiPersonPickerControl = MultiPersonPickerControl(
            self.root_panel,
            self.ALL_PEOPLE,
            header_size=self._header_size,
            font_size=self._font_size,
            on_change_callback=self.update_all_picker_exclusions,
            label="Rodzeństwo",
            bg_color="#FFF3E0"  # Light orange for siblings
        )

        pickers_box_sizer = wx.BoxSizer(wx.VERTICAL)

        top_row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_row_sizer.Add(self.parents_picker, 1, wx.EXPAND | wx.ALL, 5)
        top_row_sizer.Add(wx.StaticLine(self.root_panel, style=wx.LI_VERTICAL), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        top_row_sizer.Add(self.spouses_picker, 1, wx.EXPAND | wx.ALL, 5)

        horiz_sep = wx.StaticLine(self.root_panel, style=wx.LI_HORIZONTAL)

        bottom_row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bottom_row_sizer.Add(self.children_picker, 1, wx.EXPAND | wx.ALL, 5)
        bottom_row_sizer.Add(wx.StaticLine(self.root_panel, style=wx.LI_VERTICAL), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        bottom_row_sizer.Add(self.siblings_picker, 1, wx.EXPAND | wx.ALL, 5)

        relationship_label = self._create_frame_label(self.root_panel, "Relacje rodzinne", self._header_size, CONSTANTS.MAX_LABEL_WIDTH * 3, bold=True)

        pickers_box_sizer.Add(relationship_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)
        pickers_box_sizer.Add(top_row_sizer, 1, wx.EXPAND)
        pickers_box_sizer.Add(horiz_sep, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        pickers_box_sizer.Add(bottom_row_sizer, 1, wx.EXPAND)

        return pickers_box_sizer

    def _add_form_field(
        self,
        grid: wx.GridBagSizer,
        row: int,
        label_text: str,
        control_creator: Callable[[wx.Window], Tuple[wx.Control, wx.Sizer]]
    ) -> wx.Control:
        """
        Add a label + control pair to the grid at the specified row.

        This helper method reduces repetition when building forms by handling
        the label and control creation/positioning in one call.

        Args:
            grid: The GridBagSizer to add to
            row: Row number (0-based)
            label_text: Text for the label (e.g., "Imię:")
            control_creator: A callable that takes (parent) and returns (control, sizer).
                           Use a lambda to pass additional arguments to control factories.

        Returns:
            The created control (so it can be stored as instance variable)
        """
        # Add label to column 0
        label_sizer = self._create_frame_label_with_sizer(
            self.root_panel, label_text, self._font_size
        )
        grid.Add(
            label_sizer,
            pos=(row, 0),
            flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT | wx.RIGHT,
            border=8
        )

        # Add control to column 1
        control, control_sizer = control_creator(self.root_panel)  # Just pass parent
        grid.Add(
            control_sizer,
            pos=(row, 1),
            flag=wx.EXPAND | wx.RIGHT,
            border=50
        )

        return control

    def _create_frame_label(
        self,
        parent: wx.Window,
        label_text: str,
        font_size: int,
        max_width: int = CONSTANTS.MAX_LABEL_WIDTH,
        bold: bool = False
    ) -> wx.StaticText:
        """
        Create a static text label with custom font settings.

        Args:
            parent: Parent window
            label_text: Text to display
            font_size: Font size in points
            max_width: Maximum width before wrapping (default: CONSTANTS.MAX_LABEL_WIDTH)
            bold: Whether to make the text bold (default: False)

        Returns:
            Configured StaticText control
        """
        control = wx.StaticText(parent, label=label_text)
        control.Wrap(max_width)

        font = control.GetFont()
        font.SetPointSize(font_size)
        if bold:
            font.SetWeight(wx.FONTWEIGHT_BOLD)
        control.SetFont(font)

        return control

    def _create_frame_label_with_sizer(
        self,
        parent: wx.Window,
        label_text: str,
        font_size: int,
        max_width: int = CONSTANTS.MAX_LABEL_WIDTH,
        bold: bool = False
    ) -> wx.BoxSizer:
        """
        Create a static text label wrapped in a vertical sizer for right-alignment.

        This is used for form labels that need to align to the right of their column.

        Args:
            parent: Parent window
            label_text: Text to display
            font_size: Font size in points
            max_width: Maximum width before wrapping (default: CONSTANTS.MAX_LABEL_WIDTH)
            bold: Whether to make the text bold (default: False)

        Returns:
            BoxSizer containing the right-aligned label
        """
        control = wx.StaticText(parent, label=label_text)
        control.Wrap(max_width)

        font = control.GetFont()
        font.SetPointSize(font_size)
        if bold:
            font.SetWeight(wx.FONTWEIGHT_BOLD)
        control.SetFont(font)

        label_sizer = wx.BoxSizer(wx.VERTICAL)
        label_sizer.AddStretchSpacer()
        label_sizer.Add(control, 0, wx.ALIGN_RIGHT)

        return label_sizer
        
    def _create_single_line_text_control(
        self,
        parent: wx.Window,
        font_size: int
    ) -> Tuple[wx.TextCtrl, wx.BoxSizer]:
        """
        Create a single-line text input control.

        Args:
            parent: Parent window
            font_size: Font size in points

        Returns:
            Tuple of (TextCtrl control, BoxSizer containing it)
        """
        control = wx.TextCtrl(parent)

        font = control.GetFont()
        font.SetPointSize(font_size)
        control.SetFont(font)

        text_box_sizer = wx.BoxSizer(wx.HORIZONTAL)
        text_box_sizer.Add(control, 1, wx.EXPAND)

        return control, text_box_sizer

    def _create_multi_line_text_control(
        self,
        parent: wx.Window,
        hint_text: str,
        font_size: int
    ) -> Tuple[AutoResizeTextCtrl, wx.BoxSizer]:
        """
        Create an auto-resizing multi-line text input control.

        Args:
            parent: Parent window
            hint_text: Placeholder text shown when empty
            font_size: Font size in points

        Returns:
            Tuple of (AutoResizeTextCtrl control, BoxSizer containing it)
        """
        control = AutoResizeTextCtrl(parent, hint=hint_text, font_size=font_size)

        text_box_sizer = wx.BoxSizer(wx.HORIZONTAL)
        text_box_sizer.Add(control, 1, wx.EXPAND)

        return control, text_box_sizer

    def _create_multi_line_textbox_control(
        self,
        parent: wx.Window,
        font_size: int
    ) -> Tuple[wx.TextCtrl, wx.BoxSizer]:
        """
        Create a standard multi-line text input control (for notes).

        Args:
            parent: Parent window
            font_size: Font size in points

        Returns:
            Tuple of (TextCtrl control, BoxSizer containing it)
        """
        control = wx.TextCtrl(parent, style=wx.TE_MULTILINE)

        font = control.GetFont()
        font.SetPointSize(font_size)
        control.SetFont(font)

        text_box_sizer = wx.BoxSizer(wx.HORIZONTAL)
        text_box_sizer.Add(control, 1, wx.EXPAND)

        return control, text_box_sizer
    
    def _create_radio_box_control(
        self,
        parent: wx.Window,
        options: list[str],
        font_size: int
    ) -> Tuple[wx.RadioBox, wx.BoxSizer]:
        """
        Create a radio button group control.

        Args:
            parent: Parent window
            options: List of option labels
            font_size: Font size in points

        Returns:
            Tuple of (RadioBox control, BoxSizer containing it)
        """
        control = wx.RadioBox(parent, choices=options, majorDimension=1, style=wx.RA_SPECIFY_ROWS)

        font = control.GetFont()
        font.SetPointSize(font_size)
        control.SetFont(font)

        radio_box_sizer = wx.BoxSizer(wx.HORIZONTAL)
        radio_box_sizer.Add(control, 1, wx.EXPAND)

        return control, radio_box_sizer
    
    def _create_check_box_control(
        self,
        parent: wx.Window,
        option_name: str,
        font_size: int
    ) -> Tuple[wx.CheckBox, wx.BoxSizer]:
        """
        Create a check box control.

        Args:
            parent: Parent window
            option_name: Label text to show next to checkbox (can be empty)
            font_size: Font size in points

        Returns:
            Tuple of (CheckBox control, BoxSizer containing it)
        """
        control = wx.CheckBox(parent, label=option_name)

        font = control.GetFont()
        font.SetPointSize(font_size)
        control.SetFont(font)

        # Make checkbox larger and easier to click for elderly users
        control.SetMinSize((40, 40))  # Larger clickable area

        check_box_sizer = wx.BoxSizer(wx.HORIZONTAL)
        check_box_sizer.Add(control, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 8)  # Extra padding
        check_box_sizer.AddStretchSpacer()

        return control, check_box_sizer

    def _create_dropdown_control(
        self,
        parent: wx.Window,
        options: list[str],
        font_size: int,
        with_sizer: bool = True
    ) -> Tuple[wx.ComboBox, Optional[wx.BoxSizer]]:
        """
        Create a read-only dropdown (ComboBox) control.

        Args:
            parent: Parent window
            options: List of choices to display
            font_size: Font size in points
            with_sizer: Whether to wrap in a BoxSizer (default: True)

        Returns:
            Tuple of (ComboBox control, BoxSizer or None)
        """
        control = wx.ComboBox(parent, choices=options, style=wx.CB_READONLY)
        control.Select(0)  # Set default option

        font = control.GetFont()
        font.SetPointSize(font_size)
        control.SetFont(font)

        combo_box_sizer = None
        if with_sizer:
            combo_box_sizer = wx.BoxSizer(wx.HORIZONTAL)
            combo_box_sizer.Add(control, 1, wx.EXPAND)

        return control, combo_box_sizer

    def _create_optional_date_picker(
        self,
        parent: wx.Window,
        font_size: int
    ) -> Tuple[Dict[str, wx.ComboBox], wx.BoxSizer]:
        """
        Create a date picker with support for partial/unknown dates.

        Creates 5 dropdowns: Day, Month, Century, Decade, Unit
        Supports formats: XXXX (unknown), 1999 (full), 199X, 19XX

        Args:
            parent: Parent window
            font_size: Font size in points

        Returns:
            Tuple of:
            - Dictionary with keys: 'day', 'month', 'year_century', 'year_decade', 'year_unit'
            - BoxSizer containing all 5 dropdowns horizontally arranged
        """
        date_sizer = wx.BoxSizer(wx.HORIZONTAL)

        days = ["Dzień", "XX"] + [str(i).rjust(2, "0") for i in range(1, 32)]
        day_dropdown = wx.adv.OwnerDrawnComboBox(
            parent, choices=days, style=wx.CB_READONLY
        )
        day_font = day_dropdown.GetFont()
        day_font.SetPointSize(font_size)
        day_dropdown.SetFont(day_font)
        day_dropdown.SetPopupMaxHeight(DAY_DROPDOWN_POPUP_MAX_HEIGHT_PX)
        day_dropdown.Select(0)

        months = ["Miesiąc", "XX"] + [str(i).rjust(2, "0") for i in range(1, 13)]
        month_dropdown, _ = self._create_dropdown_control(parent, months, font_size, with_sizer=False)

        year_centuries = ["Wiek", "XX", "17", "18", "19", "20", "21"]
        century_dropdown, _ = self._create_dropdown_control(parent, year_centuries, font_size, with_sizer=False)

        year_decades = ["Dekada", "X"] + [str(i) for i in range(0, 10)]
        decade_dropdown, _ = self._create_dropdown_control(parent, year_decades, font_size, with_sizer=False)

        year_years = ["Rok", "X"] + [str(i) for i in range(0, 10)]
        year_dropdown, _ = self._create_dropdown_control(parent, year_years, font_size, with_sizer=False)

        date_sizer.Add(day_dropdown, 1, wx.EXPAND | wx.RIGHT, 5)
        date_sizer.Add(month_dropdown, 1, wx.EXPAND | wx.RIGHT, 5)
        date_sizer.Add(century_dropdown, 1, wx.EXPAND | wx.RIGHT, 5)
        date_sizer.Add(decade_dropdown, 1, wx.EXPAND | wx.RIGHT, 5)
        date_sizer.Add(year_dropdown, 1, wx.EXPAND)

        date_dropdowns_dict = {
            'day': day_dropdown,
            'month': month_dropdown,
            'year_century': century_dropdown,
            'year_decade': decade_dropdown,
            'year_unit': year_dropdown
        }

        return date_dropdowns_dict, date_sizer

    def _create_menu(self):
        """Build the three-section 'Plik' menu.

        Section 1 — New-person creation (enabled in NEW mode only)
        Section 2 — In-tree people management (Section 2 save enabled in EDIT_TREE only)
        Section 3 — Drafts management (Zaktualizuj + Dodaj enabled in EDIT_DRAFT only)

        Sections separated by wx.Menu.AppendSeparator().  Always-enabled items:
        Nowa osoba, Edytuj osobę z drzewa, Ustaw osobę-korzeń drzewa,
        Odśwież drzewo, Odśwież rody, Wyjdź, Wczytaj szkic osoby.

        MenuItem references for mode-gated items stored as self._menu_item_<key>
        so _apply_menu_mode() can toggle them by ID.
        """
        menu_bar = wx.MenuBar()
        file_menu = wx.Menu()

        # ── Section 1: New-person creation ────────────────────────────────────
        section1_new = file_menu.Append(wx.ID_ANY, "Nowa osoba")
        self.Bind(wx.EVT_MENU, self._on_new_person_click, section1_new)

        self._menu_item_save_new = file_menu.Append(wx.ID_ANY, "Zapisz osobę i dodaj do drzewa")
        self.Bind(wx.EVT_MENU, self.on_save_click, self._menu_item_save_new)

        self._menu_item_save_as_draft = file_menu.Append(wx.ID_ANY, "Zapisz osobę jako szkic")
        self.Bind(wx.EVT_MENU, self.on_save_draft_click, self._menu_item_save_as_draft)

        file_menu.AppendSeparator()

        # ── Section 2: In-tree people management ──────────────────────────────
        section2_edit = file_menu.Append(wx.ID_ANY, "Edytuj osobę z drzewa")
        self.Bind(wx.EVT_MENU, self.on_open_person_click, section2_edit)

        section2_root = file_menu.Append(wx.ID_ANY, "Ustaw osobę-korzeń drzewa")
        self.Bind(wx.EVT_MENU, self._on_pick_folder_tree_root_click, section2_root)

        self._menu_item_save_tree_changes = file_menu.Append(wx.ID_ANY, "Zapisz zmiany dla osoby na drzewie")
        self.Bind(wx.EVT_MENU, self.on_save_edit_click, self._menu_item_save_tree_changes)
        # FUTURE (parked): "person degradation" — a fourth Section 2 item
        # "Zapisz osobę z drzewa jako szkic" that copies the tree person's me.json into
        # Poczekalnia/ under a fresh UUID and switches mode to EDIT_DRAFT for further
        # editing. When implementing: enable only in EDIT_TREE mode; the state-machine
        # matrix gains one row.

        file_menu.AppendSeparator()

        # ── Section 3: Drafts management ──────────────────────────────────────
        section3_load = file_menu.Append(wx.ID_ANY, "Wczytaj szkic osoby")
        self.Bind(wx.EVT_MENU, self.on_load_draft_click, section3_load)

        self._menu_item_update_draft = file_menu.Append(wx.ID_ANY, "Zaktualizuj szkic osoby")
        self.Bind(wx.EVT_MENU, self.on_update_draft_click, self._menu_item_update_draft)

        self._menu_item_promote_draft = file_menu.Append(wx.ID_ANY, "Dodaj szkic osoby do drzewa")
        self.Bind(wx.EVT_MENU, self.on_promote_draft_click, self._menu_item_promote_draft)

        file_menu.AppendSeparator()

        # ── Always-on: refresh + refresh rody ─────────────────────────────────
        refresh_folder_tree_item = file_menu.Append(wx.ID_ANY, "Odśwież drzewo")
        self.Bind(wx.EVT_MENU, self._on_refresh_folder_tree_click, refresh_folder_tree_item)

        refresh_lineage_item = file_menu.Append(wx.ID_ANY, "Odśwież rody")
        self.Bind(wx.EVT_MENU, self._on_refresh_lineage_click, refresh_lineage_item)

        file_menu.AppendSeparator()

        # ── Exit ───────────────────────────────────────────────────────────────
        exit_item = file_menu.Append(wx.ID_EXIT, "Wyjdź")
        self.Bind(wx.EVT_MENU, self.on_exit_click, exit_item)

        menu_bar.Append(file_menu, "Plik")
        self.SetMenuBar(menu_bar)

        # Keep backward-compatible reference used in tests + _reset_to_add_mode
        # (the old _save_edit_item mapped to the EDIT_TREE save action)
        self._save_edit_item = self._menu_item_save_tree_changes

    @log_user_action("Toggle maiden-name field")
    def on_maiden_name_toggle(self, event: wx.Event) -> None:
        """Enable or disable maiden name fields based on checkbox state."""
        is_checked = event.IsChecked()

        if is_checked:
            self.maiden_name_text_box.Enable(True)
            self.other_maiden_names_text_box.Enable(True)
            self.other_maiden_names_text_box.set_hint("Wpisz kolejne nazwiska, każde w nowej linii...")
        else:
            # Try everything to clear the hint
            self.other_maiden_names_text_box.set_hint("")
            self.other_maiden_names_text_box.SetValue("")  # Clear any content too
            self.other_maiden_names_text_box.Refresh()
            self.other_maiden_names_text_box.Update()
            self.maiden_name_text_box.Enable(False)
            self.other_maiden_names_text_box.Enable(False)
            # Force parent to redraw
            self.root_panel.Refresh()
            
    @log_user_action("Toggle is-dead field")
    def on_is_dead_toggle(self, event: wx.Event) -> None:
        """Enable or disable death date pickers based on checkbox state."""
        is_checked = event.IsChecked()

        if is_checked:
            for combo_box in self.death_date_picker.values():
                combo_box.Enable(True)
        else:
            for combo_box in self.death_date_picker.values():
                combo_box.Enable(False)
            # Force parent to redraw
            self.root_panel.Refresh()

    
    @log_user_action("Save person (new)")
    def on_save_click(self, event: wx.Event) -> None:
        # Step 1: validate required fields
        errors = self._validate_form()
        if errors:
            polish_dialog(
                self,
                "\n".join(errors),
                "Błąd walidacji",
                wx.OK | wx.ICON_WARNING,
            )
            return

        # Step 2: collect form data
        person_data = PersonDataWrapper(self._collect_all_data_to_dict())

        # Step 3: resolve relationship UUIDs → folder paths
        try:
            self._resolve_relationship_paths(person_data)
        except ValueError as e:
            log_error(e, context="Save person (new): resolve_relationship_paths failed")
            polish_dialog(self, str(e), "Błąd danych", wx.OK | wx.ICON_ERROR)
            return

        # Step 4: pre-flight — folders exist and me.json files are writable
        try:
            self._preflight_checks(person_data)
        except (FileNotFoundError, IOError) as e:
            polish_dialog(self, str(e), "Błąd dostępu do pliku", wx.OK | wx.ICON_ERROR)
            return

        # Step 5: save as new person
        try:
            self._tree_service.save_person_and_add_to_tree(person_data)
        except Exception as e:
            log_error(e, context="Save person (new): save_person_and_add_to_tree failed")
            polish_dialog(
                self,
                f"Nie udało się zapisać osoby.\n\n{e}",
                "Błąd zapisu",
                wx.OK | wx.ICON_ERROR,
            )
            return

        # Step 6: success — delete the matching draft file if one exists (phases.md 3.4)
        # Drafts live under <root>/Poczekalnia/
        old_uuid = self.unique_identifier
        try:
            draft_path = self._tree_service._file_service.get_poczekalnia_path() / f"{old_uuid}.json"
            if draft_path.exists():
                draft_path.unlink()
        except (OSError, RuntimeError):
            pass  # Non-fatal; draft cleanup is best-effort

        # Step 7: success — reset form so user has a clean path to "add another person"
        person_name_for_msg = person_data.get_person_name()
        self._refresh_people_list()
        self._reset_to_add_mode()
        polish_dialog(
            self,
            f"Osoba \"{person_name_for_msg}\" została pomyślnie dodana do drzewa.\n\n"
            "Formularz został wyczyszczony — możesz dodać kolejną osobę.",
            "Zapisano",
            wx.OK | wx.ICON_INFORMATION,
        )

    @log_user_action("Save person (edit)")
    def on_save_edit_click(self, event: wx.Event) -> None:
        """Save changes to the currently loaded person (edit mode only)."""
        errors = self._validate_form()
        if errors:
            polish_dialog(self, "\n".join(errors), "Błąd walidacji", wx.OK | wx.ICON_WARNING)
            return

        person_data = PersonDataWrapper(self._collect_all_data_to_dict())

        try:
            self._resolve_relationship_paths(person_data)
        except ValueError as e:
            log_error(e, context="Save person (edit): resolve_relationship_paths failed")
            polish_dialog(self, str(e), "Błąd danych", wx.OK | wx.ICON_ERROR)
            return

        try:
            self._preflight_checks(person_data)
        except (FileNotFoundError, IOError) as e:
            polish_dialog(self, str(e), "Błąd dostępu do pliku", wx.OK | wx.ICON_ERROR)
            return

        try:
            self._tree_service.update_person_in_tree(
                person_data,
                original_location=self.location,
                original_canonical_name=self._original_name,
                original_relationships=self._original_relationships,
            )
        except Exception as e:
            log_error(e, context="Save person (edit): save flow failed")
            polish_dialog(self, f"Nie udało się zapisać zmian.\n\n{e}", "Błąd zapisu", wx.OK | wx.ICON_ERROR)
            return

        # Delete the draft file for this person's UUID if one exists (phases.md 3.4)
        # Drafts live under <root>/Poczekalnia/
        try:
            draft_path = self._tree_service._file_service.get_poczekalnia_path() / f"{self.unique_identifier}.json"
            if draft_path.exists():
                draft_path.unlink()
        except (OSError, RuntimeError):
            pass  # Non-fatal

        # Any successful save resets to NEW mode.
        person_name_for_msg = person_data.get_person_name()
        self._refresh_people_list()
        self._reset_to_add_mode()
        polish_dialog(
            self,
            f"Zmiany dla osoby \"{person_name_for_msg}\" zostały pomyślnie zapisane.\n\n"
            "Formularz został wyczyszczony — możesz dodać kolejną osobę.",
            "Zapisano",
            wx.OK | wx.ICON_INFORMATION,
        )

    def _validate_form(self) -> List[str]:
        """Check required fields. Returns list of Polish error messages (empty = valid)."""
        return []

    def _resolve_relationship_paths(self, data: PersonDataWrapper) -> None:
        """Resolve UUID lists in data to folder path lists, updating data in-place.

        Raises:
            ValueError: With Polish message if any UUID is not found in the people cache.
        """
        people = self._tree_service.list_of_people

        for ids_getter, paths_setter in [
            (data.get_spouse_ids,   data.set_spouses),
            (data.get_children_ids, data.set_children),
            (data.get_parent_ids,   data.set_parents),
            (data.get_sibling_ids,  data.set_siblings),
        ]:
            ids = ids_getter()
            paths = []
            for uid in ids:
                if uid not in people:
                    raise ValueError(
                        f"Nie znaleziono osoby w drzewie (ID: {uid}).\n"
                        "Odśwież aplikację i spróbuj ponownie."
                    )
                paths.append(people[uid][PersonDataProperty.LOCATION.value])
            paths_setter(paths)

    def _preflight_checks(self, data: PersonDataWrapper) -> None:
        """Verify all referenced folders exist and their me.json files are writable.

        Raises:
            FileNotFoundError: If a folder or me.json is missing.
            IOError: If a me.json cannot be opened for writing (e.g. locked).
        """
        all_paths = (
            data.get_spouses() +
            data.get_children() +
            data.get_parents() +
            data.get_siblings()
        )
        for folder_path in all_paths:
            folder = Path(folder_path)
            if not folder.exists():
                raise FileNotFoundError(
                    f"Nie znaleziono folderu osoby: \"{folder.name}\".\n"
                    "Sprawdź, czy folder nie został usunięty lub przeniesiony."
                )
            me_json = folder / "me.json"
            if not me_json.exists():
                raise FileNotFoundError(
                    f"Brak pliku danych (me.json) dla osoby: \"{folder.name}\"."
                )
            try:
                with open(me_json, 'a', encoding='utf-8'):
                    pass
            except IOError:
                raise IOError(
                    f"Brak dostępu do pliku danych osoby: \"{folder.name}\".\n"
                    "Plik może być otwarty w innym programie."
                )

    def _refresh_people_list(self) -> None:
        """Reload ALL_PEOPLE from the service cache and refresh all picker controls."""
        self.ALL_PEOPLE = {
            uid: person[PersonDataProperty.PERSON_NAME.value]
            for uid, person in self._tree_service.list_of_people.items()
        }
        self.parents_picker.reload_people(self.ALL_PEOPLE)
        self.children_picker.reload_people(self.ALL_PEOPLE)
        self.spouses_picker.reload_people(self.ALL_PEOPLE)
        self.siblings_picker.reload_people(self.ALL_PEOPLE)

    # =========================================================================
    # Dirty tracking and close-warning (phases.md 4.1)
    # =========================================================================

    # NOT decorated with @log_user_action — fires on every keystroke; logging
    # every keystroke would flood the journey log.
    def _on_field_dirty(self, event: wx.Event) -> None:
        """Mark the form as modified. Always calls event.Skip() so other handlers run."""
        self._is_dirty = True
        if event is not None:
            event.Skip()

    # NOT decorated with @log_user_action — fires on every picker selection change;
    # logging every change would flood the journey log.
    def _on_picker_change(self) -> None:
        """Called by picker on_change_callback — updates exclusions then sets dirty."""
        self.update_all_picker_exclusions()
        self._is_dirty = True

    def _wire_dirty_tracking(self) -> None:
        """Bind all input controls to _on_field_dirty.

        AutoResizeTextCtrl already binds EVT_TEXT in its __init__ (on_text_change) and
        calls event.Skip() to propagate it. Binding EVT_TEXT on the control from the
        frame side therefore works correctly — the event fires, both handlers run.
        """
        # Single-line text boxes
        for ctrl in (
            self.first_name_text_box,
            self.last_name_text_box,
            self.maiden_name_text_box,
        ):
            ctrl.Bind(wx.EVT_TEXT, self._on_field_dirty)

        # Multi-line auto-resize boxes: EVT_TEXT fires from on_text_change via Skip
        for ctrl in (
            self.other_first_names_text_box,
            self.other_last_names_text_box,
            self.other_maiden_names_text_box,
        ):
            ctrl.Bind(wx.EVT_TEXT, self._on_field_dirty)

        # Notes text box
        self.notes_textbox.Bind(wx.EVT_TEXT, self._on_field_dirty)

        # Checkboxes
        self.has_maiden_name_checkbox.Bind(wx.EVT_CHECKBOX, self._on_field_dirty)
        self.is_dead_checkbox.Bind(wx.EVT_CHECKBOX, self._on_field_dirty)

        # Sex dropdown
        self.sex_dropdown.Bind(wx.EVT_COMBOBOX, self._on_field_dirty)

        # Birth date dropdowns (5 combos)
        for combo in self.birth_date_picker.values():
            combo.Bind(wx.EVT_COMBOBOX, self._on_field_dirty)

        # Death date dropdowns (5 combos)
        for combo in self.death_date_picker.values():
            combo.Bind(wx.EVT_COMBOBOX, self._on_field_dirty)

        # Pickers: wire through their on_change_callback by replacing it.
        # The callback is called synchronously on every selection change inside
        # MultiPersonPickerControl. _on_picker_change() calls
        # update_all_picker_exclusions() so the exclusion logic still runs.
        #
        # IMPORTANT — ordering dependency (D4):
        #   This replaces the existing on_change_callback unconditionally. If a
        #   future _create_relation_pickers_section assigns a non-trivial callback
        #   for purposes other than dirty tracking, that behavior is silently
        #   dropped here. The only existing callback is
        #   update_all_picker_exclusions, which _on_picker_change re-invokes
        #   explicitly. If a third behavior is added, fold it into
        #   _on_picker_change rather than rebinding here.
        #   Additionally, _wire_dirty_tracking must run AFTER all
        #   _fill_form_from_draft call sites complete their initial population,
        #   otherwise the initial SetValue calls will fire _on_picker_change and
        #   spuriously mark the form dirty before the user touches anything.
        for picker in (
            self.parents_picker,
            self.children_picker,
            self.spouses_picker,
            self.siblings_picker,
        ):
            picker.on_change_callback = self._on_picker_change

    @log_user_action("Close window")
    def _on_close(self, event: wx.CloseEvent) -> None:
        """Handle window close: if dirty, offer save-draft / discard / cancel."""
        if not self._is_dirty:
            event.Skip()  # Clean state — allow close
            return

        dlg = wx.MessageDialog(
            self,
            "Masz niezapisane zmiany. Czy chcesz zapisać szkic przed zamknięciem?",
            "Niezapisane zmiany",
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
        )
        try:
            dlg.SetYesNoCancelLabels(
                "Zapisz szkic i zamknij",
                "Zamknij bez zapisywania",
                "Anuluj",
            )
        except AttributeError:
            # SetYesNoCancelLabels not available on very old wxPython builds.
            # Polish message body is still readable; button labels fall back to
            # system defaults (usually Yes/No/Cancel or locale equivalents).
            pass

        result = dlg.ShowModal()
        dlg.Destroy()

        if result == wx.ID_YES:
            try:
                data_dump = PersonDataWrapper(self._collect_all_data_to_dict())
                self._tree_service.save_person_draft(data_dump)
            except Exception as e:
                log_error(e, context="Close window: save-on-close failed")
                polish_dialog(
                    self,
                    f"Nie udało się zapisać szkicu.\n\n{e}",
                    "Błąd",
                    wx.OK | wx.ICON_ERROR,
                )
                event.Veto()
                return
            event.Skip()
        elif result == wx.ID_NO:
            event.Skip()  # Discard changes — close
        else:
            event.Veto()  # Cancel — stay open

    # -------------------------------------------------------------------------
    # Red "Zgłoś błąd" error-report button
    # -------------------------------------------------------------------------

    def _create_report_button(self) -> wx.Button:
        """Create the red error-report button.

        Background: Material Red 700 #D32F2F.
        Always enabled — handler does not depend on _tree_service state.
        """
        btn = wx.Button(self.root_panel, label="Zgłoś błąd")
        btn.SetBackgroundColour("#D32F2F")   # Material Red 700
        btn.SetForegroundColour("#FFFFFF")   # White text — high contrast
        _btn_font = btn.GetFont()
        _btn_font.SetWeight(wx.FONTWEIGHT_BOLD)
        _btn_font.SetPointSize(self._font_size)
        btn.SetFont(_btn_font)
        btn.Bind(wx.EVT_BUTTON, self._on_report_click)
        return btn

    @log_user_action("Send error report (manual)")
    def _on_report_click(self, event: wx.Event) -> None:
        """Manual error-report click.

        No confirmation, no rate-limit.  Status bar shows feedback.
        Always enabled regardless of root-folder state.
        """
        person = getattr(self, "_current_person_label", "-")
        headline = (
            f"User manually requested a report. "
            f"Currently loaded person: {person}."
        )
        sent = False
        try:
            from src.helpers.email_helper import enqueue_email_for_severity
            sent = enqueue_email_for_severity(
                severity="REPORT",
                headline=headline,
                handler_name="_user_requested_report",
            )
        except Exception:
            sent = False

        if sent:
            self.SetStatusText("Raport wysłany.")
        else:
            self.SetStatusText(
                "Raport w kolejce, zostanie wysłany gdy będzie dostępny internet."
            )
        wx.CallLater(1500, self.SetStatusText, "")

    @log_user_action("Save draft")
    def on_save_draft_click(self, event: wx.Event):
        """Save form data as a draft (no validation — drafts may have incomplete data)."""
        try:
            data_dump = PersonDataWrapper(self._collect_all_data_to_dict())
            self._tree_service.save_person_draft(data_dump)
        except Exception as e:
            log_error(e, context="Save draft: write failed")
            polish_dialog(
                self,
                f"Nie udało się zapisać szkicu.\n\n{e}",
                "Błąd zapisu szkicu",
                wx.OK | wx.ICON_ERROR,
            )
            return
        self._is_dirty = False
        polish_dialog(self, "Szkic zapisany.", "Zapisano", wx.OK | wx.ICON_INFORMATION)

    @log_user_action("Exit")
    def on_exit_click(self, event: wx.Event):
        # Route through EVT_CLOSE so the dirty-tracking dialog handles it
        self.Close()

    def _apply_loaded_draft(self, data: dict, path: str) -> None:
        """Pure-state transition after a draft is loaded.

        Extracted from on_load_draft_click so the state logic is testable
        without a wx mainloop.  Tests can call frame._apply_loaded_draft()
        directly using a SimpleNamespace stub that has unique_identifier and
        _loaded_draft_path attributes.

        Intentionally wx-free: no _apply_menu_mode call here. The caller
        (on_load_draft_click) is responsible for calling _apply_menu_mode
        after this method returns, because _apply_menu_mode requires the
        wx menu bar to be present.

        Side effects (pure state, wx-free):
          - Restores draft's UUID into self.unique_identifier.
          - Stores the draft's filesystem path in self._loaded_draft_path.
        """
        restored_uid = PersonDataWrapper(data).get_unique_identifier()
        if restored_uid:
            self.unique_identifier = restored_uid
        self._loaded_draft_path = path

    @log_user_action("Load draft")
    def on_load_draft_click(self, event: wx.Event):
        """Open the draft picker and load the selected draft into the form."""
        drafts = self._tree_service.get_list_of_drafts()
        if not drafts:
            polish_dialog(self, "Brak zapisanych szkiców.", "Info", wx.OK | wx.ICON_INFORMATION)
            return

        dialog = DraftPickerDialog(self, drafts)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.get_selected_path()
            try:
                data = self._tree_service.load_person_draft(path)
            except (json.JSONDecodeError, Exception):
                polish_dialog(
                    self,
                    "Wybrany szkic jest uszkodzony. Plik nie został wczytany.",
                    "Błąd odczytu szkicu",
                    wx.OK | wx.ICON_ERROR,
                )
                dialog.Destroy()
                return
            self._fill_form_from_draft(data)
            self._is_dirty = False
            self._apply_loaded_draft(data, path)
            self._apply_menu_mode(MenuMode.EDIT_DRAFT)
            _draft_name = PersonDataWrapper(data).get_person_name()
            set_current_person_label(self, f"Draft, {_draft_name}" if _draft_name else "Draft")

        dialog.Destroy()

    @log_user_action("Update draft")
    def on_update_draft_click(self, event: wx.Event) -> None:
        """Overwrite the currently loaded draft file in place.

        Pre-condition: self._menu_mode == MenuMode.EDIT_DRAFT (enforced via menu enable).
        Pre-condition: self._loaded_draft_path is a real file inside <poczekalnia>.

        The draft's UUID was restored into self.unique_identifier in on_load_draft_click,
        so save_person_draft writes back to <poczekalnia>/<self.unique_identifier>.json
        — the SAME file the user loaded.  No new UUID is generated anywhere on this path.

        Edge case: if the file was deleted between load and this click,
        open(path, 'w') inside write_me_file silently recreates it at the
        same UUID path.
        """
        try:
            data_dump = PersonDataWrapper(self._collect_all_data_to_dict())
            # Defensive parity check: data UUID == path basename.
            # Drift here means upstream state was lost; log and continue anyway.
            expected_uid = data_dump.get_unique_identifier()
            path_uid = Path(self._loaded_draft_path).stem if self._loaded_draft_path else None
            if path_uid and expected_uid and path_uid != expected_uid:
                log_error(
                    RuntimeError(
                        f"Draft UUID drift: path={path_uid} data={expected_uid}"
                    ),
                    context="Update draft: UUID drift detected; overwriting by data UUID",
                )
            self._tree_service.save_person_draft(data_dump)
        except Exception as e:
            log_error(e, context="Update draft: write failed")
            polish_dialog(
                self,
                f"Nie udało się zaktualizować szkicu.\n\n{e}",
                "Błąd zapisu szkicu",
                wx.OK | wx.ICON_ERROR,
            )
            return
        self._is_dirty = False
        polish_dialog(self, "Szkic zaktualizowany.", "Zapisano", wx.OK | wx.ICON_INFORMATION)
        self._reset_to_add_mode()  # any successful save -> mode resets to NEW

    @log_user_action("Promote draft to tree")
    def on_promote_draft_click(self, event: wx.Event) -> None:
        """Promote the currently loaded draft to a full tree person and delete the draft file.

        Pre-condition: self._menu_mode == MenuMode.EDIT_DRAFT (enforced via menu enable).

        Steps:
          1. Validate + resolve + preflight (same as on_save_click).
          2. save_person_and_add_to_tree (creates the tree person folder under Lista osob/).
          3. Delete the draft file at <poczekalnia>/<self.unique_identifier>.json.
             If delete fails: log INFO-CLEANUP line and continue silently — the tree
             person is canonical; the orphan draft is harmless.
          4. Reset to NEW mode.
        """
        errors = self._validate_form()
        if errors:
            polish_dialog(self, "\n".join(errors), "Błąd walidacji", wx.OK | wx.ICON_WARNING)
            return

        person_data = PersonDataWrapper(self._collect_all_data_to_dict())

        try:
            self._resolve_relationship_paths(person_data)
        except ValueError as e:
            log_error(e, context="Promote draft: resolve_relationship_paths failed")
            polish_dialog(self, str(e), "Błąd danych", wx.OK | wx.ICON_ERROR)
            return

        try:
            self._preflight_checks(person_data)
        except (FileNotFoundError, IOError) as e:
            polish_dialog(self, str(e), "Błąd dostępu do pliku", wx.OK | wx.ICON_ERROR)
            return

        try:
            self._tree_service.save_person_and_add_to_tree(person_data)
        except Exception as e:
            log_error(e, context="Promote draft: save_person_and_add_to_tree failed")
            polish_dialog(
                self,
                f"Nie udało się zapisać osoby.\n\n{e}",
                "Błąd zapisu",
                wx.OK | wx.ICON_ERROR,
            )
            return

        # Step 3: delete the loaded draft (promote disposes draft).
        # Use public log_cleanup_failure on delete failure.
        draft_path = (
            self._tree_service._file_service.get_poczekalnia_path()
            / f"{self.unique_identifier}.json"
        )
        try:
            if draft_path.exists():
                draft_path.unlink()
        except (OSError, RuntimeError) as cleanup_exc:
            # Non-fatal — the tree person is canonical.  Log INFO-CLEANUP and continue.
            log_cleanup_failure(draft_path, cleanup_exc)

        person_name_for_msg = person_data.get_person_name()
        self._refresh_people_list()
        self._reset_to_add_mode()
        polish_dialog(
            self,
            f"Osoba \"{person_name_for_msg}\" została pomyślnie dodana do drzewa "
            "(szkic został usunięty).\n\n"
            "Formularz został wyczyszczony — możesz dodać kolejną osobę.",
            "Zapisano",
            wx.OK | wx.ICON_INFORMATION,
        )

    @log_user_action("Open person for edit")
    def on_open_person_click(self, event: wx.Event) -> None:
        dialog = wx.DirDialog(
            self,
            message="Wybierz folder osoby do edycji",
            defaultPath=self._tree_service.get_people_folder(),
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
        )
        if dialog.ShowModal() == wx.ID_OK:
            folder_path = dialog.GetPath()
            dialog.Destroy()
            try:
                self._load_person_for_edit(folder_path)
            except Exception as e:
                log_error(e, context="Open person for edit: load failed")
                polish_dialog(self, str(e), "Błąd odczytu", wx.OK | wx.ICON_ERROR)
        else:
            dialog.Destroy()

    def _load_person_for_edit(self, folder_path: str) -> None:
        me_json_path = Path(folder_path) / "me.json"
        if not me_json_path.exists():
            raise FileNotFoundError("Wybrany folder nie zawiera pliku me.json.")

        try:
            raw_data = self._tree_service.load_person_draft(str(me_json_path))
            person_data = PersonDataWrapper(raw_data)
        except Exception:
            raise ValueError("Nie można odczytać danych osoby. Plik me.json może być uszkodzony.")

        self._fill_form_from_draft(person_data.to_dict())

        self.location = folder_path
        self.unique_identifier = person_data.get_unique_identifier() or str(uuid.uuid4())

        self._original_name = person_data.get_person_name()
        self._original_relationships = {
            'parents':  list(person_data.get_parents()),
            'children': list(person_data.get_children()),
            'spouses':  list(person_data.get_spouses()),
            'siblings': list(person_data.get_siblings()),
        }
        # _menu_mode is the single source of truth, set by _apply_menu_mode(EDIT_TREE) below.
        self._is_dirty = False
        self.SetTitle(f"Edytuj osobę w drzewie — {Path(folder_path).name}")
        self._apply_menu_mode(MenuMode.EDIT_TREE)
        set_current_person_label(self, person_data.get_person_name() or PERSON_PLACEHOLDER)

    # =========================================================================
    # Mode management (U2, U3, B2)
    # =========================================================================

    @property
    def _is_edit_mode(self) -> bool:
        """Backward-compat alias: True when in EDIT_TREE mode.

        _menu_mode is the single source of truth.
        This alias avoids a cascade of caller-site changes.
        Write access via `_is_edit_mode = value` is intentionally NOT
        supported — callers must use _apply_menu_mode().
        """
        return self._menu_mode == MenuMode.EDIT_TREE

    @_is_edit_mode.setter
    def _is_edit_mode(self, value: bool) -> None:
        """Silently accept legacy boolean writes.

        This setter prevents AttributeError when old call-sites write
        self._is_edit_mode = True/False.  Actual mode transitions always
        go through _apply_menu_mode() for full matrix effect.
        """
        # Do not call _apply_menu_mode() here — menu bar may not exist yet
        # during __init__.  _menu_mode will be set correctly by the first
        # explicit _apply_menu_mode() call after __init__ completes.
        pass  # No-op: _menu_mode is managed by _apply_menu_mode

    def _apply_menu_mode(self, mode: MenuMode) -> None:
        """Apply the mode to the state machine: update _menu_mode, enable/disable
        menu items, and sync mode visuals.

        This is the single call-site for all mode transitions.  Always call
        this instead of writing self._menu_mode directly.
        """
        self._menu_mode = mode
        state = compute_menu_state(mode)

        menu_bar = self.GetMenuBar()
        if menu_bar is None:
            return  # Guard: menu not yet built (should not happen post-init)

        # Map from state key to wx.MenuItem held on the frame.
        # Always-on items are not in this map (they stay enabled unconditionally).
        mode_gated = {
            "save_new":       self._menu_item_save_new,
            "save_as_draft":      self._menu_item_save_as_draft,
            "save_tree_changes":     self._menu_item_save_tree_changes,
            "update_draft": self._menu_item_update_draft,
            "promote_draft":       self._menu_item_promote_draft,
        }
        for key, item in mode_gated.items():
            menu_bar.Enable(item.GetId(), state[key])

        # Sync visual cue (palette + header strip)
        visual_map = {
            MenuMode.NEW:       'add-new',
            MenuMode.EDIT_TREE: 'edit-tree',
            MenuMode.EDIT_DRAFT: 'edit-draft',
        }
        self._apply_mode_visuals(visual_map[mode])

    def _apply_mode_visuals(self, mode: str) -> None:
        """Apply background color and header label for one of the three form modes.

        Modes: 'add-new', 'edit-tree', 'edit-draft'.
        Sets root_panel background color and updates the mode header strip.
        Calls Refresh() to force repaint. If bg-color propagation is partial
        (wxPython 4.x on Windows may not repaint all child controls), the bold
        header-strip text alone provides the visual cue.
        """
        mode_map = {
            'add-new':    self.MODE_ADD_NEW,
            'edit-tree':  self.MODE_EDIT_TREE,
            'edit-draft': self.MODE_EDIT_DRAFT,
        }
        if mode not in mode_map:
            return
        _, color, label = mode_map[mode]
        self.root_panel.SetBackgroundColour(color)
        self._mode_label.SetLabel(label)
        self.root_panel.Refresh()

    def _reset_to_add_mode(self) -> None:
        """Clear the form and return to ADD-NEW mode.

        Called after a successful new-person save and when user picks 'Nowa osoba'
        from the menu. Generates a fresh UUID, clears all controls, resets
        edit-mode state, and updates the title bar.

        IMPORTANT — _is_dirty = False MUST be the last line: picker
        set_selected_people calls above synchronously invoke on_change_callback
        -> _on_picker_change -> sets _is_dirty = True. Setting False last
        discards those synthetic dirty events from programmatic field population.
        """
        # Identity
        self.location = ''
        self.unique_identifier = str(uuid.uuid4())
        self._loaded_draft_path = None   # clear draft path on reset
        self._original_name = ''
        self._original_relationships = {}

        # Text fields
        self.first_name_text_box.SetValue('')
        self.other_first_names_text_box.SetValue('')
        self.last_name_text_box.SetValue('')
        self.other_last_names_text_box.SetValue('')
        self.maiden_name_text_box.SetValue('')
        self.other_maiden_names_text_box.SetValue('')
        self.notes_textbox.SetValue('')

        # Checkboxes
        self.has_maiden_name_checkbox.SetValue(False)
        self.maiden_name_text_box.Enable(False)
        self.other_maiden_names_text_box.Enable(False)
        self.is_dead_checkbox.SetValue(False)

        # Sex dropdown
        self.sex_dropdown.SetSelection(0)

        # Date pickers (both birth and death) — index 0 is the placeholder hint
        for combo in self.birth_date_picker.values():
            combo.SetSelection(0)
        for combo in self.death_date_picker.values():
            combo.SetSelection(0)
            combo.Enable(False)  # death dates default disabled

        # Relationship pickers
        self.parents_picker.set_selected_people([])
        self.children_picker.set_selected_people([])
        self.spouses_picker.set_selected_people([])
        self.siblings_picker.set_selected_people([])

        # Defensive: even with the picker callback contract fix, explicitly
        # recompute exclusions so reset correctness does not depend on each
        # picker firing its callback. Idempotent — all four selection sets are
        # empty at this point, so the recomputed cross-set is empty everywhere.
        self.update_all_picker_exclusions()

        # Mode UI — use state machine; sets _menu_mode + visuals
        self.SetTitle("Dodaj osobę do drzewa")
        self._apply_menu_mode(MenuMode.NEW)
        set_current_person_label(self, "New")

        # MUST be last — picker callbacks above set _is_dirty = True
        self._is_dirty = False

    @log_user_action("Reset to add-new mode")
    def _on_new_person_click(self, event: wx.Event) -> None:
        """Reset the form to ADD-NEW mode. Confirms first if there are unsaved changes."""
        if self._is_dirty:
            result = polish_dialog(
                self,
                "Masz niezapisane zmiany. Czy na pewno chcesz zacząć od nowa?\n"
                "Niezapisane zmiany zostaną utracone.",
                "Niezapisane zmiany",
                wx.YES_NO | wx.ICON_QUESTION,
            )
            if result != wx.ID_YES:
                return
        self._reset_to_add_mode()

    # =========================================================================
    # Drzewo handlers
    # =========================================================================

    @log_user_action("Pick folder tree root")
    def _on_pick_folder_tree_root_click(self, event: wx.Event) -> None:
        """Pick the root person for Drzewo. On change: confirm wipe, then rebuild."""
        current = self._tree_service._file_service.get_folder_tree_root_uuid()
        dialog = RootPersonPickerDialog(self, self.ALL_PEOPLE, current_root_uuid=current)
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return
        new_uuid = dialog.get_selected_uuid()
        dialog.Destroy()
        if not new_uuid:
            return

        if current and new_uuid != current:
            # Confirmation dialog (F3 helper with Polish labels)
            result = polish_dialog(
                self,
                "Zmiana osoby-korzenia drzewa wyczyści folder Drzewo i odbuduje go od nowa.\n\nKontynuować?",
                "Zmiana osoby-korzenia drzewa",
                wx.YES_NO | wx.ICON_QUESTION,
                yes_label="Tak, zmień",
                no_label="Anuluj",
            )
            if result != wx.ID_YES:
                return  # Abort — root unchanged

        # Persist + rebuild Drzewo
        try:
            self._tree_service.set_folder_tree_root_person(new_uuid)
            folder_tree_written, folder_tree_log = self._tree_service.rebuild_folder_tree()
        except Exception as e:
            log_error(e, context="Pick folder tree root: rebuild failed")
            polish_dialog(
                self,
                f"Nie udało się zbudować drzewa.\n\n{e}",
                "Błąd",
                wx.OK | wx.ICON_ERROR,
            )
            return

        # Rebuild Rody (shares the same root anchor as Drzewo)
        lineage_msg = ""
        try:
            lineage_written, lineage_log = self._tree_service.rebuild_lineage()
            lineage_msg = f" Rody: {lineage_written} skrótów."
            if lineage_log:
                lineage_msg += f" (uwagi w Rody/build-log.txt: {len(lineage_log)})"
        except Exception as e:
            lineage_msg = f" Rody nie udało się zbudować: {e}"

        msg = f"Drzewo zbudowane: {folder_tree_written} skrótów.{lineage_msg}"
        if folder_tree_log:
            msg += f"\n\nUwagi w pliku Drzewo/build-log.txt ({len(folder_tree_log)})."
        polish_dialog(self, msg, "Drzewo gotowe", wx.OK | wx.ICON_INFORMATION)

    @log_user_action("Refresh folder tree")
    def _on_refresh_folder_tree_click(self, event: wx.Event) -> None:
        """Rebuild Drzewo against the currently designated root person."""
        if not self._tree_service._file_service.get_folder_tree_root_uuid():
            polish_dialog(
                self,
                "Najpierw wybierz osobę-korzeń drzewa (Plik -> Wybierz osobę-korzeń drzewa).",
                "Brak osoby-korzenia",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        try:
            written, log = self._tree_service.rebuild_folder_tree()
        except Exception as e:
            log_error(e, context="Refresh folder tree: rebuild_folder_tree failed")
            polish_dialog(
                self,
                f"Nie udało się odświeżyć drzewa.\n\n{e}",
                "Błąd",
                wx.OK | wx.ICON_ERROR,
            )
            return

        msg = f"Drzewo odświeżone: {written} skrótów."
        if log:
            msg += f"\n\nUwagi w pliku Drzewo/build-log.txt ({len(log)})."
        polish_dialog(self, msg, "Drzewo odświeżone", wx.OK | wx.ICON_INFORMATION)

    @log_user_action("Refresh lineage")
    def _on_refresh_lineage_click(self, event: wx.Event) -> None:
        """Rebuild Rody against the currently designated root person (shared with Drzewo)."""
        if not self._tree_service._file_service.get_folder_tree_root_uuid():
            polish_dialog(
                self,
                "Najpierw wybierz osobę-korzeń drzewa (Plik -> Wybierz osobę-korzeń drzewa).",
                "Brak osoby-korzenia",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        try:
            written, log = self._tree_service.rebuild_lineage()
        except Exception as e:
            log_error(e, context="Refresh lineage: rebuild_lineage failed")
            polish_dialog(
                self,
                f"Nie udało się odświeżyć rodów.\n\n{e}",
                "Błąd",
                wx.OK | wx.ICON_ERROR,
            )
            return

        msg = f"Rody odświeżone: {written} skrótów."
        if log:
            msg += f"\n\nUwagi w pliku Rody/build-log.txt ({len(log)})."
        polish_dialog(self, msg, "Rody odświeżone", wx.OK | wx.ICON_INFORMATION)

    def _collect_all_data_to_dict(self) -> Dict[str, Any]:
        output = PersonDataWrapper()

        output.set_first_name(self.first_name_text_box.GetValue().strip() or self.UNKNOWN)

        other_first_names = self.other_first_names_text_box.GetValue().strip().replace('\n', ' ') or None

        if other_first_names is not None:
            output.set_other_first_names(other_first_names)
        else:
            output.set_other_first_names('')

        output.set_last_name(self.last_name_text_box.GetValue().strip() or self.UNKNOWN)

        other_last_names = self.other_last_names_text_box.GetValue().strip().replace('\n', ';') or None

        if other_last_names is not None:
            output.set_other_last_names(other_last_names)
        else:
            output.set_other_last_names('')

        output.set_has_maiden_name(self.has_maiden_name_checkbox.GetValue())
        if output.get_has_maiden_name():
            output.set_maiden_name(self.maiden_name_text_box.GetValue().strip() or self.UNKNOWN)

            other_maiden_names = self.other_maiden_names_text_box.GetValue().strip().replace('\n', ';') or None

            if other_maiden_names:
                output.set_other_maiden_names(other_maiden_names)
            else:
                output.set_other_maiden_names('')
        else:
            output.set_maiden_name('')
            output.set_other_maiden_names('')

        output.set_person_name(output.get_full_name())

        sex_control: wx.ComboBox = self.sex_dropdown
        output.set_sex(sex_control.GetValue())

        output.set_spouse_ids(self.spouses_picker.get_selected_people())

        output.set_parent_ids(self.parents_picker.get_selected_people())

        output.set_children_ids(self.children_picker.get_selected_people())

        output.set_sibling_ids(self.siblings_picker.get_selected_people())

        output.set_notes(self.notes_textbox.GetValue().strip())

        birth_date = self._build_optional_date(self.birth_date_picker)
        output.set_date_of_birth(birth_date if birth_date else '')

        if self.is_dead_checkbox.GetValue():
            death_date = self._build_optional_date(self.death_date_picker)
            output.set_date_of_death(death_date if death_date else '')
        else:
            output.set_date_of_death('')

        if self.location:
           output.set_location(self.location)

        if self.unique_identifier:
            output.set_unique_identifier(self.unique_identifier)
        else:
            output.set_unique_identifier(str(uuid.uuid4()))

        return output.to_dict()
    
    def _fill_form_from_draft(self, person_data: Dict[str, Any]) -> None:
        """Populate all form controls from a person-data dict.

        IMPORTANT — call-site contract (D3):
            Picker set_selected_people calls inside this method synchronously
            invoke on_change_callback, which invokes _on_picker_change, which
            sets self._is_dirty = True. Therefore EVERY call site of
            _fill_form_from_draft MUST set self._is_dirty = False AFTER calling
            this method, or the form will be falsely flagged dirty.
            Current call sites that observe this:
                - on_load_draft_click: sets _is_dirty = False after
                - _load_person_for_edit: sets _is_dirty = False after
                - _reset_to_add_mode: sets _is_dirty = False after its own clears
            New call sites must follow the same pattern.
        """
        person_data_wrapper = PersonDataWrapper(person_data)
        self.first_name_text_box.SetValue(person_data_wrapper.get_first_name())

        other_first_names: str = person_data_wrapper.get_other_first_names()
        if other_first_names is not None:
            self.other_first_names_text_box.SetValue(other_first_names.replace(' ', '\n'))
        else:
            self.other_first_names_text_box.SetValue('')

        self.last_name_text_box.SetValue(person_data_wrapper.get_last_name())

        other_last_names: str = person_data_wrapper.get_other_last_names()
        if other_last_names is not None:
            self.other_last_names_text_box.SetValue(other_last_names.replace(';', '\n'))
        else:
            self.other_last_names_text_box.SetValue('')

        has_maiden_name: bool | None = person_data_wrapper.get_has_maiden_name()
        self.has_maiden_name_checkbox.SetValue(has_maiden_name if has_maiden_name is not None else False)
        if has_maiden_name:
            self.maiden_name_text_box.Enable(True)
            self.other_maiden_names_text_box.Enable(True)
            self.maiden_name_text_box.SetValue(person_data_wrapper.get_maiden_name())

            other_maiden_names: str = person_data_wrapper.get_other_maiden_names()

            if other_maiden_names:
                self.other_maiden_names_text_box.SetValue(other_maiden_names.replace(';', '\n'))
            else:
                self.other_maiden_names_text_box.SetValue('')
        else:
            self.maiden_name_text_box.SetValue('')
            self.other_maiden_names_text_box.SetValue('')

        self.sex_dropdown.SetValue(person_data_wrapper.get_sex())
        self.spouses_picker.set_selected_people(person_data_wrapper.get_spouse_ids())
        self.parents_picker.set_selected_people(person_data_wrapper.get_parent_ids())
        self.children_picker.set_selected_people(person_data_wrapper.get_children_ids())
        self.siblings_picker.set_selected_people(person_data_wrapper.get_sibling_ids())

        self.notes_textbox.SetValue(person_data_wrapper.get_notes())

        birth_date = self._deconstruct_optional_date(person_data_wrapper.get_date_of_birth())
        self.birth_date_picker['day'].SetValue(birth_date[0])
        self.birth_date_picker['month'].SetValue(birth_date[1])
        self.birth_date_picker['year_century'].SetValue(birth_date[2])
        self.birth_date_picker['year_decade'].SetValue(birth_date[3])
        self.birth_date_picker['year_unit'].SetValue(birth_date[4])

        raw_death_date: bool | None = person_data_wrapper.get_date_of_death()
        self.is_dead_checkbox.SetValue(bool(raw_death_date))

        if self.is_dead_checkbox.GetValue():

            death_date = self._deconstruct_optional_date(raw_death_date)
            self.death_date_picker['day'].SetValue(death_date[0])
            self.death_date_picker['day'].Enable(True)
            self.death_date_picker['month'].SetValue(death_date[1])
            self.death_date_picker['month'].Enable(True)
            self.death_date_picker['year_century'].SetValue(death_date[2])
            self.death_date_picker['year_century'].Enable(True)
            self.death_date_picker['year_decade'].SetValue(death_date[3])
            self.death_date_picker['year_decade'].Enable(True)
            self.death_date_picker['year_unit'].SetValue(death_date[4])
            self.death_date_picker['year_unit'].Enable(True)
    
    def _deconstruct_optional_date(self, date: str | None) -> Tuple[str, str, str, str, str]:
        
        if date is None:
            return ('XX', 'XX', 'XX', 'X', 'X')
        
        optional_date = re.match(r"[X0-9]{4}-[X0-9]{2}-[X0-9]{2}", date)
        if not optional_date:
            return ('XX', 'XX', 'XX', 'X', 'X')
        
        found_strings = optional_date.group().split('-')

        day = found_strings[2]
        month = found_strings[1]
        century = found_strings[0][:2]
        decade = found_strings[0][2:3]
        year = found_strings[0][3:]

        return (day, month, century, decade, year)

    def _build_optional_date(self, date_picker: Dict[str, wx.ComboBox]) -> Optional[str]:
        # Check if ANY value was selected (not all hints)
        any_selected = any(date_picker[key].GetSelection() > 0 for key in date_picker.keys())

        if not any_selected:
            return None

        def get(key: str, default: str) -> str:
            if date_picker[key].GetSelection() > 0:
                return date_picker[key].GetStringSelection()
            return default

        year = get('year_century', 'XX') + get('year_decade', 'X') + get('year_unit', 'X')
        month = get('month', 'XX')
        day = get('day', 'XX')

        return f"{year}-{month}-{day}"


        


        


        









