"""Polish-button-label dialog helper.

Provides _polish_dialog() — a thin wrapper around wx.MessageDialog that applies
Polish button labels via SetYesNoCancelLabels / SetYesNoLabels / SetOKLabel.
Falls back silently on AttributeError for old wxPython builds.

Extracted as a module so both add_person_frame.py and
draft_picker_dialog.py can share it without duplication.
"""

import wx


def polish_dialog(
    parent: wx.Window,
    message: str,
    title: str,
    style: int,
    yes_label: str = "Tak",
    no_label: str = "Nie",
    cancel_label: str = "Anuluj",
    ok_label: str = "OK",
) -> int:
    """Polish-button-label wrapper around wx.MessageDialog.

    Style hints (passed through unchanged):
        - wx.OK | wx.ICON_INFORMATION
        - wx.YES_NO | wx.ICON_QUESTION
        - wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION

    Polish labels are applied via SetYesNoCancelLabels / SetYesNoLabels /
    SetOKLabel as appropriate. Falls back silently on AttributeError (very old
    wxPython builds).

    Returns:
        int: The wx.ID_* value returned by ShowModal().
    """
    dlg = wx.MessageDialog(parent, message, title, style)
    try:
        if (style & wx.YES_NO) and (style & wx.CANCEL):
            dlg.SetYesNoCancelLabels(yes_label, no_label, cancel_label)
        elif style & wx.YES_NO:
            dlg.SetYesNoLabels(yes_label, no_label)
        elif style & wx.OK:
            dlg.SetOKLabel(ok_label)
    except AttributeError:
        pass  # Older wxPython — fall back to system labels
    result = dlg.ShowModal()
    dlg.Destroy()
    return result
