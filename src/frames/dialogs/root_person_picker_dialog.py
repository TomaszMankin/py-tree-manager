"""Single-select root-person picker dialog for Drzewo.

Opens a dialog over Lista osob allowing the user to select exactly one
person as the Drzewo root person. Modeled on DraftPickerDialog but uses
a wx.ListBox with substring search filter.
"""

from typing import Dict, Optional

import wx

from src.frames.dialogs.polish_dialog import polish_dialog


class RootPersonPickerDialog(wx.Dialog):
    """Single-select picker over Lista osob; returns the chosen UUID."""

    def __init__(
        self,
        parent: wx.Window,
        all_people: Dict[str, str],
        current_root_uuid: Optional[str] = None,
    ):
        """
        Args:
            parent: Parent window.
            all_people: Dict of {uuid: full_name} for all people in Lista osob.
            current_root_uuid: UUID of the currently designated root person (pre-selected).
        """
        super().__init__(
            parent,
            title="Wybierz osobę-korzeń drzewa",
            size=(600, 500),
        )
        self.selected_uuid: Optional[str] = None
        self._uuid_for_index: Dict[int, str] = {}
        self._all_people = all_people

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Search box
        self.search_box = wx.TextCtrl(panel)
        self.search_box.SetHint("Wpisz imię lub nazwisko...")

        # Person list
        self.list_ctrl = wx.ListBox(panel, style=wx.LB_SINGLE)
        self._populate_list("")

        # Pre-select the current root person (if any)
        if current_root_uuid:
            for idx, uid in self._uuid_for_index.items():
                if uid == current_root_uuid:
                    self.list_ctrl.SetSelection(idx)
                    break

        # OK / Cancel buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, "Wybierz")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Anuluj")
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()

        sizer.Add(self.search_box, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.BOTTOM, 8)
        panel.SetSizer(sizer)

        self.search_box.Bind(wx.EVT_TEXT, self._on_search)
        self.list_ctrl.Bind(wx.EVT_LISTBOX_DCLICK, self._on_double_click)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok_click)

    def _populate_list(self, search: str) -> None:
        """Rebuild the ListBox with an optional substring filter."""
        self.list_ctrl.Clear()
        self._uuid_for_index = {}
        s = search.strip().lower()
        for uid, name in sorted(self._all_people.items(), key=lambda kv: kv[1].lower()):
            if not s or s in name.lower():
                idx = self.list_ctrl.Append(name)
                self._uuid_for_index[idx] = uid

    def _on_search(self, _event) -> None:
        self._populate_list(self.search_box.GetValue())

    def _on_ok_click(self, _event) -> None:
        idx = self.list_ctrl.GetSelection()
        if idx == wx.NOT_FOUND:
            polish_dialog(
                self,
                "Wybierz osobę z listy.",
                "Brak wyboru",
                wx.OK | wx.ICON_WARNING,
            )
            return
        self.selected_uuid = self._uuid_for_index[idx]
        self.EndModal(wx.ID_OK)

    def _on_double_click(self, _event) -> None:
        self._on_ok_click(None)

    def get_selected_uuid(self) -> Optional[str]:
        """Return the UUID of the selected person, or None if cancelled."""
        return self.selected_uuid
