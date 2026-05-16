from typing import Dict, List
import wx

class MultiPersonPickerControl(wx.Panel):

    def __init__(self, parent, all_people: Dict[str, str], font_size=14, header_size=18, label="", on_change_callback=None, bg_color="#FFFFFF", **kwargs):
        """
        Creates a searchable multi-person picker with Add/Remove functionality.

        Returns:
            - container: The main panel containing everything
            - search_box: TextCtrl for searching
            - results_list: ListBox showing filtered results
            - selected_list: ListBox showing selected people
            - selected_people: List to track selected person UUIDs
        """
        super().__init__(parent)
        self.all_people = all_people
        self.selected_people_uuids: List[str] = []
        self.excluded_people_uuids: List[str] = []
        self.on_change_callback = on_change_callback

        # Set background color and add subtle border
        self.SetBackgroundColour(bg_color)

        # Main container panel with padding
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- SEARCH SECTION ---
        search_label = wx.StaticText(self, label=f"{label}", style=wx.ALIGN_CENTER)
        font = search_label.GetFont()
        font.SetPointSize(header_size)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        search_label.SetFont(font)

        self.search_box = wx.TextCtrl(self)
        self.search_box.SetHint("Wpisz imię lub nazwisko...")
        search_font = self.search_box.GetFont()
        search_font.SetPointSize(font_size)
        self.search_box.SetFont(search_font)

        # Results list (available people to add)
        self.results_list = wx.ListBox(self, choices=[], style=wx.LB_SINGLE)
        for key, value in self.all_people.items():
            index = self.results_list.Append(value)
            self.results_list.SetClientData(index, key)
        self.results_list.SetMinSize((-1, 120))  # Show ~6 items
        results_font = self.results_list.GetFont()
        results_font.SetPointSize(font_size)
        self.results_list.SetFont(results_font)

        # "Add" button
        self.add_button = wx.Button(self, label="Dodaj →")
        self.add_button.SetFont(search_font)

        # --- SELECTED SECTION ---

        # Selected people display (read-only list)
        self.selected_list = wx.ListBox(self, choices=[], style=wx.LB_SINGLE)
        self.selected_list.SetMinSize((-1, 100))
        self.selected_list.SetFont(results_font)

        # "Remove" button
        self.remove_button = wx.Button(self, label="← Usuń")
        self.remove_button.SetFont(search_font)

        # Bind events
        self.search_box.Bind(wx.EVT_TEXT, self.on_search)
        self.add_button.Bind(wx.EVT_BUTTON, self.on_add)
        self.remove_button.Bind(wx.EVT_BUTTON, self.on_remove)
        self.results_list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_results_double_click)
        self.selected_list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_selected_double_click)

        # --- LAYOUT ---

        # Create padded outer sizer for breathing room
        outer_sizer = wx.BoxSizer(wx.VERTICAL)

        # Search section with better spacing
        main_sizer.Add(search_label, 0, wx.BOTTOM | wx.ALIGN_CENTER | wx.TOP, 8)
        main_sizer.Add(self.search_box, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 8)
        main_sizer.Add(self.results_list, 1, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 8)
        main_sizer.Add(self.add_button, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 12)

        # Selected section
        main_sizer.Add(self.selected_list, 1, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 8)
        main_sizer.Add(self.remove_button, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        outer_sizer.Add(main_sizer, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(outer_sizer)
    
    # --- EVENT HANDLERS ---
    def set_excluded_people(self, excluded):
          """Update list of people that should be excluded from search results"""
          self.excluded_people_uuids = excluded
          self.on_search(None)  # Refresh the results list

    def on_search(self, event):
        """Filter results as user types"""
        search_term = self.search_box.GetValue().lower()

        # Exclude both selected AND externally excluded people
        all_excluded = set(self.selected_people_uuids + self.excluded_people_uuids)

        if not search_term:
            self.results_list.Set([])
            for key, value in self.all_people.items():
                if key not in all_excluded:
                    self.results_list.Append(value, key)
        else:
            self.results_list.Set([])
            for key, value in self.all_people.items():
                if search_term in value.lower() and key not in all_excluded:
                    self.results_list.Append(value, key)

    def get_selected_people(self) -> List[str]:
        """Get list of selected people UUIDs"""

        count = self.selected_list.GetCount()
        output: List[str] = []
        for i in range(count):
            output.append(self.selected_list.GetClientData(i))
        return output

    def on_add(self, event):
        """Add selected person from results to selected list"""
        selection = self.results_list.GetSelection()
        if selection == wx.NOT_FOUND:
            return  # Nothing selected

        person_name = self.results_list.GetString(selection)
        person_uuid = self.results_list.GetClientData(selection)

        # Add to selected list
        self.selected_people_uuids.append(person_uuid)
        index = self.selected_list.Append(person_name)
        self.selected_list.SetClientData(index, person_uuid)

        # Remove from available list
        self.results_list.Delete(selection)

        # Clear search to show all remaining
        self.search_box.SetValue("")
        self.on_search(None)

        if self.on_change_callback != None:
            self.on_change_callback()

    def on_remove(self, event):
        """Remove person from selected list"""
        selection = self.selected_list.GetSelection()
        if selection == wx.NOT_FOUND:
            return  # Nothing selected

        person_uuid = self.selected_list.GetClientData(selection)

        # Remove from selected list
        self.selected_people_uuids.remove(person_uuid)
        self.selected_list.Delete(selection)

        # Refresh available list to include this person again
        self.on_search(None)

        if self.on_change_callback != None:
            self.on_change_callback()

    def on_results_double_click(self, event):
        """Quick add: double-click in results list"""
        self.on_add(event)

    def on_selected_double_click(self, event):
        """Quick remove: double-click in selected list"""
        self.on_remove(event)

    def set_selected_people(self, ids: List[str]) -> None:
        self.selected_list.Clear()
        self.selected_people_uuids.clear()

        if not ids or len(ids) == 0:
            return

        for id in ids:

            if id not in self.all_people:
                raise RuntimeError(f"Person with id <{id}> has not been found in the tree.")

            self.selected_people_uuids.append(id)
            self.selected_list.Append(self.all_people[id], id)

        self.on_search(None)

        if self.on_change_callback is not None:
            self.on_change_callback()

    def reload_people(self, new_people: Dict[str, str]) -> None:
        """Replace the full available people list and refresh the results view.

        Called after a new person is added to the tree so the picker immediately
        reflects the updated list without restarting the application.

        Args:
            new_people: Dict mapping UUID -> display name for all known people.
        """
        self.all_people = new_people
        self.on_search(None)


