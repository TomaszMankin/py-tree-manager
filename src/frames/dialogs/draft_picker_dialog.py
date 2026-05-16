from datetime import datetime
from pathlib import Path
from typing import Dict, List
import json

import wx

from src.frames.dialogs.polish_dialog import polish_dialog
from src.services.file_service import FileService
from src.wrappers.person_data_wrapper import PersonDataProperty, PersonDataWrapper

class DraftPickerDialog(wx.Dialog):

    def __init__(self, parent, paths: List[str]):
        super().__init__(parent, title="Wybierz zapisany szkic", size=(600, 400))

        self._file_service = FileService()
        self.selected_path = None
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list_ctrl.InsertColumn(0, "Imię i nazwisko", width=300)
        # phases.md 3.3: second column shows last-modified date, not UUID
        self.list_ctrl.InsertColumn(1, "Ostatnio zmieniony", width=270)

        self._paths: Dict[int, str] = {}
        for path in paths:
            try:
                draft_me = self._file_service.read_me_file(path)
            except (json.JSONDecodeError, Exception):
                # Corrupted draft — skip without crashing the dialog.
                # The user will see it missing from the list.
                continue
            draft_me_wrapper = PersonDataWrapper(draft_me)
            id_on_list_ctrl = self.list_ctrl.InsertItem(
                self.list_ctrl.GetItemCount(),
                draft_me_wrapper.get_full_name()
            )
            # Compute last-modified date for display
            try:
                mtime = Path(path).stat().st_mtime
                date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            except OSError:
                date_str = "—"
            self.list_ctrl.SetItem(id_on_list_ctrl, 1, date_str)
            self._paths[id_on_list_ctrl] = path

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, "Otwórz")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Anuluj")
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()

        sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        panel.SetSizer(sizer)

        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_double_click)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok_click)
        self.Maximize()
        # on_cancel_click?

    def _on_ok_click(self, event):
        id_on_list_ctrl: int = self.list_ctrl.GetFirstSelected()
        if id_on_list_ctrl == -1:
            polish_dialog(self, "Wybierz szkic osoby z listy.", "Brak wyboru", wx.OK | wx.ICON_WARNING)
            return
        self.selected_path = self._paths[id_on_list_ctrl]
        self.EndModal(wx.ID_OK)

    def _on_double_click(self, event):
        self._on_ok_click(event)

    def get_selected_path(self) -> str | None:
        return self.selected_path
