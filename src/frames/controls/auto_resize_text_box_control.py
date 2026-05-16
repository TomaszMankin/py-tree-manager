import wx

class AutoResizeTextCtrl(wx.TextCtrl):
    def __init__(self, parent, font_size=14, hint="", min_lines=1, **kwargs):
        super().__init__(parent, style=wx.TE_MULTILINE, **kwargs)
        self.SetHint(hint)
        self.min_lines = min_lines

        font = self.GetFont()
        font.SetPointSize(font_size)
        self.SetFont(font)

        self.line_height = self.GetTextExtent("M")[1] + 4
        self.Bind(wx.EVT_TEXT, self.on_text_change)
        self.SetMinSize((300, self.line_height * self.min_lines))

    def set_hint(self, hint: str):
        self.SetHint(hint)

    def on_text_change(self, event):
        text = self.GetValue()
        lines = text.count('\n') + 1
        lines = max(lines, self.min_lines)
        new_height = self.line_height * lines
        self.SetMinSize((-1, new_height))
        self.GetParent().Layout()
        event.Skip()